#!/usr/bin/env python3
"""
Script de teste local para PNCP Data Extractor
Testa funcionalidades principais antes do deploy AWS
"""

import os
import sys
import json
import tempfile
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Adicionar diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from storage_manager import StorageManager
from aws_config import AWSConfigManager

def test_storage_manager():
    """Testa o StorageManager em modo local"""
    print("🧪 Testando StorageManager (modo local)...")
    
    # Forçar modo local
    os.environ.pop('AWS_DEFAULT_REGION', None)
    os.environ.pop('AWS_REGION', None)
    
    storage = StorageManager(use_s3=False)
    
    # Criar dados de teste
    test_data = pd.DataFrame({
        'numero_contrato': ['001/2024', '002/2024'],
        'objeto': ['Teste 1', 'Teste 2'],
        'valor': [10000.0, 20000.0],
        'data_assinatura': ['2024-01-15', '2024-01-16']
    })
    
    # Testar salvamento local
    test_date = datetime.now() - timedelta(days=1)
    file_path = storage.save_to_parquet(test_data, test_date)
    print(f"✅ Arquivo salvo em: {file_path}")
    
    # Verificar se arquivo existe
    if os.path.exists(file_path):
        print("✅ Arquivo parquet criado com sucesso")
        
        # Testar leitura
        df_loaded = pd.read_parquet(file_path)
        print(f"✅ Dados lidos: {len(df_loaded)} registros")
        
        # Limpar arquivo de teste
        os.remove(file_path)
        print("✅ Limpeza concluída")
    else:
        print("❌ Arquivo não foi criado")
        return False
    
    return True

def test_aws_config():
    """Testa configuração AWS (se credenciais disponíveis)"""
    print("🧪 Testando AwsConfig...")
    
    try:
        aws_config = AWSConfigManager()
        
        if aws_config.is_aws_environment():
            print("✅ Ambiente AWS detectado")
            
            # Testar conexão com AWS
            try:
                aws_config.validate_aws_credentials()
                print("✅ Credenciais AWS válidas")
                return True
            except Exception as e:
                print(f"⚠️  Credenciais AWS inválidas: {e}")
                return False
        else:
            print("ℹ️  Ambiente local detectado (sem credenciais AWS)")
            return True
            
    except Exception as e:
        print(f"❌ Erro na configuração AWS: {e}")
        return False

def test_llm_filter_mock():
    """Testa filtro LLM com dados mockados"""
    print("🧪 Testando filtro LLM (mock)...")
    
    # Dados de teste para filtro
    test_contracts = [
        {
            "numero_contrato": "001/2024",
            "objeto": "Aquisição de equipamentos de informática para modernização do parque tecnológico",
            "valor": 150000.0
        },
        {
            "numero_contrato": "002/2024", 
            "objeto": "Serviços de limpeza e conservação predial",
            "valor": 50000.0
        },
        {
            "numero_contrato": "003/2024",
            "objeto": "Desenvolvimento de sistema de gestão digital e plataforma de BI",
            "valor": 300000.0
        }
    ]
    
    # Simular critérios de filtro
    tech_keywords = ['informática', 'tecnológico', 'digital', 'sistema', 'BI', 'software']
    
    filtered_contracts = []
    for contract in test_contracts:
        objeto_lower = contract['objeto'].lower()
        if any(keyword in objeto_lower for keyword in tech_keywords):
            filtered_contracts.append(contract)
    
    print(f"✅ Contratos filtrados: {len(filtered_contracts)}/{len(test_contracts)}")
    
    for contract in filtered_contracts:
        print(f"  - {contract['numero_contrato']}: {contract['objeto'][:60]}...")
    
    return len(filtered_contracts) > 0

def test_environment_setup():
    """Testa configuração do ambiente"""
    print("🧪 Testando configuração do ambiente...")
    
    # Verificar dependências Python
    required_packages = [
        'requests', 'pandas', 'boto3', 'openai', 'python-dotenv'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} - não encontrado")
    
    if missing_packages:
        print(f"⚠️  Pacotes faltando: {', '.join(missing_packages)}")
        print("Execute: pip install -r requirements.txt")
        return False
    
    # Verificar estrutura de diretórios
    required_dirs = ['data', 'logs']
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            print(f"✅ Diretório criado: {dir_name}")
        else:
            print(f"✅ Diretório existe: {dir_name}")
    
    return True

def test_sample_extraction():
    """Testa extração com dados de amostra"""
    print("🧪 Testando extração de amostra...")
    
    # Simular resposta da API PNCP
    mock_api_response = {
        "data": [
            {
                "numeroContrato": "001/2024",
                "objetoContrato": "Aquisição de notebooks e equipamentos de TI",
                "valorContrato": 125000.50,
                "dataAssinatura": "2024-01-15",
                "nomeRazaoSocialFornecedor": "Tech Solutions LTDA"
            },
            {
                "numeroContrato": "002/2024", 
                "objetoContrato": "Serviços de desenvolvimento de software",
                "valorContrato": 280000.00,
                "dataAssinatura": "2024-01-20",
                "nomeRazaoSocialFornecedor": "DevCorp S.A."
            }
        ],
        "totalElements": 2
    }
    
    # Converter para DataFrame
    df = pd.DataFrame(mock_api_response["data"])
    
    # Simular processamento e salvamento
    storage = StorageManager(use_s3=False)
    
    try:
        file_path = storage.save_to_parquet(df, datetime.now())
        print(f"✅ Dados de amostra salvos em: {file_path}")
        
        # Verificar conteúdo
        df_loaded = pd.read_parquet(file_path)
        print(f"✅ Registros processados: {len(df_loaded)}")
        
        # Limpar
        os.remove(file_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na extração de amostra: {e}")
        return False

def run_all_tests():
    """Executa todos os testes locais"""
    print("=" * 60)
    print("🚀 PNCP Data Extractor - Testes Locais")
    print("=" * 60)
    
    tests = [
        ("Configuração do Ambiente", test_environment_setup),
        ("Storage Manager", test_storage_manager),
        ("AWS Config", test_aws_config),
        ("Filtro LLM (Mock)", test_llm_filter_mock),
        ("Extração de Amostra", test_sample_extraction)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erro durante teste: {e}")
            results.append((test_name, False))
    
    # Resumo dos resultados
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1
    
    print(f"\nResultado: {passed}/{len(results)} testes passaram")
    
    if passed == len(results):
        print("🎉 Todos os testes locais passaram! Sistema pronto para deploy.")
        return True
    else:
        print("⚠️  Alguns testes falharam. Revise as configurações antes do deploy.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)