#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caminhos canônicos, tradução Win<->Linux, dirs, texto e tempo."""
from __future__ import annotations

import datetime
import os
import re
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# Casa canônica + tradução determinística de caminhos (Win <-> Linux)
# --------------------------------------------------------------------------

WIN_ROOT = os.environ.get("BIBLIOTECA_WIN_ROOT", "D:\\")

LINUX_ROOT = os.environ.get("BIBLIOTECA_LINUX_ROOT", "/run/media/tuco/Games")

REL_HOME = Path("Tuco-Compartilhado") / "Jogos" / "biblioteca"



def resolve_home() -> Path:
    env = os.environ.get("BIBLIOTECA_HOME")
    if env:
        return Path(env)
    if os.name == "nt":
        cand = Path(WIN_ROOT) / REL_HOME
        if cand.is_dir():
            return cand
    else:
        cand = Path(LINUX_ROOT) / REL_HOME
        if cand.is_dir():
            return cand
    return BASE_DIR



HOME_DIR = resolve_home()

DEFAULT_DB = HOME_DIR / "biblioteca.db"

BACKUP_DIR = HOME_DIR / "backups"

CAPAS_DIR = HOME_DIR / "capas"

PRESETS_DIR = HOME_DIR / "presets"



def garantir_dirs() -> None:
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    CAPAS_DIR.mkdir(parents=True, exist_ok=True)
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)



def _com_barra(p: str) -> str:
    return p.replace("\\", "/")



def win_para_linux(p: str) -> str:
    """D:\\Games\\X -> /run/media/tuco/Games/Games/X. Fora de D:\\, devolve igual."""
    n = _com_barra(p)
    w = _com_barra(WIN_ROOT).rstrip("/") + "/"
    if n[: len(w)].lower() == w.lower():
        return LINUX_ROOT.rstrip("/") + "/" + n[len(w):]
    return p



def linux_para_win(p: str) -> str:
    n = _com_barra(p)
    lx = LINUX_ROOT.rstrip("/") + "/"
    if n[: len(lx)].lower() == lx.lower():
        resto = n[len(lx):].replace("/", "\\")
        return WIN_ROOT.rstrip("\\") + "\\" + resto
    return p



def traduzir_para_atual(p: str) -> str:
    """Converte um caminho gravado para o equivalente neste SO (ou igual)."""
    if not p:
        return p
    return linux_para_win(p) if os.name == "nt" else win_para_linux(p)



def existe_aqui_ou_traduzido(p: str) -> tuple[bool, str]:
    """(existe, caminho_que_existe_ou_traduzido). Para exibir e executar."""
    if not p:
        return False, ""
    if Path(p).exists():
        return True, p
    t = traduzir_para_atual(p)
    if t != p and Path(t).exists():
        return True, t
    return False, t



def resolver_exe(d: dict) -> tuple[str, str]:
    """(executável final neste SO, origem). exe_win/exe_linux vencem o legado."""
    if os.name == "nt":
        esp = (d.get("exe_win") or "").strip()
        if esp:
            return esp, "exe_win"
    else:
        esp = (d.get("exe_linux") or "").strip()
        if esp:
            return esp, "exe_linux"
    return traduzir_para_atual((d.get("executable_path") or "").strip()), "executavel"



def agora_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")



def log_erro(contexto: str, detalhe: str) -> None:
    """Anexa uma linha em erros.log (casa). Nunca levanta; diagnóstico local."""
    try:
        HOME_DIR.mkdir(parents=True, exist_ok=True)
        with open(HOME_DIR / "erros.log", "a", encoding="utf-8") as fh:
            fh.write(f"{agora_iso()} [{contexto}] {detalhe}\n")
    except OSError:
        pass



def _txt(v) -> str:
    """Texto limpo: sem NUL (quebra Path/SQLite) e sem espaços nas bordas."""
    if v is None:
        return ""
    return (v if isinstance(v, str) else str(v)).replace("\x00", "").strip()



def _desaspas(s: str) -> str:
    """Remove um par de aspas duplas coladas (colo de 'copiar como caminho')."""
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s



def slugify(s: str) -> str:
    n = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    n = re.sub(r"[^a-zA-Z0-9]+", "-", n.lower()).strip("-")
    return n or "capa"


# Extensões de ROM por provider (aqui p/ scans e emuladores usarem sem ciclo).
ROM_EXTS_3DS = {".cci", ".cxi", ".3ds", ".3dsx", ".elf", ".app", ".axf"}

__all__ = ['BASE_DIR', 'WIN_ROOT', 'LINUX_ROOT', 'REL_HOME', 'resolve_home', 'HOME_DIR', 'DEFAULT_DB', 'BACKUP_DIR', 'CAPAS_DIR', 'PRESETS_DIR', 'garantir_dirs', '_com_barra', 'win_para_linux', 'linux_para_win', 'traduzir_para_atual', 'existe_aqui_ou_traduzido', 'resolver_exe', 'agora_iso', 'log_erro', '_txt', '_desaspas', 'slugify',
 'ROM_EXTS_3DS']
