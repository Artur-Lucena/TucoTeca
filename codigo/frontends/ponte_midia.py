"""Ponte: Filmes e Séries (1.4.4) — pastas, índice, Cinemeta, progresso e legendas.

Varrer as pastas (disco + catálogo) e renovar as séries seguidas rodam como
trabalho; o resto é leitura local ou uma consulta curta ao Cinemeta.
"""
from __future__ import annotations

import re

from ponte_params import inteiro, lista, opcao, texto

ESCOPO = "midia"
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
        return {"trabalho": trabalhos.iniciar("Varrer Filmes e Séries", tarefa, cancelavel=True, escopo=ESCOPO)}

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


__all__ = ["metodos_midia"]
