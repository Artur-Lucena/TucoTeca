"""Histórico de notificações do app (dados/notificacoes.json): sobrevive a fechar e abrir.

Cada aviso é {id, texto, tom, em}; o id deduplica (o mesmo aviso sobe para o
topo com a hora nova). Guarda os 200 mais recentes.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from bib_nucleo.arquivos import gravar_atomico

LIMITE = 200
TONS = ("info", "atencao")


def _arquivo() -> Path:
    from bib_nucleo.base import DADOS_DIR
    return DADOS_DIR / "notificacoes.json"


def _ler() -> list[dict]:
    try:
        dados = json.loads(_arquivo().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    itens = dados.get("avisos") if isinstance(dados, dict) else None
    return [a for a in (itens or []) if isinstance(a, dict) and a.get("id") and a.get("texto")]


def _gravar(itens: list[dict]) -> None:
    arq = _arquivo()
    arq.parent.mkdir(parents=True, exist_ok=True)
    gravar_atomico(arq, json.dumps({"avisos": itens[:LIMITE]}, ensure_ascii=False, indent=1).encode("utf-8"))


def _normalizar(aviso: dict) -> dict:
    texto = " ".join(str(aviso.get("texto") or "").split())[:500]
    if not texto:
        raise ValueError("aviso sem texto")
    ident = str(aviso.get("id") or texto)[:200]
    tom = aviso.get("tom") if aviso.get("tom") in TONS else "info"
    em = str(aviso.get("em") or datetime.now().astimezone().isoformat(timespec="seconds"))
    return {"id": ident, "texto": texto, "tom": tom, "em": em}


def listar() -> list[dict]:
    """Mais recentes primeiro."""
    return _ler()


def registrar(avisos: list[dict]) -> list[dict]:
    """Junta avisos novos ao histórico (os novos ficam no topo); devolve o histórico."""
    novos = [_normalizar(a) for a in avisos if isinstance(a, dict)]
    ids = {a["id"] for a in novos}
    itens = novos + [a for a in _ler() if a["id"] not in ids]
    _gravar(itens)
    return itens[:LIMITE]


def dispensar(ident: str) -> list[dict]:
    itens = [a for a in _ler() if a["id"] != ident]
    _gravar(itens)
    return itens


def limpar() -> list[dict]:
    _gravar([])
    return []


__all__ = ["LIMITE", "listar", "registrar", "dispensar", "limpar"]
