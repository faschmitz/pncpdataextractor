#!/usr/bin/env python3
"""
LLM Filter - Filtro Inteligente usando OpenAI
Implementa filtro avançado baseado em LLM para análise contextual de licitações
"""

import os
import json
import hashlib
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

import openai
from dotenv import load_dotenv

from prompts import PromptBuilder


# Carregar variáveis de ambiente
load_dotenv()


@dataclass
class LLMResponse:
    """Estrutura da resposta do LLM"""
    decisao: str  # APROVAR ou REJEITAR
    categoria: str = ""
    confianca: int = 0
    justificativa: str = ""
    tokens_used: int = 0
    response_time: float = 0.0
    cached: bool = False


@dataclass
class LLMFilterStats:
    """Estatísticas do filtro LLM"""
    total_queries: int = 0
    aprovados: int = 0
    rejeitados: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_response_time: float = 0.0
    errors: int = 0


class LLMFilter:
    """Filtro inteligente usando OpenAI LLM"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configurações da API OpenAI
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY não encontrada no arquivo .env")
        
        # Configurar cliente OpenAI
        openai.api_key = self.api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        
        # Configurações do modelo
        self.model = self.config.get('llm_model', os.getenv('LLM_MODEL', 'gpt-3.5-turbo'))
        self.max_tokens = self.config.get('llm_max_tokens', int(os.getenv('LLM_MAX_TOKENS', '500')))
        self.temperature = self.config.get('llm_temperature', float(os.getenv('LLM_TEMPERATURE', '0.1')))
        
        # Configurações de rate limiting
        self.max_requests_per_minute = self.config.get('llm_max_requests_per_minute', 60)
        self.delay_between_requests = self.config.get('llm_delay_between_requests', 1.0)
        
        # Cache em memória para a sessão
        self.cache = {}
        self.cache_ttl = self.config.get('cache_ttl_hours', 24)  # TTL em horas
        
        # Rate limiting
        self.request_timestamps = []
        
        # Estatísticas
        self.stats = LLMFilterStats()
        
        # Construtor de prompts
        self.prompt_builder = PromptBuilder()
        
        # Configurações de custo (preços por 1K tokens em USD)
        self.token_costs = {
            'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002},
            'gpt-3.5-turbo-1106': {'input': 0.001, 'output': 0.002},
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03}
        }
        
        self.logger.info(f"LLM Filter inicializado com modelo: {self.model}")
    
    def _generate_cache_key(self, objetivo_compra: str) -> str:
        """Gera chave única para cache baseada no conteúdo"""
        # Normalizar texto para cache
        normalized = objetivo_compra.lower().strip()
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Verifica se entrada do cache ainda é válida"""
        if 'timestamp' not in cache_entry:
            return False
        
        entry_time = datetime.fromisoformat(cache_entry['timestamp'])
        expiry_time = entry_time + timedelta(hours=self.cache_ttl)
        
        return datetime.now() < expiry_time
    
    def _get_from_cache(self, objetivo_compra: str) -> Optional[LLMResponse]:
        """Recupera resultado do cache se disponível e válido"""
        cache_key = self._generate_cache_key(objetivo_compra)
        
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if self._is_cache_valid(cache_entry):
                self.stats.cache_hits += 1
                response = LLMResponse(**cache_entry['response'])
                response.cached = True
                self.logger.debug(f"Cache HIT para: {objetivo_compra[:50]}...")
                return response
            else:
                # Remove entrada expirada
                del self.cache[cache_key]
        
        self.stats.cache_misses += 1
        return None
    
    def _save_to_cache(self, objetivo_compra: str, response: LLMResponse):
        """Salva resultado no cache"""
        cache_key = self._generate_cache_key(objetivo_compra)
        self.cache[cache_key] = {
            'timestamp': datetime.now().isoformat(),
            'response': asdict(response)
        }
        self.logger.debug(f"Resultado salvo no cache para: {objetivo_compra[:50]}...")
    
    def _wait_for_rate_limit(self):
        """Implementa rate limiting simples"""
        now = time.time()
        
        # Remove timestamps antigos (mais de 1 minuto)
        self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < 60]
        
        # Verifica se precisa esperar
        if len(self.request_timestamps) >= self.max_requests_per_minute:
            sleep_time = 60 - (now - self.request_timestamps[0])
            if sleep_time > 0:
                self.logger.info(f"Rate limit atingido. Aguardando {sleep_time:.1f}s...")
                time.sleep(sleep_time)
        
        # Adiciona timestamp atual
        self.request_timestamps.append(now)
        
        # Delay adicional entre requisições
        if self.delay_between_requests > 0:
            time.sleep(self.delay_between_requests)
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse da resposta do LLM para extrair informações estruturadas"""
        response_data = {
            'decisao': 'REJEITAR',  # Padrão conservador
            'categoria': '',
            'confianca': 0,
            'justificativa': ''
        }
        
        # Debug: log da resposta completa para análise
        self.logger.debug(f"Resposta LLM completa: {response_text}")
        
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('DECISAO:') or line.startswith('DECISÃO:'):
                decision = line.replace('DECISAO:', '').replace('DECISÃO:', '').strip().upper()
                if decision in ['APROVAR', 'REJEITAR']:
                    response_data['decisao'] = decision
            
            elif line.startswith('CATEGORIA:'):
                response_data['categoria'] = line.replace('CATEGORIA:', '').strip()
            
            elif line.startswith('CONFIANCA:') or line.startswith('CONFIANÇA:'):
                try:
                    conf_text = line.replace('CONFIANCA:', '').replace('CONFIANÇA:', '').replace('%', '').strip()
                    response_data['confianca'] = int(conf_text)
                except ValueError:
                    response_data['confianca'] = 0
            
            elif line.startswith('JUSTIFICATIVA:'):
                response_data['justificativa'] = line.replace('JUSTIFICATIVA:', '').strip()
        
        # Detectar inconsistência: se justificativa sugere aprovação mas decisão é rejeitar
        justificativa_lower = response_data['justificativa'].lower()
        if (response_data['decisao'] == 'REJEITAR' and response_data['confianca'] == 0 and 
            ('se enquadra' in justificativa_lower or 'materiais educacionais' in justificativa_lower)):
            self.logger.warning(f"Possível inconsistência detectada - ajustando decisão baseada na justificativa")
            response_data['decisao'] = 'APROVAR'
            response_data['confianca'] = 85  # Confiança moderada para casos corrigidos
        
        return response_data
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calcula custo estimado da requisição"""
        if self.model not in self.token_costs:
            return 0.0
        
        costs = self.token_costs[self.model]
        input_cost = (input_tokens / 1000) * costs['input']
        output_cost = (output_tokens / 1000) * costs['output']
        
        return input_cost + output_cost
    
    def query_llm(self, objetivo_compra: str, context: Dict[str, Any] = None) -> LLMResponse:
        """
        Consulta o LLM para análise do objetivo de compra
        
        Args:
            objetivo_compra: Texto do objetivo de compra
            context: Contexto adicional (categorias pré-identificadas, etc.)
        
        Returns:
            LLMResponse com a análise do LLM
        """
        # Verificar cache primeiro
        cached_response = self._get_from_cache(objetivo_compra)
        if cached_response:
            return cached_response
        
        # Preparar prompt
        prompt = self.prompt_builder.build_contextual_prompt(objetivo_compra, context)
        
        start_time = time.time()
        
        try:
            self.stats.total_queries += 1
            
            # Rate limiting
            self._wait_for_rate_limit()
            
            # Fazer requisição para OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é um especialista em análise de licitações públicas."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=0.9
            )
            
            response_time = time.time() - start_time
            
            # Extrair informações da resposta
            response_text = response.choices[0].message.content
            parsed_response = self._parse_llm_response(response_text)
            
            # Calcular tokens e custo
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            cost = self._calculate_cost(input_tokens, output_tokens)
            
            # Criar objeto de resposta
            llm_response = LLMResponse(
                decisao=parsed_response['decisao'],
                categoria=parsed_response['categoria'],
                confianca=parsed_response['confianca'],
                justificativa=parsed_response['justificativa'],
                tokens_used=total_tokens,
                response_time=response_time,
                cached=False
            )
            
            # Atualizar estatísticas
            if llm_response.decisao == 'APROVAR':
                self.stats.aprovados += 1
            else:
                self.stats.rejeitados += 1
            
            self.stats.total_tokens += total_tokens
            self.stats.total_cost_usd += cost
            self.stats.avg_response_time = (
                (self.stats.avg_response_time * (self.stats.total_queries - 1) + response_time) / 
                self.stats.total_queries
            )
            
            # Salvar no cache
            self._save_to_cache(objetivo_compra, llm_response)
            
            self.logger.info(f"LLM {llm_response.decisao}: {objetivo_compra[:60]}... "
                           f"(Confiança: {llm_response.confianca}%, "
                           f"Tokens: {total_tokens}, "
                           f"Custo: ${cost:.4f})")
            
            return llm_response
            
        except Exception as e:
            self.stats.errors += 1
            self.logger.error(f"Erro na consulta LLM para '{objetivo_compra[:50]}...': {e}")
            
            # Retornar resposta padrão em caso de erro
            return LLMResponse(
                decisao='REJEITAR',  # Conservador em caso de erro
                categoria='',
                confianca=0,
                justificativa=f'Erro na análise LLM: {str(e)}',
                tokens_used=0,
                response_time=time.time() - start_time,
                cached=False
            )
    
    def should_include_record(self, record: Dict[str, Any], context: Dict[str, Any] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Interface principal para determinar se um registro deve ser incluído
        
        Args:
            record: Registro da licitação
            context: Contexto adicional do filtro de palavras-chave
        
        Returns:
            tuple: (incluir: bool, motivo: str, detalhes: dict)
        """
        objetivo_compra = record.get('objetoCompra', '')
        if not objetivo_compra:
            return False, "objetoCompra vazio", {}
        
        # Consultar LLM
        llm_response = self.query_llm(objetivo_compra, context)
        
        # Determinar inclusão baseada na resposta
        incluir = llm_response.decisao == 'APROVAR'
        
        # Preparar detalhes
        detalhes = {
            'llm_decisao': llm_response.decisao,
            'llm_categoria': llm_response.categoria,
            'llm_confianca': llm_response.confianca,
            'llm_justificativa': llm_response.justificativa,
            'llm_tokens_used': llm_response.tokens_used,
            'llm_response_time': llm_response.response_time,
            'llm_cached': llm_response.cached,
            'objetivo_compra': objetivo_compra[:200] + '...' if len(objetivo_compra) > 200 else objetivo_compra
        }
        
        motivo = f"LLM {llm_response.decisao} (confiança: {llm_response.confianca}%)"
        
        return incluir, motivo, detalhes
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas detalhadas do filtro LLM"""
        cache_hit_rate = 0.0
        if self.stats.cache_hits + self.stats.cache_misses > 0:
            cache_hit_rate = (self.stats.cache_hits / (self.stats.cache_hits + self.stats.cache_misses)) * 100
        
        approval_rate = 0.0
        if self.stats.total_queries > 0:
            approval_rate = (self.stats.aprovados / self.stats.total_queries) * 100
        
        return {
            'total_queries': self.stats.total_queries,
            'aprovados': self.stats.aprovados,
            'rejeitados': self.stats.rejeitados,
            'approval_rate_percent': round(approval_rate, 2),
            'cache_hits': self.stats.cache_hits,
            'cache_misses': self.stats.cache_misses,
            'cache_hit_rate_percent': round(cache_hit_rate, 2),
            'total_tokens': self.stats.total_tokens,
            'avg_tokens_per_query': round(self.stats.total_tokens / max(1, self.stats.total_queries), 2),
            'total_cost_usd': round(self.stats.total_cost_usd, 4),
            'avg_cost_per_query': round(self.stats.total_cost_usd / max(1, self.stats.total_queries), 4),
            'avg_response_time_seconds': round(self.stats.avg_response_time, 3),
            'errors': self.stats.errors,
            'model_used': self.model,
            'cache_size': len(self.cache)
        }
    
    def log_statistics(self):
        """Loga estatísticas detalhadas"""
        stats = self.get_statistics()
        
        self.logger.info("=" * 60)
        self.logger.info("ESTATÍSTICAS DO FILTRO LLM")
        self.logger.info("=" * 60)
        self.logger.info(f"Modelo utilizado: {stats['model_used']}")
        self.logger.info(f"Total de consultas: {stats['total_queries']}")
        self.logger.info(f"Aprovados: {stats['aprovados']} ({stats['approval_rate_percent']:.1f}%)")
        self.logger.info(f"Rejeitados: {stats['rejeitados']}")
        self.logger.info(f"Erros: {stats['errors']}")
        self.logger.info("")
        self.logger.info("CACHE:")
        self.logger.info(f"  Hits: {stats['cache_hits']} ({stats['cache_hit_rate_percent']:.1f}%)")
        self.logger.info(f"  Misses: {stats['cache_misses']}")
        self.logger.info(f"  Tamanho: {stats['cache_size']} entradas")
        self.logger.info("")
        self.logger.info("PERFORMANCE:")
        self.logger.info(f"  Tempo médio de resposta: {stats['avg_response_time_seconds']:.3f}s")
        self.logger.info(f"  Tokens totais: {stats['total_tokens']:,}")
        self.logger.info(f"  Tokens por consulta: {stats['avg_tokens_per_query']:.1f}")
        self.logger.info("")
        self.logger.info("CUSTOS:")
        self.logger.info(f"  Custo total: ${stats['total_cost_usd']:.4f}")
        self.logger.info(f"  Custo por consulta: ${stats['avg_cost_per_query']:.4f}")
        self.logger.info("=" * 60)


def main():
    """Função de teste do LLM Filter"""
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    
    # Teste básico
    try:
        llm_filter = LLMFilter()
        
        # Registros de teste
        test_records = [
            {"objetoCompra": "Aquisição de canetas esferográficas azuis para uso escolar"},
            {"objetoCompra": "Compra de lápis de cor 12 cores para educação infantil"},
            {"objetoCompra": "Aquisição de equipamentos médicos hospitalares"},
            {"objetoCompra": "Material de escritório: grampeadores, furadores e clipes"},
            {"objetoCompra": "Construção de ponte rodoviária"},
            {"objetoCompra": "Aquisição de mouse e teclado para laboratório de informática"},
        ]
        
        print("=== TESTE DO LLM FILTER ===")
        
        for i, record in enumerate(test_records):
            incluir, motivo, detalhes = llm_filter.should_include_record(record)
            status = "✅ INCLUIR" if incluir else "❌ REJEITAR"
            objetivo = record['objetoCompra']
            
            print(f"\n{i+1}. {status}")
            print(f"   Objetivo: {objetivo}")
            print(f"   Motivo: {motivo}")
            print(f"   Categoria LLM: {detalhes.get('llm_categoria', 'N/A')}")
            print(f"   Justificativa: {detalhes.get('llm_justificativa', 'N/A')}")
            print(f"   Tokens: {detalhes.get('llm_tokens_used', 0)}")
            print(f"   Cached: {detalhes.get('llm_cached', False)}")
        
        # Estatísticas finais
        print("\n" + "="*60)
        llm_filter.log_statistics()
        
    except Exception as e:
        print(f"Erro no teste: {e}")


if __name__ == "__main__":
    main()