"""bib_nucleo.rede — integrações de rede/download, isoladas do núcleo limpo.

Módulos que falam com a internet (catálogos, capas, yt-dlp, músicas online,
Spotify, torrentes, repacks) vivem aqui. O núcleo (`bib_nucleo`) não depende
deles; consumidores importam por `bib_nucleo.rede.<módulo>`.

Flag de recurso: `BIBLIOTECA_REDE=0` desliga a rede em massa (modo avião),
para conseguir usar o Hub sem nenhuma integração remota.
"""
from __future__ import annotations

import os

__all__ = ["rede_ativa", "exigir_rede"]

_MODULOS = ("fontes", "repacks", "torrents", "videos_youtube",
            "musica_online", "spotify", "online")


def rede_ativa() -> bool:
    """Rede liberada? (default sim; `BIBLIOTECA_REDE=0` desliga)."""
    return os.environ.get("BIBLIOTECA_REDE", "1").strip().lower() not in ("0", "false", "nao", "não", "off")


def exigir_rede(acao: str = "Esta ação") -> None:
    """Levanta ValueError claro quando a rede está desligada pela flag."""
    if not rede_ativa():
        raise ValueError(f"{acao} precisa de rede, mas BIBLIOTECA_REDE=0 "
                          "(modo avião). Ligue BIBLIOTECA_REDE=1 para usar.")


def abrir_rede(url, **opcoes):
    """Última barreira antes de HTTP; cobre também interfaces clássicas/scripts."""
    import urllib.request
    exigir_rede("Esta consulta/download")
    return urllib.request.urlopen(url, **opcoes)
