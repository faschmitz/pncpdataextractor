#!/usr/bin/env python3
"""
Script master para executar todos os testes do PNCP Data Extractor
Organiza e executa toda a suite de testes em sequência lógica
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

def run_script(script_path, description):
    """Executa um script de teste e retorna resultado"""
    print(f"\n{'='*20} {description} {'='*20}")
    print(f"⚡ Executando: {script_path}")
    print(f"🕐 Horário: {datetime.now().strftime('%H:%M:%S')}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutos timeout
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSOU ({duration:.1f}s)")
            if result.stdout:
                print("📄 Output resumido:")
                # Mostrar apenas linhas importantes do output
                lines = result.stdout.split('\n')
                for line in lines:
                    if any(marker in line for marker in ['✅', '❌', '⚠️', '🎉', '📊', 'RESUMO']):
                        print(f"  {line}")
            return True, duration, result.stdout, result.stderr
        else:
            print(f"❌ {description} - FALHOU ({duration:.1f}s)")
            print("📄 Stderr:")
            print(result.stderr)
            return False, duration, result.stdout, result.stderr
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT (>10min)")
        return False, 600, "", "Timeout expired"
    except Exception as e:
        print(f"💥 {description} - ERRO: {e}")
        return False, 0, "", str(e)

def check_script_availability():
    """Verifica quais scripts de teste estão disponíveis"""
    scripts = {
        'test_local.py': 'Testes Locais',
        'tests/test_storage_manager.py': 'Testes Unitários - StorageManager', 
        'tests/test_aws_config.py': 'Testes Unitários - AwsConfig',
        'test_infrastructure.py': 'Validação Infraestrutura CDK',
        'test_integration.py': 'Testes Integração AWS',
        'test_end_to_end.py': 'Teste End-to-End',
        'test_ci_cd.py': 'Validação CI/CD'
    }
    
    available_scripts = {}
    missing_scripts = []
    
    for script_path, description in scripts.items():
        if Path(script_path).exists():
            available_scripts[script_path] = description
        else:
            missing_scripts.append((script_path, description))
    
    return available_scripts, missing_scripts

def run_unit_tests():
    """Executa testes unitários com pytest"""
    print(f"\n{'='*20} Testes Unitários (pytest) {'='*20}")
    
    if not Path('tests').exists():
        print("⚠️  Diretório 'tests' não encontrado")
        return False, 0
    
    start_time = time.time()
    
    try:
        # Verificar se pytest está instalado
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', '--version'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("⚠️  pytest não está instalado")
            print("Execute: pip install pytest pytest-cov")
            return False, 0
        
        # Executar testes
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', 'tests/', '-v', '--tb=short'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ Testes Unitários - PASSOU ({duration:.1f}s)")
            # Mostrar resumo dos testes
            lines = result.stdout.split('\n')
            for line in lines:
                if 'passed' in line or 'failed' in line or 'PASSED' in line or 'FAILED' in line:
                    print(f"  {line}")
            return True, duration
        else:
            print(f"❌ Testes Unitários - FALHOU ({duration:.1f}s)")
            print("📄 Erros:")
            print(result.stdout[-1000:])  # Últimas 1000 chars
            return False, duration
            
    except subprocess.TimeoutExpired:
        print("⏰ Testes Unitários - TIMEOUT")
        return False, 300
    except Exception as e:
        print(f"💥 Testes Unitários - ERRO: {e}")
        return False, 0

def generate_test_report(results):
    """Gera relatório final dos testes"""
    print("\n" + "="*80)
    print("📊 RELATÓRIO FINAL DOS TESTES - PNCP DATA EXTRACTOR")
    print("="*80)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results if result['passed'])
    total_duration = sum(result['duration'] for result in results)
    
    print(f"\n📈 ESTATÍSTICAS GERAIS:")
    print(f"Total de testes: {total_tests}")
    print(f"Testes passou: {passed_tests}")
    print(f"Testes falhou: {total_tests - passed_tests}")
    print(f"Taxa de sucesso: {passed_tests/total_tests*100:.1f}%")
    print(f"Tempo total: {total_duration:.1f}s ({total_duration/60:.1f}min)")
    
    print(f"\n📋 RESULTADOS DETALHADOS:")
    for i, result in enumerate(results, 1):
        status = "✅ PASSOU" if result['passed'] else "❌ FALHOU"
        print(f"{i:2d}. {result['description']:<35} {status:10} ({result['duration']:5.1f}s)")
    
    # Categorizar resultados
    critical_failures = []
    warnings = []
    
    for result in results:
        if not result['passed']:
            if any(critical in result['description'] for critical in ['Unitários', 'End-to-End', 'Locais']):
                critical_failures.append(result['description'])
            else:
                warnings.append(result['description'])
    
    if critical_failures:
        print(f"\n🚨 FALHAS CRÍTICAS ({len(critical_failures)}):")
        for failure in critical_failures:
            print(f"  ❌ {failure}")
    
    if warnings:
        print(f"\n⚠️  AVISOS ({len(warnings)}):")
        for warning in warnings:
            print(f"  ⚠️  {warning}")
    
    # Recomendações
    print(f"\n💡 RECOMENDAÇÕES:")
    
    if passed_tests == total_tests:
        print("🎉 Todos os testes passaram! Sistema pronto para deploy.")
        print("📝 Próximos passos:")
        print("  1. Configure secrets no GitHub")
        print("  2. Faça commit para testar CI/CD") 
        print("  3. Deploy da infraestrutura AWS")
        print("  4. Monitoramento em produção")
    elif passed_tests >= total_tests * 0.8:
        print("✅ Maioria dos testes passou. Sistema funcional com algumas pendências.")
        print("📝 Corrija as falhas antes do deploy em produção.")
    else:
        print("❌ Muitos testes falharam. Revise configuração antes de prosseguir.")
        print("📝 Foque nas falhas críticas primeiro.")
    
    return passed_tests == total_tests

def main():
    """Executa toda a suite de testes"""
    print("🚀 PNCP DATA EXTRACTOR - SUITE COMPLETA DE TESTES")
    print(f"⏰ Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Verificar scripts disponíveis
    available_scripts, missing_scripts = check_script_availability()
    
    if missing_scripts:
        print("⚠️  Scripts de teste faltando:")
        for script, desc in missing_scripts:
            print(f"  - {script}: {desc}")
        print()
    
    print(f"📋 Executando {len(available_scripts)} + 1 suites de teste...")
    
    results = []
    
    # 1. Testes Unitários (pytest)
    if Path('tests').exists():
        passed, duration = run_unit_tests()
        results.append({
            'description': 'Testes Unitários (pytest)',
            'passed': passed,
            'duration': duration
        })
    
    # 2. Executar scripts de teste em ordem lógica
    test_order = [
        ('test_local.py', 'Testes Locais'),
        ('test_infrastructure.py', 'Validação Infraestrutura CDK'),
        ('test_integration.py', 'Testes Integração AWS'),
        ('test_end_to_end.py', 'Teste End-to-End'),
        ('test_ci_cd.py', 'Validação CI/CD')
    ]
    
    for script_path, description in test_order:
        if script_path in available_scripts:
            passed, duration, stdout, stderr = run_script(script_path, description)
            results.append({
                'description': description,
                'passed': passed,
                'duration': duration,
                'stdout': stdout,
                'stderr': stderr
            })
    
    # 3. Gerar relatório final
    success = generate_test_report(results)
    
    print(f"\n⏰ Concluído em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Execução interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Erro crítico: {e}")
        sys.exit(1)