#!/usr/bin/env python3
"""
Prompts Templates - Templates contextuais dinâmicos para análise LLM de licitações
Prompts inteligentes baseados no contexto da Etapa 1 (filtro de palavras-chave)
"""

import json
from typing import List, Dict, Any, Optional


class ContextualLicitationPrompts:
    """Templates de prompts contextuais baseados em filtros.json"""
    
    def __init__(self, filtros_file: str = "filtros.json"):
        self.filtros_file = filtros_file
        self.filtros_cache = None
    
    def _load_filtros(self) -> Dict[str, List[str]]:
        """Carrega filtros.json com cache inteligente"""
        if self.filtros_cache is None:
            try:
                with open(self.filtros_file, 'r', encoding='utf-8') as f:
                    self.filtros_cache = json.load(f)
            except Exception:
                self.filtros_cache = {}
        return self.filtros_cache
    
    def get_contextual_prompt(self, objetivo_compra: str, context: Dict[str, Any] = None) -> str:
        """
        Gera prompt contextual focado na categoria detectada pela Etapa 1
        
        Args:
            objetivo_compra: Texto do objetivo de compra
            context: Contexto da Etapa 1 com grupo_matched, termo_matched, etc.
        """
        context = context or {}
        filtros = self._load_filtros()
        
        # Extrair informações do contexto
        grupo_matched = context.get('grupo_matched', '')
        termo_matched = context.get('termo_matched', '')
        
        if grupo_matched and grupo_matched in filtros:
            # PROMPT CONTEXTUAL FOCADO - só a categoria detectada
            exemplos_categoria = filtros[grupo_matched]
            exemplos_str = ", ".join(exemplos_categoria) if exemplos_categoria else "termos relacionados"
            
            return f"""Você é um especialista em categorização de materiais de escritório e educacionais.

CONTEXTO DA ANÁLISE PRÉVIA:
A Etapa 1 (filtro por palavras-chave) detectou que este objeto de compra está relacionado à categoria "{grupo_matched}".
Termo específico detectado: "{termo_matched}"

CATEGORIA DETECTADA: {grupo_matched}
EXEMPLOS DESTA CATEGORIA: {exemplos_str}

OBJETO DE COMPRA A VALIDAR:
"{objetivo_compra}"

TAREFA:
Confirme se o objeto de compra realmente pertence à categoria "{grupo_matched}" considerando:
1. O contexto completo do objeto (não apenas palavras isoladas)
2. Se o uso principal se alinha com a categoria detectada
3. Os exemplos específicos desta categoria listados acima

INSTRUÇÕES:
- APROVAR: Se o objeto principal realmente se enquadra na categoria {grupo_matched}
- REJEITAR: Se o objeto não se enquadra adequadamente (falso positivo da Etapa 1)
- Considere sinônimos e variações dos termos
- Ignore serviços complementares (instalação, manutenção, etc.)

FORMATO DA RESPOSTA:
DECISAO: [APROVAR/REJEITAR]
CATEGORIA: {grupo_matched}
CONFIANCA: [0-100]%
JUSTIFICATIVA: [breve explicação da decisão]"""
            
        else:
            # PROMPT GENÉRICO (caso não tenha contexto específico)
            return self._get_generic_prompt(objetivo_compra)
    
    def _get_generic_prompt(self, objetivo_compra: str) -> str:
        """Prompt genérico para casos sem contexto específico"""
        return f"""Você é um especialista em análise de licitações públicas.

OBJETO DE COMPRA:
"{objetivo_compra}"

CATEGORIAS ALVO:
- Materiais de escritório (canetas, papel, grampeadores, etc.)
- Materiais educacionais (lápis de cor, cadernos, livros didáticos, etc.)
- Materiais de informática básicos (mouse, teclado, pen drive, etc.)
- Acessórios escolares (mochilas, estojos, lancheiras, etc.)
- Materiais de arte e criatividade (tintas, pincéis, massa de modelar, etc.)

TAREFA:
Determine se o objeto de compra se refere principalmente aos materiais listados acima.

FORMATO DA RESPOSTA:
DECISAO: [APROVAR/REJEITAR]
CATEGORIA: [categoria mais específica, se aplicável]
CONFIANCA: [0-100]%
JUSTIFICATIVA: [breve explicação da decisão]"""


class LicitationPrompts:
    """Templates de prompts para análise de licitações (versão legada)"""
    
    @staticmethod
    def get_categorization_prompt(objetivo_compra: str, categorias_encontradas: List[str] = None) -> str:
        """
        Prompt principal para categorização de objeto de compra
        
        Args:
            objetivo_compra: Texto do objeto de compra a ser analisado
            categorias_encontradas: Lista de categorias já identificadas pelo filtro de palavras
        """
        categorias_contexto = ""
        if categorias_encontradas:
            categorias_contexto = f"""
CATEGORIAS PRÉ-IDENTIFICADAS pelo filtro de palavras-chave:
{', '.join(categorias_encontradas)}

Use essas categorias como contexto, mas NÃO se limite apenas a elas.
"""
        
        return f"""Você é um especialista em análise de licitações públicas e materiais de escritório/educacionais.

TAREFA: Analise o objeto de compra abaixo e determine se ele se refere a MATERIAIS DE ESCRITÓRIO, EDUCACIONAIS OU SIMILARES.

{categorias_contexto}

OBJETO DE COMPRA A ANALISAR:
"{objetivo_compra}"

CRITÉRIOS DE ANÁLISE:
1. Materiais de escritório (canetas, papel, grampeadores, etc.)
2. Materiais educacionais (lápis de cor, cadernos, livros didáticos, etc.)
3. Materiais de informática básicos (mouse, teclado, pen drive, etc.)
4. Acessórios escolares (mochilas, estojos, lancheiras, etc.)
5. Materiais de arte e criatividade (tintas, pincéis, massa de modelar, etc.)

INSTRUÇÕES:
- Analise o CONTEXTO COMPLETO, não apenas palavras isoladas
- Considere SINÔNIMOS e VARIAÇÕES de termos
- Avalie se o objeto principal da compra se enquadra nas categorias acima
- Ignore serviços complementares (instalação, manutenção, etc.)

RESPOSTA OBRIGATÓRIA (escolha apenas uma opção):
- APROVAR: Se o objeto de compra se refere principalmente aos materiais listados
- REJEITAR: Se o objeto de compra NÃO se refere aos materiais listados

FORMATO DA RESPOSTA:
DECISAO: [APROVAR/REJEITAR]
CATEGORIA: [nome da categoria mais específica, se aplicável]
CONFIANCA: [0-100]%
JUSTIFICATIVA: [breve explicação da decisão]"""

    @staticmethod
    def get_category_refinement_prompt(objetivo_compra: str, categoria_inicial: str) -> str:
        """
        Prompt para refinamento de categoria já identificada
        
        Args:
            objetivo_compra: Texto do objeto de compra
            categoria_inicial: Categoria inicialmente identificada
        """
        return f"""Você é um especialista em categorização de materiais de escritório e educacionais.

TAREFA: Refine a categorização do objeto de compra abaixo.

OBJETO DE COMPRA:
"{objetivo_compra}"

CATEGORIA INICIAL IDENTIFICADA:
{categoria_inicial}

CATEGORIAS DISPONÍVEIS PARA REFINAMENTO:
- ACESSORIOS_CELULAR: carregadores, cabos, capas, películas
- ACESSORIOS_INFORMATICA: mouse, teclado, webcam, cabo HDMI
- AUDIO: caixas de som, microfones, headsets
- CANETAS: canetas, marcadores, marca-texto
- CADERNOS: cadernos, blocos, agendas
- CALCULADORAS: calculadoras científicas, básicas
- COLA: colas brancas, bastão, silicone
- LAPIS: lápis de cor, grafite, lapiseiras
- PAPEL: papéis diversos, formulários
- IMPRESSOS: impressos fiscais, formulários
- OUTROS: outros materiais válidos

RESPOSTA:
CATEGORIA_REFINADA: [categoria mais específica]
CONFIANCA: [0-100]%
OBSERVACOES: [detalhes relevantes]"""

    @staticmethod
    def get_batch_analysis_prompt(objetivos_compra: List[str]) -> str:
        """
        Prompt para análise em lote de múltiplos objetos de compra
        
        Args:
            objetivos_compra: Lista de objetos de compra para analisar
        """
        objetivos_numerados = "\n".join([f"{i+1}. {obj}" for i, obj in enumerate(objetivos_compra)])
        
        return f"""Você é um especialista em análise de licitações públicas.

TAREFA: Analise os objetos de compra abaixo e determine quais se referem a MATERIAIS DE ESCRITÓRIO, EDUCACIONAIS OU SIMILARES.

OBJETOS DE COMPRA:
{objetivos_numerados}

Para cada item, responda:
- APROVAR ou REJEITAR
- Categoria principal (se aplicável)

FORMATO DA RESPOSTA:
1. DECISAO: [APROVAR/REJEITAR] - CATEGORIA: [categoria] - CONFIANÇA: [0-100]%
2. DECISAO: [APROVAR/REJEITAR] - CATEGORIA: [categoria] - CONFIANÇA: [0-100]%
[continue para todos os itens...]"""

    @staticmethod
    def get_uncertainty_prompt(objetivo_compra: str) -> str:
        """
        Prompt especial para casos incertos que precisam de análise mais cuidadosa
        
        Args:
            objetivo_compra: Objeto de compra com classificação incerta
        """
        return f"""Você é um especialista sênior em licitações públicas com foco em materiais educacionais e de escritório.

CASO ESPECIAL - ANÁLISE DETALHADA NECESSÁRIA

OBJETO DE COMPRA:
"{objetivo_compra}"

Este caso foi identificado como INCERTO pelo sistema inicial. Faça uma análise MUITO CUIDADOSA considerando:

1. CONTEXTO PRINCIPAL: Qual é o objetivo principal da compra?
2. PROPORÇÃO: Que porcentagem se refere a materiais de escritório/educacionais?
3. CLASSIFICAÇÃO PRINCIPAL: Como esta licitação seria classificada prioritariamente?

MATERIAIS ALVO (que DEVEMOS incluir):
- Materiais de escritório básicos
- Materiais educacionais e escolares  
- Acessórios de informática básicos
- Materiais de arte e criatividade

MATERIAIS FORA DO ESCOPO (que DEVEMOS excluir):
- Equipamentos eletrônicos complexos
- Móveis e estruturas
- Serviços de manutenção/instalação
- Materiais de construção
- Equipamentos médicos/industriais

RESPOSTA DETALHADA:
DECISAO_FINAL: [APROVAR/REJEITAR]
CATEGORIA_PRINCIPAL: [categoria mais adequada]
PORCENTAGEM_RELEVANTE: [% do objeto que se refere aos materiais alvo]
ANALISE_DETALHADA: [explicação completa da decisão]
CONFIANCA: [0-100]%"""


class PromptBuilder:
    """Construtor inteligente de prompts contextuais baseado no filtros.json"""
    
    def __init__(self, filtros_file: str = "filtros.json"):
        self.contextual_prompts = ContextualLicitationPrompts(filtros_file)
        self.legacy_prompts = LicitationPrompts()  # Para compatibilidade
    
    def build_contextual_prompt(self, 
                              objetivo_compra: str, 
                              context: Dict[str, Any] = None) -> str:
        """
        Constrói prompt contextual inteligente baseado na Etapa 1
        
        Args:
            objetivo_compra: Texto do objeto de compra
            context: Contexto da Etapa 1 (grupo_matched, termo_matched, etc.)
        """
        context = context or {}
        
        # Usar nova lógica contextual baseada em filtros.json
        return self.contextual_prompts.get_contextual_prompt(objetivo_compra, context)
    
    def build_batch_prompt(self, objetivos_compra: List[str]) -> str:
        """Constrói prompt para análise em lote (compatibilidade)"""
        return self.legacy_prompts.get_batch_analysis_prompt(objetivos_compra)
    
    def build_focused_prompt(self, objetivo_compra: str, etapa1_results: Dict[str, Any]) -> str:
        """
        Constrói prompt super focado baseado nos resultados da Etapa 1
        
        Args:
            objetivo_compra: Texto do objetivo de compra
            etapa1_results: Resultados específicos da Etapa 1
        """
        return self.contextual_prompts.get_contextual_prompt(objetivo_compra, etapa1_results)


def main():
    """Função de teste dos prompts"""
    builder = PromptBuilder()
    
    # Teste básico
    teste_objetivo = "Aquisição de canetas esferográficas azuis e vermelhas para uso escolar"
    prompt = builder.build_contextual_prompt(teste_objetivo)
    
    print("=== TESTE DE PROMPT ===")
    print(prompt)
    print("\n" + "="*60)


if __name__ == "__main__":
    main()