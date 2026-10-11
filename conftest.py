"""Pytest: espelha os caminhos e o isolamento do runner oficial da suíte.

O runner `codigo/ferramentas/testes/executar.py` é a fonte da verdade na CI:
além do isolamento de ambiente, ele roda cada caso em subprocesso próprio com
audit hook que bloqueia rede, escrita fora da sandbox e processos externos.
Aqui, para desenvolvimento rápido, replicamos apenas o isolamento de ambiente
(fixture autouse) — a proteção forte continua sendo o runner.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent
CODIGO = RAIZ / "codigo"
FRONTENDS = CODIGO / "frontends"
TESTES = CODIGO / "ferramentas" / "testes"
for _p in (str(CODIGO), str(FRONTENDS), str(TESTES)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


@pytest.fixture(autouse=True)
def _sandbox_local(tmp_path, monkeypatch):
    """Isolamento de ambiente por teste (espelha `executar.isolar`)."""
    raiz = tmp_path.resolve()
    for sub in ("dados", "emu/user", "roms", "appdata", "programdata", "home"):
        (raiz / sub).mkdir(parents=True, exist_ok=True)
    for chave in list(os.environ):
        if chave.startswith("BIBLIOTECA_") or chave == "HYDRA_DB_PATH":
            monkeypatch.delenv(chave, raising=False)
    monkeypatch.setenv("BIBLIOTECA_HOME", str(raiz / "dados"))
    monkeypatch.setenv("BIBLIOTECA_AZAHAR_DIR", str(raiz / "emu"))
    monkeypatch.setenv("BIBLIOTECA_WIN_ROOT", str(raiz / "win"))
    monkeypatch.setenv("BIBLIOTECA_LINUX_ROOT", str(raiz / "linux"))
    monkeypatch.setenv("BIBLIOTECA_MAC_ROOT", str(raiz / "mac"))
    monkeypatch.setenv("BIBLIOTECA_SCAN_ROOTS", str(raiz / "roms"))
    monkeypatch.setenv("BIBLIOTECA_ROMS_ROOTS", str(raiz / "roms"))
    monkeypatch.setenv("APPDATA", str(raiz / "appdata"))
    monkeypatch.setenv("LOCALAPPDATA", str(raiz / "appdata"))
    monkeypatch.setenv("ProgramData", str(raiz / "programdata"))
    monkeypatch.setenv("HOME", str(raiz / "home"))
    monkeypatch.setenv("USERPROFILE", str(raiz / "home"))
    anterior = tempfile.tempdir
    tempfile.tempdir = str(raiz)
    try:
        yield
    finally:
        tempfile.tempdir = anterior
