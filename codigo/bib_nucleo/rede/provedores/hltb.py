"""HowLongToBeat (sem chave, API não oficial): horas para zerar.

Desligado por padrão: o site muda a API sem aviso. Quando falha, a página do
jogo deixa preencher as horas à mão.
"""
from __future__ import annotations

import json

from bib_nucleo.rede import online
from bib_nucleo.rede.provedores._apoio import normalizar_titulo, obter, respeitar_ritmo

URL = "https://howlongtobeat.com/api/search"
VALIDADE = 30 * 86400


def _horas(segundos) -> float:
    try:
        return round(float(segundos) / 3600 * 2) / 2
    except (TypeError, ValueError):
        return 0.0


def buscar(jogo: dict, meta: dict) -> dict:
    titulo = str(jogo.get("titulo") or "").strip()
    if len(titulo) < 2:
        return {}
    corpo = {"searchType": "games", "searchTerms": titulo.split(), "searchPage": 1, "size": 5,
             "searchOptions": {"games": {"userId": 0, "platform": "", "sortCategory": "popular",
                                         "rangeCategory": "main", "rangeTime": {"min": 0, "max": 0},
                                         "gameplay": {"perspective": "", "flow": "", "genre": ""},
                                         "modifier": ""},
                               "users": {"sortCategory": "postcount"}, "filter": "", "sort": 0,
                               "randomizer": 0}}

    def consultar():
        respeitar_ritmo("howlongtobeat.com", 2.0)
        try:
            return online.requisitar_json(
                URL, dados=json.dumps(corpo).encode("utf-8"),
                headers={"Content-Type": "application/json", "Referer": "https://howlongtobeat.com/",
                         "Origin": "https://howlongtobeat.com"})
        except ValueError:
            raise ValueError("o HowLongToBeat mudou ou recusou a consulta; "
                             "preencha as horas à mão na página do jogo.") from None
    dados = obter("hltb", titulo.casefold(), VALIDADE, consultar)
    alvo = normalizar_titulo(titulo)
    for item in dados.get("data") or []:
        if not isinstance(item, dict) or normalizar_titulo(item.get("game_name") or "") != alvo:
            continue
        horas = {"principal": _horas(item.get("comp_main")), "extra": _horas(item.get("comp_plus")),
                 "completo": _horas(item.get("comp_100"))}
        if any(horas.values()):
            return {"hltb": horas}
    return {}


__all__ = ["buscar"]
