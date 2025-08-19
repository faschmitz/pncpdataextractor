#!/bin/bash
# Script para fazer deploy da imagem Docker para ECR

set -e

# Configurações
AWS_ACCOUNT_ID="566387937580"
AWS_REGION="us-east-2"
REPOSITORY_NAME="pncp-extractor"
IMAGE_TAG="latest"

# URLs
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
FULL_IMAGE_URI="${ECR_URI}/${REPOSITORY_NAME}:${IMAGE_TAG}"

echo "🚀 Iniciando deploy para ECR..."
echo "   Repository: ${FULL_IMAGE_URI}"

# 1. Fazer login no ECR
echo "🔐 Fazendo login no ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# 2. Build da imagem
echo "🔨 Fazendo build da imagem Docker..."
docker build -t ${REPOSITORY_NAME}:${IMAGE_TAG} .

# 3. Tag para ECR
echo "🏷️  Taggeando imagem para ECR..."
docker tag ${REPOSITORY_NAME}:${IMAGE_TAG} ${FULL_IMAGE_URI}

# 4. Push para ECR
echo "📤 Fazendo push da imagem para ECR..."
docker push ${FULL_IMAGE_URI}

echo "✅ Deploy concluído com sucesso!"
echo "   Imagem disponível em: ${FULL_IMAGE_URI}"

# 5. Verificar se a imagem foi criada
echo "🔍 Verificando imagem no ECR..."
aws ecr describe-images --repository-name ${REPOSITORY_NAME} --region ${AWS_REGION} --query 'imageDetails[0].{imageTags:imageTags,imagePushedAt:imagePushedAt,imageSizeInBytes:imageSizeInBytes}'

echo "🎉 Deploy para ECR concluído! O agendamento diário agora funcionará corretamente."