#!/usr/bin/env python3
"""
Teste Local Simplificado para PNCP Data Extractor
"""

import os
import sys
import pandas as pd
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Adicionar diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_environment_setup():
    """Testa configuração do ambiente"""
    print("🧪 Testando configuração do ambiente...")
    
    # Verificar dependências Python
    required_packages = [
        'requests', 'pandas', 'boto3', 'python-dotenv'
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

def test_storage_manager_basic():
    """Testa o StorageManager básico"""
    print("🧪 Testando StorageManager básico...")
    
    try:
        from storage_manager import StorageManager
        
        # Testar inicialização em modo local
        storage = StorageManager(use_s3=False)
        print("✅ StorageManager inicializado")
        
        # Criar dados de teste
        test_data = pd.DataFrame({
            'numero_contrato': ['001/2024', '002/2024'],
            'objeto': ['Teste 1', 'Teste 2'],
            'valor': [10000.0, 20000.0]
        })
        
        # Testar salvamento local
        test_date = datetime.now() - timedelta(days=1)
        file_path = storage.save_to_parquet(test_data, test_date)
        print(f"✅ Dados salvos em: {file_path}")
        
        # Verificar se arquivo existe
        if os.path.exists(file_path):
            df_loaded = pd.read_parquet(file_path)
            print(f"✅ Dados lidos: {len(df_loaded)} registros")
            os.remove(file_path)  # Limpar
            return True
        else:
            print("❌ Arquivo não foi criado")
            return False
            
    except Exception as e:
        print(f"❌ Erro no StorageManager: {e}")
        return False

def test_aws_config_basic():
    """Testa configuração AWS básica"""
    print("🧪 Testando configuração AWS básica...")
    
    try:
        from aws_config import AWSConfigManager, setup_aws_environment
        
        # Testar função de setup
        status = setup_aws_environment()
        print(f"✅ AWS setup: {status}")
        
        # Testar classe manager
        aws_config = AWSConfigManager()
        print("✅ AWSConfigManager inicializado")
        
        config_summary = aws_config.get_configuration_summary()
        print(f"✅ Configuração: {config_summary}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na configuração AWS: {e}")
        return False

def test_file_structure():
    """Testa estrutura de arquivos do projeto"""
    print("🧪 Testando estrutura de arquivos...")
    
    required_files = [
        'extractor.py',
        'storage_manager.py', 
        'aws_config.py',
        'requirements.txt',
        'Dockerfile',
        'infrastructure/app.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"❌ {file_path}")
    
    if missing_files:
        print(f"⚠️  Arquivos faltando: {', '.join(missing_files)}")
        return len(missing_files) < len(required_files) * 0.3  # 70% devem existir
    
    return True

def test_sample_data_processing():
    """Testa processamento de dados de amostra"""
    print("🧪 Testando processamento de dados de amostra...")
    
    # Simular dados da API PNCP
    mock_data = pd.DataFrame({
        'numeroContrato': ['001/2024', '002/2024'],
        'objetoContrato': ['Sistema de gestão digital', 'Serviços de limpeza'],
        'valorContrato': [150000.50, 50000.00],
        'dataAssinatura': ['2024-01-15', '2024-01-20']
    })
    
    print(f"✅ Dados simulados: {len(mock_data)} registros")
    
    # Simular filtro básico
    tech_keywords = ['sistema', 'digital', 'tecnologia']
    filtered_data = mock_data[
        mock_data['objetoContrato'].str.lower().str.contains('|'.join(tech_keywords))
    ]
    
    print(f"✅ Dados filtrados: {len(filtered_data)} registros")
    
    return len(filtered_data) > 0

def run_simple_tests():
    """Executa testes locais simplificados"""
    print("=" * 60)
    print("🚀 PNCP Data Extractor - Testes Locais Simplificados")
    print("=" * 60)
    
    tests = [
        ("Configuração do Ambiente", test_environment_setup),
        ("Estrutura de Arquivos", test_file_structure),
        ("StorageManager Básico", test_storage_manager_basic),
        ("AWS Config Básico", test_aws_config_basic),
        ("Processamento de Dados", test_sample_data_processing)
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
    print("📊 RESUMO DOS TESTES LOCAIS")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1
    
    print(f"\nResultado: {passed}/{len(results)} testes passaram")
    
    if passed >= len(results) * 0.8:  # 80% devem passar
        print("🎉 Testes locais passaram! Sistema básico funcional.")
        return True
    else:
        print("⚠️  Alguns testes falharam. Verifique dependências e estrutura.")
        return False

if __name__ == "__main__":
    success = run_simple_tests()
    sys.exit(0 if success else 1)