"""Preferências de aparência do Hub (tema e densidade), persistidas na coleção.

Fica fora de `bib_nucleo/rede/` porque é config local, não integração de rede.
Caminho: `dados/aparencia.json`. Sempre devolve um dict completo com defaults.
"""
from __future__ import annotations

import os
from pathlib import Path

TEMAS = ("escuro", "claro")
DENSIDADES = ("compacto", "conforto", "bigpicture")
_PADRAO = {"tema": "escuro", "densidade": "conforto", "auto_backup": True, "modo_simples": False}
_ARQUIVO = "aparencia.json"


def _alvo() -> Path:
    from bib_nucleo import base
    return base.DADOS_DIR / _ARQUIVO


def _validar(dados: dict) -> dict:
    tema = str((dados or {}).get("tema") or "").strip().lower()
    densidade = str((dados or {}).get("densidade") or "").strip().lower()
    auto = (dados or {}).get("auto_backup")
    simples = (dados or {}).get("modo_simples")
    return {"tema": tema if tema in TEMAS else _PADRAO["tema"],
            "densidade": densidade if densidade in DENSIDADES else _PADRAO["densidade"],
            "auto_backup": auto if isinstance(auto, bool) else _PADRAO["auto_backup"],
            "modo_simples": simples if isinstance(simples, bool) else _PADRAO["modo_simples"]}


def ler_aparencia() -> dict:
    """Preferências vigentes (default: escuro/conforto). Nunca levanta."""
    from bib_nucleo.rede import online
    try:
        cru = online.ler_json(_alvo(), _PADRAO)
    except Exception:
        return dict(_PADRAO)
    return _validar(cru if isinstance(cru, dict) else {})


def salvar_aparencia(tema: str = "", densidade: str = "", auto_backup=None, modo_simples=None) -> dict:
    """Grava preferências. Campo vazio mantém o atual; valor fora da lista é ignorado."""
    from bib_nucleo.rede import online
    atual = ler_aparencia()
    tema = (tema or "").strip().lower()
    densidade = (densidade or "").strip().lower()
    novo = {"tema": tema if tema in TEMAS else atual["tema"],
            "densidade": densidade if densidade in DENSIDADES else atual["densidade"],
            "auto_backup": bool(auto_backup) if auto_backup is not None else atual["auto_backup"],
            "modo_simples": bool(modo_simples) if modo_simples is not None else atual["modo_simples"]}
    if novo != atual:
        online.gravar_json(_alvo(), novo, backup=True)
    return novo
