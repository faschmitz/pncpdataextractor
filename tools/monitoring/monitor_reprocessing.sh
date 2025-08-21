#!/bin/bash
echo "🔍 MONITORAMENTO DO REPROCESSAMENTO"
echo "================================="
echo ""

echo "📅 $(date)"
echo ""

echo "1. Verificando tasks ECS em execução:"
aws ecs list-tasks --cluster pncp-extractor-cluster --desired-status RUNNING

echo ""
echo "2. Verificando arquivos mais recentes no S3:"
aws s3 ls s3://pncp-extractor-data-prod-566387937580/raw-data/year=2025/month=08/ --recursive | tail -5

echo ""
echo "3. Estado atual:"
aws s3 cp s3://pncp-extractor-data-prod-566387937580/state.json - | jq '.last_extraction_date, .processed_dates[-3:]'

echo ""
echo "4. Log do CloudWatch (últimas 10 linhas):"
aws logs describe-log-groups --log-group-name-prefix "/aws/ecs/" | jq -r '.logGroups[0].logGroupName' | head -1 | xargs -I {} aws logs tail {} --since 10m

echo ""
echo "Para monitoramento contínuo, execute:"
echo "watch -n 30 './monitor_reprocessing.sh'"