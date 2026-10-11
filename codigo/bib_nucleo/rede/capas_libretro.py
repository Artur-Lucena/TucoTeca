"""Capas offline via LibRetro Thumbnails (thumbnails.libretro.com) — sob ação do usuário.

Catálogo público (nomes No-Intro), sem chave. Hoje cobre 3DS e NDS.
Regra do repositório: caracteres `&*/:`<>?|"\\` no nome viram `_`. Se o título local
não bater com o nome No-Intro, a capa não é achada e o usuário recebe um aviso claro.
"""
from __future__ import annotations

import urllib.parse

from bib_nucleo.rede import exigir_rede, online

BASE = "https://thumbnails.libretro.com"
SISTEMAS = {"3DS": "Nintendo - Nintendo 3DS", "NDS": "Nintendo - Nintendo DS"}
_PROIBIDOS = str.maketrans({c: "_" for c in '&*/:`<>?|"\\'})


def sistema_de(plataforma: str) -> str:
    chave = (plataforma or "").strip().upper()
    if chave not in SISTEMAS:
        raise ValueError(f"Sem catálogo LibRetro para {plataforma or 'esta plataforma'} "
                         "(disponível para 3DS e NDS).")
    return SISTEMAS[chave]


def nome_arquivo(titulo: str) -> str:
    return (titulo or "").strip().translate(_PROIBIDOS)


def url_boxart(plataforma: str, titulo: str) -> str:
    sistema = sistema_de(plataforma)
    nome = nome_arquivo(titulo)
    if not nome:
        raise ValueError("Título vazio: não há como procurar a capa.")
    return (f"{BASE}/{urllib.parse.quote(sistema)}/Named_Boxarts/"
            f"{urllib.parse.quote(nome)}.png")


def buscar_capa_libretro(plataforma: str, titulo: str, timeout: int = 15) -> dict:
    """{'raw', 'ext', 'url'} da capa. Levanta ValueError (rede, plataforma, título, imagem)."""
    url = url_boxart(plataforma, titulo)
    try:
        raw, ext, _cache = online.baixar_imagem(url, timeout)
    except ValueError as e:
        raise ValueError(f"Capa não encontrada no LibRetro para '{titulo}'. "
                         f"O nome precisa bater com o No-Intro ({e})") from None
    return {"raw": raw, "ext": ext, "url": url}
