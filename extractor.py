#!/usr/bin/env python3
"""
PNCP Contratações Extractor - Extrator Especializado para Contratações Públicas

Este script realiza a extração completa e incremental de dados de contratações públicas
do endpoint /v1/contratacoes/publicacao da API do PNCP, salvando em arquivos Parquet.
"""

import os
import json
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import time
from dataclasses import dataclass, asdict
import concurrent.futures
from threading import Lock
from domain_tables import DomainTables
from filter_manager import FilterManager


@dataclass
class ExtractorConfig:
    """Configurações do extrator de contratações"""
    base_url: str = "https://pncp.gov.br/api/consulta/v1"
    endpoint: str = "contratacoes/publicacao"
    output_dir: str = "data"
    state_file: str = "state.json"
    page_size: int = 50  # Aumentado para otimizar
    delay_between_requests: float = 0.5  # Reduzido para ser mais eficiente
    max_retries: int = 5
    retry_delay: float = 2.0
    date_format: str = "%Y-%m-%d"
    start_year: int = 2025
    start_month: int = 1
    start_day: int = 1
    max_workers: int = 3  # Para paginação paralela
    # Configurações de estrutura
    partitioned_structure: bool = True
    consolidation_days: int = 30
    daily_extraction: bool = True
    # Modalidades de contratação mais comuns
    modalidades_contratacao: List[str] = None
    # Configurações de filtro
    filtro_ativo: bool = True
    filtro_threshold: float = 0.7
    filtro_log_matches: bool = True
    filtros_file: str = "filtros.json"
    
    def __post_init__(self):
        if self.modalidades_contratacao is None:
            # Usar todas as modalidades ativas do domínio
            self.modalidades_contratacao = [str(codigo) for codigo in DomainTables.get_modalidades_ativas()]


class PNCPContractionsExtractor:
    """Extrator especializado para contratações do PNCP"""
    
    def __init__(self, config: ExtractorConfig = None):
        self.config = config or ExtractorConfig()
        self.setup_logging()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PNCP-Contractions-Extractor/2.0',
            'Accept': '*/*'
        })
        self._lock = Lock()
        self.domain_tables = DomainTables()
        
        # Inicializar filter manager
        filter_config = {
            'filtro_ativo': self.config.filtro_ativo,
            'filtro_threshold': self.config.filtro_threshold,
            'filtro_log_matches': self.config.filtro_log_matches
        }
        self.filter_manager = FilterManager(
            filtros_file=self.config.filtros_file, 
            config=filter_config
        )
        
        # Criar diretórios necessários
        self._setup_directory_structure()
        
    def setup_logging(self):
        """Configura o sistema de logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('extractor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _setup_directory_structure(self):
        """Configura a estrutura de diretórios para dados particionados"""
        base_dir = Path(self.config.output_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        
        if self.config.partitioned_structure:
            # Criar diretórios para estrutura particionada
            (base_dir / "consolidated").mkdir(exist_ok=True)
            (base_dir / "metadata").mkdir(exist_ok=True)
            (base_dir / "metadata" / "data_quality_reports").mkdir(exist_ok=True)
            
            # Criar diretórios por ano (se não existirem)
            current_year = datetime.now().year
            for year in range(self.config.start_year, current_year + 1):
                year_dir = base_dir / f"year={year}"
                year_dir.mkdir(exist_ok=True)
                
                # Criar diretórios por mês
                for month in range(1, 13):
                    month_dir = year_dir / f"month={month:02d}"
                    month_dir.mkdir(exist_ok=True)
        
    def _get_partitioned_path(self, date_str: str) -> Path:
        """Retorna o caminho particionado para uma data específica"""
        date_obj = datetime.strptime(date_str, self.config.date_format)
        base_dir = Path(self.config.output_dir)
        
        if self.config.partitioned_structure:
            return base_dir / f"year={date_obj.year}" / f"month={date_obj.month:02d}"
        else:
            return base_dir
        
    def load_state(self) -> Dict[str, Any]:
        """Carrega o estado da última execução"""
        state_path = Path(self.config.state_file)
        if state_path.exists():
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Erro ao carregar estado: {e}. Iniciando do zero.")
        
        # Estado inicial - começar de 2021 (início do PNCP)
        return {
            'last_extraction_date': None,
            'total_records_extracted': 0,
            'last_extraction_timestamp': None,
            'modalidades_processadas': {},
            'periodos_completos': []
        }
    
    def save_state(self, state: Dict[str, Any]):
        """Salva o estado atual"""
        try:
            with self._lock:
                with open(self.config.state_file, 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=2, ensure_ascii=False, default=str)
                self.logger.info(f"Estado salvo: total_records={state.get('total_records_extracted', 0)}")
        except Exception as e:
            self.logger.error(f"Erro ao salvar estado: {e}")
    
    def make_request(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Faz uma requisição para a API com retry logic otimizado"""
        url = f"{self.config.base_url}/{self.config.endpoint}"
        
        for attempt in range(self.config.max_retries):
            try:
                self.logger.debug(f"Requisição: {params} (tentativa {attempt + 1})")
                response = self.session.get(url, params=params, timeout=120)
                response.raise_for_status()
                
                # Delay entre requisições
                time.sleep(self.config.delay_between_requests)
                
                return response.json()
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Erro na requisição (tentativa {attempt + 1}): {e}")
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)  # Backoff exponencial
                    time.sleep(delay)
                else:
                    self.logger.error(f"Falha após {self.config.max_retries} tentativas: {params}")
                    raise
    
    def get_total_pages(self, start_date: str, end_date: str, modalidade: str) -> int:
        """Obtém o número total de páginas para um período e modalidade"""
        params = {
            'dataInicial': start_date.replace('-', ''),
            'dataFinal': end_date.replace('-', ''),
            'codigoModalidadeContratacao': modalidade,
            'pagina': 1,
            'tamanhoPagina': self.config.page_size
        }
        
        try:
            response = self.make_request(params)
            if response and 'totalPaginas' in response:
                total_pages = response['totalPaginas']
                total_records = response.get('totalRegistros', 0)
                self.logger.info(f"Modalidade {modalidade}: {total_records} registros em {total_pages} páginas")
                return total_pages
            return 0
        except Exception as e:
            self.logger.error(f"Erro ao obter total de páginas para modalidade {modalidade}: {e}")
            return 0
    
    def extract_page_data(self, start_date: str, end_date: str, modalidade: str, page: int) -> Tuple[List[Dict[str, Any]], int]:
        """Extrai dados de uma página específica"""
        params = {
            'dataInicial': start_date.replace('-', ''),
            'dataFinal': end_date.replace('-', ''),
            'codigoModalidadeContratacao': modalidade,
            'pagina': page,
            'tamanhoPagina': self.config.page_size
        }
        
        try:
            response = self.make_request(params)
            if response and 'data' in response:
                data = response['data']
                self.logger.debug(f"Modalidade {modalidade}, Página {page}: {len(data)} registros")
                return data, len(data)
            return [], 0
        except Exception as e:
            self.logger.error(f"Erro ao extrair página {page} da modalidade {modalidade}: {e}")
            return [], 0
    
    def enrich_record_with_domain_data(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Enriquece um registro com informações das tabelas de domínio e aplica filtro"""
        # Aplicar filtro primeiro
        incluir, motivo, detalhes_filtro = self.filter_manager.should_include_record(record)
        if not incluir:
            return None  # Registro filtrado
        
        enriched = record.copy()
        
        try:
            # Adicionar informações do filtro
            enriched['filtro_aplicado'] = True
            enriched['filtro_motivo'] = motivo
            enriched['filtro_grupo_matched'] = detalhes_filtro.get('grupo_matched', '')
            enriched['filtro_termo_matched'] = detalhes_filtro.get('termo_matched', '')
            enriched['filtro_criterio'] = detalhes_filtro.get('criterio', '')
            
            # Enriquecer modalidade
            if 'modalidadeId' in record:
                modalidade_id = record['modalidadeId']
                enriched['modalidade_nome_dominio'] = self.domain_tables.get_modalidade_nome(modalidade_id)
                enriched['modalidade_descricao_dominio'] = self.domain_tables.get_modalidade_descricao(modalidade_id)
            
            # Enriquecer situação de compra
            if 'situacaoCompraId' in record:
                situacao_id = record['situacaoCompraId']
                enriched['situacao_compra_nome_dominio'] = self.domain_tables.get_situacao_compra_nome(situacao_id)
            
            # Enriquecer modo de disputa
            if 'modoDisputaId' in record:
                modo_id = record['modoDisputaId']
                enriched['modo_disputa_nome_dominio'] = self.domain_tables.get_modo_disputa_nome(modo_id)
            
            # Enriquecer critério de julgamento
            if 'criterioJulgamentoId' in record:
                criterio_id = record['criterioJulgamentoId']
                enriched['criterio_julgamento_nome_dominio'] = self.domain_tables.get_criterio_julgamento_nome(criterio_id)
            
            # Enriquecer instrumento convocatório
            if 'instrumentoConvocatorioId' in record:
                instrumento_id = record['instrumentoConvocatorioId']
                enriched['instrumento_convocatorio_nome_dominio'] = self.domain_tables.get_instrumento_convocatorio_nome(instrumento_id)
            
            # Enriquecer dados do órgão
            if 'orgaoEntidade' in record and isinstance(record['orgaoEntidade'], dict):
                orgao = record['orgaoEntidade']
                if 'esferaId' in orgao:
                    enriched['esfera_nome_dominio'] = self.domain_tables.get_esfera_nome(orgao['esferaId'])
                if 'poderId' in orgao:
                    enriched['poder_nome_dominio'] = self.domain_tables.get_poder_nome(orgao['poderId'])
            
        except Exception as e:
            self.logger.warning(f"Erro ao enriquecer registro: {e}")
        
        return enriched
    
    def extract_modalidade_parallel(self, start_date: str, end_date: str, modalidade: str) -> List[Dict[str, Any]]:
        """Extrai todos os dados de uma modalidade usando paginação paralela"""
        modalidade_nome = self.domain_tables.get_modalidade_nome(int(modalidade))
        self.logger.info(f"Iniciando extração da modalidade {modalidade} - {modalidade_nome} ({start_date} - {end_date})")
        
        # Obter total de páginas
        total_pages = self.get_total_pages(start_date, end_date, modalidade)
        if total_pages == 0:
            self.logger.info(f"Nenhuma página encontrada para modalidade {modalidade} - {modalidade_nome}")
            return []
        
        all_data = []
        
        # Extração paralela das páginas
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_page = {
                executor.submit(self.extract_page_data, start_date, end_date, modalidade, page): page
                for page in range(1, total_pages + 1)
            }
            
            for future in concurrent.futures.as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    page_data, count = future.result()
                    # Enriquecer cada registro com dados de domínio e aplicar filtro
                    enriched_data = []
                    for record in page_data:
                        enriched_record = self.enrich_record_with_domain_data(record)
                        if enriched_record is not None:  # Só adiciona se passou no filtro
                            enriched_data.append(enriched_record)
                    
                    all_data.extend(enriched_data)
                    if count > 0:
                        filtered_count = len(enriched_data)
                        self.logger.info(f"Modalidade {modalidade} ({modalidade_nome}), Página {page}: {count} registros extraídos, {filtered_count} aprovados pelo filtro")
                except Exception as e:
                    self.logger.error(f"Erro na página {page} da modalidade {modalidade}: {e}")
        
        self.logger.info(f"Modalidade {modalidade} - {modalidade_nome} concluída: {len(all_data)} registros totais")
        return all_data
    
    def extract_period_data(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Extrai dados de todas as modalidades para um período"""
        self.logger.info(f"Extraindo período: {start_date} até {end_date}")
        
        all_period_data = []
        
        for modalidade in self.config.modalidades_contratacao:
            try:
                modalidade_data = self.extract_modalidade_parallel(start_date, end_date, modalidade)
                all_period_data.extend(modalidade_data)
                
                # Pequena pausa entre modalidades
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Erro ao processar modalidade {modalidade}: {e}")
                continue
        
        self.logger.info(f"Período {start_date}-{end_date}: {len(all_period_data)} registros totais")
        return all_period_data
    
    def save_to_parquet(self, data: List[Dict[str, Any]], date_str: str):
        """Salva os dados em formato Parquet com estrutura particionada"""
        if not data:
            self.logger.info(f"Nenhum dado para salvar na data {date_str}")
            return
        
        try:
            df = pd.DataFrame(data)
            
            # Adicionar colunas de controle
            df['extraction_date'] = datetime.now().isoformat()
            df['data_publicacao'] = date_str
            
            # Determinar caminho e nome do arquivo
            if self.config.daily_extraction:
                # Estrutura diária
                date_obj = datetime.strptime(date_str, self.config.date_format)
                filename = f"pncp_contratos_{date_obj.strftime('%Y%m%d')}.parquet"
                filepath = self._get_partitioned_path(date_str) / filename
            else:
                # Estrutura mensal (legado)
                date_obj = datetime.strptime(date_str, self.config.date_format)
                period_label = f"{date_obj.year}{date_obj.month:02d}"
                filename = f"pncp_contratacoes_{period_label}.parquet"
                filepath = Path(self.config.output_dir) / filename
            
            # Criar diretório se não existir
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Salvar em Parquet
            df.to_parquet(filepath, index=False)
            
            self.logger.info(f"Dados salvos: {filepath} ({len(df)} registros)")
            
            # Salvar metadata
            self._save_extraction_metadata(date_str, len(df), str(filepath))
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar dados em Parquet: {e}")
            raise
    
    def _save_extraction_metadata(self, date_str: str, record_count: int, filepath: str):
        """Salva metadata da extração"""
        metadata_dir = Path(self.config.output_dir) / "metadata"
        metadata_file = metadata_dir / "extraction_log.json"
        
        # Carregar metadata existente
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        else:
            metadata = {"extractions": []}
        
        # Adicionar nova extração
        extraction_info = {
            "date": date_str,
            "timestamp": datetime.now().isoformat(),
            "records": record_count,
            "filepath": filepath,
            "filter_stats": self.filter_manager.get_statistics() if hasattr(self, 'filter_manager') else {}
        }
        
        # Remover extração anterior da mesma data (se existir)
        metadata["extractions"] = [e for e in metadata["extractions"] if e["date"] != date_str]
        metadata["extractions"].append(extraction_info)
        
        # Salvar metadata atualizada
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
    
    def get_date_ranges_for_extraction(self, state: Dict[str, Any], historical: bool = False) -> List[str]:
        """Determina as datas para extração (uma por dia)"""
        dates = []
        
        if historical or not state.get('last_extraction_date'):
            # Extração histórica completa - desde data configurada
            config_start_date = datetime(self.config.start_year, self.config.start_month, self.config.start_day)
            today = datetime.now()
            
            # Gerar todas as datas desde a data inicial até hoje
            current_date = config_start_date
            while current_date.date() <= today.date():
                dates.append(current_date.strftime(self.config.date_format))
                current_date += timedelta(days=1)
                
        else:
            # Extração incremental - apenas dias não processados
            last_date = datetime.strptime(state['last_extraction_date'], self.config.date_format)
            today = datetime.now()
            
            # Gerar datas desde o dia seguinte ao último processado até hoje
            current_date = last_date + timedelta(days=1)
            while current_date.date() <= today.date():
                dates.append(current_date.strftime(self.config.date_format))
                current_date += timedelta(days=1)
        
        return dates
    
    def run_extraction(self, historical: bool = False):
        """Execução principal da extração"""
        self.logger.info(f"Iniciando extração {'histórica' if historical else 'incremental'} do PNCP")
        
        # Carregar estado
        state = self.load_state()
        
        # Determinar datas para extração
        dates_to_extract = self.get_date_ranges_for_extraction(state, historical)
        
        if not dates_to_extract:
            self.logger.info("Não há novas datas para extrair")
            return
        
        total_extracted = 0
        processed_dates = state.get('processed_dates', [])
        
        self.logger.info(f"Total de datas para processar: {len(dates_to_extract)}")
        
        for date_str in dates_to_extract:
            # Verificar se a data já foi processada
            if date_str in processed_dates:
                self.logger.info(f"Data {date_str} já processada, pulando...")
                continue
            
            try:
                self.logger.info(f"Processando data: {date_str}")
                
                # Extrair dados da data (mesmo dia para início e fim)
                daily_data = self.extract_period_data(date_str, date_str)
                
                if daily_data:
                    # Salvar dados
                    self.save_to_parquet(daily_data, date_str)
                    
                    # Atualizar estado
                    state['last_extraction_date'] = date_str
                    state['total_records_extracted'] = state.get('total_records_extracted', 0) + len(daily_data)
                    state['last_extraction_timestamp'] = datetime.now().isoformat()
                    
                    if 'processed_dates' not in state:
                        state['processed_dates'] = []
                    state['processed_dates'].append(date_str)
                    
                    total_extracted += len(daily_data)
                    
                    self.logger.info(f"Data {date_str} concluída: {len(daily_data)} registros")
                else:
                    self.logger.info(f"Nenhum dado encontrado para a data {date_str}")
                    # Marcar data como processada mesmo sem dados
                    if 'processed_dates' not in state:
                        state['processed_dates'] = []
                    state['processed_dates'].append(date_str)
                
                # Salvar estado a cada data processada
                self.save_state(state)
                
            except Exception as e:
                self.logger.error(f"Erro ao processar data {date_str}: {e}")
                continue
        
        self.logger.info(f"Extração concluída! {total_extracted} novos registros extraídos")
        
        # Log estatísticas do filtro
        if self.config.filtro_ativo:
            self.filter_manager.log_final_statistics()
        
        # Salvar estado final
        self.save_state(state)
    
    def consolidate_old_files(self, days_threshold: int = None):
        """Consolida arquivos diários antigos em arquivos mensais para otimizar storage"""
        if days_threshold is None:
            days_threshold = self.config.consolidation_days
        
        self.logger.info(f"Iniciando consolidação de arquivos com mais de {days_threshold} dias")
        
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        base_dir = Path(self.config.output_dir)
        consolidated_dir = base_dir / "consolidated"
        
        # Dicionário para agrupar arquivos por mês/ano
        monthly_groups = {}
        files_to_consolidate = []
        
        # Encontrar todos os arquivos diários elegíveis para consolidação
        for year_dir in base_dir.glob("year=*"):
            year = int(year_dir.name.split("=")[1])
            for month_dir in year_dir.glob("month=*"):
                month = int(month_dir.name.split("=")[1])
                
                month_key = f"{year}-{month:02d}"
                monthly_groups[month_key] = []
                
                for daily_file in month_dir.glob("pncp_contratos_*.parquet"):
                    # Extrair data do nome do arquivo
                    date_str = daily_file.stem.replace("pncp_contratos_", "")
                    try:
                        file_date = datetime.strptime(date_str, "%Y%m%d")
                        if file_date < cutoff_date:
                            monthly_groups[month_key].append(daily_file)
                            files_to_consolidate.append(daily_file)
                    except ValueError:
                        continue
        
        if not files_to_consolidate:
            self.logger.info("Nenhum arquivo elegível para consolidação encontrado")
            return
        
        self.logger.info(f"Encontrados {len(files_to_consolidate)} arquivos para consolidar")
        
        # Consolidar por mês
        for month_key, files in monthly_groups.items():
            if not files:
                continue
                
            try:
                self.logger.info(f"Consolidando {len(files)} arquivos do mês {month_key}")
                
                # Ler todos os arquivos do mês
                monthly_data = []
                for file_path in files:
                    df = pd.read_parquet(file_path)
                    monthly_data.append(df)
                
                if monthly_data:
                    # Combinar todos os dataframes
                    consolidated_df = pd.concat(monthly_data, ignore_index=True)
                    
                    # Salvar arquivo consolidado
                    consolidated_filename = f"pncp_contratos_{month_key.replace('-', '')}_consolidated.parquet"
                    consolidated_path = consolidated_dir / consolidated_filename
                    consolidated_df.to_parquet(consolidated_path, index=False)
                    
                    self.logger.info(f"Arquivo consolidado criado: {consolidated_path} ({len(consolidated_df)} registros)")
                    
                    # Remover arquivos diários originais
                    for file_path in files:
                        file_path.unlink()
                        self.logger.debug(f"Arquivo removido: {file_path}")
                    
                    # Remover diretórios vazios
                    for file_path in files:
                        parent_dir = file_path.parent
                        if parent_dir.exists() and not any(parent_dir.iterdir()):
                            parent_dir.rmdir()
                            self.logger.debug(f"Diretório vazio removido: {parent_dir}")
                
            except Exception as e:
                self.logger.error(f"Erro ao consolidar arquivos do mês {month_key}: {e}")
                continue
        
        self.logger.info("Consolidação concluída")


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extrator de Contratações do PNCP')
    parser.add_argument('--historical', action='store_true', 
                       help='Executar extração histórica completa')
    parser.add_argument('--config', default='config.json',
                       help='Arquivo de configuração JSON')
    parser.add_argument('--consolidate', action='store_true',
                       help='Executar consolidação de arquivos antigos')
    parser.add_argument('--consolidate-days', type=int, default=30,
                       help='Consolidar arquivos com mais de N dias (padrão: 30)')
    
    args = parser.parse_args()
    
    # Carregar configuração se existir
    config_path = Path(args.config)
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            config = ExtractorConfig(**config_data)
            print(f"Configuração carregada de: {args.config}")
        except Exception as e:
            print(f"Erro ao carregar configuração: {e}. Usando configuração padrão.")
            config = ExtractorConfig()
    else:
        config = ExtractorConfig()
        print("Usando configuração padrão")
    
    # Criar extrator
    extractor = PNCPContractionsExtractor(config)
    
    # Executar consolidação se solicitado
    if args.consolidate:
        extractor.consolidate_old_files(days_threshold=args.consolidate_days)
    else:
        # Executar extração normal
        extractor.run_extraction(historical=args.historical)


if __name__ == "__main__":
    main()