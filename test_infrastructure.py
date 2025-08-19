#!/usr/bin/env python3
"""
Script de validação da infraestrutura AWS CDK
Testa se os templates CloudFormation estão corretos antes do deploy
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path

def run_command(command, cwd=None, capture_output=True):
    """Executa comando e retorna resultado"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            timeout=300  # 5 minutos timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Comando excedeu timeout de 5 minutos"
    except Exception as e:
        return False, "", str(e)

def test_python_dependencies():
    """Testa se dependências Python do CDK estão instaladas"""
    print("🧪 Testando dependências Python do CDK...")
    
    required_packages = [
        'aws-cdk-lib',
        'constructs',
        'boto3'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"⚠️  Pacotes faltando: {', '.join(missing_packages)}")
        print("Execute: cd infrastructure && pip install -r requirements.txt")
        return False
    
    return True

def test_node_dependencies():
    """Testa se Node.js e AWS CDK estão instalados"""
    print("🧪 Testando dependências Node.js...")
    
    # Testar Node.js
    success, stdout, stderr = run_command("node --version")
    if not success:
        print("❌ Node.js não encontrado")
        return False
    else:
        print(f"✅ Node.js {stdout.strip()}")
    
    # Testar AWS CDK
    success, stdout, stderr = run_command("cdk --version")
    if not success:
        print("❌ AWS CDK não encontrado")
        print("Execute: npm install -g aws-cdk")
        return False
    else:
        print(f"✅ AWS CDK {stdout.strip()}")
    
    return True

def test_aws_credentials():
    """Testa se credenciais AWS estão configuradas"""
    print("🧪 Testando credenciais AWS...")
    
    # Verificar variáveis de ambiente
    aws_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION']
    missing_vars = []
    
    for var in aws_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        print("Configure as credenciais AWS antes de prosseguir")
        return False
    
    # Testar conexão com AWS
    success, stdout, stderr = run_command("aws sts get-caller-identity")
    if not success:
        print(f"❌ Erro ao conectar com AWS: {stderr}")
        return False
    else:
        try:
            identity = json.loads(stdout)
            print(f"✅ AWS conectado - Account: {identity['Account']}")
            return True
        except json.JSONDecodeError:
            print("❌ Resposta AWS inválida")
            return False

def test_cdk_bootstrap():
    """Testa se CDK bootstrap foi executado"""
    print("🧪 Testando CDK bootstrap...")
    
    region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    success, stdout, stderr = run_command(f"aws cloudformation describe-stacks --stack-name CDKToolkit --region {region}")
    
    if not success:
        print("⚠️  CDK bootstrap não foi executado")
        print("Execute: cd infrastructure && cdk bootstrap")
        return False
    else:
        print("✅ CDK bootstrap executado")
        return True

def test_cdk_synth():
    """Testa síntese dos templates CDK"""
    print("🧪 Testando síntese CDK...")
    
    infrastructure_dir = Path(__file__).parent / "infrastructure"
    
    if not infrastructure_dir.exists():
        print("❌ Diretório infrastructure não encontrado")
        return False
    
    success, stdout, stderr = run_command("cdk synth --all", cwd=str(infrastructure_dir))
    
    if not success:
        print(f"❌ Erro na síntese CDK:")
        print(stderr)
        return False
    else:
        print("✅ Síntese CDK bem-sucedida")
        # Verificar se templates foram gerados
        if "Resources:" in stdout:
            print("✅ Templates CloudFormation gerados")
            return True
        else:
            print("⚠️  Templates podem estar vazios")
            return False

def test_cdk_diff():
    """Testa diff do CDK contra ambiente atual"""
    print("🧪 Testando CDK diff...")
    
    infrastructure_dir = Path(__file__).parent / "infrastructure"
    success, stdout, stderr = run_command("cdk diff --all", cwd=str(infrastructure_dir))
    
    # CDK diff pode retornar código 1 mesmo com sucesso se houver diferenças
    if "Error" in stderr and "AccessDenied" not in stderr:
        print(f"❌ Erro no CDK diff: {stderr}")
        return False
    else:
        print("✅ CDK diff executado")
        if "Stack" in stdout:
            print("ℹ️  Existem diferenças a serem aplicadas")
        else:
            print("ℹ️  Nenhuma diferença detectada")
        return True

def test_stack_structure():
    """Testa estrutura dos stacks CDK"""
    print("🧪 Testando estrutura dos stacks...")
    
    infrastructure_dir = Path(__file__).parent / "infrastructure"
    
    # Verificar arquivos essenciais
    required_files = [
        "app.py",
        "requirements.txt",
        "stacks/storage_stack.py",
        "stacks/security_stack.py", 
        "stacks/compute_stack.py",
        "stacks/orchestration_stack.py",
        "stacks/monitoring_stack.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = infrastructure_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)
            print(f"❌ {file_path}")
        else:
            print(f"✅ {file_path}")
    
    if missing_files:
        print(f"⚠️  Arquivos faltando: {', '.join(missing_files)}")
        return False
    
    return True

def test_cdk_list_stacks():
    """Testa listagem de stacks CDK"""
    print("🧪 Testando listagem de stacks...")
    
    infrastructure_dir = Path(__file__).parent / "infrastructure"
    success, stdout, stderr = run_command("cdk list", cwd=str(infrastructure_dir))
    
    if not success:
        print(f"❌ Erro ao listar stacks: {stderr}")
        return False
    
    expected_stacks = [
        "PNCPExtractorStorageStack",
        "PNCPExtractorSecurityStack", 
        "PNCPExtractorComputeStack",
        "PNCPExtractorOrchestrationStack",
        "PNCPExtractorMonitoringStack"
    ]
    
    found_stacks = []
    for line in stdout.split('\n'):
        line = line.strip()
        if line and not line.startswith('*'):
            found_stacks.append(line)
            print(f"✅ Stack encontrado: {line}")
    
    missing_stacks = [stack for stack in expected_stacks if stack not in found_stacks]
    if missing_stacks:
        print(f"⚠️  Stacks faltando: {', '.join(missing_stacks)}")
        return False
    
    print(f"✅ Todos os {len(expected_stacks)} stacks encontrados")
    return True

def test_cloudformation_templates():
    """Testa validação dos templates CloudFormation gerados"""
    print("🧪 Testando templates CloudFormation...")
    
    infrastructure_dir = Path(__file__).parent / "infrastructure"
    
    # Gerar templates em diretório temporário
    with tempfile.TemporaryDirectory() as temp_dir:
        success, stdout, stderr = run_command(
            f"cdk synth --all --output {temp_dir}",
            cwd=str(infrastructure_dir)
        )
        
        if not success:
            print(f"❌ Erro ao gerar templates: {stderr}")
            return False
        
        # Verificar se templates foram gerados
        template_files = list(Path(temp_dir).glob("*.template.json"))
        
        if not template_files:
            print("❌ Nenhum template CloudFormation gerado")
            return False
        
        print(f"✅ {len(template_files)} templates gerados")
        
        # Validar cada template
        for template_file in template_files:
            success, stdout, stderr = run_command(
                f"aws cloudformation validate-template --template-body file://{template_file}"
            )
            
            if not success:
                print(f"❌ Template inválido: {template_file.name}")
                print(f"Erro: {stderr}")
                return False
            else:
                print(f"✅ Template válido: {template_file.name}")
        
        return True

def run_all_infrastructure_tests():
    """Executa todos os testes de infraestrutura"""
    print("=" * 60)
    print("🚀 PNCP Data Extractor - Testes de Infraestrutura")
    print("=" * 60)
    
    tests = [
        ("Dependências Python", test_python_dependencies),
        ("Dependências Node.js", test_node_dependencies),
        ("Credenciais AWS", test_aws_credentials),
        ("CDK Bootstrap", test_cdk_bootstrap),
        ("Estrutura dos Stacks", test_stack_structure),
        ("Listagem de Stacks", test_cdk_list_stacks),
        ("Síntese CDK", test_cdk_synth),
        ("CDK Diff", test_cdk_diff),
        ("Templates CloudFormation", test_cloudformation_templates)
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
    print("📊 RESUMO DOS TESTES DE INFRAESTRUTURA")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1
    
    print(f"\nResultado: {passed}/{len(results)} testes passaram")
    
    if passed == len(results):
        print("🎉 Infraestrutura validada! Pronta para deploy.")
        return True
    else:
        print("⚠️  Alguns testes falharam. Corrija os problemas antes do deploy.")
        return False

if __name__ == "__main__":
    success = run_all_infrastructure_tests()
    sys.exit(0 if success else 1)