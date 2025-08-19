#!/usr/bin/env python3
"""
AWS Configuration Manager para PNCP Data Extractor

Este módulo gerencia a configuração AWS, incluindo:
- Recuperação de secrets do AWS Secrets Manager
- Configuração de variáveis de ambiente
- Validação de credenciais AWS
"""

import os
import json
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, Optional, Any

class AWSConfigManager:
    """Gerenciador de configuração AWS"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.secrets_client = None
        self.region = self._get_aws_region()
        
        # Tentar inicializar cliente de secrets
        try:
            self.secrets_client = boto3.client('secretsmanager', region_name=self.region)
            self.logger.info(f"AWS Secrets Manager inicializado na região: {self.region}")
        except Exception as e:
            self.logger.warning(f"Erro ao inicializar Secrets Manager: {e}")
    
    def _get_aws_region(self) -> str:
        """Determina a região AWS a partir das variáveis de ambiente ou metadados"""
        # Ordem de precedência: AWS_DEFAULT_REGION, AWS_REGION, us-east-1 (padrão)
        region = os.getenv('AWS_DEFAULT_REGION') or os.getenv('AWS_REGION')
        
        if not region:
            # Tentar obter região dos metadados EC2/ECS se disponível
            try:
                import requests
                response = requests.get(
                    'http://169.254.169.254/latest/meta-data/placement/availability-zone',
                    timeout=2
                )
                if response.status_code == 200:
                    region = response.text[:-1]  # Remove último caractere (zona)
                    self.logger.info(f"Região detectada dos metadados: {region}")
            except:
                pass
        
        # Usar us-east-1 como padrão
        if not region:
            region = 'us-east-1'
            self.logger.info(f"Usando região padrão: {region}")
        
        return region
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Recupera um secret do AWS Secrets Manager
        
        Args:
            secret_name: Nome do secret
            
        Returns:
            Valor do secret ou None se não encontrado
        """
        if not self.secrets_client:
            self.logger.warning("Secrets Manager não disponível")
            return None
            
        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            
            # Secrets podem ser string simples ou JSON
            secret_value = response['SecretString']
            try:
                # Tentar parsear como JSON
                secret_json = json.loads(secret_value)
                # Se for JSON, retornar a primeira chave encontrada
                if isinstance(secret_json, dict):
                    return list(secret_json.values())[0]
            except json.JSONDecodeError:
                # Se não for JSON, retornar string diretamente
                pass
                
            return secret_value
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                self.logger.warning(f"Secret não encontrado: {secret_name}")
            elif error_code == 'AccessDeniedException':
                self.logger.error(f"Sem permissão para acessar secret: {secret_name}")
            else:
                self.logger.error(f"Erro ao recuperar secret {secret_name}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Erro inesperado ao recuperar secret {secret_name}: {e}")
            return None
    
    def setup_environment_variables(self) -> Dict[str, Any]:
        """
        Configura variáveis de ambiente necessárias para a aplicação
        
        Returns:
            Dicionário com status da configuração
        """
        config_status = {
            'aws_region': self.region,
            'secrets_manager_available': self.secrets_client is not None,
            'environment_variables': {},
            'errors': []
        }
        
        # Lista de variáveis necessárias e seus secrets correspondentes
        required_vars = {
            'OPENAI_API_KEY': 'pncp/openai-api-key',
            'S3_BUCKET': None,  # Deve ser definida via variável de ambiente
        }
        
        for env_var, secret_name in required_vars.items():
            current_value = os.getenv(env_var)
            
            if current_value:
                # Variável já definida
                config_status['environment_variables'][env_var] = 'SET'
                self.logger.info(f"{env_var} já configurada")
            elif secret_name:
                # Tentar recuperar do Secrets Manager
                secret_value = self.get_secret(secret_name)
                if secret_value:
                    os.environ[env_var] = secret_value
                    config_status['environment_variables'][env_var] = 'SET_FROM_SECRET'
                    self.logger.info(f"{env_var} configurada a partir do Secrets Manager")
                else:
                    config_status['environment_variables'][env_var] = 'MISSING'
                    config_status['errors'].append(f"{env_var} não encontrada")
                    self.logger.error(f"{env_var} não pôde ser configurada")
            else:
                # Variável obrigatória não definida
                config_status['environment_variables'][env_var] = 'MISSING'
                config_status['errors'].append(f"{env_var} não definida")
                self.logger.error(f"{env_var} é obrigatória mas não foi definida")
        
        # Configurar outras variáveis AWS se não estiverem definidas
        if not os.getenv('AWS_DEFAULT_REGION'):
            os.environ['AWS_DEFAULT_REGION'] = self.region
            config_status['environment_variables']['AWS_DEFAULT_REGION'] = 'SET_DEFAULT'
        
        # Configurar bucket S3 padrão se não estiver definido
        if not os.getenv('S3_BUCKET'):
            default_bucket = 'pncp-data-bucket'
            os.environ['S3_BUCKET'] = default_bucket
            config_status['environment_variables']['S3_BUCKET'] = 'SET_DEFAULT'
            self.logger.info(f"S3_BUCKET definido como padrão: {default_bucket}")
        
        return config_status
    
    def validate_aws_credentials(self) -> bool:
        """
        Valida se as credenciais AWS estão funcionando
        
        Returns:
            True se as credenciais são válidas, False caso contrário
        """
        try:
            # Tentar fazer uma chamada simples para verificar credenciais
            sts_client = boto3.client('sts', region_name=self.region)
            response = sts_client.get_caller_identity()
            
            account = response.get('Account', 'N/A')
            arn = response.get('Arn', 'N/A')
            
            self.logger.info(f"Credenciais AWS válidas - Conta: {account}, ARN: {arn}")
            return True
            
        except NoCredentialsError:
            self.logger.error("Credenciais AWS não encontradas")
            return False
        except ClientError as e:
            self.logger.error(f"Erro de credenciais AWS: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Erro inesperado validando credenciais: {e}")
            return False
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Retorna um resumo da configuração atual
        
        Returns:
            Dicionário com informações de configuração
        """
        config_status = self.setup_environment_variables()
        credentials_valid = self.validate_aws_credentials()
        
        return {
            'aws_region': self.region,
            'credentials_valid': credentials_valid,
            'secrets_manager_available': config_status['secrets_manager_available'],
            'environment_variables': config_status['environment_variables'],
            'errors': config_status['errors'],
            'ready_for_production': credentials_valid and len(config_status['errors']) == 0
        }

def setup_aws_environment() -> Dict[str, Any]:
    """
    Função utilitária para configurar o ambiente AWS
    
    Returns:
        Status da configuração
    """
    aws_config = AWSConfigManager()
    return aws_config.get_configuration_summary()

if __name__ == "__main__":
    # Configurar logging para execução standalone
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configurar ambiente e mostrar status
    status = setup_aws_environment()
    
    print("=== Configuração AWS ===")
    print(f"Região: {status['aws_region']}")
    print(f"Credenciais válidas: {status['credentials_valid']}")
    print(f"Secrets Manager disponível: {status['secrets_manager_available']}")
    print(f"Pronto para produção: {status['ready_for_production']}")
    
    print("\nVariáveis de ambiente:")
    for var, status_val in status['environment_variables'].items():
        print(f"  {var}: {status_val}")
    
    if status['errors']:
        print(f"\nErros encontrados:")
        for error in status['errors']:
            print(f"  - {error}")