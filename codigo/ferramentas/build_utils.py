#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utilitários de build de preparar_release.py e preparar_runtime_python.py:
SHA-256 de arquivo e download verificado (cache, SHA e tamanho mínimo)."""
from __future__ import annotations

import hashlib
import shutil
import urllib.request
from pathlib import Path


# --------------------------------------------------------------------------
# SHA-256
# --------------------------------------------------------------------------
def sha_arquivo(p: Path) -> str:
    """Retorna SHA-256 hex do arquivo (lê em chunks de 256 KiB)."""
    h = hashlib.sha256()
    with p.open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 256), b""):
            h.update(bloco)
    return h.hexdigest()


# --------------------------------------------------------------------------
# download verificado com cache
# --------------------------------------------------------------------------
def baixar_verificado(
    url: str,
    nome: str,
    cache_dir: Path,
    *,
    sha256: str = "",
    minimo: int = 0,
    timeout: int = 120,
) -> Path:
    """
    Baixa `url` para `cache_dir/nome` com verificação de SHA-256 e tamanho mínimo.

    - Se arquivo já existe, tem tamanho >= minimo e SHA bate: usa cache.
    - Senão baixa em arquivo .part e troca atomicamente.
    - Levanta SystemExit em falha (mantém comportamento dos montar_*.py).
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    destino = cache_dir / nome
    if destino.is_file() and destino.stat().st_size >= minimo:
        if not sha256 or sha_arquivo(destino) == sha256:
            print(f"[cache] {nome} ({destino.stat().st_size // 1048576} MB)")
            return destino
        print(f"[cache] {nome} SHA divergente; rebaixando...")
        destino.unlink(missing_ok=True)

    print(f"[baixar] {nome}")
    tmp = destino.with_suffix(destino.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "TucoTeca-build"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r, tmp.open("wb") as f:
            shutil.copyfileobj(r, f, 1024 * 256)
    except Exception as e:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"falha ao baixar {nome}: {e}")

    if tmp.stat().st_size < minimo:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"{nome} veio pequeno demais (link quebrou?)")

    if sha256 and sha_arquivo(tmp) != sha256:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"{nome}: sha256 divergente (descartado)")

    tmp.replace(destino)
    print(f"[ok] {nome} ({destino.stat().st_size // 1048576} MB)")
    return destino
