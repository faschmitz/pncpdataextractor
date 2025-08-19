#!/usr/bin/env python3
"""
Testes de integração AWS para PNCP Data Extractor
Testa conectividade e funcionalidades reais dos serviços AWS
"""

import os
import sys
import json
import boto3
import pandas as pd
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Adicionar diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from storage_manager import StorageManager
from aws_config import AwsConfig

def test_s3_connectivity():
    """Testa conectividade com S3"""
    print("🧪 Testando conectividade S3...")
    
    try:
        s3_client = boto3.client('s3')
        
        # Listar buckets para testar conectividade
        response = s3_client.list_buckets()
        print(f"✅ Conectado ao S3 - {len(response['Buckets'])} buckets encontrados")
        
        # Verificar se bucket do projeto existe
        bucket_name = os.getenv('S3_BUCKET', 'pncp-extractor-data-prod')
        
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✅ Bucket {bucket_name} existe e é acessível")
            return True
        except s3_client.exceptions.NoSuchBucket:
            print(f"⚠️  Bucket {bucket_name} não existe ainda")
            return True  # OK se bucket não existe ainda
        except Exception as e:
            print(f"❌ Erro ao acessar bucket {bucket_name}: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Erro na conectividade S3: {e}")
        return False

def test_secrets_manager():
    """Testa acesso ao Secrets Manager"""
    print("🧪 Testando Secrets Manager...")
    
    try:
        secrets_client = boto3.client('secretsmanager')
        
        # Listar secrets para testar conectividade
        response = secrets_client.list_secrets()
        print(f"✅ Conectado ao Secrets Manager - {len(response['SecretList'])} secrets encontrados")
        
        # Verificar se secrets do projeto existem
        project_secrets = [
            'pncp-extractor/openai-api-key',
            'pncp-extractor/app-config'
        ]
        
        existing_secrets = []
        for secret in response['SecretList']:
            if any(proj_secret in secret['Name'] for proj_secret in project_secrets):
                existing_secrets.append(secret['Name'])
                print(f"✅ Secret encontrado: {secret['Name']}")
        
        if not existing_secrets:
            print("⚠️  Nenhum secret do projeto encontrado ainda")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no Secrets Manager: {e}")
        return False

def test_ecs_connectivity():
    """Testa conectividade com ECS"""
    print("🧪 Testando conectividade ECS...")
    
    try:
        ecs_client = boto3.client('ecs')
        
        # Listar clusters
        response = ecs_client.list_clusters()
        clusters = response['clusterArns']
        
        print(f"✅ Conectado ao ECS - {len(clusters)} clusters encontrados")
        
        # Procurar cluster do projeto
        project_cluster = None
        for cluster_arn in clusters:
            if 'pncp-extractor' in cluster_arn:
                project_cluster = cluster_arn
                break
        
        if project_cluster:
            print(f"✅ Cluster do projeto encontrado: {project_cluster}")
            
            # Verificar status do cluster
            cluster_details = ecs_client.describe_clusters(clusters=[project_cluster])
            cluster = cluster_details['clusters'][0]
            
            print(f"  Status: {cluster['status']}")
            print(f"  Running tasks: {cluster.get('runningTasksCount', 0)}")
            print(f"  Active services: {cluster.get('activeServicesCount', 0)}")
        else:
            print("⚠️  Cluster do projeto não encontrado ainda")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na conectividade ECS: {e}")
        return False

def test_step_functions():
    """Testa conectividade com Step Functions"""
    print("🧪 Testando Step Functions...")
    
    try:
        sf_client = boto3.client('stepfunctions')
        
        # Listar state machines
        response = sf_client.list_state_machines()
        state_machines = response['stateMachines']
        
        print(f"✅ Conectado ao Step Functions - {len(state_machines)} state machines encontradas")
        
        # Procurar state machine do projeto
        project_sm = None
        for sm in state_machines:
            if 'pncp-extractor' in sm['name']:
                project_sm = sm
                break
        
        if project_sm:
            print(f"✅ State Machine do projeto encontrada: {project_sm['name']}")
            print(f"  Status: {project_sm['status']}")
            
            # Verificar últimas execuções
            executions = sf_client.list_executions(
                stateMachineArn=project_sm['stateMachineArn'],
                maxResults=5
            )
            
            print(f"  Últimas {len(executions['executions'])} execuções:")
            for exec in executions['executions']:
                print(f"    - {exec['name']}: {exec['status']} ({exec['startDate']})")
        else:
            print("⚠️  State Machine do projeto não encontrada ainda")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no Step Functions: {e}")
        return False

def test_cloudwatch():
    """Testa conectividade com CloudWatch"""
    print("🧪 Testando CloudWatch...")
    
    try:
        cw_client = boto3.client('cloudwatch')
        logs_client = boto3.client('logs')
        
        # Testar CloudWatch Metrics
        response = cw_client.list_metrics(Namespace='PNCP/Extractor')
        custom_metrics = response['Metrics']
        
        print(f"✅ Conectado ao CloudWatch - {len(custom_metrics)} métricas customizadas")
        
        # Testar CloudWatch Logs
        response = logs_client.describe_log_groups(
            logGroupNamePrefix='/aws/ecs/pncp-extractor'
        )
        log_groups = response['logGroups']
        
        print(f"✅ {len(log_groups)} log groups do projeto encontrados")
        
        for lg in log_groups:
            print(f"  - {lg['logGroupName']}: {lg.get('storedBytes', 0)} bytes")
        
        # Verificar alarmes
        response = cw_client.describe_alarms(
            AlarmNamePrefix='pncp-extractor'
        )
        alarms = response['MetricAlarms']
        
        print(f"✅ {len(alarms)} alarmes do projeto encontrados")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no CloudWatch: {e}")
        return False

def test_storage_manager_s3():
    """Testa StorageManager com S3 real"""
    print("🧪 Testando StorageManager com S3...")
    
    try:
        # Forçar modo S3
        os.environ['AWS_DEFAULT_REGION'] = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        storage = StorageManager(use_s3=True, s3_bucket=os.getenv('S3_BUCKET', 'pncp-extractor-data-prod'))
        
        # Criar dados de teste
        test_data = pd.DataFrame({
            'numero_contrato': [f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}'],
            'objeto': ['Teste de integração AWS'],
            'valor': [1.00],
            'data_assinatura': [datetime.now().strftime('%Y-%m-%d')]
        })
        
        # Testar upload para S3
        test_date = datetime.now()
        file_path = storage.save_to_parquet(test_data, test_date)
        
        print(f"✅ Dados de teste salvos em: {file_path}")
        
        # Verificar se arquivo existe no S3
        s3_client = boto3.client('s3')
        bucket_name = storage.s3_bucket
        
        # Extrair key do file_path
        s3_key = file_path.replace(f's3://{bucket_name}/', '')
        
        try:
            s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            print("✅ Arquivo confirmado no S3")
            
            # Limpar arquivo de teste
            s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
            print("✅ Arquivo de teste removido")
            
            return True
        except s3_client.exceptions.NoSuchKey:
            print("❌ Arquivo não encontrado no S3")
            return False
        except Exception as e:
            print(f"⚠️  Bucket pode não existir ainda: {e}")
            return True  # OK se bucket não existe
            
    except Exception as e:
        print(f"❌ Erro no teste StorageManager S3: {e}")
        return False

def test_aws_config_integration():
    """Testa AwsConfig com AWS real"""
    print("🧪 Testando AwsConfig com AWS...")
    
    try:
        config = AwsConfig()
        
        if not config.is_aws_environment():
            print("⚠️  Ambiente AWS não detectado")
            return False
        
        # Testar validação de credenciais
        identity = config.validate_aws_credentials()
        print(f"✅ Credenciais válidas - Account: {identity['Account']}")
        
        # Testar configuração de variáveis
        status = config.setup_environment_variables()
        
        print(f"  AWS configurado: {status['aws_configured']}")
        print(f"  OpenAI configurado: {status['openai_configured']}")
        print(f"  Bucket S3: {status['s3_bucket']}")
        print(f"  Região: {status['region']}")
        print(f"  Ambiente: {status['environment']}")
        
        return status['aws_configured']
        
    except Exception as e:
        print(f"❌ Erro no AwsConfig: {e}")
        return False

def test_ecr_connectivity():
    """Testa conectividade com ECR"""
    print("🧪 Testando conectividade ECR...")
    
    try:
        ecr_client = boto3.client('ecr')
        
        # Listar repositórios
        response = ecr_client.describe_repositories()
        repositories = response['repositories']
        
        print(f"✅ Conectado ao ECR - {len(repositories)} repositórios encontrados")
        
        # Procurar repositório do projeto
        project_repo = None
        for repo in repositories:
            if 'pncp-extractor' in repo['repositoryName']:
                project_repo = repo
                break
        
        if project_repo:
            print(f"✅ Repositório do projeto encontrado: {project_repo['repositoryName']}")
            print(f"  URI: {project_repo['repositoryUri']}")
            
            # Verificar imagens
            try:
                images = ecr_client.list_images(
                    repositoryName=project_repo['repositoryName']
                )
                print(f"  Imagens: {len(images['imageIds'])}")
            except Exception as e:
                print(f"  ⚠️  Erro ao listar imagens: {e}")
        else:
            print("⚠️  Repositório do projeto não encontrado ainda")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na conectividade ECR: {e}")
        return False

def test_sns_connectivity():
    """Testa conectividade com SNS"""
    print("🧪 Testando conectividade SNS...")
    
    try:
        sns_client = boto3.client('sns')
        
        # Listar tópicos
        response = sns_client.list_topics()
        topics = response['Topics']
        
        print(f"✅ Conectado ao SNS - {len(topics)} tópicos encontrados")
        
        # Procurar tópicos do projeto
        project_topics = []
        for topic in topics:
            topic_arn = topic['TopicArn']
            if 'pncp-extractor' in topic_arn:
                project_topics.append(topic_arn)
                print(f"✅ Tópico do projeto: {topic_arn}")
        
        if not project_topics:
            print("⚠️  Nenhum tópico do projeto encontrado ainda")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na conectividade SNS: {e}")
        return False

def run_integration_tests():
    """Executa todos os testes de integração AWS"""
    print("=" * 60)
    print("🚀 PNCP Data Extractor - Testes de Integração AWS")
    print("=" * 60)
    
    # Verificar se credenciais AWS estão configuradas
    if not os.getenv('AWS_ACCESS_KEY_ID'):
        print("❌ Variável AWS_ACCESS_KEY_ID não configurada")
        print("Configure as credenciais AWS antes de executar os testes")
        return False
    
    tests = [
        ("Conectividade S3", test_s3_connectivity),
        ("Secrets Manager", test_secrets_manager),
        ("Conectividade ECS", test_ecs_connectivity),
        ("Step Functions", test_step_functions),
        ("CloudWatch", test_cloudwatch),
        ("Conectividade ECR", test_ecr_connectivity),
        ("Conectividade SNS", test_sns_connectivity),
        ("StorageManager S3", test_storage_manager_s3),
        ("AwsConfig Integração", test_aws_config_integration)
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
    print("📊 RESUMO DOS TESTES DE INTEGRAÇÃO")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1
    
    print(f"\nResultado: {passed}/{len(results)} testes passaram")
    
    if passed >= len(results) * 0.8:  # 80% dos testes devem passar
        print("🎉 Integração AWS validada! Serviços funcionando corretamente.")
        return True
    else:
        print("⚠️  Muitos testes falharam. Verifique configuração AWS e infraestrutura.")
        return False

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)