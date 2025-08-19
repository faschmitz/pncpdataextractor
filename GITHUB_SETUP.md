# GitHub CI/CD Setup - PNCP Data Extractor

## 🚀 Pipeline Automatizado Completo

O projeto já possui um pipeline CI/CD completo configurado que realiza:
- ✅ Testes automatizados (pytest, linting, type checking)
- ✅ Build e push de imagens Docker para ECR
- ✅ Deploy de infraestrutura via AWS CDK
- ✅ Update automático das task definitions ECS
- ✅ Testes de integração pós-deploy
- ✅ Notificações de status

## 🔐 GitHub Secrets Obrigatórios

Para o pipeline funcionar, configure estes secrets em **Settings → Secrets and variables → Actions**:

### AWS Credentials (OBRIGATÓRIOS)
```
AWS_ACCESS_KEY_ID = [sua_access_key_aqui]
AWS_SECRET_ACCESS_KEY = [sua_secret_key_aqui]  
AWS_ACCOUNT_ID = [seu_account_id_aqui]
```

### Opcional
```
CODECOV_TOKEN = [seu_token_codecov_se_desejar_coverage]
```

## 🎯 Como Configurar

### 1. Acessar GitHub Secrets
1. Vá para o repositório no GitHub
2. Clique em **Settings** 
3. No menu lateral, clique **Secrets and variables** → **Actions**
4. Clique **New repository secret**

### 2. Adicionar cada secret
Para cada secret acima:
- **Name**: Nome exato (ex: `AWS_ACCESS_KEY_ID`)
- **Value**: Valor correspondente
- Clique **Add secret**

### 3. Validar configuração
Execute o script de validação local:
```bash
python test_ci_cd.py
```

## 🚀 Trigger do Pipeline

### Automático
- **Push para main**: Deploy completo automático
- **Pull Request**: Apenas testes

### Manual  
- **Actions → CI/CD Pipeline → Run workflow**
- Escolha environment (prod/staging)
- Opção de deploy de infraestrutura

## 📊 Monitoramento

### GitHub Actions
- Acesse: **Actions** tab no repositório
- Monitore execução de cada job
- Logs detalhados em caso de falha

### AWS Console
- **ECR**: Verificar imagens Docker
- **ECS**: Status do cluster e tasks
- **CloudFormation**: Stacks de infraestrutura

## 🔄 Fluxo Completo

```
Commit → Push to main
    ↓
1. Tests (pytest, lint, mypy)
    ↓
2. Build Docker Image → Push ECR
    ↓ 
3. Deploy Infrastructure (CDK)
    ↓
4. Update ECS Task Definition
    ↓
5. Integration Tests
    ↓
6. Success Notification ✅
```

## 🎉 Benefícios

### Deploy Automático de Setembro
- **1º/09**: Sistema extrai dados automaticamente
- **Novos schemas**: Deployados via CI/CD
- **Zero downtime**: Rolling updates
- **Rollback**: Versioning de task definitions

### Qualidade Garantida
- **Tests first**: Falha early, não late
- **Security scans**: Trivy nas imagens
- **Infrastructure as code**: CDK versionado
- **Integration tests**: Validação completa

## 🛠️ Resolução de Problemas

### Pipeline Failing?
1. Verifique logs detalhados em Actions
2. Confirme secrets configurados corretamente  
3. Valide permissions IAM se necessário
4. Execute `python test_ci_cd.py` localmente

### ECS Task Failing?
1. Verifique CloudWatch logs
2. Confirme ECR image foi criada
3. Valide task definition atualizada
4. Check ECS cluster capacity

## ✅ Status Atual

- ✅ **Workflow configurado** e corrigido
- ✅ **Referências AWS** atualizadas para us-east-2
- ✅ **Task definitions** alinhadas
- ⚠️  **Secrets necessários** para ativação
- 🎯 **Pronto para deploy** após configuração de secrets

---

**Próximo passo**: Configure os GitHub Secrets e faça um commit para testar o pipeline completo! 🚀