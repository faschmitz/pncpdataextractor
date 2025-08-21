#!/usr/bin/env python3
"""
Script de debug para testar persistência do state
"""

import json
import boto3
from datetime import datetime, timedelta

def test_state_logic():
    """Testa a lógica de determinação de datas para extração"""
    
    # Simular state atual
    state = {
        'last_extraction_date': '2025-08-19',
        'last_extraction_timestamp': '2025-08-19T23:59:59.999999',
        'processed_dates': ['2025-08-16', '2025-08-18', '2025-08-19']
    }
    
    # Configuração simulada
    production_mode = True
    date_format = '%Y-%m-%d'
    
    print("🔍 Testando lógica de extração incremental...")
    print(f"State atual: {state['last_extraction_date']}")
    print(f"Production mode: {production_mode}")
    print()
    
    # Determinar datas para extração (copiando lógica do extractor.py)
    dates = []
    
    if not state.get('last_extraction_date'):
        print("❌ Primeira execução - faria extração histórica")
        return
    
    # Extração incremental
    last_date = datetime.strptime(state['last_extraction_date'], date_format)
    today = datetime.now()
    
    print(f"last_date: {last_date.date()}")
    print(f"today: {today.date()}")
    
    if production_mode:
        # Pegar apenas ontem (dados já consolidados)
        yesterday = today - timedelta(days=1)
        print(f"yesterday: {yesterday.date()}")
        
        if yesterday.date() > last_date.date():
            dates.append(yesterday.strftime(date_format))
            print(f"✅ Data para processar: {yesterday.strftime(date_format)}")
        else:
            print(f"❌ Nenhuma data para processar (yesterday {yesterday.date()} <= last_date {last_date.date()})")
    else:
        # Desenvolvimento: pegar todos os dias perdidos
        current_date = last_date + timedelta(days=1)
        while current_date.date() <= today.date():
            dates.append(current_date.strftime(date_format))
            current_date += timedelta(days=1)
    
    print(f"\nDatas para processar: {dates}")
    
    if dates:
        date_to_process = dates[0]
        print(f"\nSimulando processamento de {date_to_process}...")
        
        # Simular atualização do state
        new_state = state.copy()
        new_state['last_extraction_date'] = date_to_process
        new_state['last_extraction_timestamp'] = datetime.now().isoformat()
        new_state['processed_dates'] = state['processed_dates'] + [date_to_process]
        
        print(f"State atualizado:")
        print(f"  last_extraction_date: {new_state['last_extraction_date']}")
        print(f"  processed_dates: {new_state['processed_dates'][-3:]}")
        
        return new_state
    
    return None

def test_s3_save():
    """Testa salvamento no S3"""
    print("\n🔍 Testando salvamento no S3...")
    
    try:
        s3_client = boto3.client('s3')
        bucket = 'pncp-extractor-data-prod-566387937580'
        
        # Criar state de teste
        test_state = {
            'last_extraction_date': '2025-08-20',
            'last_extraction_timestamp': datetime.now().isoformat(),
            'test_field': 'DEBUG_TEST',
            'processed_dates': ['2025-08-19', '2025-08-20']
        }
        
        # Salvar no S3
        state_json = json.dumps(test_state, indent=2, ensure_ascii=False, default=str)
        
        s3_client.put_object(
            Bucket=bucket,
            Key='state_debug_test.json',
            Body=state_json.encode('utf-8'),
            ContentType='application/json'
        )
        
        print("✅ Teste de salvamento no S3 bem-sucedido")
        
        # Tentar ler de volta
        response = s3_client.get_object(Bucket=bucket, Key='state_debug_test.json')
        read_data = json.loads(response['Body'].read().decode('utf-8'))
        
        print("✅ Teste de leitura do S3 bem-sucedido")
        print(f"Dados lidos: {read_data['test_field']}")
        
        # Limpar teste
        s3_client.delete_object(Bucket=bucket, Key='state_debug_test.json')
        print("✅ Arquivo de teste removido")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste S3: {e}")
        return False

def main():
    """Executa testes de debug"""
    print("🚀 Iniciando debug da persistência do state...")
    print("=" * 50)
    
    # Teste 1: Lógica de extração
    new_state = test_state_logic()
    
    # Teste 2: Salvamento S3
    s3_works = test_s3_save()
    
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS TESTES:")
    print(f"✅ Lógica de extração: {'OK' if new_state else 'PROBLEMA'}")
    print(f"✅ Salvamento S3: {'OK' if s3_works else 'PROBLEMA'}")
    
    if new_state and s3_works:
        print("\n🎯 CAUSA PROVÁVEL:")
        print("O problema pode estar na execução real do save_state durante o processamento.")
        print("Verifique se há exceptions sendo silenciadas ou se o save_state não está sendo chamado.")
    else:
        print("\n🔧 PROBLEMAS IDENTIFICADOS:")
        if not new_state:
            print("- Lógica de determinação de datas para extração")
        if not s3_works:
            print("- Problema de acesso/permissões no S3")

if __name__ == "__main__":
    main()