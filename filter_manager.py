#!/usr/bin/env python3
"""
FilterManager - Filtro Inteligente para objetoCompra
Implementa filtro baseado em busca de termos com normalização
"""

import json
import re
import unicodedata
from typing import Dict, List, Any, Tuple
import logging


class FilterManager:
    """Gerenciador de filtros inteligentes para licitações"""
    
    def __init__(self, filtros_file: str = "filtros.json", config: Dict[str, Any] = None):
        self.filtros_file = filtros_file
        self.config = config or {}
        self.grupos_termos = self._load_grupos_termos()
        self.logger = logging.getLogger(__name__)
        
        # Configurações do filtro
        self.ativo = self.config.get('filtro_ativo', True)
        self.log_matches = self.config.get('filtro_log_matches', True)
        
        # Estatísticas
        self.stats = {
            'total_analisados': 0,
            'filtrados_aprovados': 0,
            'filtrados_rejeitados': 0,
            'matches_por_grupo': {},
            'matches_por_termo': {}
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
        Determina se um registro deve ser incluído baseado no objetoCompra
        
        Returns:
            tuple: (incluir: bool, motivo: str, detalhes: dict)
        """
        if not self.ativo:
            return True, "Filtro desativado", {}
        
        self.stats['total_analisados'] += 1
        
        objetivo_compra = record.get('objetoCompra', '')
        if not objetivo_compra:
            self.stats['filtrados_rejeitados'] += 1
            return False, "objetoCompra vazio", {}
        
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
                self._update_stats(grupo, grupo)
                detalhes = {
                    'grupo_matched': grupo,
                    'termo_matched': grupo,
                    'criterio': f'Nome do grupo "{grupo}" (palavra exata)',
                    'objetivo_compra': objetivo_compra[:100] + '...' if len(objetivo_compra) > 100 else objetivo_compra
                }
                if self.log_matches:
                    self.logger.info(f"MATCH GRUPO: '{grupo}' em '{objetivo_compra[:50]}...'")
                return True, f"Match com grupo '{grupo}'", detalhes
            
            # Depois testa cada termo do grupo (palavra exata)
            for termo in termos:
                termo_normalizado = self._normalize_text(termo)
                if termo_normalizado and self._match_exact_word(objetivo_normalizado, termo_normalizado):
                    self._update_stats(grupo, termo)
                    detalhes = {
                        'grupo_matched': grupo,
                        'termo_matched': termo,
                        'criterio': f'Termo "{termo}" do grupo "{grupo}" (palavra exata)',
                        'objetivo_compra': objetivo_compra[:100] + '...' if len(objetivo_compra) > 100 else objetivo_compra
                    }
                    if self.log_matches:
                        self.logger.info(f"MATCH TERMO: '{termo}' (grupo: {grupo}) em '{objetivo_compra[:50]}...'")
                    return True, f"Match com termo '{termo}' do grupo '{grupo}'", detalhes
        
        # Nenhum termo ou grupo matched
        self.stats['filtrados_rejeitados'] += 1
        return False, "Nenhum termo correspondente encontrado", {'objetivo_compra': objetivo_compra[:100]}
    
    def _update_stats(self, grupo: str, termo: str):
        """Atualiza estatísticas de matches"""
        self.stats['filtrados_aprovados'] += 1
        
        if grupo not in self.stats['matches_por_grupo']:
            self.stats['matches_por_grupo'][grupo] = 0
        self.stats['matches_por_grupo'][grupo] += 1
        
        if termo not in self.stats['matches_por_termo']:
            self.stats['matches_por_termo'][termo] = 0
        self.stats['matches_por_termo'][termo] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de filtragem"""
        if self.stats['total_analisados'] == 0:
            return self.stats
        
        taxa_aprovacao = (self.stats['filtrados_aprovados'] / self.stats['total_analisados']) * 100
        
        return {
            **self.stats,
            'taxa_aprovacao_percent': round(taxa_aprovacao, 2),
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
    
    def log_final_statistics(self):
        """Loga estatísticas finais de filtragem"""
        stats = self.get_statistics()
        
        self.logger.info("=" * 60)
        self.logger.info("ESTATÍSTICAS DE FILTRAGEM")
        self.logger.info("=" * 60)
        self.logger.info(f"Total analisados: {stats['total_analisados']}")
        self.logger.info(f"Aprovados: {stats['filtrados_aprovados']}")
        self.logger.info(f"Rejeitados: {stats['filtrados_rejeitados']}")
        self.logger.info(f"Taxa de aprovação: {stats.get('taxa_aprovacao_percent', 0):.2f}%")
        
        self.logger.info("\\nTop 10 grupos mais encontrados:")
        for grupo, count in stats.get('top_grupos', []):
            self.logger.info(f"  {grupo}: {count}")
        
        self.logger.info("\\nTop 10 termos mais encontrados:")
        for termo, count in stats.get('top_termos', []):
            self.logger.info(f"  {termo}: {count}")
        
        self.logger.info("=" * 60)


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