"""bib_nucleo — núcleo fatiado (base, banco, scans, emuladores, pacotes).

As integrações de rede/download ficam em `bib_nucleo.rede`. Para manter
consumidores antigos funcionando, os nomes históricos (`bib_nucleo.fontes`,
`from bib_nucleo import online`, `import bib_core` etc.) continuam
resolvíveis via import preguiçoso abaixo — sem custo de inicialização e sem
ciclos de importação. Código novo deve importar `bib_nucleo.rede.<módulo>`.
"""
from __future__ import annotations

import importlib

_REDE = {
    "fontes", "repacks", "torrents", "videos_youtube",
    "musica_online", "spotify", "online",
}

# Exporta config explicitamente para consumidores
from .config import cfg, get_config, reset_config  # noqa: F401


def __getattr__(nome: str):
    if nome in _REDE:
        modulo = importlib.import_module(f"bib_nucleo.rede.{nome}")
        globals()[nome] = modulo
        return modulo
    if nome in ("cfg", "get_config", "reset_config"):
        from .config import cfg as _cfg
        from .config import get_config as _gc
        from .config import reset_config as _rc
        globals()[nome] = _cfg if nome == "cfg" else (_gc if nome == "get_config" else _rc)
        return globals()[nome]
    raise AttributeError(f"bib_nucleo não tem atributo {nome!r}")


def __dir__():
    return sorted(list(globals()) + list(_REDE))
