#!/usr/bin/env python3
"""
Teste da normalização de schema
"""
import sys
import os

# Adicionar o diretório atual ao path para importar o extractor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extractor import PNCPContractionsExtractor, ExtractorConfig
import pandas as pd

def test_schema_normalization():
    """Testa a normalização de schema"""
    print("🧪 Testando normalização de schema...")
    
    # Configurar extrator
    config = ExtractorConfig()
    extractor = PNCPContractionsExtractor(config)
    
    # Registros de teste simulando inconsistências da API
    test_records = [
        # Registro com campos nested completos
        {
            'numeroCompra': '123',
            'objetoCompra': 'Teste com dados completos',
            'unidadeOrgao': {
                'municipioNome': 'São Paulo',
                'ufSigla': 'SP',
                'codigoIbge': '123456'
            },
            'orgaoEntidade': {
                'cnpj': '12345678000190',
                'razaoSocial': 'Órgão Teste'
            },
            'amparoLegal': {
                'nome': 'Lei 14.133/2021',
                'codigo': 1
            },
            'fontesOrcamentarias': [
                {'nome': 'Fonte A', 'codigo': 100}
            ]
        },
        # Registro com campos NULL (simulando inconsistência)
        {
            'numeroCompra': '456',
            'objetoCompra': 'Teste com campos nulos',
            'unidadeOrgao': None,
            'orgaoEntidade': None,
            'amparoLegal': None,
            'unidadeSubRogada': None,
            'orgaoSubRogado': None,
            'fontesOrcamentarias': None
        },
        # Registro com campos incompletos
        {
            'numeroCompra': '789',
            'objetoCompra': 'Teste com campos incompletos',
            'unidadeOrgao': {
                'municipioNome': 'Rio de Janeiro'
                # faltando outros campos
            },
            'orgaoEntidade': {
                'cnpj': '98765432000110'
                # faltando outros campos
            },
            'fontesOrcamentarias': []
        }
    ]
    
    # Aplicar normalização
    normalized_records = []
    for record in test_records:
        # Simular enriquecimento básico
        enriched = record.copy()
        enriched['filtro_aplicado'] = True
        enriched['filtro_motivo'] = 'Teste'
        enriched['filtro_grupo_matched'] = ''
        enriched['filtro_termo_matched'] = ''
        enriched['filtro_criterio'] = ''
        
        # Aplicar normalização
        normalized = extractor.normalize_record_schema(enriched)
        normalized_records.append(normalized)
        
        print(f"📝 Registro {record['numeroCompra']} normalizado:")
        print(f"   unidadeOrgao: {type(normalized.get('unidadeOrgao'))}")
        print(f"   orgaoEntidade: {type(normalized.get('orgaoEntidade'))}")
        print(f"   fontesOrcamentarias: {type(normalized.get('fontesOrcamentarias'))}")
        print()
    
    # Criar DataFrame de teste
    df = pd.DataFrame(normalized_records)
    
    # Adicionar colunas de controle
    df['extraction_date'] = '2025-08-19T12:00:00'
    df['data_publicacao'] = '2025-08-19'
    
    print("📊 DataFrame criado com sucesso!")
    print(f"   Linhas: {len(df)}")
    print(f"   Colunas: {len(df.columns)}")
    print(f"   Tipos por coluna:")
    for col, dtype in df.dtypes.items():
        if col in ['unidadeOrgao', 'orgaoEntidade', 'fontesOrcamentarias', 'unidadeSubRogada', 'orgaoSubRogado']:
            print(f"      {col}: {dtype}")
    
    # Salvar como parquet de teste
    test_file = 'test_normalized_schema.parquet'
    df.to_parquet(test_file, index=False)
    print(f"✅ Parquet de teste salvo: {test_file}")
    
    # Ler de volta para verificar
    df_read = pd.read_parquet(test_file)
    print(f"✅ Parquet lido com sucesso: {len(df_read)} registros")
    
    # Verificar se todos os campos nested estão presentes e são structs
    for col in ['unidadeOrgao', 'orgaoEntidade', 'amparoLegal', 'unidadeSubRogada', 'orgaoSubRogado']:
        if col in df_read.columns:
            sample_value = df_read[col].iloc[0]
            print(f"   {col}: {type(sample_value)} - {'dict-like' if isinstance(sample_value, dict) else 'other'}")
    
    print("🎉 Teste concluído com sucesso!")

if __name__ == "__main__":
    test_schema_normalization()