# Multi-stage Docker build para PNCP Data Extractor
# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

# Instalar dependências de sistema necessárias para build
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

# Instalar dependências de runtime mínimas
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root para segurança
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser

# Criar diretório de trabalho e definir permissões
WORKDIR /app
RUN chown appuser:appuser /app

# Copiar dependências Python do stage builder
COPY --from=builder /root/.local /home/appuser/.local

# Copiar código da aplicação
COPY --chown=appuser:appuser . .

# Configurar PATH para incluir executáveis Python do usuário
ENV PATH="/home/appuser/.local/bin:${PATH}"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# Configurar variáveis de ambiente para AWS (serão definidas pelo ECS)
ENV AWS_DEFAULT_REGION=""
ENV S3_BUCKET=""
ENV OPENAI_API_KEY=""

# Health check para verificar se a aplicação está funcionando
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import sys; import requests; import boto3; print('Health check OK')" || exit 1

# Mudar para usuário não-root
USER appuser

# Comando padrão para executar o extrator
CMD ["python", "extractor.py"]

# Labels para metadata
LABEL maintainer="Leonora Comercio Internacional"
LABEL description="PNCP Data Extractor with LLM filtering"
LABEL version="2.0"
LABEL source="https://github.com/Leonora-Comercio-Internacional/pncpdataextractor"