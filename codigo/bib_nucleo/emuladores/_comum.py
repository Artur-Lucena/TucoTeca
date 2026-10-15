#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emuladores: resolução de executável compartilhada (qualquer emulador)."""
from __future__ import annotations

from pathlib import Path


def _app_macos(pasta: Path) -> str:
    """Binário dentro de *.app (macOS): bundle -> Contents/MacOS/<bin>.

    Ordem: nome exato do .app > prefixo do nome > maior arquivo (helpers
    tipo *-room nunca vencem um binário da família). Qualquer emulador
    (Azahar, DeSmuME) resolve pelo mesmo caminho.
    """
    try:
        if not pasta.is_dir():
            return ""
        for app in sorted(pasta.glob("*.app")):
            macos = app / "Contents" / "MacOS"
            if not macos.is_dir():
                continue
            bins = [b for b in macos.iterdir() if b.is_file()]
            if not bins:
                continue
            alvo = app.stem.lower()
            exatos = [b for b in bins if b.name.lower() == alvo]
            if exatos:
                return str(exatos[0])
            familia = [b for b in bins if b.name.lower().startswith(alvo)]
            cands = familia or bins
            try:
                return str(max(cands, key=lambda b: b.stat().st_size))
            except OSError:
                return str(cands[0])
        return ""
    except OSError:
        return ""


def _appimage_na_pasta(pasta: Path, prefixo: str) -> str:
    """Acha prefixo*.AppImage sem depender de caixa (ext4 é case-sensitive)."""
    try:
        if not pasta.is_dir():
            return ""
        alvos = [p for p in pasta.iterdir()
                 if p.is_file() and p.name.lower().startswith(prefixo.lower())
                 and p.name.lower().endswith(".appimage")]
        if not alvos:
            return ""
        return str(sorted(alvos, key=lambda p: p.name.lower())[-1])
    except OSError:
        return ""


__all__ = ["_app_macos", "_appimage_na_pasta"]
