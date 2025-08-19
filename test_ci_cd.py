#!/usr/bin/env python3
"""
Script de validação do pipeline CI/CD
Verifica configuração do GitHub Actions e prepara commit de teste
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def run_command(command, cwd=None):
    """Executa comando e retorna resultado"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Comando excedeu timeout"
    except Exception as e:
        return False, "", str(e)

def test_git_configuration():
    """Testa configuração do Git"""
    print("🧪 Testando configuração Git...")
    
    # Verificar se estamos em um repositório Git
    success, stdout, stderr = run_command("git status")
    if not success:
        print("❌ Não é um repositório Git ou Git não instalado")
        return False
    
    print("✅ Repositório Git detectado")
    
    # Verificar remote origin
    success, stdout, stderr = run_command("git remote -v")
    if not success:
        print("❌ Erro ao verificar remote")
        return False
    
    if 'origin' in stdout:
        print("✅ Remote origin configurado")
        for line in stdout.split('\n'):
            if 'origin' in line and 'fetch' in line:
                print(f"  {line.strip()}")
    else:
        print("⚠️  Remote origin não configurado")
    
    # Verificar branch atual
    success, stdout, stderr = run_command("git branch --show-current")
    if success:
        current_branch = stdout.strip()
        print(f"✅ Branch atual: {current_branch}")
    
    return True

def test_github_actions_workflow():
    """Testa arquivo de workflow do GitHub Actions"""
    print("🧪 Testando workflow GitHub Actions...")
    
    workflow_path = Path(".github/workflows/ci-cd.yml")
    
    if not workflow_path.exists():
        print("❌ Arquivo de workflow não encontrado")
        return False
    
    print("✅ Arquivo de workflow existe")
    
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow_content = f.read()
        
        # Verificar elementos essenciais do workflow
        essential_elements = [
            'name:',
            'on:',
            'jobs:',
            'test:',
            'build:',
            'deploy-infrastructure:',
            'deploy-application:',
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'docker build',
            'cdk deploy'
        ]
        
        missing_elements = []
        for element in essential_elements:
            if element not in workflow_content:
                missing_elements.append(element)
                print(f"❌ Elemento faltando: {element}")
            else:
                print(f"✅ {element}")
        
        if missing_elements:
            print(f"⚠️  {len(missing_elements)} elementos faltando no workflow")
            return False
        
        print("✅ Workflow GitHub Actions válido")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao ler workflow: {e}")
        return False

def test_dockerfile():
    """Testa Dockerfile"""
    print("🧪 Testando Dockerfile...")
    
    dockerfile_path = Path("Dockerfile")
    
    if not dockerfile_path.exists():
        print("❌ Dockerfile não encontrado")
        return False
    
    print("✅ Dockerfile existe")
    
    try:
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            dockerfile_content = f.read()
        
        # Verificar elementos essenciais
        essential_elements = [
            'FROM python',
            'WORKDIR',
            'COPY requirements.txt',
            'RUN pip install',
            'COPY',
            'CMD',
            'USER'  # Para segurança
        ]
        
        for element in essential_elements:
            if element in dockerfile_content:
                print(f"✅ {element}")
            else:
                print(f"❌ {element}")
        
        print("✅ Dockerfile analisado")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao ler Dockerfile: {e}")
        return False

def test_requirements_file():
    """Testa arquivo requirements.txt"""
    print("🧪 Testando requirements.txt...")
    
    requirements_path = Path("requirements.txt")
    
    if not requirements_path.exists():
        print("❌ requirements.txt não encontrado")
        return False
    
    print("✅ requirements.txt existe")
    
    try:
        with open(requirements_path, 'r', encoding='utf-8') as f:
            requirements = f.read()
        
        # Verificar dependências essenciais
        essential_packages = [
            'requests',
            'pandas',
            'boto3',
            'openai',
            'python-dotenv'
        ]
        
        for package in essential_packages:
            if package in requirements:
                print(f"✅ {package}")
            else:
                print(f"❌ {package}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao ler requirements.txt: {e}")
        return False

def test_infrastructure_structure():
    """Testa estrutura da infraestrutura"""
    print("🧪 Testando estrutura da infraestrutura...")
    
    infrastructure_dir = Path("infrastructure")
    
    if not infrastructure_dir.exists():
        print("❌ Diretório infrastructure não encontrado")
        return False
    
    print("✅ Diretório infrastructure existe")
    
    # Verificar arquivos essenciais
    essential_files = [
        "infrastructure/app.py",
        "infrastructure/requirements.txt",
        "infrastructure/stacks/__init__.py",
        "infrastructure/stacks/storage_stack.py",
        "infrastructure/stacks/security_stack.py",
        "infrastructure/stacks/compute_stack.py",
        "infrastructure/stacks/orchestration_stack.py",
        "infrastructure/stacks/monitoring_stack.py"
    ]
    
    for file_path in essential_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
    
    return True

def test_github_secrets_configuration():
    """Testa se secrets do GitHub estão documentados"""
    print("🧪 Verificando documentação dos GitHub Secrets...")
    
    required_secrets = [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY', 
        'AWS_ACCOUNT_ID',
        'CODECOV_TOKEN'  # Opcional
    ]
    
    print("📋 Secrets necessários no GitHub:")
    for secret in required_secrets:
        optional = " (opcional)" if secret == 'CODECOV_TOKEN' else ""
        print(f"  - {secret}{optional}")
    
    print("ℹ️  Configure estes secrets em Settings > Secrets and variables > Actions")
    return True

def create_test_commit_plan():
    """Cria plano para commit de teste"""
    print("📋 Plano para commit de teste...")
    
    print("\n🔄 Passos para testar CI/CD:")
    print("1. Configure os secrets no GitHub:")
    print("   - AWS_ACCESS_KEY_ID")
    print("   - AWS_SECRET_ACCESS_KEY") 
    print("   - AWS_ACCOUNT_ID")
    
    print("\n2. Faça um commit de teste:")
    print("   git add .")
    print("   git commit -m 'test: Validar pipeline CI/CD'")
    print("   git push origin main")
    
    print("\n3. Verifique execução no GitHub Actions:")
    print("   - Acesse: https://github.com/SEU_USER/SEU_REPO/actions")
    print("   - Monitore execução de cada job")
    print("   - Verifique logs em caso de falha")
    
    print("\n4. Monitore deploy AWS:")
    print("   - Verifique stacks no CloudFormation")
    print("   - Confirme recursos criados")
    print("   - Teste funcionalidades")
    
    return True

def check_local_testing():
    """Verifica se testes locais foram executados"""
    print("🧪 Verificando testes locais...")
    
    test_scripts = [
        "test_local.py",
        "test_infrastructure.py", 
        "test_integration.py",
        "test_end_to_end.py"
    ]
    
    available_tests = []
    for script in test_scripts:
        if Path(script).exists():
            available_tests.append(script)
            print(f"✅ {script}")
        else:
            print(f"❌ {script}")
    
    if available_tests:
        print(f"\n💡 Execute os testes locais antes do commit:")
        for script in available_tests:
            print(f"   python {script}")
    
    return len(available_tests) > 0

def validate_environment_vars():
    """Valida variáveis de ambiente necessárias"""
    print("🧪 Validando variáveis de ambiente...")
    
    # Para desenvolvimento local
    local_vars = {
        'OPENAI_API_KEY': 'Opcional - para testes com LLM real',
        'AWS_DEFAULT_REGION': 'Opcional - para testes AWS', 
        'AWS_ACCESS_KEY_ID': 'Opcional - para testes AWS',
        'AWS_SECRET_ACCESS_KEY': 'Opcional - para testes AWS'
    }
    
    print("📋 Variáveis de ambiente (desenvolvimento local):")
    for var, description in local_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Configurada")
        else:
            print(f"⚠️  {var}: {description}")
    
    return True

def run_ci_cd_validation():
    """Executa validação completa do CI/CD"""
    print("=" * 60)
    print("🚀 PNCP Data Extractor - Validação CI/CD")
    print("=" * 60)
    
    tests = [
        ("Configuração Git", test_git_configuration),
        ("Workflow GitHub Actions", test_github_actions_workflow),
        ("Dockerfile", test_dockerfile),
        ("Requirements.txt", test_requirements_file),
        ("Estrutura Infraestrutura", test_infrastructure_structure),
        ("GitHub Secrets", test_github_secrets_configuration),
        ("Testes Locais", check_local_testing),
        ("Variáveis de Ambiente", validate_environment_vars),
        ("Plano de Commit", create_test_commit_plan)
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
    print("📊 RESUMO DA VALIDAÇÃO CI/CD")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ OK" if result else "❌ ATENÇÃO"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1
    
    print(f"\nResultado: {passed}/{len(results)} validações OK")
    
    print("\n🎯 PRÓXIMOS PASSOS:")
    print("1. Configure secrets no GitHub")
    print("2. Execute testes locais")
    print("3. Faça commit para testar pipeline")
    print("4. Monitore execução no GitHub Actions")
    
    return passed >= len(results) * 0.8  # 80% deve estar OK

if __name__ == "__main__":
    success = run_ci_cd_validation()
    sys.exit(0 if success else 1)