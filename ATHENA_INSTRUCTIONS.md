# 🔥 AWS Athena Setup - Instruções Passo a Passo

## 📋 Pré-requisitos
1. **Console AWS**: https://console.aws.amazon.com/athena/
2. **Região**: us-east-2 (Ohio)
3. **Arquivo SQL**: `athena_setup.sql` (criado neste projeto)

## 🚀 Passos para Configurar

### **1. Acessar Athena Console**
- Vá para: https://us-east-2.console.aws.amazon.com/athena/
- Certifique-se que está na região **us-east-2**

### **2. Configurar Query Result Location**
- **Settings** → **Manage** 
- **Query result location**: `s3://pncp-extractor-data-prod-566387937580/athena-results/`
- **Save**

### **3. Executar Setup SQL**
Copie e execute cada query do arquivo `athena_setup.sql`:

#### **Query 1: Criar Database**
```sql
CREATE DATABASE IF NOT EXISTS pncp_data
COMMENT 'Dados PNCP extraídos automaticamente';
```

#### **Query 2: Usar Database** 
```sql
USE pncp_data;
```

#### **Query 3: Criar Tabela** 
```sql
-- Copiar toda a query CREATE EXTERNAL TABLE do arquivo
-- (Query longa com todas as colunas e particionamento)
```

### **4. Testar com Query de Validação**
```sql
SELECT COUNT(*) as total_registros 
FROM contratos 
WHERE year = 2025 AND month = 8;
```

**Resultado esperado**: ~1000 registros (vs 19 do consolidado bugado)

## ✅ Resultados Esperados

### **Comparação de Performance:**
| Método | Registros | Performance | Manutenção |
|--------|-----------|-------------|------------|
| **❌ Consolidado** | 19 (bugado) | Lento | Manual |
| **✅ Athena** | ~1000 (íntegro) | Rápido | Zero |

### **Queries Prontas para Usar:**
- **📊 Total de registros**: Query 5
- **📅 Por dia**: Query 6  
- **🏢 Por modalidade**: Query 7
- **💰 Top contratos**: Query 8
- **🔍 Análise filtros**: Query 9
- **💻 Contratos TI**: Query 10

## 🎯 Próximos Passos (Após Setup)
1. **Validar integridade** dos dados  
2. **Testar performance** com queries complexas
3. **Conectar BI tools** (Power BI, Tableau, etc.)
4. **Comparar** com consolidado bugado

## 📞 Suporte
Execute as queries e me informe:
- ✅ **Sucesso**: Quantos registros retornaram
- ❌ **Erro**: Qual mensagem de erro apareceu

**O Athena vai resolver definitivamente o problema de dados perdidos!** 🚀