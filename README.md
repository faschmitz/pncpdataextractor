# PNCP Data Extractor

Sistema de extração incremental de dados de contratações públicas do Portal Nacional de Contratações Públicas (PNCP).

## Características

- ✅ **Extração Diária**: Um arquivo Parquet por dia
- ✅ **Estrutura Particionada**: Organização por ano/mês
- ✅ **Filtros Inteligentes**: Busca exata por palavras (sem acentos/maiúsculas)
- ✅ **Consolidação Automática**: Arquivos antigos são consolidados mensalmente
- ✅ **Metadata Completa**: Log detalhado de cada extração

## Estrutura de Arquivos

```
PNCP/
├── config.json              # Configurações do sistema
├── state.json               # Estado das extrações
├── filtros.json            # Termos de filtro organizados por grupos
├── extractor.py            # Extrator principal
├── filter_manager.py       # Gerenciador de filtros
├── domain_tables.py        # Tabelas de domínio do PNCP
├── requirements.txt        # Dependências Python
├── extractor.log          # Log de execução
├── data/                  # Dados extraídos
│   ├── year=2025/
│   │   └── month=01/
│   │       └── pncp_contratos_20250120.parquet
│   ├── consolidated/      # Arquivos consolidados
│   └── metadata/         # Logs e relatórios
│       └── extraction_log.json
└── venv/                 # Ambiente virtual Python
```

## Uso

### Instalação
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### Comandos

```bash
# Extração incremental diária (padrão)
python extractor.py

# Extração histórica completa desde 01/01/2025
python extractor.py --historical

# Consolidação de arquivos antigos (>30 dias)
python extractor.py --consolidate

# Usar configuração personalizada
python extractor.py --config custom_config.json
```

### Configuração para Cron (Execução Diária)
```bash
# Adicionar ao crontab para execução diária às 6h
0 6 * * * cd /path/to/PNCP && source venv/bin/activate && python extractor.py
```

## Configuração

O arquivo `config.json` contém todas as configurações do sistema:

- **Data inicial**: 01/01/2025
- **Estrutura particionada**: Ativa
- **Consolidação**: Arquivos com +30 dias
- **Filtros**: Ativo com busca exata por palavras

## Filtros

O sistema usa filtros baseados em 38 grupos de produtos (AUDIO, CANETAS, BORRACHA, etc.) com busca exata por palavras, ignorando apenas acentos e maiúsculas/minúsculas.

## Dados Gerados

- **Formato**: Parquet (alta performance)
- **Granularidade**: Diária  
- **Metadata**: Cada registro inclui informações de filtro aplicado
- **Enriquecimento**: Dados complementados com tabelas de domínio PNCP