#!/usr/bin/env python3
"""
FilterManager - Filtro Inteligente para objetoCompra
Implementa filtro baseado em busca de termos com normalização
"""

import json
import re
import unicodedata
from typing import Dict, List, Any, Tuple, Optional
import logging

# Importar LLM Filter (com fallback gracioso)
try:
    from llm_filter import LLMFilter
    LLM_AVAILABLE = True
except ImportError as e:
    LLM_AVAILABLE = False
    logging.warning(f"LLM Filter não disponível: {e}. Usando apenas filtro por palavras-chave.")


class FilterManager:
    """Gerenciador de filtros inteligentes para licitações"""
    
    def __init__(self, filtros_file: str = "filtros.json", config: Dict[str, Any] = None):
        self.filtros_file = filtros_file
        self.config = config or {}
        self.grupos_termos = self._load_grupos_termos()
        self.logger = logging.getLogger(__name__)
        
        # Configurações do filtro por palavras-chave
        self.ativo = self.config.get('filtro_ativo', True)
        self.log_matches = self.config.get('filtro_log_matches', True)
        
        # Configurações do filtro LLM
        self.llm_ativo = self.config.get('llm_filtro_ativo', True) and LLM_AVAILABLE
        self.llm_filter: Optional[LLMFilter] = None
        
        # Inicializar LLM Filter se disponível e ativo
        if self.llm_ativo:
            try:
                self.llm_filter = LLMFilter(config=self.config)
                self.logger.info("Filtro híbrido inicializado: Palavras-chave + LLM")
            except Exception as e:
                self.logger.error(f"Erro ao inicializar LLM Filter: {e}")
                self.llm_ativo = False
        else:
            self.logger.info("Filtro simples inicializado: Apenas palavras-chave")
        
        # Estatísticas
        self.stats = {
            'total_analisados': 0,
            'etapa1_aprovados': 0,  # Aprovados pelo filtro de palavras
            'etapa1_rejeitados': 0,  # Rejeitados pelo filtro de palavras
            'etapa2_aprovados': 0,  # Aprovados pelo LLM
            'etapa2_rejeitados': 0,  # Rejeitados pelo LLM
            'filtrados_aprovados': 0,  # Total final aprovado
            'filtrados_rejeitados': 0,  # Total final rejeitado
            'matches_por_grupo': {},
            'matches_por_termo': {},
            'llm_economizados': 0  # Registros que não precisaram ir para o LLM
        }
        
    def _load_grupos_termos(self) -> Dict[str, List[str]]:
        """Carrega grupos e termos do arquivo filtros.json"""
        try:
            with open(self.filtros_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception as e:
            self.logger.error(f"Erro ao carregar filtros: {e}")
            return {}
    
    def _normalize_text(self, texto: str) -> str:
        """Normaliza texto removendo acentos e convertendo para minúsculas"""
        if not texto:
            return ""
        # Remove acentos
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join(char for char in texto if unicodedata.category(char) != 'Mn')
        # Minúsculas
        texto = texto.lower()
        return texto
    
    def _match_exact_word(self, texto: str, termo: str) -> bool:
        """
        Verifica se o termo aparece como palavra completa no texto
        Usa regex para buscar palavras exatas (word boundaries)
        """
        if not termo or not texto:
            return False
        
        # Escapar caracteres especiais do regex no termo
        termo_escaped = re.escape(termo)
        
        # Padrão regex: palavra completa com boundaries (\b)
        pattern = r'\b' + termo_escaped + r'\b'
        
        return bool(re.search(pattern, texto))
    
    def should_include_record(self, record: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Determina se um registro deve ser incluído usando filtro híbrido (palavras-chave + LLM)
        
        ESTRATÉGIA DE 2 ETAPAS:
        1. Etapa 1: Filtro por palavras-chave (rápido e barato)
        2. Etapa 2: Se aprovado na Etapa 1, análise LLM (contextual e precisa)
        
        Returns:
            tuple: (incluir: bool, motivo: str, detalhes: dict)
        """
        if not self.ativo:
            return True, "Filtro desativado", {}
        
        self.stats['total_analisados'] += 1
        
        objetivo_compra = record.get('objetoCompra', '')
        if not objetivo_compra:
            self.stats['filtrados_rejeitados'] += 1
            self.stats['etapa1_rejeitados'] += 1
            return False, "objetoCompra vazio", {}
        
        # ===== ETAPA 1: FILTRO POR PALAVRAS-CHAVE =====
        etapa1_aprovado, etapa1_motivo, etapa1_detalhes = self._apply_keyword_filter(objetivo_compra)
        
        if not etapa1_aprovado:
            # Rejeitado na Etapa 1 - não precisa LLM
            self.stats['filtrados_rejeitados'] += 1
            self.stats['etapa1_rejeitados'] += 1
            self.stats['llm_economizados'] += 1
            
            return False, f"Etapa 1 (Palavras-chave): {etapa1_motivo}", etapa1_detalhes
        
        # Aprovado na Etapa 1
        self.stats['etapa1_aprovados'] += 1
        
        # ===== ETAPA 2: ANÁLISE LLM (se disponível) =====
        if self.llm_ativo and self.llm_filter:
            try:
                # Contexto específico e focado baseado na detecção da Etapa 1
                context = {
                    'grupo_matched': etapa1_detalhes.get('grupo_matched', ''),
                    'termo_matched': etapa1_detalhes.get('termo_matched', ''),
                    'criterio': etapa1_detalhes.get('criterio', ''),
                    'etapa1_motivo': etapa1_motivo,
                    'etapa1_detalhes': etapa1_detalhes
                }
                
                etapa2_aprovado, etapa2_motivo, etapa2_detalhes = self.llm_filter.should_include_record(record, context)
                
                if etapa2_aprovado:
                    self.stats['filtrados_aprovados'] += 1
                    self.stats['etapa2_aprovados'] += 1
                else:
                    self.stats['filtrados_rejeitados'] += 1
                    self.stats['etapa2_rejeitados'] += 1
                
                # Combinar detalhes das duas etapas
                detalhes_final = {
                    **etapa1_detalhes,
                    **etapa2_detalhes,
                    'filtro_etapa1_motivo': etapa1_motivo,
                    'filtro_etapa2_motivo': etapa2_motivo,
                    'filtro_hibrido': True
                }
                
                motivo_final = f"Híbrido: Etapa1 ✓ → Etapa2 {'✓' if etapa2_aprovado else '✗'} | {etapa2_motivo}"
                
                return etapa2_aprovado, motivo_final, detalhes_final
                
            except Exception as e:
                self.logger.error(f"Erro na Etapa 2 (LLM): {e}. Usando resultado da Etapa 1.")
                # Fallback: usar resultado da Etapa 1
                pass
        
        # Sem LLM disponível ou erro - usar apenas resultado da Etapa 1
        self.stats['filtrados_aprovados'] += 1
        etapa1_detalhes['filtro_hibrido'] = False
        etapa1_detalhes['llm_disponivel'] = self.llm_ativo
        
        return True, f"Apenas Etapa 1 (Palavras-chave): {etapa1_motivo}", etapa1_detalhes
    
    def _apply_keyword_filter(self, objetivo_compra: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        ETAPA 1: Aplica filtro por palavras-chave (implementação original)
        
        Returns:
            tuple: (aprovado: bool, motivo: str, detalhes: dict)
        """
        objetivo_normalizado = self._normalize_text(objetivo_compra)
        
        # Ordenar grupos por tamanho (maior primeiro) para evitar matches parciais
        grupos_ordenados = sorted(
            self.grupos_termos.items(), 
            key=lambda x: len(x[0]), 
            reverse=True
        )
        
        # Testa cada grupo e seus termos
        for grupo, termos in grupos_ordenados:
            # Primeiro testa o nome do grupo (palavra exata)
            grupo_normalizado = self._normalize_text(grupo)
            if grupo_normalizado and self._match_exact_word(objetivo_normalizado, grupo_normalizado):
                self._update_keyword_stats(grupo, grupo)
                detalhes = {
                    'grupo_matched': grupo,
                    'termo_matched': grupo,
                    'criterio': f'Nome do grupo "{grupo}" (palavra exata)',
                    'objetivo_compra': objetivo_compra[:100] + '...' if len(objetivo_compra) > 100 else objetivo_compra,
                    'etapa': 1
                }
                if self.log_matches:
                    self.logger.info(f"ETAPA 1 - MATCH GRUPO: '{grupo}' em '{objetivo_compra[:50]}...'")
                return True, f"Match com grupo '{grupo}'", detalhes
            
            # Depois testa cada termo do grupo (palavra exata)
            for termo in termos:
                termo_normalizado = self._normalize_text(termo)
                if termo_normalizado and self._match_exact_word(objetivo_normalizado, termo_normalizado):
                    self._update_keyword_stats(grupo, termo)
                    detalhes = {
                        'grupo_matched': grupo,
                        'termo_matched': termo,
                        'criterio': f'Termo "{termo}" do grupo "{grupo}" (palavra exata)',
                        'objetivo_compra': objetivo_compra[:100] + '...' if len(objetivo_compra) > 100 else objetivo_compra,
                        'etapa': 1
                    }
                    if self.log_matches:
                        self.logger.info(f"ETAPA 1 - MATCH TERMO: '{termo}' (grupo: {grupo}) em '{objetivo_compra[:50]}...'")
                    return True, f"Match com termo '{termo}' do grupo '{grupo}'", detalhes
        
        # Nenhum termo ou grupo matched na Etapa 1
        return False, "Nenhum termo correspondente encontrado", {
            'objetivo_compra': objetivo_compra[:100] + '...' if len(objetivo_compra) > 100 else objetivo_compra,
            'etapa': 1
        }
    
    def _update_keyword_stats(self, grupo: str, termo: str):
        """Atualiza estatísticas de matches de palavras-chave"""
        if grupo not in self.stats['matches_por_grupo']:
            self.stats['matches_por_grupo'][grupo] = 0
        self.stats['matches_por_grupo'][grupo] += 1
        
        if termo not in self.stats['matches_por_termo']:
            self.stats['matches_por_termo'][termo] = 0
        self.stats['matches_por_termo'][termo] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de filtragem híbrida"""
        if self.stats['total_analisados'] == 0:
            return self.stats
        
        # Calcular taxas
        taxa_aprovacao_final = (self.stats['filtrados_aprovados'] / self.stats['total_analisados']) * 100
        taxa_etapa1 = (self.stats['etapa1_aprovados'] / self.stats['total_analisados']) * 100 if self.stats['total_analisados'] > 0 else 0
        taxa_economia_llm = (self.stats['llm_economizados'] / self.stats['total_analisados']) * 100 if self.stats['total_analisados'] > 0 else 0
        
        # Estatísticas básicas
        stats_base = {
            **self.stats,
            'taxa_aprovacao_final_percent': round(taxa_aprovacao_final, 2),
            'taxa_etapa1_aprovacao_percent': round(taxa_etapa1, 2),
            'taxa_economia_llm_percent': round(taxa_economia_llm, 2),
            'filtro_hibrido_ativo': self.llm_ativo,
            'top_grupos': sorted(
                self.stats['matches_por_grupo'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10],
            'top_termos': sorted(
                self.stats['matches_por_termo'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        }
        
        # Adicionar estatísticas do LLM se disponível
        if self.llm_ativo and self.llm_filter:
            try:
                llm_stats = self.llm_filter.get_statistics()
                stats_base['llm_stats'] = llm_stats
            except Exception as e:
                self.logger.warning(f"Erro ao obter estatísticas LLM: {e}")
        
        return stats_base
    
    def log_final_statistics(self):
        """Loga estatísticas finais de filtragem híbrida"""
        stats = self.get_statistics()
        
        self.logger.info("=" * 80)
        self.logger.info("ESTATÍSTICAS DE FILTRAGEM HÍBRIDA")
        self.logger.info("=" * 80)
        self.logger.info(f"Filtro híbrido ativo: {'SIM' if stats.get('filtro_hibrido_ativo', False) else 'NÃO'}")
        self.logger.info(f"Total analisados: {stats['total_analisados']:,}")
        self.logger.info("")
        
        # Estatísticas por etapa
        self.logger.info("FLUXO DO FILTRO:")
        self.logger.info(f"  📋 Total de registros: {stats['total_analisados']:,}")
        self.logger.info(f"  🔍 Etapa 1 (Palavras-chave):")
        self.logger.info(f"    ✅ Aprovados: {stats['etapa1_aprovados']:,} ({stats.get('taxa_etapa1_aprovacao_percent', 0):.1f}%)")
        self.logger.info(f"    ❌ Rejeitados: {stats['etapa1_rejeitados']:,}")
        
        if stats.get('filtro_hibrido_ativo', False):
            self.logger.info(f"  🤖 Etapa 2 (LLM):")
            self.logger.info(f"    ✅ Aprovados: {stats['etapa2_aprovados']:,}")
            self.logger.info(f"    ❌ Rejeitados: {stats['etapa2_rejeitados']:,}")
            self.logger.info(f"  💰 Economia LLM: {stats['llm_economizados']:,} consultas evitadas ({stats.get('taxa_economia_llm_percent', 0):.1f}%)")
        
        self.logger.info("")
        self.logger.info("RESULTADO FINAL:")
        self.logger.info(f"  ✅ Total aprovados: {stats['filtrados_aprovados']:,}")
        self.logger.info(f"  ❌ Total rejeitados: {stats['filtrados_rejeitados']:,}")
        self.logger.info(f"  📊 Taxa de aprovação: {stats.get('taxa_aprovacao_final_percent', 0):.2f}%")
        
        # Top grupos e termos
        if stats.get('top_grupos'):
            self.logger.info("\\n📈 Top 10 grupos mais encontrados:")
            for grupo, count in stats['top_grupos']:
                self.logger.info(f"    {grupo}: {count:,}")
        
        if stats.get('top_termos'):
            self.logger.info("\\n🔑 Top 10 termos mais encontrados:")
            for termo, count in stats['top_termos']:
                self.logger.info(f"    {termo}: {count:,}")
        
        # Estatísticas detalhadas do LLM
        if stats.get('llm_stats'):
            llm_stats = stats['llm_stats']
            self.logger.info("\\n🤖 ESTATÍSTICAS DETALHADAS DO LLM:")
            self.logger.info(f"    Modelo: {llm_stats.get('model_used', 'N/A')}")
            self.logger.info(f"    Consultas: {llm_stats.get('total_queries', 0):,}")
            self.logger.info(f"    Cache hits: {llm_stats.get('cache_hits', 0):,} ({llm_stats.get('cache_hit_rate_percent', 0):.1f}%)")
            self.logger.info(f"    Tokens totais: {llm_stats.get('total_tokens', 0):,}")
            self.logger.info(f"    Custo total: ${llm_stats.get('total_cost_usd', 0):.4f}")
            self.logger.info(f"    Tempo médio: {llm_stats.get('avg_response_time_seconds', 0):.3f}s")
            if llm_stats.get('errors', 0) > 0:
                self.logger.info(f"    ⚠️  Erros: {llm_stats['errors']}")
        
        self.logger.info("=" * 80)


def main():
    """Função para testar o FilterManager"""
    # Teste básico
    filter_manager = FilterManager()
    
    # Registros de teste
    test_records = [
        {"objetoCompra": "Aquisição de canetas esferográficas azuis"},
        {"objetoCompra": "Compra de lápis de cor para escola"},
        {"objetoCompra": "Material de escritório: cadernos e blocos"},
        {"objetoCompra": "Equipamentos de informática"},
        {"objetoCompra": "Aquisição de cola branca escolar"},
        {"objetoCompra": "Compra de mouse e teclado"},
        {"objetoCompra": ""},
    ]
    
    print("=== TESTE DO FILTER MANAGER ===")
    for i, record in enumerate(test_records):
        incluir, motivo, detalhes = filter_manager.should_include_record(record)
        status = "✅ INCLUIR" if incluir else "❌ REJEITAR"
        print(f"{i+1}. {status}: {record.get('objetoCompra', 'VAZIO')}")
        print(f"   Motivo: {motivo}")
        if detalhes.get('criterio'):
            print(f"   Critério: {detalhes['criterio']}")
        print()
    
    # Estatísticas
    print("=== ESTATÍSTICAS ===")
    stats = filter_manager.get_statistics()
    print(f"Total: {stats['total_analisados']}")
    print(f"Aprovados: {stats['filtrados_aprovados']}")
    print(f"Taxa: {stats.get('taxa_aprovacao_percent', 0):.1f}%")


if __name__ == "__main__":
    main()