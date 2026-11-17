#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validação de parâmetros da ponte NDJSON, num lugar só.

Os handlers repetiam o mesmo bloco (`params.get` + `isinstance` + `strip` +
`raise`). Estas funções devolvem o valor limpo ou levantam `ValueError` com as
MESMAS mensagens que a ponte sempre usou (os testes de contrato conferem o
texto): "X deve ser um texto", "X deve ser um inteiro", "id deve ser um
inteiro positivo", "X deve ser um de: a, b".

Uso no handler:
    caminho = texto(params, "caminho")
    jogo = ident(params)
    acao = opcao(params, "acao", ("pausar", "retomar"))
"""
from __future__ import annotations

from collections.abc import Iterable

_FALTA = object()


def texto(params: dict, chave: str, obrigatorio: bool = True, maximo: int | None = None,
          padrao: str = "") -> str:
    """Texto sem espaços nas pontas; obrigatório não pode ficar vazio."""
    valor = params.get(chave, _FALTA)
    if valor is _FALTA or valor is None:
        if obrigatorio:
            raise ValueError(f"{chave} deve ser um texto")
        return padrao
    if not isinstance(valor, str):
        raise ValueError(f"{chave} deve ser um texto")
    valor = valor.strip()
    if obrigatorio and not valor:
        raise ValueError(f"{chave} deve ser um texto")
    if maximo is not None and len(valor) > maximo:
        raise ValueError(f"{chave} passa de {maximo} caracteres")
    return valor


def inteiro(params: dict, chave: str, positivo: bool = False) -> int:
    """Inteiro de verdade (bool não conta). `positivo` exige > 0."""
    valor = params.get(chave)
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError(f"{chave} deve ser um inteiro positivo" if positivo
                         else f"{chave} deve ser um inteiro")
    if positivo and valor <= 0:
        raise ValueError(f"{chave} deve ser um inteiro positivo")
    return valor


def ident(params: dict, chave: str = "id") -> int:
    """Identificador local (inteiro positivo)."""
    return inteiro(params, chave, positivo=True)


def opcao(params: dict, chave: str, opcoes: Iterable[str]) -> str:
    """Valor de um vocabulário fechado."""
    opcoes = tuple(opcoes)
    valor = params.get(chave)
    if valor not in opcoes:
        raise ValueError(f"{chave} deve ser um de: {', '.join(opcoes)}")
    return valor


def objeto(params: dict, chave: str) -> dict:
    valor = params.get(chave)
    if not isinstance(valor, dict):
        raise ValueError(f"{chave} deve ser um objeto")
    return valor


def lista(params: dict, chave: str) -> list:
    valor = params.get(chave)
    if not isinstance(valor, list):
        raise ValueError(f"{chave} deve ser uma lista")
    return valor


__all__ = ["texto", "inteiro", "ident", "opcao", "objeto", "lista"]
