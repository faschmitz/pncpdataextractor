#!/usr/bin/env python3
"""
Storage Manager - Abstração para armazenamento em S3 ou local

Este módulo fornece uma interface unificada para salvar arquivos
tanto localmente (desenvolvimento) quanto no S3 (produção).
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import pandas as pd
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import io

class StorageManager:
    """Gerenciador de armazenamento com suporte a S3 e sistema local"""
    
    def __init__(self, use_s3: bool = None, s3_bucket: str = None):
        self.logger = logging.getLogger(__name__)
        
        # Auto-detectar se deve usar S3 baseado em variáveis de ambiente
        if use_s3 is None:
            use_s3 = bool(os.getenv('AWS_DEFAULT_REGION') or os.getenv('AWS_REGION'))
        
        self.use_s3 = use_s3
        self.s3_bucket = s3_bucket or os.getenv('S3_BUCKET', 'pncp-data-bucket')
        
        if self.use_s3:
            try:
                self.s3_client = boto3.client('s3')
                self.logger.info(f"StorageManager inicializado com S3: bucket={self.s3_bucket}")
                
                # Verificar se o bucket existe
                self._verify_bucket_access()
                
            except NoCredentialsError:
                self.logger.warning("Credenciais AWS não encontradas, usando armazenamento local")
                self.use_s3 = False
                self.s3_client = None
            except Exception as e:
                self.logger.warning(f"Erro ao inicializar S3, usando armazenamento local: {e}")
                self.use_s3 = False
                self.s3_client = None
        else:
            self.s3_client = None
            self.logger.info("StorageManager inicializado com armazenamento local")
    
    def _verify_bucket_access(self):
        """Verificar se o bucket S3 existe e é acessível"""
        try:
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
            self.logger.info(f"Acesso ao bucket S3 verificado: {self.s3_bucket}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                self.logger.error(f"Bucket S3 não encontrado: {self.s3_bucket}")
                raise ValueError(f"Bucket S3 não existe: {self.s3_bucket}")
            elif error_code == '403':
                self.logger.error(f"Sem permissão para acessar bucket S3: {self.s3_bucket}")
                raise ValueError(f"Sem permissão para bucket S3: {self.s3_bucket}")
            else:
                raise
    
    def save_parquet(self, df: pd.DataFrame, file_path: str) -> bool:
        """
        Salva DataFrame como arquivo Parquet
        
        Args:
            df: DataFrame para salvar
            file_path: Caminho do arquivo (relativo para S3, absoluto para local)
            
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        try:
            if self.use_s3:
                return self._save_parquet_s3(df, file_path)
            else:
                return self._save_parquet_local(df, file_path)
        except Exception as e:
            self.logger.error(f"Erro ao salvar parquet {file_path}: {e}")
            return False
    
    def _save_parquet_s3(self, df: pd.DataFrame, s3_key: str) -> bool:
        """Salva DataFrame no S3 como Parquet"""
        try:
            # Converter DataFrame para bytes usando buffer em memória
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False, engine='pyarrow')
            parquet_buffer.seek(0)
            
            # Upload para S3
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=parquet_buffer.getvalue(),
                ContentType='application/octet-stream',
                Metadata={
                    'records': str(len(df)),
                    'created_at': datetime.utcnow().isoformat(),
                    'source': 'pncp-extractor'
                }
            )
            
            self.logger.info(f"Arquivo Parquet salvo no S3: s3://{self.s3_bucket}/{s3_key} ({len(df)} registros)")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar no S3: {e}")
            return False
    
    def _save_parquet_local(self, df: pd.DataFrame, file_path: str) -> bool:
        """Salva DataFrame localmente como Parquet"""
        try:
            # Garantir que o diretório existe
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Salvar arquivo
            df.to_parquet(file_path, index=False, engine='pyarrow')
            
            self.logger.info(f"Arquivo Parquet salvo localmente: {file_path} ({len(df)} registros)")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar localmente: {e}")
            return False
    
    def read_parquet(self, file_path: str) -> pd.DataFrame:
        """Lê arquivo Parquet do S3 ou local"""
        try:
            if self.use_s3:
                return self._read_parquet_s3(file_path)
            else:
                return self._read_parquet_local(file_path)
        except Exception as e:
            self.logger.error(f"Erro ao ler parquet {file_path}: {e}")
            return None
    
    def _read_parquet_s3(self, s3_key: str) -> pd.DataFrame:
        """Lê DataFrame do S3"""
        try:
            # Download do S3 para buffer em memória
            obj = self.s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
            parquet_buffer = io.BytesIO(obj['Body'].read())
            
            # Ler DataFrame do buffer
            df = pd.read_parquet(parquet_buffer, engine='pyarrow')
            
            self.logger.debug(f"Arquivo Parquet lido do S3: s3://{self.s3_bucket}/{s3_key} ({len(df)} registros)")
            return df
            
        except Exception as e:
            self.logger.error(f"Erro ao ler do S3: {e}")
            return None
    
    def _read_parquet_local(self, file_path: str) -> pd.DataFrame:
        """Lê DataFrame local"""
        try:
            df = pd.read_parquet(file_path, engine='pyarrow')
            self.logger.debug(f"Arquivo Parquet lido: {file_path} ({len(df)} registros)")
            return df
        except Exception as e:
            self.logger.error(f"Erro ao ler arquivo local: {e}")
            return None
    
    def save_json(self, data: Dict[Any, Any], file_path: str) -> bool:
        """
        Salva dados como arquivo JSON
        
        Args:
            data: Dados para salvar
            file_path: Caminho do arquivo
            
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        try:
            if self.use_s3:
                return self._save_json_s3(data, file_path)
            else:
                return self._save_json_local(data, file_path)
        except Exception as e:
            self.logger.error(f"Erro ao salvar JSON {file_path}: {e}")
            return False
    
    def _save_json_s3(self, data: Dict[Any, Any], s3_key: str) -> bool:
        """Salva JSON no S3"""
        try:
            json_str = json.dumps(data, indent=2, default=str, ensure_ascii=False)
            
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=json_str.encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'created_at': datetime.utcnow().isoformat(),
                    'source': 'pncp-extractor'
                }
            )
            
            self.logger.info(f"JSON salvo no S3: s3://{self.s3_bucket}/{s3_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar JSON no S3: {e}")
            return False
    
    def _save_json_local(self, data: Dict[Any, Any], file_path: str) -> bool:
        """Salva JSON localmente"""
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
            
            self.logger.info(f"JSON salvo localmente: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar JSON localmente: {e}")
            return False
    
    def load_json(self, file_path: str) -> Optional[Dict[Any, Any]]:
        """
        Carrega dados de arquivo JSON
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Dados carregados ou None se erro
        """
        try:
            if self.use_s3:
                return self._load_json_s3(file_path)
            else:
                return self._load_json_local(file_path)
        except Exception as e:
            self.logger.error(f"Erro ao carregar JSON {file_path}: {e}")
            return None
    
    def _load_json_s3(self, s3_key: str) -> Optional[Dict[Any, Any]]:
        """Carrega JSON do S3"""
        try:
            response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
            json_str = response['Body'].read().decode('utf-8')
            return json.loads(json_str)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                self.logger.warning(f"Arquivo JSON não encontrado no S3: {s3_key}")
            else:
                self.logger.error(f"Erro ao carregar JSON do S3: {e}")
            return None
    
    def _load_json_local(self, file_path: str) -> Optional[Dict[Any, Any]]:
        """Carrega JSON localmente"""
        try:
            if not Path(file_path).exists():
                self.logger.warning(f"Arquivo JSON não encontrado: {file_path}")
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.error(f"Erro ao carregar JSON localmente: {e}")
            return None
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Retorna informações sobre a configuração de armazenamento"""
        return {
            'use_s3': self.use_s3,
            's3_bucket': self.s3_bucket if self.use_s3 else None,
            'storage_type': 'S3' if self.use_s3 else 'Local'
        }