"""
Testes unitários para StorageManager
"""

import pytest
import pandas as pd
import os
import tempfile
import shutil
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage_manager import StorageManager

class TestStorageManager:
    
    @pytest.fixture
    def temp_dir(self):
        """Criar diretório temporário para testes"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_data(self):
        """Dados de amostra para testes"""
        return pd.DataFrame({
            'numero_contrato': ['001/2024', '002/2024', '003/2024'],
            'objeto': ['Teste 1', 'Teste 2', 'Teste 3'],
            'valor': [10000.0, 20000.0, 30000.0],
            'data_assinatura': ['2024-01-15', '2024-01-16', '2024-01-17']
        })
    
    def test_init_local_mode(self):
        """Testa inicialização em modo local"""
        with patch.dict(os.environ, {}, clear=True):
            storage = StorageManager()
            assert storage.use_s3 == False
            assert storage.s3_client is None
            assert storage.s3_bucket is None
    
    def test_init_aws_mode(self):
        """Testa inicialização em modo AWS"""
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}):
            with patch('boto3.client') as mock_boto3:
                mock_s3 = Mock()
                mock_boto3.return_value = mock_s3
                
                storage = StorageManager(s3_bucket='test-bucket')
                
                assert storage.use_s3 == True
                assert storage.s3_client == mock_s3
                assert storage.s3_bucket == 'test-bucket'
                mock_boto3.assert_called_once_with('s3')
    
    def test_init_explicit_local(self):
        """Testa inicialização explicitamente local"""
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}):
            storage = StorageManager(use_s3=False)
            assert storage.use_s3 == False
    
    def test_save_to_parquet_local(self, sample_data, temp_dir):
        """Testa salvamento de parquet em modo local"""
        storage = StorageManager(use_s3=False)
        
        # Mudar diretório de trabalho para temp
        with patch('os.getcwd', return_value=temp_dir):
            test_date = datetime(2024, 1, 15)
            file_path = storage.save_to_parquet(sample_data, test_date)
            
            # Verificar se arquivo foi criado
            assert os.path.exists(file_path)
            assert 'pncp_contratos_20240115.parquet' in file_path
            
            # Verificar conteúdo
            df_loaded = pd.read_parquet(file_path)
            pd.testing.assert_frame_equal(df_loaded, sample_data)
    
    @patch('boto3.client')
    def test_save_to_parquet_s3(self, mock_boto3, sample_data):
        """Testa salvamento de parquet no S3"""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}):
            storage = StorageManager(s3_bucket='test-bucket')
            
            test_date = datetime(2024, 1, 15)
            file_path = storage.save_to_parquet(sample_data, test_date)
            
            # Verificar se tentou fazer upload para S3
            mock_s3.upload_file.assert_called_once()
            
            # Verificar path S3
            expected_s3_path = 'raw-data/year=2024/month=01/pncp_contratos_20240115.parquet'
            assert expected_s3_path in file_path
    
    def test_save_consolidated_local(self, sample_data, temp_dir):
        """Testa salvamento de dados consolidados em modo local"""
        storage = StorageManager(use_s3=False)
        
        with patch('os.getcwd', return_value=temp_dir):
            test_date = datetime(2024, 1, 15)
            file_path = storage.save_consolidated(sample_data, test_date)
            
            assert os.path.exists(file_path)
            assert 'pncp_consolidado_20240115.parquet' in file_path
            
            # Verificar conteúdo
            df_loaded = pd.read_parquet(file_path)
            pd.testing.assert_frame_equal(df_loaded, sample_data)
    
    @patch('boto3.client')
    def test_save_consolidated_s3(self, mock_boto3, sample_data):
        """Testa salvamento de dados consolidados no S3"""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}):
            storage = StorageManager(s3_bucket='test-bucket')
            
            test_date = datetime(2024, 1, 15)
            file_path = storage.save_consolidated(sample_data, test_date)
            
            mock_s3.upload_file.assert_called_once()
            expected_s3_path = 'consolidated/year=2024/month=01/pncp_consolidado_20240115.parquet'
            assert expected_s3_path in file_path
    
    def test_save_logs_json_local(self, temp_dir):
        """Testa salvamento de logs JSON em modo local"""
        storage = StorageManager(use_s3=False)
        
        test_logs = {
            'timestamp': '2024-01-15T10:00:00',
            'records_processed': 100,
            'records_filtered': 25,
            'execution_time': 120.5
        }
        
        with patch('os.getcwd', return_value=temp_dir):
            test_date = datetime(2024, 1, 15)
            file_path = storage.save_logs_json(test_logs, test_date)
            
            assert os.path.exists(file_path)
            assert 'pncp_logs_20240115.json' in file_path
            
            # Verificar conteúdo
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                logs_loaded = json.load(f)
            assert logs_loaded == test_logs
    
    @patch('boto3.client')
    def test_save_logs_json_s3(self, mock_boto3):
        """Testa salvamento de logs JSON no S3"""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        test_logs = {'test': 'data'}
        
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}):
            storage = StorageManager(s3_bucket='test-bucket')
            
            test_date = datetime(2024, 1, 15)
            file_path = storage.save_logs_json(test_logs, test_date)
            
            mock_s3.upload_file.assert_called_once()
            expected_s3_path = 'logs/year=2024/month=01/pncp_logs_20240115.json'
            assert expected_s3_path in file_path
    
    def test_generate_local_path(self):
        """Testa geração de path local"""
        storage = StorageManager(use_s3=False)
        test_date = datetime(2024, 1, 15)
        
        path = storage._generate_local_path('test', test_date, '.txt')
        
        expected = 'data/year=2024/month=01/test_20240115.txt'
        assert path == expected
    
    def test_generate_s3_key(self):
        """Testa geração de chave S3"""
        storage = StorageManager(use_s3=True)
        test_date = datetime(2024, 1, 15)
        
        key = storage._generate_s3_key('prefix', 'test', test_date, '.txt')
        
        expected = 'prefix/year=2024/month=01/test_20240115.txt'
        assert key == expected
    
    def test_ensure_local_dir_exists(self, temp_dir):
        """Testa criação de diretórios locais"""
        storage = StorageManager(use_s3=False)
        
        test_dir = os.path.join(temp_dir, 'test', 'subdir')
        storage._ensure_local_dir_exists(test_dir)
        
        assert os.path.exists(test_dir)
        assert os.path.isdir(test_dir)
    
    @patch('boto3.client')
    def test_s3_upload_error_handling(self, mock_boto3, sample_data):
        """Testa tratamento de erros no upload S3"""
        mock_s3 = Mock()
        mock_s3.upload_file.side_effect = Exception("S3 upload failed")
        mock_boto3.return_value = mock_s3
        
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}):
            storage = StorageManager(s3_bucket='test-bucket')
            
            with pytest.raises(Exception, match="S3 upload failed"):
                test_date = datetime(2024, 1, 15)
                storage.save_to_parquet(sample_data, test_date)
    
    def test_empty_dataframe(self):
        """Testa comportamento com DataFrame vazio"""
        storage = StorageManager(use_s3=False)
        empty_df = pd.DataFrame()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('os.getcwd', return_value=temp_dir):
                test_date = datetime(2024, 1, 15)
                file_path = storage.save_to_parquet(empty_df, test_date)
                
                # Deve criar arquivo mesmo com DataFrame vazio
                assert os.path.exists(file_path)
                df_loaded = pd.read_parquet(file_path)
                assert len(df_loaded) == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])