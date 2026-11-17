"""Versão do TucoTeca e User-Agent das requisições de rede, num lugar só.

`VERSION` fica na raiz do projeto — no checkout e também dentro do app
instalado (`resources/tucoteca/VERSION`), sempre dois níveis acima deste
pacote. Só stdlib e sem importar o resto do núcleo (evita ciclos).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

REPOSITORIO = "https://github.com/Artur-Lucena/TucoTeca"


@lru_cache(maxsize=1)
def versao_app() -> str:
    """Versão SemVer de `VERSION`; '0.0.0' se o arquivo faltar ou vier vazio."""
    try:
        texto = (Path(__file__).resolve().parents[2] / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"
    return texto or "0.0.0"


def user_agent(detalhe: str = "") -> str:
    """`TucoTeca/1.4.5 (+repo)`; `detalhe` entra entre parênteses quando informado."""
    extra = f"; {detalhe}" if detalhe else ""
    return f"TucoTeca/{versao_app()} (+{REPOSITORIO}{extra})"


__all__ = ["REPOSITORIO", "versao_app", "user_agent"]
