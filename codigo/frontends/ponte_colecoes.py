"""Ponte: coleções, catálogo da loja Steam e importação das lojas instaladas (1.4.3).

Catálogo: uma consulta curta por pedido (cache no núcleo), como a busca de
capas. Ler as lojas instaladas varre disco e registro: roda como trabalho.
"""
from __future__ import annotations

from ponte_params import inteiro, texto

ESCOPO_LOJAS = "lojas-instaladas"


def metodos_colecoes(trabalhos) -> dict:
    def _id(params, chave="id"):
        return inteiro(params, chave, positivo=True)

    def listar(servico, params):
        return servico.colecoes()

    def criar(servico, params):
        return servico.criar_colecao(texto(params, "nome", maximo=60))

    def renomear(servico, params):
        return servico.renomear_colecao(_id(params), texto(params, "nome", maximo=60))

    def apagar(servico, params):
        return servico.apagar_colecao(_id(params))

    def do_jogo(servico, params):
        return servico.colecoes_do_jogo(_id(params))

    def definir(servico, params):
        dentro = params.get("dentro")
        if not isinstance(dentro, bool):
            raise ValueError("dentro deve ser verdadeiro ou falso")
        return servico.definir_colecao_jogo(_id(params, "colecao"), _id(params, "jogo"), dentro)

    def loja_destaques(servico, params):
        return servico.loja_destaques()

    def loja_buscar(servico, params):
        return servico.loja_buscar(texto(params, "termo", maximo=100))

    def loja_pagina(servico, params):
        appid = texto(params, "appid", maximo=12)
        if not appid.isdigit():
            raise ValueError("appid deve conter só dígitos")
        return servico.loja_pagina(appid)

    def loja_desejar(servico, params):
        appid = texto(params, "appid", maximo=12)
        if not appid.isdigit():
            raise ValueError("appid deve conter só dígitos")
        return servico.loja_desejar(appid, texto(params, "titulo", maximo=200))

    def lojas_prever(servico, params):
        def tarefa(progresso, bandeira):
            return servico.prever_lojas()
        return {"trabalho": trabalhos.iniciar("Ler lojas instaladas", tarefa, escopo=ESCOPO_LOJAS)}

    return {
        "colecoes.listar": listar,
        "colecoes.criar": criar,
        "colecoes.renomear": renomear,
        "colecoes.apagar": apagar,
        "colecoes.definir": definir,
        "jogo.colecoes": do_jogo,
        "loja.destaques": loja_destaques,
        "loja.buscar": loja_buscar,
        "loja.pagina": loja_pagina,
        "loja.desejar": loja_desejar,
        "jogos.lojas_prever": lojas_prever,
    }


__all__ = ["metodos_colecoes"]
