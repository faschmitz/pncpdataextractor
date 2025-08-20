#!/usr/bin/env python3
import boto3
import os
import tempfile
import subprocess
import json

def normalize_parquet_with_athena():
    """Usa Athena para normalizar schemas criando uma nova tabela"""
    
    athena_client = boto3.client('athena')
    
    # Query para criar tabela normalizada
    query = """
    CREATE TABLE pncp_data.contratos_normalized AS
    SELECT 
        numero,
        objeto,
        CAST(valorinicial AS double) as valorinicial,
        dataassinatura,
        datainiciovigencia,
        datafimvigencia,
        CAST(valorglobal AS double) as valorglobal,
        situacao,
        modalidadecontratacao,
        CAST(codigomodalidade AS bigint) as codigomodalidade,
        nifornecedor,
        nomerazaosocialfornecedor,
        CASE 
            WHEN unidadeorgao IS NULL THEN 
                CAST(ROW(NULL, NULL, NULL, NULL, NULL, NULL) AS ROW(
                    codigoibge varchar, 
                    codigounidade varchar, 
                    municipionome varchar, 
                    nomeunidade varchar, 
                    ufnome varchar, 
                    ufsigla varchar
                ))
            ELSE unidadeorgao
        END as unidadeorgao,
        CASE 
            WHEN orgaoentidade IS NULL THEN 
                CAST(ROW(NULL, NULL, NULL, NULL) AS ROW(
                    cnpj varchar, 
                    razaosocial varchar, 
                    poderid bigint, 
                    esferaid bigint
                ))
            ELSE orgaoentidade
        END as orgaoentidade,
        CASE 
            WHEN unidadesubrogada IS NULL THEN 
                CAST(ROW(NULL, NULL, NULL, NULL, NULL, NULL) AS ROW(
                    codigoibge varchar, 
                    codigounidade varchar, 
                    municipionome varchar, 
                    nomeunidade varchar, 
                    ufnome varchar, 
                    ufsigla varchar
                ))
            ELSE unidadesubrogada
        END as unidadesubrogada,
        datainclusao,
        dataultimaalteracao,
        usuarioinclusao,
        usuarioultimaalteracao,
        year,
        month
    FROM pncp_data.contratos 
    WHERE year = '2025' AND month = '08'
    """
    
    try:
        response = athena_client.start_query_execution(
            QueryString=query,
            ResultConfiguration={
                'OutputLocation': 's3://pncp-extractor-data-prod-566387937580/athena-results/'
            },
            WorkGroup='primary'
        )
        
        execution_id = response['QueryExecutionId']
        print(f"Query executada: {execution_id}")
        
        # Aguardar conclusão
        import time
        for i in range(30):  # 5 minutos máximo
            result = athena_client.get_query_execution(QueryExecutionId=execution_id)
            status = result['QueryExecution']['Status']['State']
            
            if status == 'SUCCEEDED':
                print("✅ Tabela normalizada criada com sucesso!")
                return True
            elif status == 'FAILED':
                error = result['QueryExecution']['Status']['StateChangeReason']
                print(f"❌ Query falhou: {error}")
                return False
            
            time.sleep(10)
        
        print("⏱️ Timeout na query")
        return False
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    normalize_parquet_with_athena()
