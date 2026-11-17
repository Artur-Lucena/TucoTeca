"""Cinemeta (catálogo público do Stremio, sem chave): filmes e séries por id IMDb.

Só metadados: catálogo, busca e `meta` (com temporadas/episódios em
`videos`). Nada de streams, torrents ou addons. Textos em inglês.
"""
from __future__ import annotations

import urllib.parse

from bib_nucleo.rede import online
from bib_nucleo.rede.provedores._apoio import obter, respeitar_ritmo

BASE = "https://v3-cinemeta.strem.io"
TIPOS = ("movie", "series")
GENEROS = ("Action", "Adventure", "Animation", "Biography", "Comedy", "Crime", "Documentary", "Drama",
           "Family", "Fantasy", "History", "Horror", "Mystery", "Romance", "Sci-Fi", "Sport", "Thriller",
           "War", "Western")


def _get(caminho: str) -> dict:
    respeitar_ritmo("v3-cinemeta.strem.io", 0.2)
    return online.requisitar_json(BASE + caminho, timeout=12)


def _tipo(tipo: str) -> str:
    if tipo not in TIPOS:
        raise ValueError("tipo deve ser movie ou series")
    return tipo


def _extras(**extras) -> str:
    partes = [f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in extras.items() if v not in (None, "", 0)]
    return ("/" + "&".join(partes)) if partes else ""


def catalogo(tipo: str, genero: str = "", pular: int = 0) -> list[dict]:
    """Populares (cache 12 h). `genero` de GENEROS; `pular` em múltiplos de 100."""
    _tipo(tipo)
    if genero and genero not in GENEROS:
        raise ValueError("Gênero desconhecido.")
    caminho = f"/catalog/{tipo}/top{_extras(genre=genero, skip=int(pular))}.json"
    dados = obter("cinemeta-catalogo", caminho, 12 * 3600, lambda: _get(caminho))
    return [m for m in (dados.get("metas") or []) if isinstance(m, dict) and str(m.get("id", "")).startswith("tt")]


def buscar(tipo: str, termo: str) -> list[dict]:
    _tipo(tipo)
    termo = " ".join(str(termo or "").split())
    if len(termo) < 2:
        raise ValueError("Digite pelo menos dois caracteres.")
    caminho = f"/catalog/{tipo}/top{_extras(search=termo)}.json"
    dados = obter("cinemeta-busca", caminho.casefold(), 7 * 86400, lambda: _get(caminho))
    return [m for m in (dados.get("metas") or []) if isinstance(m, dict) and str(m.get("id", "")).startswith("tt")]


def meta(tipo: str, imdb: str, validade_s: float | None = None) -> dict:
    """Ficha completa; séries trazem `videos` (episódios). Cache 12 h (série) / 30 dias (filme)."""
    _tipo(tipo)
    imdb = str(imdb or "")
    if not imdb.startswith("tt") or not imdb[2:].isdigit():
        raise ValueError("id IMDb inválido.")
    validade = validade_s if validade_s is not None else (12 * 3600 if tipo == "series" else 30 * 86400)
    caminho = f"/meta/{tipo}/{imdb}.json"
    dados = obter("cinemeta-meta", caminho, validade, lambda: _get(caminho))
    m = dados.get("meta") if isinstance(dados, dict) else None
    if not isinstance(m, dict) or not m.get("id"):
        raise ValueError("O Cinemeta não conhece este título.")
    return m


def resumo(m: dict) -> dict:
    """Cartão para listas (Descobrir, busca)."""
    return {"imdb_id": str(m.get("imdb_id") or m.get("id")), "tipo": "series" if m.get("type") == "series" else "movie",
            "nome": str(m.get("name") or ""), "ano": str(m.get("releaseInfo") or m.get("year") or ""),
            "poster": str(m.get("poster") or "") if online.url_https(str(m.get("poster") or "")) else "",
            "nota": str(m.get("imdbRating") or "")}


__all__ = ["BASE", "TIPOS", "GENEROS", "catalogo", "buscar", "meta", "resumo"]
