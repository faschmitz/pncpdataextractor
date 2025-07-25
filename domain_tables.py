#!/usr/bin/env python3
"""
Tabelas de Domínio do PNCP - Portal Nacional de Contratações Públicas

Este módulo contém todas as tabelas de domínio oficiais do PNCP,
baseadas na documentação oficial disponível em:
https://pncp.gov.br/app/entidades-dominio
"""

from typing import Dict, List, Optional


class DomainTables:
    """Tabelas de domínio do PNCP"""
    
    # Modalidades de Contratação (baseado em https://pncp.gov.br/app/entidades-dominio)
    MODALIDADES_CONTRATACAO = {
        1: {
            "nome": "Leilão - Eletrônico",
            "descricao": "Modalidade de licitação para alienação de bens imóveis ou de bens móveis inservíveis ou legalmente apreendidos a quem oferecer o maior lance",
            "ativo": True
        },
        2: {
            "nome": "Diálogo Competitivo",
            "descricao": "Modalidade de licitação utilizada para contratação de obras, serviços e fornecimentos quando não é possível definir previamente a solução técnica mais adequada",
            "ativo": True
        },
        3: {
            "nome": "Concurso",
            "descricao": "Modalidade de licitação para escolha de trabalho técnico, científico ou artístico",
            "ativo": True
        },
        4: {
            "nome": "Concorrência - Eletrônica",
            "descricao": "Modalidade de licitação entre quaisquer interessados que, na fase inicial de habilitação preliminar, comprovem possuir os requisitos mínimos de qualificação exigidos no edital para execução de seu objeto",
            "ativo": True
        },
        5: {
            "nome": "Concorrência - Presencial",
            "descricao": "Modalidade de licitação entre quaisquer interessados que, na fase inicial de habilitação preliminar, comprovem possuir os requisitos mínimos de qualificação exigidos no edital para execução de seu objeto",
            "ativo": True
        },
        6: {
            "nome": "Pregão - Eletrônico",
            "descricao": "Modalidade de licitação obrigatória para aquisição de bens e serviços comuns, qualquer que seja o valor estimado da contratação",
            "ativo": True
        },
        7: {
            "nome": "Pregão - Presencial",
            "descricao": "Modalidade de licitação para aquisição de bens e serviços comuns, realizada de forma presencial",
            "ativo": True
        },
        8: {
            "nome": "Dispensa",
            "descricao": "Situação em que é possível a realização direta de contratação, mas a licitação é dispensada por determinação legal",
            "ativo": True
        },
        9: {
            "nome": "Inexigibilidade",
            "descricao": "Situação em que é impossível a competição, seja pela natureza específica do negócio, seja pelos objetivos sociais visados pela Administração",
            "ativo": True
        },
        10: {
            "nome": "Manifestação de Interesse",
            "descricao": "Procedimento para manifestação de interesse privado para posterior abertura de processo licitatório ou contratação direta",
            "ativo": True
        },
        11: {
            "nome": "Pré-qualificação",
            "descricao": "Procedimento anterior à licitação destinado a identificar licitantes que reúnam condições de habilitação exigidas para o certame",
            "ativo": True
        },
        12: {
            "nome": "Credenciamento",
            "descricao": "Procedimento para seleção de interessados em prestar serviços ou fornecer bens de forma não exclusiva",
            "ativo": True
        },
        13: {
            "nome": "Leilão - Presencial",
            "descricao": "Modalidade de licitação realizada sob a forma presencial para alienação de bens imóveis ou de bens móveis inservíveis ou legalmente apreendidos a quem oferecer o maior lance",
            "ativo": True
        }
    }
    
    # Situações de Compra (observadas nos dados da API)
    SITUACOES_COMPRA = {
        1: {
            "nome": "Divulgada no PNCP",
            "descricao": "Contratação divulgada no Portal Nacional de Contratações Públicas"
        },
        2: {
            "nome": "Em Andamento",
            "descricao": "Processo de contratação em andamento"
        },
        3: {
            "nome": "Anulada",
            "descricao": "Processo de contratação anulado"
        },
        4: {
            "nome": "Cancelada",
            "descricao": "Processo de contratação cancelado"
        },
        5: {
            "nome": "Concluída",
            "descricao": "Processo de contratação concluído"
        },
        6: {
            "nome": "Suspensa",
            "descricao": "Processo de contratação suspenso temporariamente"
        }
    }
    
    # Modos de Disputa (baseado em https://pncp.gov.br/app/entidades-dominio)
    MODOS_DISPUTA = {
        1: {
            "nome": "Aberto",
            "descricao": "Modo de disputa onde as propostas são apresentadas de forma aberta"
        },
        2: {
            "nome": "Fechado",
            "descricao": "Modo de disputa onde as propostas são apresentadas de forma sigilosa"
        },
        3: {
            "nome": "Aberto-Fechado",
            "descricao": "Primeira fase aberta, segunda fase fechada"
        },
        4: {
            "nome": "Fechado-Aberto",
            "descricao": "Primeira fase fechada, segunda fase aberta"
        }
    }
    
    # Critérios de Julgamento (baseado em https://pncp.gov.br/app/entidades-dominio)
    CRITERIOS_JULGAMENTO = {
        1: {
            "nome": "Menor preço",
            "descricao": "Critério de julgamento baseado no menor preço ofertado"
        },
        2: {
            "nome": "Maior desconto",
            "descricao": "Critério de julgamento baseado no maior desconto oferecido"
        },
        3: {
            "nome": "Melhor técnica",
            "descricao": "Critério de julgamento baseado na qualidade técnica"
        },
        4: {
            "nome": "Técnica e preço",
            "descricao": "Critério de julgamento que combina aspectos técnicos e preço"
        },
        5: {
            "nome": "Maior lance",
            "descricao": "Critério de julgamento baseado no maior lance oferecido (usado em leilões)"
        },
        6: {
            "nome": "Maior oferta",
            "descricao": "Critério de julgamento baseado na maior oferta"
        }
    }
    
    # Tipos de Instrumento Convocatório (baseado em https://pncp.gov.br/app/entidades-dominio)
    TIPOS_INSTRUMENTO_CONVOCATORIO = {
        1: {
            "nome": "Edital",
            "descricao": "Instrumento convocatório utilizado no leilão, no pregão, na concorrência, no concurso e no diálogo competitivo"
        },
        2: {
            "nome": "Aviso de Contratação Direta",
            "descricao": "Instrumento convocatório utilizado na Contratação Direta"
        },
        3: {
            "nome": "Ato que autoriza a Contratação Direta",
            "descricao": "Instrumento convocatório utilizado na Dispensa com Disputa"
        },
        4: {
            "nome": "Edital de Chamamento Público",
            "descricao": "Instrumento convocatório utilizado para processos auxiliares"
        }
    }
    
    # Esferas de Governo (baseado em https://pncp.gov.br/app/entidades-dominio)
    ESFERAS_GOVERNO = {
        "F": {
            "nome": "Federal",
            "descricao": "Esfera Federal - Administração Pública Federal"
        },
        "E": {
            "nome": "Estadual", 
            "descricao": "Esfera Estadual - Administração Pública Estadual"
        },
        "M": {
            "nome": "Municipal",
            "descricao": "Esfera Municipal - Administração Pública Municipal"
        }
    }
    
    # Poderes
    PODERES = {
        "E": {
            "nome": "Executivo",
            "descricao": "Poder Executivo"
        },
        "L": {
            "nome": "Legislativo", 
            "descricao": "Poder Legislativo"
        },
        "J": {
            "nome": "Judiciário",
            "descricao": "Poder Judiciário"
        },
        "N": {
            "nome": "Não Especificado",
            "descricao": "Poder não especificado ou outros"
        }
    }
    
    @classmethod
    def get_modalidade_nome(cls, codigo: int) -> str:
        """Retorna o nome da modalidade pelo código"""
        modalidade = cls.MODALIDADES_CONTRATACAO.get(codigo)
        return modalidade["nome"] if modalidade else f"Modalidade {codigo}"
    
    @classmethod
    def get_modalidade_descricao(cls, codigo: int) -> str:
        """Retorna a descrição da modalidade pelo código"""
        modalidade = cls.MODALIDADES_CONTRATACAO.get(codigo)
        return modalidade["descricao"] if modalidade else f"Modalidade não encontrada: {codigo}"
    
    @classmethod
    def get_modalidades_ativas(cls) -> List[int]:
        """Retorna lista de códigos de modalidades ativas"""
        return [codigo for codigo, dados in cls.MODALIDADES_CONTRATACAO.items() 
                if dados["ativo"]]
    
    @classmethod
    def get_situacao_compra_nome(cls, codigo: int) -> str:
        """Retorna o nome da situação de compra pelo código"""
        situacao = cls.SITUACOES_COMPRA.get(codigo)
        return situacao["nome"] if situacao else f"Situação {codigo}"
    
    @classmethod
    def get_modo_disputa_nome(cls, codigo: int) -> str:
        """Retorna o nome do modo de disputa pelo código"""
        modo = cls.MODOS_DISPUTA.get(codigo)
        return modo["nome"] if modo else f"Modo {codigo}"
    
    @classmethod
    def get_criterio_julgamento_nome(cls, codigo: int) -> str:
        """Retorna o nome do critério de julgamento pelo código"""
        criterio = cls.CRITERIOS_JULGAMENTO.get(codigo)
        return criterio["nome"] if criterio else f"Critério {codigo}"
    
    @classmethod
    def get_instrumento_convocatorio_nome(cls, codigo: int) -> str:
        """Retorna o nome do instrumento convocatório pelo código"""
        instrumento = cls.TIPOS_INSTRUMENTO_CONVOCATORIO.get(codigo)
        return instrumento["nome"] if instrumento else f"Instrumento {codigo}"
    
    @classmethod
    def get_esfera_nome(cls, codigo: str) -> str:
        """Retorna o nome da esfera pelo código"""
        esfera = cls.ESFERAS_GOVERNO.get(codigo)
        return esfera["nome"] if esfera else f"Esfera {codigo}"
    
    @classmethod  
    def get_poder_nome(cls, codigo: str) -> str:
        """Retorna o nome do poder pelo código"""
        poder = cls.PODERES.get(codigo)
        return poder["nome"] if poder else f"Poder {codigo}"
    
    @classmethod
    def validate_modalidade(cls, codigo: int) -> bool:
        """Valida se o código de modalidade existe e está ativo"""
        modalidade = cls.MODALIDADES_CONTRATACAO.get(codigo)
        return modalidade is not None and modalidade["ativo"]
    
    @classmethod
    def get_modalidades_por_categoria(cls) -> Dict[str, List[int]]:
        """Agrupa modalidades por categoria"""
        categorias = {
            "Licitação Tradicional": [3, 4, 5, 6, 7],  # Concurso, Concorrência, Pregão
            "Leilão": [1, 13],  # Leilão Eletrônico e Presencial
            "Procedimentos Especiais": [2, 10, 11, 12],  # Diálogo, Manifestação, Pré-qual, Credenc.
            "Contratação Direta": [8, 9]  # Dispensa, Inexigibilidade
        }
        return categorias
    
    @classmethod
    def get_modalidades_eletronicas(cls) -> List[int]:
        """Retorna modalidades que são eletrônicas"""
        return [1, 4, 6]  # Leilão Eletrônico, Concorrência Eletrônica, Pregão Eletrônico
    
    @classmethod
    def get_modalidades_presenciais(cls) -> List[int]:
        """Retorna modalidades que são presenciais"""
        return [5, 7, 13]  # Concorrência Presencial, Pregão Presencial, Leilão Presencial


def main():
    """Função para testar as tabelas de domínio"""
    dt = DomainTables()
    
    print("=== TABELAS DE DOMÍNIO DO PNCP (ATUALIZADAS) ===\n")
    
    print("MODALIDADES DE CONTRATAÇÃO:")
    for codigo in dt.get_modalidades_ativas():
        nome = dt.get_modalidade_nome(codigo)
        print(f"  {codigo:2d} - {nome}")
    
    print(f"\nTotal de modalidades ativas: {len(dt.get_modalidades_ativas())}")
    
    print("\nMODOS DE DISPUTA:")
    for codigo, dados in dt.MODOS_DISPUTA.items():
        print(f"  {codigo} - {dados['nome']}")
    
    print("\nCRITÉRIOS DE JULGAMENTO:")
    for codigo, dados in dt.CRITERIOS_JULGAMENTO.items():
        print(f"  {codigo} - {dados['nome']}")
    
    print("\nTIPOS DE INSTRUMENTO CONVOCATÓRIO:")
    for codigo, dados in dt.TIPOS_INSTRUMENTO_CONVOCATORIO.items():
        print(f"  {codigo} - {dados['nome']}")
    
    print("\nESFERAS DE GOVERNO:")
    for codigo, dados in dt.ESFERAS_GOVERNO.items():
        print(f"  {codigo} - {dados['nome']}")
    
    print("\nPODERES:")
    for codigo, dados in dt.PODERES.items():
        print(f"  {codigo} - {dados['nome']}")
    
    print(f"\nModalidades por categoria:")
    for categoria, codigos in dt.get_modalidades_por_categoria().items():
        print(f"  {categoria}: {codigos}")
    
    print(f"\nModalidades eletrônicas: {dt.get_modalidades_eletronicas()}")
    print(f"Modalidades presenciais: {dt.get_modalidades_presenciais()}")
    
    print("\n=== VALIDAÇÃO COMPLETA ===")
    print(f"Tabelas implementadas: 6")
    print(f"Modalidades: {len(dt.MODALIDADES_CONTRATACAO)}")
    print(f"Modos de Disputa: {len(dt.MODOS_DISPUTA)}")
    print(f"Critérios: {len(dt.CRITERIOS_JULGAMENTO)}")
    print(f"Instrumentos: {len(dt.TIPOS_INSTRUMENTO_CONVOCATORIO)}")
    print(f"Esferas: {len(dt.ESFERAS_GOVERNO)}")
    print(f"Poderes: {len(dt.PODERES)}")


if __name__ == "__main__":
    main()