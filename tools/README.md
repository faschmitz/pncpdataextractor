# PNCP Tools

Ferramentas auxiliares para manutenção e diagnóstico do sistema PNCP Data Extractor.

## 🔧 Schema Fixes (`schema_fixes/`)

Ferramentas para correção de problemas de schema em arquivos parquet que causam erros `HIVE_CANNOT_OPEN_SPLIT` no Athena/Qlik.

### `fix_parquet_schemas.py`
**Script principal para normalização de schemas**

Resolve inconsistências de schema normalizando campos struct para evitar conflitos entre `PrimitiveColumnIO` e `GroupColumnIO`.

```bash
python3 tools/schema_fixes/fix_parquet_schemas.py
```

**Funcionalidades:**
- Normaliza campos struct (unidadeOrgao, orgaoEntidade, etc.)
- Corrige incompatibilidades de tipo
- Mantém backup automático dos arquivos originais
- Processa múltiplos arquivos em paralelo

### `fix_all_august_files.py`
**Correção em massa de arquivos de um período**

Processa todos os arquivos de um mês/período aplicando normalização de schema.

```bash
python3 tools/schema_fixes/fix_all_august_files.py
```

**Funcionalidades:**
- Processamento em lote com paralelização
- Schema de referência baseado em arquivo funcional
- Backup automático de todos os arquivos
- Relatório detalhado de sucessos/falhas

### `rebuild_problematic_file.py`
**Reconstrução completa de arquivos específicos**

Para casos onde a normalização simples não resolve, reconstrói o arquivo do zero.

```bash
python3 tools/schema_fixes/rebuild_problematic_file.py
```

**Funcionalidades:**
- Reconstrução byte-level do arquivo parquet
- Aplicação de schema de referência
- Backup do arquivo original
- Verificação de integridade pós-rebuild

## 📊 Monitoring (`monitoring/`)

### `monitor_reprocessing.sh`
**Monitoramento de tasks ECS e processamento**

Script para acompanhar execução de tasks ECS e validar resultados.

```bash
./tools/monitoring/monitor_reprocessing.sh
```

**Funcionalidades:**
- Status de tasks ECS em execução
- Listagem de arquivos mais recentes no S3
- Verificação do state.json atual
- Logs do CloudWatch

## 🐛 Debug (`debug/`)

### `debug_state.py`
**Diagnóstico de persistência de estado**

Testa lógica de determinação de datas e persistência no S3.

```bash
python3 tools/debug/debug_state.py
```

**Funcionalidades:**
- Simulação da lógica de extração incremental
- Teste de salvamento/leitura do S3
- Diagnóstico de problemas de state

## 📖 Histórico

Estas ferramentas foram desenvolvidas durante a resolução do problema crítico de schema inconsistency que causava erros `HIVE_CANNOT_OPEN_SPLIT` no Qlik Cloud, impedindo o acesso aos dados via Athena.

**Problema resolvido:** Inconsistências de schema em arquivos parquet onde alguns campos eram definidos como `NULL` vs `STRUCT`, causando falhas na leitura pelo Hive/Trino engine do Athena.

**Solução implementada:** Normalização completa de schemas usando PyArrow, com fallback para reconstrução de arquivos quando necessário.

---

*Ferramentas desenvolvidas com Claude Code para manutenção do PNCP Data Extractor*