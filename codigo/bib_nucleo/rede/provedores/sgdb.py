"""SteamGridDB (chave do usuário): hero, logo e ícone."""
from __future__ import annotations

import urllib.parse

from bib_nucleo.rede import online
from bib_nucleo.rede.provedores._apoio import obter, respeitar_ritmo

BASE = "https://www.steamgriddb.com/api/v2"
VALIDADE = 14 * 86400
TIPOS = {"hero": "heroes", "logo": "logos", "icone": "icons", "capa": "grids"}


def _get(caminho: str) -> dict:
    chave = online.chave_provedor("steamgriddb_key")
    if not chave:
        raise ValueError("Configure a chave SteamGridDB em Configurações.")
    respeitar_ritmo("steamgriddb.com", 0.4)
    return online.requisitar_json(BASE + caminho, headers={"Authorization": "Bearer " + chave})


def resolver_id(jogo: dict, meta: dict) -> str:
    ident = str(meta.get("sgdb_id") or "")
    if ident.isdigit():
        return ident
    appid = str(meta.get("steam_appid") or "")
    if appid.isdigit():
        try:
            dados = obter("sgdb-steam", appid, VALIDADE, lambda: _get(f"/games/steam/{appid}"))
            ident = str((dados.get("data") or {}).get("id") or "")
            if ident.isdigit():
                return ident
        except ValueError:
            pass  # jogo fora da Steam ou appid desconhecido: cai na busca por nome
    titulo = str(jogo.get("titulo") or "").strip()
    if len(titulo) < 2:
        return ""
    dados = obter("sgdb-busca", titulo.casefold(), VALIDADE,
                  lambda: _get("/search/autocomplete/" + urllib.parse.quote(titulo, safe="")))
    for item in dados.get("data") or []:
        if isinstance(item, dict) and str(item.get("id") or "").isdigit():
            return str(item["id"])
    return ""


def artes(ident: str, tipo: str, limite: int = 6) -> list[dict]:
    """Candidatos de um tipo de arte: [{url, preview, autor}]."""
    recurso = TIPOS.get(tipo)
    if not recurso or not str(ident).isdigit():
        return []
    filtro = "?dimensions=600x900&types=static" if tipo == "capa" else "?types=static"
    dados = obter(f"sgdb-{recurso}", str(ident), VALIDADE, lambda: _get(f"/{recurso}/game/{ident}{filtro}"))
    saida = []
    for a in (dados.get("data") or [])[:limite]:
        url = str(a.get("url") or "") if isinstance(a, dict) else ""
        if online.url_https(url):
            saida.append({"url": url, "preview": str(a.get("thumb") or url),
                          "autor": str((a.get("author") or {}).get("name") or "")})
    return saida


def buscar(jogo: dict, meta: dict) -> dict:
    ident = resolver_id(jogo, meta)
    if not ident:
        return {}
    saida: dict = {"sgdb_id": ident}
    for tipo in ("hero", "logo", "icone"):
        lista = artes(ident, tipo, limite=1)
        if lista:
            saida[f"{tipo}_url"] = lista[0]["url"]
    return saida


__all__ = ["resolver_id", "artes", "buscar"]
