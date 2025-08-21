#!/usr/bin/env python3
"""
Script para reconstruir arquivo parquet problemático
Reescreve o arquivo usando o mesmo schema dos arquivos funcionais
"""

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from io import BytesIO
import json
from datetime import datetime

def rebuild_problematic_file():
    """Reconstrói o arquivo problemático com schema consistente"""
    
    s3_client = boto3.client('s3')
    bucket = 'pncp-extractor-data-prod-566387937580'
    
    # Arquivos
    problematic_file = 'raw-data/year=2025/month=08/pncp_contratos_20250803.parquet'
    working_file = 'raw-data/year=2025/month=08/pncp_contratos_20250820.parquet'
    
    print("🔄 Reconstruindo arquivo problemático...")
    print(f"Arquivo problemático: {problematic_file}")
    print(f"Arquivo de referência: {working_file}")
    
    try:
        # 1. Baixar arquivo de referência (funcional)
        print("\n📥 Baixando arquivo de referência...")
        response = s3_client.get_object(Bucket=bucket, Key=working_file)
        reference_data = response['Body'].read()
        reference_table = pq.read_table(BytesIO(reference_data))
        reference_schema = reference_table.schema
        
        print(f"✅ Schema de referência carregado com {len(reference_schema)} campos")
        
        # 2. Baixar arquivo problemático
        print("\n📥 Baixando arquivo problemático...")
        response = s3_client.get_object(Bucket=bucket, Key=problematic_file)
        problem_data = response['Body'].read()
        problem_table = pq.read_table(BytesIO(problem_data))
        
        print(f"✅ Arquivo problemático carregado com {len(problem_table)} registros")
        
        # 3. Converter para DataFrame para manipulação
        df = problem_table.to_pandas()
        print(f"✅ Convertido para DataFrame: {df.shape}")
        
        # 4. Garantir tipos consistentes para campos struct
        struct_fields = ['unidadeOrgao', 'orgaoEntidade']
        
        for field in struct_fields:
            if field in df.columns:
                print(f"🔧 Normalizando campo struct: {field}")
                
                # Definir schema padrão baseado no arquivo de referência
                if field == 'unidadeOrgao':
                    default_struct = {
                        'codigoIbge': None,
                        'codigoUnidade': None,
                        'municipioNome': None,
                        'nomeUnidade': None,
                        'ufNome': None,
                        'ufSigla': None
                    }
                elif field == 'orgaoEntidade':
                    default_struct = {
                        'cnpj': None,
                        'esferaId': None,
                        'poderId': None,
                        'razaoSocial': None
                    }
                
                # Normalizar todos os valores
                def normalize_struct(value):
                    if pd.isna(value) or value is None:
                        return default_struct.copy()
                    if isinstance(value, dict):
                        normalized = default_struct.copy()
                        normalized.update(value)
                        return normalized
                    return default_struct.copy()
                
                df[field] = df[field].apply(normalize_struct)
        
        # 5. Criar tabela Arrow com schema do arquivo de referência
        print("\n🔧 Reconstruindo com schema de referência...")
        
        # Converter DataFrame de volta para Arrow table usando schema de referência
        rebuilt_table = pa.Table.from_pandas(df, schema=reference_schema, preserve_index=False)
        
        print(f"✅ Tabela reconstruída com schema consistente")
        print(f"   Registros: {len(rebuilt_table)}")
        print(f"   Campos: {len(rebuilt_table.schema)}")
        
        # 6. Escrever novo arquivo parquet
        print("\n💾 Salvando arquivo reconstruído...")
        
        buffer = BytesIO()
        pq.write_table(
            rebuilt_table, 
            buffer,
            compression='snappy',
            write_statistics=True,
            use_dictionary=True
        )
        
        # 7. Fazer backup do arquivo original
        backup_key = problematic_file.replace('.parquet', '_backup.parquet')
        print(f"🗂️ Criando backup: {backup_key}")
        
        s3_client.copy_object(
            Bucket=bucket,
            CopySource={'Bucket': bucket, 'Key': problematic_file},
            Key=backup_key
        )
        
        # 8. Substituir arquivo original
        print(f"🔄 Substituindo arquivo original...")
        
        s3_client.put_object(
            Bucket=bucket,
            Key=problematic_file,
            Body=buffer.getvalue(),
            ContentType='application/octet-stream'
        )
        
        # 9. Verificar o novo arquivo
        print("\n✅ Verificando arquivo reconstruído...")
        response = s3_client.get_object(Bucket=bucket, Key=problematic_file)
        verification_data = response['Body'].read()
        verification_table = pq.read_table(BytesIO(verification_data))
        
        print(f"   Registros: {len(verification_table)}")
        print(f"   Schema fields: {len(verification_table.schema)}")
        
        # Verificar campos struct específicos
        for field in struct_fields:
            if field in verification_table.schema.names:
                field_type = verification_table.schema.field(field).type
                print(f"   {field}: {field_type}")
        
        print(f"\n🎯 ARQUIVO RECONSTRUÍDO COM SUCESSO!")
        print(f"Backup salvo em: s3://{bucket}/{backup_key}")
        print(f"Arquivo original substituído: s3://{bucket}/{problematic_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante reconstrução: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_athena_compatibility():
    """Verifica se o arquivo pode ser lido pelo Athena"""
    print("\n🔍 Verificando compatibilidade com Athena...")
    
    try:
        import subprocess
        
        # Tentar query simples no arquivo reconstruído
        query = """
        SELECT COUNT(*) as total_records
        FROM "pncp"."contratos" 
        WHERE year = '2025' AND month = '08'
        AND _source_file LIKE '%pncp_contratos_20250803%'
        """
        
        print("📊 Executando query de teste no Athena...")
        print(f"Query: {query.strip()}")
        
        # Usar AWS CLI para executar query
        result = subprocess.run([
            'aws', 'athena', 'start-query-execution',
            '--query-string', query,
            '--result-configuration', 'OutputLocation=s3://pncp-extractor-data-prod-566387937580/athena-results/',
            '--work-group', 'primary'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            query_result = json.loads(result.stdout)
            execution_id = query_result['QueryExecutionId']
            print(f"✅ Query iniciada: {execution_id}")
            return execution_id
        else:
            print(f"❌ Erro ao executar query: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return None

def main():
    """Executa reconstrução completa"""
    print("🚀 Iniciando reconstrução do arquivo problemático...")
    print("=" * 60)
    
    # Reconstruir arquivo
    success = rebuild_problematic_file()
    
    if success:
        print("\n" + "=" * 60)
        print("🎯 RECONSTRUÇÃO CONCLUÍDA!")
        print("📋 PRÓXIMOS PASSOS:")
        print("1. Testar acesso via Qlik Cloud")
        print("2. Verificar se o erro HIVE_CANNOT_OPEN_SPLIT foi resolvido")
        print("3. Monitorar logs de futuras execuções")
        
        # Verificar compatibilidade com Athena
        execution_id = verify_athena_compatibility()
        if execution_id:
            print(f"\n🔗 Query de teste executando: {execution_id}")
            print("Use 'aws athena get-query-execution --query-execution-id {execution_id}' para verificar status")
    else:
        print("\n❌ RECONSTRUÇÃO FALHOU!")
        print("Verifique os logs acima para detalhes do erro")

if __name__ == "__main__":
    main()