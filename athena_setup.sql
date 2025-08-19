-- ===============================================
-- SETUP ATHENA PARA DADOS PNCP
-- Execute essas queries no AWS Athena Console
-- ===============================================

-- 1. Criar Database
CREATE DATABASE IF NOT EXISTS pncp_data
COMMENT 'Dados PNCP extraídos automaticamente';

-- 2. Usar o database
USE pncp_data;

-- 3. Criar Tabela Externa com Particionamento Hive
CREATE EXTERNAL TABLE IF NOT EXISTS contratos (
  -- Campos principais dos contratos
  numeroContrato string,
  objetoContrato string,
  valorContrato double,
  dataAssinatura string,
  modalidadeLicitacao string,
  dataPublicacao string,
  sequencialContratacao bigint,
  codigoUnidadeOrgao string,
  
  -- Campos de enriquecimento
  modalidade_nome_dominio string,
  modalidade_descricao_dominio string,
  situacao_compra_nome_dominio string,
  modo_disputa_nome_dominio string,
  criterio_julgamento_nome_dominio string,
  instrumento_convocatorio_nome_dominio string,
  esfera_nome_dominio string,
  poder_nome_dominio string,
  
  -- Campos de filtro
  filtro_aplicado boolean,
  filtro_motivo string,
  filtro_grupo_matched string,
  filtro_termo_matched string,
  filtro_criterio string,
  
  -- Campos de controle
  extraction_date string,
  data_publicacao_control string
)
PARTITIONED BY (
  year int,
  month int
)
STORED AS PARQUET
LOCATION 's3://pncp-extractor-data-prod-566387937580/raw-data/'
TBLPROPERTIES (
  'has_encrypted_data'='false',
  'projection.enabled'='true',
  'projection.year.type'='integer',
  'projection.year.range'='2025,2030',
  'projection.year.interval'='1',
  'projection.month.type'='integer', 
  'projection.month.range'='1,12',
  'projection.month.interval'='1',
  'storage.location.template'='s3://pncp-extractor-data-prod-566387937580/raw-data/year=${year}/month=${month}/'
);

-- 4. Descobrir Partições Automaticamente (caso projection não funcione)
-- MSCK REPAIR TABLE contratos;

-- ===============================================
-- QUERIES DE VALIDAÇÃO E TESTE
-- ===============================================

-- 5. Contar todos os registros
SELECT COUNT(*) as total_registros 
FROM contratos 
WHERE year = 2025 AND month = 8;

-- 6. Registros por dia
SELECT 
  data_publicacao,
  COUNT(*) as registros,
  ROUND(AVG(valorContrato), 2) as valor_medio
FROM contratos 
WHERE year = 2025 AND month = 8 
  AND data_publicacao IS NOT NULL
GROUP BY data_publicacao 
ORDER BY data_publicacao;

-- 7. Análise por modalidade  
SELECT 
  modalidadeLicitacao,
  COUNT(*) as contratos,
  SUM(valorContrato) as valor_total
FROM contratos 
WHERE year = 2025 AND month = 8
GROUP BY modalidadeLicitacao 
ORDER BY contratos DESC;

-- 8. Top 10 contratos por valor
SELECT 
  numeroContrato,
  objetoContrato,
  valorContrato,
  modalidadeLicitacao,
  dataAssinatura
FROM contratos 
WHERE year = 2025 AND month = 8
ORDER BY valorContrato DESC 
LIMIT 10;

-- 9. Análise de filtros (quantos foram aprovados)
SELECT 
  filtro_aplicado,
  filtro_motivo,
  COUNT(*) as quantidade
FROM contratos 
WHERE year = 2025 AND month = 8
GROUP BY filtro_aplicado, filtro_motivo
ORDER BY quantidade DESC;

-- 10. Contratos de TI (exemplo de análise de negócio)
SELECT 
  numeroContrato,
  objetoContrato,
  valorContrato,
  modalidadeLicitacao
FROM contratos 
WHERE year = 2025 AND month = 8
  AND (
    LOWER(objetoContrato) LIKE '%tecnologia%' OR
    LOWER(objetoContrato) LIKE '%informacao%' OR  
    LOWER(objetoContrato) LIKE '%software%' OR
    LOWER(objetoContrato) LIKE '%sistema%'
  )
ORDER BY valorContrato DESC;