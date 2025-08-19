"""
Testes unitários para AwsConfig
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aws_config import AwsConfig

class TestAwsConfig:
    
    def test_init_without_aws_credentials(self):
        """Testa inicialização sem credenciais AWS"""
        with patch.dict(os.environ, {}, clear=True):
            config = AwsConfig()
            assert config.is_aws_environment() == False
            assert config.secrets_client is None
    
    @patch('boto3.client')
    def test_init_with_aws_credentials(self, mock_boto3):
        """Testa inicialização com credenciais AWS"""
        mock_secrets = Mock()
        mock_boto3.return_value = mock_secrets
        
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}):
            config = AwsConfig()
            
            assert config.is_aws_environment() == True
            assert config.region == 'us-east-1'
            assert config.secrets_client == mock_secrets
            mock_boto3.assert_called_once_with('secretsmanager', region_name='us-east-1')
    
    def test_is_aws_environment_with_region(self):
        """Testa detecção de ambiente AWS com AWS_DEFAULT_REGION"""
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-west-2'}, clear=True):
            config = AwsConfig()
            assert config.is_aws_environment() == True
            assert config.region == 'us-west-2'
    
    def test_is_aws_environment_with_aws_region(self):
        """Testa detecção de ambiente AWS com AWS_REGION"""
        with patch.dict(os.environ, {'AWS_REGION': 'eu-west-1'}, clear=True):
            config = AwsConfig()
            assert config.is_aws_environment() == True
            assert config.region == 'eu-west-1'
    
    def test_is_aws_environment_precedence(self):
        """Testa precedência entre AWS_DEFAULT_REGION e AWS_REGION"""
        with patch.dict(os.environ, {
            'AWS_DEFAULT_REGION': 'us-east-1',
            'AWS_REGION': 'us-west-2'
        }, clear=True):
            config = AwsConfig()
            # AWS_DEFAULT_REGION tem precedência
            assert config.region == 'us-east-1'
    
    @patch('boto3.client')
    def test_get_secret_success(self, mock_boto3):
        """Testa recuperação de secret com sucesso"""
        mock_secrets = Mock()
        mock_secrets.get_secret_value.return_value = {
            'SecretString': 'test-secret-value'
        }
        mock_boto3.return_value = mock_secrets
        
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}):
            config = AwsConfig()
            result = config.get_secret('test-secret-name')
            
            assert result == 'test-secret-value'
            mock_secrets.get_secret_value.assert_called_once_with(
                SecretId='test-secret-name'
            )
    
    @patch('boto3.client')
    def test_get_secret_not_found(self, mock_boto3):
        """Testa recuperação de secret não encontrado"""
        from botocore.exceptions import ClientError
        
        mock_secrets = Mock()
        mock_secrets.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}},
            'GetSecretValue'
        )
        mock_boto3.return_value = mock_secrets
        
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}):
            config = AwsConfig()
            result = config.get_secret('non-existent-secret')
            
            assert result is None
    
    @patch('boto3.client')
    def test_get_secret_access_denied(self, mock_boto3):
        """Testa recuperação de secret com acesso negado"""
        from botocore.exceptions import ClientError
        
        mock_secrets = Mock()
        mock_secrets.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException'}},
            'GetSecretValue'
        )
        mock_boto3.return_value = mock_secrets
        
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}):
            config = AwsConfig()
            
            with pytest.raises(Exception, match="Erro ao recuperar secret"):
                config.get_secret('access-denied-secret')
    
    @patch('boto3.client')
    def test_setup_openai_api_key_from_secret(self, mock_boto3):
        """Testa configuração da API key OpenAI a partir do secret"""
        mock_secrets = Mock()
        mock_secrets.get_secret_value.return_value = {
            'SecretString': '{"api_key": "sk-test123456789"}'
        }
        mock_boto3.return_value = mock_secrets
        
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}, clear=True):
            config = AwsConfig()
            config.setup_openai_api_key()
            
            # Verificar se variável de ambiente foi definida
            assert os.environ.get('OPENAI_API_KEY') == 'sk-test123456789'
    
    @patch('boto3.client')
    def test_setup_openai_api_key_json_parse_error(self, mock_boto3):
        """Testa erro na parsing do JSON do secret"""
        mock_secrets = Mock()
        mock_secrets.get_secret_value.return_value = {
            'SecretString': 'invalid-json'
        }
        mock_boto3.return_value = mock_secrets
        
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}, clear=True):
            config = AwsConfig()
            
            # Deve usar o valor diretamente se não for JSON válido
            config.setup_openai_api_key()
            assert os.environ.get('OPENAI_API_KEY') == 'invalid-json'
    
    def test_setup_openai_api_key_local_mode(self):
        """Testa configuração da API key em modo local"""
        with patch.dict(os.environ, {}, clear=True):
            config = AwsConfig()
            config.setup_openai_api_key()
            
            # Em modo local, não deve fazer nada
            assert 'OPENAI_API_KEY' not in os.environ
    
    @patch('boto3.client')
    def test_validate_aws_credentials_success(self, mock_boto3):
        """Testa validação de credenciais AWS com sucesso"""
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {
            'Account': '123456789012',
            'UserId': 'test-user',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/test-role'
        }
        
        with patch('boto3.client') as mock_client:
            mock_client.return_value = mock_sts
            
            with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}):
                config = AwsConfig()
                identity = config.validate_aws_credentials()
                
                assert identity['Account'] == '123456789012'
                mock_sts.get_caller_identity.assert_called_once()
    
    @patch('boto3.client')
    def test_validate_aws_credentials_failure(self, mock_boto3):
        """Testa validação de credenciais AWS com falha"""
        from botocore.exceptions import ClientError
        
        mock_sts = Mock()
        mock_sts.get_caller_identity.side_effect = ClientError(
            {'Error': {'Code': 'InvalidUserID.NotFound'}},
            'GetCallerIdentity'
        )
        
        with patch('boto3.client') as mock_client:
            mock_client.return_value = mock_sts
            
            with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}):
                config = AwsConfig()
                
                with pytest.raises(Exception, match="Credenciais AWS inválidas"):
                    config.validate_aws_credentials()
    
    def test_validate_aws_credentials_local_mode(self):
        """Testa validação de credenciais em modo local"""
        with patch.dict(os.environ, {}, clear=True):
            config = AwsConfig()
            
            with pytest.raises(Exception, match="Ambiente AWS não configurado"):
                config.validate_aws_credentials()
    
    @patch('boto3.client')
    def test_get_s3_bucket_name_from_env(self, mock_boto3):
        """Testa obtenção do nome do bucket S3 da variável de ambiente"""
        with patch.dict(os.environ, {
            'AWS_DEFAULT_REGION': 'us-east-1',
            'S3_BUCKET': 'test-bucket-name'
        }):
            config = AwsConfig()
            bucket_name = config.get_s3_bucket_name()
            
            assert bucket_name == 'test-bucket-name'
    
    @patch('boto3.client')
    def test_get_s3_bucket_name_default(self, mock_boto3):
        """Testa obtenção do nome padrão do bucket S3"""
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}, clear=True):
            config = AwsConfig()
            bucket_name = config.get_s3_bucket_name()
            
            assert bucket_name == 'pncp-extractor-data-prod'
    
    def test_get_environment_prod(self):
        """Testa detecção de ambiente de produção"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'prod'}, clear=True):
            config = AwsConfig()
            assert config.get_environment() == 'prod'
    
    def test_get_environment_default(self):
        """Testa ambiente padrão"""
        with patch.dict(os.environ, {}, clear=True):
            config = AwsConfig()
            assert config.get_environment() == 'prod'
    
    @patch('boto3.client')
    def test_setup_environment_variables(self, mock_boto3):
        """Testa configuração de variáveis de ambiente"""
        mock_secrets = Mock()
        mock_secrets.get_secret_value.return_value = {
            'SecretString': '{"api_key": "sk-test123"}'
        }
        mock_boto3.return_value = mock_secrets
        
        with patch.dict(os.environ, {
            'AWS_DEFAULT_REGION': 'us-east-1',
            'S3_BUCKET': 'custom-bucket'
        }, clear=True):
            config = AwsConfig()
            status = config.setup_environment_variables()
            
            assert status['aws_configured'] == True
            assert status['openai_configured'] == True
            assert status['s3_bucket'] == 'custom-bucket'
            assert status['region'] == 'us-east-1'
            assert status['environment'] == 'prod'
            
            # Verificar se variáveis foram definidas
            assert os.environ.get('OPENAI_API_KEY') == 'sk-test123'
    
    def test_setup_environment_variables_local(self):
        """Testa configuração de variáveis em modo local"""
        with patch.dict(os.environ, {}, clear=True):
            config = AwsConfig()
            status = config.setup_environment_variables()
            
            assert status['aws_configured'] == False
            assert status['openai_configured'] == False
            assert status['s3_bucket'] is None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])