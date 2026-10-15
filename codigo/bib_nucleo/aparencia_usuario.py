"""Preferências de aparência do Hub (tema, densidade e escala de texto).

Fica fora de `bib_nucleo/rede/` porque é config local, não integração de rede.
Caminho: `dados/aparencia.json`. Sempre devolve um dict completo com defaults.
"""
from __future__ import annotations

from pathlib import Path

TEMAS = ("escuro", "claro")
DENSIDADES = ("compacto", "conforto", "bigpicture")
ESCALA_MIN, ESCALA_MAX, ESCALA_PADRAO = 0.8, 1.5, 1.0
_PADRAO = {"tema": "escuro", "densidade": "conforto", "escala_texto": ESCALA_PADRAO,
           "auto_backup": True, "modo_simples": False}
_ARQUIVO = "aparencia.json"


def _alvo() -> Path:
    from bib_nucleo import base
    return base.DADOS_DIR / _ARQUIVO


def _escala(valor, atual: float | None = None) -> float:
    """Escala válida: número finito em [0.8, 1.5]; inválido mantém o atual.

    Sem `atual`, usa o padrão (100%). NaN/inf e não-numéricos nunca entram.
    """
    padrao = ESCALA_PADRAO if atual is None else atual
    try:
        numero = round(float(valor), 3)
    except (TypeError, ValueError):
        return padrao
    if numero != numero or numero in (float("inf"), float("-inf")):  # NaN/inf
        return padrao
    return min(ESCALA_MAX, max(ESCALA_MIN, numero))


def _validar(dados: dict) -> dict:
    tema = str((dados or {}).get("tema") or "").strip().lower()
    densidade = str((dados or {}).get("densidade") or "").strip().lower()
    auto = (dados or {}).get("auto_backup")
    simples = (dados or {}).get("modo_simples")
    return {"tema": tema if tema in TEMAS else _PADRAO["tema"],
            "densidade": densidade if densidade in DENSIDADES else _PADRAO["densidade"],
            "escala_texto": _escala((dados or {}).get("escala_texto", ESCALA_PADRAO)),
            "auto_backup": auto if isinstance(auto, bool) else _PADRAO["auto_backup"],
            "modo_simples": simples if isinstance(simples, bool) else _PADRAO["modo_simples"]}


def ler_aparencia() -> dict:
    """Preferências vigentes (default: escuro/conforto/100%). Nunca levanta."""
    from bib_nucleo.rede import online
    try:
        cru = online.ler_json(_alvo(), _PADRAO)
    except Exception:
        return dict(_PADRAO)
    return _validar(cru if isinstance(cru, dict) else {})


def salvar_aparencia(tema: str = "", densidade: str = "", auto_backup=None,
                     modo_simples=None, escala_texto=None) -> dict:
    """Grava preferências. Campo vazio mantém o atual; fora da lista é ignorado."""
    from bib_nucleo.rede import online
    atual = ler_aparencia()
    tema = (tema or "").strip().lower()
    densidade = (densidade or "").strip().lower()
    escala = atual["escala_texto"] if escala_texto is None else _escala(escala_texto, atual["escala_texto"])
    novo = {"tema": tema if tema in TEMAS else atual["tema"],
            "densidade": densidade if densidade in DENSIDADES else atual["densidade"],
            "escala_texto": escala,
            "auto_backup": bool(auto_backup) if auto_backup is not None else atual["auto_backup"],
            "modo_simples": bool(modo_simples) if modo_simples is not None else atual["modo_simples"]}
    if novo != atual:
        online.gravar_json(_alvo(), novo, backup=True)
    return novo
