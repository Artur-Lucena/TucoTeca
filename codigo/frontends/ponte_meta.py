"""Ponte: página do jogo e metadados dos provedores (1.4.2).

Buscar nos provedores e baixar arte passa por rede e pode levar vários
segundos: roda como trabalho cancelável (a ponte NDJSON é serial e cada
pedido tem 30 s). Ler a página não faz rede.
"""
from __future__ import annotations

from ponte_params import inteiro, lista, objeto, opcao, texto

ESCOPO = "metadados"


def metodos_meta(trabalhos) -> dict:
    def _id(params):
        return inteiro(params, "id", positivo=True)

    def pagina(servico, params):
        return servico.pagina_jogo(_id(params))

    def enriquecer(servico, params):
        gid = _id(params)
        chaves = params.get("provedores")
        if chaves is not None:
            chaves = lista(params, "provedores")
            if not all(isinstance(c, str) for c in chaves):
                raise ValueError("provedores deve ser uma lista de textos")
        titulo = servico.jogo(gid).get("titulo") or f"#{gid}"

        def tarefa(progresso, bandeira):
            return servico.enriquecer_jogo(gid, chaves, progresso, bandeira.is_set)
        return {"trabalho": trabalhos.iniciar(f"Buscar dados de {titulo}", tarefa,
                                              cancelavel=True, escopo=ESCOPO)}

    def enriquecer_lote(servico, params):
        def tarefa(progresso, bandeira):
            return servico.enriquecer_lote(progresso, bandeira.is_set)
        return {"trabalho": trabalhos.iniciar("Buscar dados dos jogos", tarefa,
                                              cancelavel=True, escopo=ESCOPO)}

    def meta_salvar(servico, params):
        return servico.salvar_meta(_id(params), objeto(params, "campos"))

    def artes_buscar(servico, params):
        return servico.buscar_artes(_id(params), opcao(params, "tipo", ("hero", "logo", "icone")))

    def arte_aplicar(servico, params):
        tipo = opcao(params, "tipo", ("hero", "logo", "icone"))
        url = texto(params, "url", maximo=1000)
        return servico.aplicar_arte(_id(params), tipo, url)

    def provedores_ler(servico, params):
        return servico.provedores_metadados()

    def provedores_configurar(servico, params):
        ligados = params.get("ligados")
        if ligados is not None:
            ligados = objeto(params, "ligados")
        return servico.configurar_metadados(
            ligados, texto(params, "retro_user", obrigatorio=False, maximo=64),
            texto(params, "retro_key", obrigatorio=False, maximo=256))

    return {
        "jogo.pagina": pagina,
        "jogo.enriquecer": enriquecer,
        "jogos.enriquecer_lote": enriquecer_lote,
        "jogo.meta_salvar": meta_salvar,
        "jogo.artes_buscar": artes_buscar,
        "jogo.arte_aplicar": arte_aplicar,
        "metadados.provedores": provedores_ler,
        "metadados.configurar": provedores_configurar,
    }


__all__ = ["metodos_meta"]
