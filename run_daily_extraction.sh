#!/bin/bash

# Script para execução diária via ECS
# Uso: ./run_daily_extraction.sh

# AWS credentials configuradas no ECS Task Role
# export AWS_ACCESS_KEY_ID=[CONFIGURED_IN_ECS]
# export AWS_SECRET_ACCESS_KEY=[CONFIGURED_IN_ECS]
export AWS_DEFAULT_REGION=us-east-2

echo "🕕 Iniciando execução diária PNCP - $(date)"

# Executar task completa no ECS Fargate
aws ecs run-task \
  --cluster pncp-extractor-cluster \
  --task-definition pncp-extractor-production-complete:1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-01a1c4a376f9b4349],assignPublicIp=ENABLED}" \
  --count 1

if [ $? -eq 0 ]; then
    echo "✅ Task executada com sucesso!"
    echo "📊 Acompanhe os logs em CloudWatch: /ecs/pncp-extractor"
else
    echo "❌ Erro ao executar task"
    exit 1
fi

echo "🎉 Execução diária iniciada - $(date)"