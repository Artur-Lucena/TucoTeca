"""Versão do TucoTeca e User-Agent das requisições de rede, num lugar só.

`codigo/VERSION` fica ao lado de bib_nucleo — no checkout e também dentro do
app instalado (`resources/tucoteca/codigo/VERSION`), sempre um nível acima deste
pacote. Só stdlib e sem importar o resto do núcleo (evita ciclos).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

REPOSITORIO = "https://github.com/Artur-Lucena/TucoTeca"


@lru_cache(maxsize=1)
def versao_app() -> str:
    """Versão SemVer de `codigo/VERSION`; '0.0.0' se o arquivo faltar ou vier vazio."""
    try:
        texto = (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"
    return texto or "0.0.0"


def user_agent(detalhe: str = "") -> str:
    """`TucoTeca/1.4.6 (+repo)`; `detalhe` entra entre parênteses quando informado."""
    extra = f"; {detalhe}" if detalhe else ""
    return f"TucoTeca/{versao_app()} (+{REPOSITORIO}{extra})"


__all__ = ["REPOSITORIO", "versao_app", "user_agent"]
