#!/usr/bin/env python3
"""
Script para normalizar schemas dos arquivos parquet existentes no S3
Corrige inconsistências que causam HIVE_CANNOT_OPEN_SPLIT
"""

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from io import BytesIO
import sys
from typing import Dict, Any, List
import tempfile
import os

class ParquetSchemaNormalizer:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket = 'pncp-extractor-data-prod-566387937580'
        self.prefix = 'raw-data/year=2025/month=08/'
        
        # Schema consistente para campos estruturados
        self.consistent_schema = self._create_consistent_schema()

    def _create_consistent_schema(self):
        """Define schema consistente baseado na análise dos dados"""
        return pa.schema([
            # Campos básicos (mantidos como estão)
            ('numeroControlePNCP', pa.string()),
            ('numeroCompra', pa.string()),
            ('objetoCompra', pa.string()),
            ('valorTotalEstimado', pa.float64()),
            ('valorTotalHomologado', pa.float64()),
            ('modalidadeId', pa.int64()),
            ('modalidadeNome', pa.string()),
            ('situacaoCompraId', pa.int64()),
            ('situacaoCompraNome', pa.string()),
            ('modoDisputaId', pa.int64()),
            ('modoDisputaNome', pa.string()),
            ('dataAberturaProposta', pa.string()),
            ('dataEncerramentoProposta', pa.string()),
            ('dataPublicacaoPncp', pa.string()),
            ('linkSistemaOrigem', pa.string()),
            ('linkProcessoEletronico', pa.string()),
            ('processo', pa.string()),
            ('sequencialCompra', pa.int64()),
            ('anoCompra', pa.int64()),
            ('srp', pa.bool_()),
            ('tipoInstrumentoConvocatorioCodigo', pa.int64()),
            ('tipoInstrumentoConvocatorioNome', pa.string()),
            ('informacaoComplementar', pa.string()),
            ('justificativaPresencial', pa.string()),
            
            # Campos estruturados COM SCHEMA CONSISTENTE
            ('unidadeOrgao', pa.struct([
                ('codigoIbge', pa.string()),
                ('codigoUnidade', pa.string()),
                ('municipioNome', pa.string()),
                ('nomeUnidade', pa.string()),
                ('ufNome', pa.string()),
                ('ufSigla', pa.string())
            ])),
            ('orgaoEntidade', pa.struct([
                ('cnpj', pa.string()),
                ('esferaId', pa.string()),
                ('poderId', pa.string()),
                ('razaoSocial', pa.string())
            ])),
            ('unidadeSubRogada', pa.struct([
                ('codigoIbge', pa.string()),
                ('codigoUnidade', pa.string()),
                ('municipioNome', pa.string()),
                ('nomeUnidade', pa.string()),
                ('ufNome', pa.string()),
                ('ufSigla', pa.string())
            ])),
            ('orgaoSubRogado', pa.struct([
                ('cnpj', pa.string()),
                ('esferaId', pa.string()),
                ('poderId', pa.string()),
                ('razaoSocial', pa.string())
            ])),
            ('amparoLegal', pa.struct([
                ('codigo', pa.int64()),
                ('descricao', pa.string()),
                ('nome', pa.string())
            ])),
            
            # Array de fontes orçamentárias
            ('fontesOrcamentarias', pa.list_(pa.struct([
                ('codigo', pa.int64()),
                ('dataInclusao', pa.string()),
                ('descricao', pa.string()),
                ('nome', pa.string())
            ]))),
            
            # Campos de filtro
            ('filtro_aplicado', pa.bool_()),
            ('filtro_motivo', pa.string()),
            ('filtro_grupo_matched', pa.string()),
            ('filtro_termo_matched', pa.string()),
            ('filtro_criterio', pa.string()),
            
            # Campos de domínio
            ('modalidade_nome_dominio', pa.string()),
            ('modalidade_descricao_dominio', pa.string()),
            ('situacao_compra_nome_dominio', pa.string()),
            ('modo_disputa_nome_dominio', pa.string()),
            ('esfera_nome_dominio', pa.string()),
            ('poder_nome_dominio', pa.string()),
            
            # Metadados
            ('dataInclusao', pa.string()),
            ('dataAtualizacao', pa.string()),
            ('dataAtualizacaoGlobal', pa.string()),
            ('usuarioNome', pa.string()),
            ('extraction_date', pa.string()),
            ('data_publicacao', pa.string())
        ])

    def normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza um registro para garantir schema consistente"""
        normalized = record.copy()
        
        # Schemas padrão para campos nested
        default_unidade = {
            'codigoIbge': None,
            'codigoUnidade': None, 
            'municipioNome': None,
            'nomeUnidade': None,
            'ufNome': None,
            'ufSigla': None
        }
        
        default_orgao = {
            'cnpj': None,
            'esferaId': None,
            'poderId': None,
            'razaoSocial': None
        }
        
        default_amparo = {
            'codigo': None,
            'descricao': None,
            'nome': None
        }
        
        # Normalizar cada campo estruturado
        for field_name, default_schema in [
            ('unidadeOrgao', default_unidade),
            ('unidadeSubRogada', default_unidade),
            ('orgaoEntidade', default_orgao),
            ('orgaoSubRogado', default_orgao),
            ('amparoLegal', default_amparo)
        ]:
            if field_name in normalized:
                if normalized[field_name] is None or pd.isna(normalized[field_name]):
                    normalized[field_name] = default_schema.copy()
                elif isinstance(normalized[field_name], dict):
                    # Garantir que todos os campos existem
                    for key, default_val in default_schema.items():
                        if key not in normalized[field_name]:
                            normalized[field_name][key] = default_val
                else:
                    # Se não é dict nem None, usar padrão
                    normalized[field_name] = default_schema.copy()
            else:
                normalized[field_name] = default_schema.copy()
        
        # Normalizar fontesOrcamentarias
        if 'fontesOrcamentarias' in normalized:
            if normalized['fontesOrcamentarias'] is None:
                normalized['fontesOrcamentarias'] = []
            elif not isinstance(normalized['fontesOrcamentarias'], list):
                normalized['fontesOrcamentarias'] = []
        else:
            normalized['fontesOrcamentarias'] = []
        
        return normalized

    def process_parquet_file(self, key: str) -> bool:
        """Processa um arquivo parquet específico"""
        try:
            print(f"  Processando {key}...")
            
            # Download do arquivo
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            parquet_data = response['Body'].read()
            
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp_file:
                tmp_file.write(parquet_data)
                tmp_path = tmp_file.name
            
            try:
                # Ler com pandas
                df = pd.read_parquet(tmp_path)
                
                if len(df) == 0:
                    print(f"    ⚠️  Arquivo vazio: {key}")
                    return True
                
                print(f"    📊 {len(df)} registros encontrados")
                
                # Normalizar todos os registros
                records = df.to_dict('records')
                normalized_records = []
                
                for i, record in enumerate(records):
                    try:
                        normalized_record = self.normalize_record(record)
                        normalized_records.append(normalized_record)
                    except Exception as e:
                        print(f"    ⚠️  Erro no registro {i}: {e}")
                        # Usar registro original como fallback
                        normalized_records.append(record)
                
                # Criar DataFrame normalizado
                normalized_df = pd.DataFrame(normalized_records)
                
                # Converter para Arrow Table com schema consistente
                # Primeiro, vamos usar apenas as colunas que existem no schema
                available_columns = []
                for field in self.consistent_schema:
                    if field.name in normalized_df.columns:
                        available_columns.append(field.name)
                
                # Criar schema apenas com colunas disponíveis
                available_schema_fields = [
                    field for field in self.consistent_schema 
                    if field.name in available_columns
                ]
                available_schema = pa.schema(available_schema_fields)
                
                # Selecionar apenas colunas disponíveis
                df_subset = normalized_df[available_columns]
                
                # Converter para PyArrow Table
                table = pa.Table.from_pandas(df_subset, schema=available_schema)
                
                # Salvar normalizado
                output_buffer = BytesIO()
                pq.write_table(table, output_buffer)
                output_buffer.seek(0)
                
                # Upload de volta para S3
                self.s3_client.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=output_buffer.getvalue(),
                    ContentType='application/octet-stream'
                )
                
                print(f"    ✅ Normalizado: {len(normalized_records)} registros")
                return True
                
            finally:
                # Limpar arquivo temporário
                os.unlink(tmp_path)
                
        except Exception as e:
            print(f"    ❌ Erro: {e}")
            return False

    def normalize_all_files(self):
        """Normaliza todos os arquivos parquet no S3"""
        print(f"🔧 Normalizando schemas dos arquivos parquet...")
        print(f"📁 Bucket: {self.bucket}")
        print(f"📂 Prefix: {self.prefix}")
        print()
        
        try:
            # Listar arquivos
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket, 
                Prefix=self.prefix
            )
            
            if 'Contents' not in response:
                print("❌ Nenhum arquivo encontrado")
                return False
            
            files = [
                obj['Key'] for obj in response['Contents'] 
                if obj['Key'].endswith('.parquet')
            ]
            
            print(f"📋 {len(files)} arquivos encontrados")
            print()
            
            # Processar cada arquivo
            success_count = 0
            for file_key in files:
                if self.process_parquet_file(file_key):
                    success_count += 1
                print()
            
            print(f"🎯 Resultado: {success_count}/{len(files)} arquivos normalizados")
            
            if success_count == len(files):
                print("✅ TODOS OS ARQUIVOS NORMALIZADOS COM SUCESSO!")
                print("💡 Schemas agora são consistentes - Qlik deve funcionar!")
                return True
            else:
                print("⚠️  Alguns arquivos tiveram problemas")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao listar arquivos: {e}")
            return False

def main():
    """Executa normalização de schemas"""
    print("🚀 Iniciando normalização definitiva de schemas parquet...")
    print()
    
    normalizer = ParquetSchemaNormalizer()
    success = normalizer.normalize_all_files()
    
    if success:
        print()
        print("🎉 NORMALIZAÇÃO CONCLUÍDA!")
        print("Próximo passo: recriar view flattened completa")
    else:
        print()
        print("❌ Normalização falhou - verifique os logs acima")

if __name__ == "__main__":
    main()