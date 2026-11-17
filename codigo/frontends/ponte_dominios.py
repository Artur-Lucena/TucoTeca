"""Ponte: métodos por domínio da 1.4 (página do jogo, coleções/loja, Filmes e Séries).

Buscar nos provedores, baixar arte, ler as lojas instaladas, varrer as pastas
de vídeo e renovar séries passam por rede ou disco e podem levar segundos:
rodam como trabalho cancelável (a ponte NDJSON é serial e cada pedido tem
30 s). O resto é leitura local ou uma consulta curta com cache no núcleo.
"""
from __future__ import annotations

import re

from ponte_params import ident, inteiro, lista, objeto, opcao, texto

# ---------------------------------------------------------------- página do jogo e provedores

ESCOPO_META = "metadados"


def metodos_meta(trabalhos) -> dict:
    def pagina(servico, params):
        return servico.pagina_jogo(ident(params))

    def enriquecer(servico, params):
        gid = ident(params)
        chaves = params.get("provedores")
        if chaves is not None:
            chaves = lista(params, "provedores")
            if not all(isinstance(c, str) for c in chaves):
                raise ValueError("provedores deve ser uma lista de textos")
        titulo = servico.jogo(gid).get("titulo") or f"#{gid}"

        def tarefa(progresso, bandeira):
            return servico.enriquecer_jogo(gid, chaves, progresso, bandeira.is_set)
        return {"trabalho": trabalhos.iniciar(f"Buscar dados de {titulo}", tarefa,
                                              cancelavel=True, escopo=ESCOPO_META)}

    def enriquecer_lote(servico, params):
        def tarefa(progresso, bandeira):
            return servico.enriquecer_lote(progresso, bandeira.is_set)
        return {"trabalho": trabalhos.iniciar("Buscar dados dos jogos", tarefa,
                                              cancelavel=True, escopo=ESCOPO_META)}

    def meta_salvar(servico, params):
        return servico.salvar_meta(ident(params), objeto(params, "campos"))

    def artes_buscar(servico, params):
        return servico.buscar_artes(ident(params), opcao(params, "tipo", ("hero", "logo", "icone")))

    def arte_aplicar(servico, params):
        tipo = opcao(params, "tipo", ("hero", "logo", "icone"))
        url = texto(params, "url", maximo=1000)
        return servico.aplicar_arte(ident(params), tipo, url)

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


# ---------------------------------------------------------------- coleções, loja Steam e lojas instaladas

ESCOPO_LOJAS = "lojas-instaladas"


def metodos_colecoes(trabalhos) -> dict:
    def criar(servico, params):
        return servico.criar_colecao(texto(params, "nome", maximo=60))

    def renomear(servico, params):
        return servico.renomear_colecao(ident(params), texto(params, "nome", maximo=60))

    def apagar(servico, params):
        return servico.apagar_colecao(ident(params))

    def do_jogo(servico, params):
        return servico.colecoes_do_jogo(ident(params))

    def definir(servico, params):
        dentro = params.get("dentro")
        if not isinstance(dentro, bool):
            raise ValueError("dentro deve ser verdadeiro ou falso")
        return servico.definir_colecao_jogo(ident(params, "colecao"), ident(params, "jogo"), dentro)

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


# ---------------------------------------------------------------- Filmes e Séries

ESCOPO_MIDIA = "midia"
_IMDB = re.compile(r"^tt\d{5,10}$")
_CHAVE = re.compile(r"^(tt\d{5,10}(:\d{1,3}:\d{1,4})?|arq:[0-9a-f]{40}|arq:\d+)$")


def _imdb(params) -> str:
    v = texto(params, "imdb", maximo=12)
    if not _IMDB.match(v):
        raise ValueError("imdb deve ser um id IMDb (tt…)")
    return v


def _chave(valor) -> str:
    if not isinstance(valor, str) or not _CHAVE.match(valor):
        raise ValueError("chave de vídeo inválida")
    return valor


def _numero(params, chave) -> float:
    v = params.get(chave)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0 or v != v:
        raise ValueError(f"{chave} deve ser um número ≥ 0")
    return float(v)


def metodos_midia(trabalhos) -> dict:
    def _arquivo(params):
        return inteiro(params, "arquivo", positivo=True)

    def varrer(servico, params):
        def tarefa(progresso, bandeira):
            return servico.midia_varrer(progresso, bandeira.is_set)
        return {"trabalho": trabalhos.iniciar("Varrer Filmes e Séries", tarefa, cancelavel=True, escopo=ESCOPO_MIDIA)}

    def atualizar_seguidas(servico, params):
        forcar = params.get("forcar", False) is True

        def tarefa(progresso, bandeira):
            r = servico.midia_atualizar_seguidas(forcar)
            return {**r, "silencioso": True}
        return {"trabalho": trabalhos.iniciar("Atualizar séries seguidas", tarefa, escopo="midia-seguidas")}

    def titulo(servico, params):
        tipo = opcao(params, "tipo", ("movie", "series")) if params.get("tipo") else ""
        return servico.midia_titulo(_imdb(params), tipo)

    def descobrir(servico, params):
        tipo = opcao(params, "tipo", ("movie", "series"))
        genero = texto(params, "genero", obrigatorio=False, maximo=20)
        termo = texto(params, "termo", obrigatorio=False, maximo=100)
        pular = params.get("pular", 0)
        if isinstance(pular, bool) or not isinstance(pular, int) or not 0 <= pular <= 2000:
            raise ValueError("pular deve ser um inteiro entre 0 e 2000")
        return servico.midia_descobrir(tipo, genero, pular, termo)

    def lista_alternar(servico, params):
        return servico.midia_lista_alternar(_imdb(params), opcao(params, "tipo", ("movie", "series")))

    def seguir(servico, params):
        valor = params.get("seguir")
        if not isinstance(valor, bool):
            raise ValueError("seguir deve ser verdadeiro ou falso")
        return servico.midia_seguir(_imdb(params), valor)

    def corrigir(servico, params):
        tipo = opcao(params, "tipo", ("movie", "series"))
        temporada = episodio = None
        if tipo == "series":
            temporada, episodio = inteiro(params, "temporada"), inteiro(params, "episodio")
        return servico.midia_corrigir(_arquivo(params), _imdb(params), tipo, temporada, episodio)

    def salvar_posicao(servico, params):
        return servico.midia_salvar_posicao(_chave(params.get("chave")), _numero(params, "posicao"),
                                            _numero(params, "duracao"))

    def marcar(servico, params):
        chaves = [_chave(c) for c in lista(params, "chaves")][:500]
        valor = params.get("assistido")
        if not isinstance(valor, bool):
            raise ValueError("assistido deve ser verdadeiro ou falso")
        return servico.midia_marcar(chaves, valor)

    def externo(servico, params):
        reprodutor = opcao(params, "reprodutor", ("auto", "vlc", "mpv", "mpchc")) if params.get("reprodutor") else "auto"
        return servico.midia_externo(_arquivo(params), reprodutor)

    return {
        "midia.pastas": lambda s, p: s.midia_pastas(),
        "midia.pasta_adicionar": lambda s, p: s.midia_pasta_adicionar(texto(p, "caminho", maximo=1000)),
        "midia.pasta_remover": lambda s, p: s.midia_pasta_remover(inteiro(p, "id", positivo=True)),
        "midia.varrer": varrer,
        "midia.biblioteca": lambda s, p: s.midia_biblioteca(),
        "midia.titulo": titulo,
        "midia.descobrir": descobrir,
        "midia.continuar": lambda s, p: s.midia_continuar(),
        "midia.lista": lambda s, p: s.midia_lista(),
        "midia.lista_alternar": lista_alternar,
        "midia.seguir": seguir,
        "midia.calendario": lambda s, p: s.midia_calendario(),
        "midia.atualizar_seguidas": atualizar_seguidas,
        "midia.corrigir": corrigir,
        "midia.reproduzir": lambda s, p: s.midia_reproduzir(inteiro(p, "arquivo", positivo=True)),
        "midia.externo": externo,
        "midia.salvar_posicao": salvar_posicao,
        "midia.marcar": marcar,
        "midia.legenda": lambda s, p: s.midia_legenda(inteiro(p, "arquivo", positivo=True), inteiro(p, "indice")),
    }


__all__ = ["metodos_colecoes", "metodos_meta", "metodos_midia"]
