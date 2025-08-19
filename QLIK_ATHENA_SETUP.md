# 🔗 Qlik Cloud + AWS Athena - Setup Completo

## 📋 Pré-requisitos
1. **Qlik Cloud**: Tenant ativo
2. **AWS Athena**: Database `pncp_data` configurado
3. **Permissions**: IAM para Qlik acessar Athena

## 🚀 Métodos de Conexão

### **Método 1: Amazon Athena Connector (RECOMENDADO)**

#### **1.1 Configurar no Qlik Cloud**
1. **Data Integration** → **Add data**
2. **Connectors** → **Amazon Athena**
3. **Configurações**:
   - **Region**: us-east-2
   - **S3 Staging Directory**: `s3://pncp-extractor-data-prod-566387937580/athena-results/`
   - **Database**: `pncp_data`
   - **Workgroup**: `primary` (ou criar específico)

#### **1.2 Credenciais AWS**
```json
{
  "access_key_id": "[sua_access_key_aqui]",
  "secret_access_key": "[sua_secret_key_aqui]",
  "region": "us-east-2"
}
```

#### **1.3 Query de Teste**
```sql
SELECT COUNT(*) as total_contratos
FROM contratos 
WHERE year = 2025 AND month = 8;
```

### **Método 2: JDBC Connection (Alternativo)**

#### **2.1 JDBC URL**
```
jdbc:awsathena://athena.us-east-2.amazonaws.com:443;
S3OutputLocation=s3://pncp-extractor-data-prod-566387937580/athena-results/;
Workgroup=primary
```

#### **2.2 Driver**
- **Download**: Amazon Athena JDBC Driver
- **Class**: `com.simba.athena.jdbc.Driver`

## 📊 Modelo de Dados Qlik Otimizado

### **3.1 Script de Carga Principal**
```qlik
// Conectar ao Athena
CONNECT TO 'lib://Amazon Athena';

// Carregar dados principais
Contratos:
LOAD
    numeroContrato,
    objetoContrato,
    valorContrato,
    DATE(dataAssinatura) as dataAssinatura,
    modalidadeLicitacao,
    DATE(dataPublicacao) as dataPublicacao,
    sequencialContratacao,
    codigoUnidadeOrgao,
    
    // Campos enriquecidos
    modalidade_nome_dominio as ModalidadeNome,
    situacao_compra_nome_dominio as SituacaoCompra,
    esfera_nome_dominio as EsferaNome,
    poder_nome_dominio as PoderNome,
    
    // Campos de filtro
    filtro_aplicado as FiltroAplicado,
    filtro_motivo as FiltroMotivo,
    
    // Partições
    year as Ano,
    month as Mes
FROM contratos
WHERE year = 2025 AND month = 8;

// Criar dimensões de tempo
Calendar:
LOAD DISTINCT
    dataPublicacao,
    Year(dataPublicacao) as AnoPublicacao,
    Month(dataPublicacao) as MesPublicacao,
    Day(dataPublicacao) as DiaPublicacao,
    WeekDay(dataPublicacao) as DiaSemana,
    Week(dataPublicacao) as Semana,
    Quarter(dataPublicacao) as Trimestre
RESIDENT Contratos;

// Criar dimensão de modalidades
Modalidades:
LOAD DISTINCT
    modalidadeLicitacao,
    ModalidadeNome
RESIDENT Contratos;
```

### **3.2 Medidas Calculadas**
```qlik
// Total de Contratos
=Count(numeroContrato)

// Valor Total
=Sum(valorContrato)

// Valor Médio
=Avg(valorContrato)

// Taxa de Aprovação do Filtro
=Count({<FiltroAplicado={'1'}>} numeroContrato) / Count(numeroContrato)

// Contratos por Modalidade
=Count(numeroContrato) / Count(TOTAL numeroContrato)

// Crescimento Mensal
=Sum(valorContrato) / Above(Sum(valorContrato))

// Contratos de TI
=Count({<objetoContrato={'*tecnologia*', '*software*', '*sistema*'}>} numeroContrato)
```

## 📈 Dashboards Principais

### **4.1 Overview Executivo**
- **📊 KPIs**: Total Contratos, Valor Total, Valor Médio
- **📅 Tendência**: Evolução diária/semanal
- **🏢 Top Modalidades**: Distribuição por tipo
- **💰 Top Contratos**: Maiores valores

### **4.2 Análise Operacional**
- **🔍 Eficácia Filtro**: Taxa aprovação LLM
- **⚖️ Distribuição Esferas**: Federal, Estadual, Municipal  
- **📋 Status Contratos**: Por situação
- **🎯 Segmentação**: Por poder (Executivo, Legislativo, etc.)

### **4.3 Análise de TI**
- **💻 Contratos Tecnologia**: Filtros específicos
- **📊 Valores TI**: Comparativo com outros setores
- **🔍 Objetos TI**: Análise textual
- **📈 Crescimento TI**: Evolução temporal

## ⚡ Otimizações de Performance

### **5.1 Configurações Qlik**
```qlik
// Usar apenas dados necessários
SET ThousandSep=',';
SET DecimalSep='.';
SET MoneyFormat='R$ #.##0,00';
SET TimeFormat='h:mm:ss TT';
SET DateFormat='DD/MM/YYYY';
SET TimestampFormat='DD/MM/YYYY h:mm:ss[.fff] TT';

// Otimizar memória
SET HidePrefix='_';
SET HideSuffix='';
```

### **5.2 Queries Athena Otimizadas**
```sql
-- Usar sempre filtros de partição
WHERE year = 2025 AND month = 8

-- Limitar colunas desnecessárias
SELECT numeroContrato, valorContrato, modalidadeLicitacao
FROM contratos 
WHERE year = 2025

-- Usar agregações no source
SELECT 
  modalidadeLicitacao,
  COUNT(*) as total_contratos,
  SUM(valorContrato) as valor_total
FROM contratos 
WHERE year = 2025 AND month = 8
GROUP BY modalidadeLicitacao
```

## 🔒 Configurações de Segurança

### **6.1 IAM Policy para Qlik**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "athena:BatchGetQueryExecution",
        "athena:GetQueryExecution", 
        "athena:GetQueryResults",
        "athena:GetWorkGroup",
        "athena:ListQueryExecutions",
        "athena:StartQueryExecution",
        "athena:StopQueryExecution"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketLocation",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::pncp-extractor-data-prod-566387937580",
        "arn:aws:s3:::pncp-extractor-data-prod-566387937580/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase",
        "glue:GetTable",
        "glue:GetPartitions"
      ],
      "Resource": "*"
    }
  ]
}
```

## 🎯 Próximos Passos

### **Fase 1: Configuração (1-2 horas)**
1. ✅ Configurar conector Athena no Qlik
2. ✅ Testar conectividade com query simples  
3. ✅ Validar retorno de dados

### **Fase 2: Desenvolvimento (2-3 horas)**
1. ✅ Implementar script de carga otimizado
2. ✅ Criar medidas calculadas principais
3. ✅ Desenvolver dashboards básicos

### **Fase 3: Otimização (1 hora)**
1. ✅ Ajustar performance queries
2. ✅ Configurar refresh automático
3. ✅ Implementar alertas/monitoramento

## 📞 Suporte
- **Teste Connection**: Query COUNT simples primeiro
- **Erro comum**: S3 permissions para staging directory
- **Performance**: Sempre usar filtros year/month

**Qlik + Athena = Performance máxima com dados íntegros!** 🚀