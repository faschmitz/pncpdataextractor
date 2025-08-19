#!/usr/bin/env python3
"""
AWS CDK Application para PNCP Data Extractor

Esta aplicação define toda a infraestrutura AWS necessária para executar
o sistema de extração de dados PNCP com filtro LLM em produção.
"""

import os
from aws_cdk import App, Environment, Tags

from stacks.storage_stack import StorageStack
from stacks.security_stack import SecurityStack
from stacks.compute_stack import ComputeStack
from stacks.orchestration_stack import OrchestrationStack
from stacks.monitoring_stack import MonitoringStack


# Configurações do ambiente
ACCOUNT = os.getenv('CDK_DEFAULT_ACCOUNT')
REGION = os.getenv('CDK_DEFAULT_REGION', 'us-east-1')

# Configurações da aplicação
APP_NAME = "pncp-extractor"
ENVIRONMENT = os.getenv('ENVIRONMENT', 'prod')

def main():
    """Função principal para definir a aplicação CDK"""
    app = App()
    
    # Ambiente AWS
    env = Environment(account=ACCOUNT, region=REGION)
    
    # Tags globais para todos os recursos
    Tags.of(app).add("Project", "PNCP-DataExtractor")
    Tags.of(app).add("Environment", ENVIRONMENT)
    Tags.of(app).add("ManagedBy", "CDK")
    Tags.of(app).add("Owner", "Leonora-Comercio-Internacional")
    
    # Stack de armazenamento (S3 buckets)
    storage_stack = StorageStack(
        app, 
        f"{APP_NAME}-storage-{ENVIRONMENT}",
        app_name=APP_NAME,
        environment=ENVIRONMENT,
        env=env,
        description="S3 buckets e políticas de armazenamento para PNCP Data Extractor"
    )
    
    # Stack de segurança (IAM roles, Secrets Manager)
    security_stack = SecurityStack(
        app,
        f"{APP_NAME}-security-{ENVIRONMENT}",
        storage_stack=storage_stack,
        app_name=APP_NAME,
        environment=ENVIRONMENT,
        env=env,
        description="Recursos de segurança: IAM roles, políticas e Secrets Manager"
    )
    
    # Stack de computação (ECS cluster, task definitions)
    compute_stack = ComputeStack(
        app,
        f"{APP_NAME}-compute-{ENVIRONMENT}",
        storage_stack=storage_stack,
        security_stack=security_stack,
        app_name=APP_NAME,
        environment=ENVIRONMENT,
        env=env,
        description="Recursos de computação: ECS cluster e task definitions"
    )
    
    # Stack de orquestração (EventBridge, Step Functions)
    orchestration_stack = OrchestrationStack(
        app,
        f"{APP_NAME}-orchestration-{ENVIRONMENT}",
        compute_stack=compute_stack,
        security_stack=security_stack,
        app_name=APP_NAME,
        environment=ENVIRONMENT,
        env=env,
        description="Orquestração: EventBridge Scheduler e Step Functions"
    )
    
    # Stack de monitoramento (CloudWatch, SNS)
    monitoring_stack = MonitoringStack(
        app,
        f"{APP_NAME}-monitoring-{ENVIRONMENT}",
        compute_stack=compute_stack,
        orchestration_stack=orchestration_stack,
        app_name=APP_NAME,
        environment=ENVIRONMENT,
        env=env,
        description="Monitoramento: CloudWatch dashboards, alarms e notificações SNS"
    )
    
    # Dependências entre stacks
    security_stack.add_dependency(storage_stack)
    compute_stack.add_dependency(security_stack)
    orchestration_stack.add_dependency(compute_stack)
    monitoring_stack.add_dependency(orchestration_stack)
    
    app.synth()

if __name__ == "__main__":
    main()