# 🧪 Guia de Testes - PNCP Data Extractor

Este documento descreve como testar completamente o sistema PNCP Data Extractor antes do deploy em produção.

## 📋 Visão Geral dos Testes

O sistema possui uma suite completa de testes organizados em camadas:

### 1. 🏠 Testes Locais (`test_local.py`)
- Testa funcionalidades básicas sem AWS
- Valida StorageManager em modo local
- Simula filtro LLM com dados mockados
- Verifica estrutura de diretórios

### 2. 🔬 Testes Unitários (`tests/`)
- `test_storage_manager.py`: Testes completos do StorageManager
- `test_aws_config.py`: Testes completos do AwsConfig
- Executados com `pytest`

### 3. 🏗️ Validação Infraestrutura (`test_infrastructure.py`)
- Valida templates CDK
- Executa `cdk synth` e `cdk diff`
- Verifica estrutura dos stacks
- Valida templates CloudFormation

### 4. 🔗 Testes Integração (`test_integration.py`)
- Testa conectividade real com AWS
- Verifica S3, ECS, Step Functions, etc.
- Valida StorageManager com S3 real
- Requer credenciais AWS

### 5. 🎯 Teste End-to-End (`test_end_to_end.py`)
- Simula extração completa de dados
- Testa todo o pipeline de ponta a ponta
- Valida armazenamento e processamento
- Simula monitoramento

### 6. 🚀 Validação CI/CD (`test_ci_cd.py`)
- Verifica configuração GitHub Actions
- Valida Dockerfile e estrutura
- Documenta secrets necessários
- Prepara plano de deploy

## 🚀 Execução Rápida

### Executar Todos os Testes
```bash
python run_all_tests.py
```

### Executar Teste Específico
```bash
# Testes locais (sem AWS)
python test_local.py

# Testes unitários
pytest tests/ -v

# Validação infraestrutura
python test_infrastructure.py

# Testes integração (requer AWS)
python test_integration.py

# Teste end-to-end
python test_end_to_end.py

# Validação CI/CD
python test_ci_cd.py
```

## ⚙️ Configuração do Ambiente

### Dependências Python
```bash
pip install -r requirements.txt
pip install pytest pytest-cov flake8 black mypy
```

### Variáveis de Ambiente (Opcionais)

Para testes locais básicos:
```bash
# Não requer configuração especial
```

Para testes com AWS:
```bash
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export S3_BUCKET=your_bucket_name  # opcional
```

Para testes com OpenAI:
```bash
export OPENAI_API_KEY=sk-your-api-key
```

## 📊 Interpretação dos Resultados

### ✅ Status de Sucesso
- **Todos Verde**: Sistema pronto para deploy
- **Maioria Verde**: Funcionando com pequenas pendências
- **Muitos Vermelhos**: Requer correções antes do deploy

### ⚠️ Avisos Comuns
- **AWS não configurado**: Normal em ambiente local
- **Secrets não encontrados**: Normal se infraestrutura não foi deployada
- **OpenAI não configurado**: Use modo mock para testes

### ❌ Falhas Críticas
- **Imports falhando**: Verificar requirements.txt
- **Estrutura de arquivos**: Verificar se todos os arquivos foram criados
- **Templates CDK inválidos**: Verificar sintaxe dos stacks

## 🏗️ Fluxo de Testes Recomendado

### Fase 1: Desenvolvimento Local
```bash
# 1. Testes básicos
python test_local.py

# 2. Testes unitários
pytest tests/ -v

# 3. Validar infraestrutura
python test_infrastructure.py
```

### Fase 2: Preparação AWS
```bash
# 1. Configurar credenciais AWS
aws configure

# 2. Testes integração
python test_integration.py

# 3. Teste end-to-end
python test_end_to_end.py
```

### Fase 3: Deploy e CI/CD
```bash
# 1. Validar CI/CD
python test_ci_cd.py

# 2. Configurar GitHub Secrets
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - AWS_ACCOUNT_ID

# 3. Commit e push para testar pipeline
git add .
git commit -m "test: Validar pipeline CI/CD"
git push origin main
```

## 🔍 Troubleshooting

### Erro: ModuleNotFoundError
```bash
# Instalar dependências
pip install -r requirements.txt

# Verificar Python path
python -c "import sys; print(sys.path)"
```

### Erro: AWS Credentials
```bash
# Verificar credenciais
aws sts get-caller-identity

# Configurar região
export AWS_DEFAULT_REGION=us-east-1
```

### Erro: CDK Commands
```bash
# Instalar CDK
npm install -g aws-cdk

# Bootstrap CDK
cd infrastructure
cdk bootstrap
```

### Erro: Docker Build
```bash
# Testar build local
docker build -t pncp-test .

# Verificar Dockerfile
docker run --rm pncp-test python --version
```

## 📈 Métricas de Qualidade

### Cobertura de Testes
- Testes unitários: >80%
- Testes integração: Principais serviços AWS
- Teste E2E: Pipeline completo

### Performance
- Testes locais: <30s
- Testes unitários: <60s
- Testes integração: <300s
- Teste E2E: <180s

### Confiabilidade
- Taxa sucesso local: 100%
- Taxa sucesso AWS: >80% (dependente da infraestrutura)
- False positives: <5%

## 🎯 Próximos Passos Após Testes

1. **Todos os testes passaram**:
   - Configure GitHub Secrets
   - Execute deploy da infraestrutura
   - Monitor produção

2. **Alguns testes falharam**:
   - Corrija falhas críticas
   - Re-execute suite de testes
   - Documente limitações conhecidas

3. **Muitos testes falharam**:
   - Revise configuração do ambiente
   - Verifique dependências
   - Consulte logs detalhados

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique logs detalhados dos testes
2. Consulte documentação AWS CDK
3. Revise configuração GitHub Actions
4. Valide credenciais e permissões AWS

---

**Última atualização**: Agosto 2024  
**Versão dos testes**: 1.0  
**Compatibilidade**: Python 3.12+, AWS CDK 2.x