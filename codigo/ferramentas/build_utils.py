#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitários de build compartilhados entre montar_*.py e preparar_release.py.

Centraliza:
- sha_arquivo (hash SHA-256 de arquivo, em chunks)
- escrever_tarxz (escritor .tar.xz PAX_FORMAT preset=6, validação opcional)
- baixar_verificado (download com cache, verificação de SHA e tamanho mínimo)

Mantém API existente dos módulos antigos; apenas delega para cá.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import tarfile
import urllib.request
from pathlib import Path
from typing import Callable, Optional


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
# escritor .tar.xz unificado
# --------------------------------------------------------------------------
def _iter_arq_para_tar(raiz: Path):
    """Itera arquivos recursivamente sob raiz (sem symlinks, sem recursão explícita)."""
    for p in sorted(raiz.rglob("*")):
        if p.is_file() and not p.is_symlink():
            yield p


def escrever_tarxz(
    raiz: Path,
    saida: Path,
    *,
    filtro: Optional[Callable[[Path], bool]] = None,
    strip_parente: int = 1,
    verificar: bool = True,
) -> Path:
    """
    Cria arquivo .tar.xz (LZMA2 preset=6, PAX_FORMAT) a partir de `raiz`.

    Args:
        raiz: diretório raiz cujos arquivos entram no tarball.
        saida: caminho do .tar.xz a criar (pai deve existir).
        filtro: callable(Path) -> bool para incluir/excluir arquivos.
        strip_parente: quantos níveis de pai remover do caminho interno
                       (1 = remove o nome do próprio diretório raiz).
        verificar: se True, reabre o tarball e valida integridade (testzip).

    Retorna:
        Path do arquivo criado.
    """
    saida.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(saida, "w:xz", preset=6, format=tarfile.PAX_FORMAT) as t:
        for p in _iter_arq_para_tar(raiz):
            if filtro and not filtro(p):
                continue
            # caminho relativo no tarball
            partes = p.relative_to(raiz).parts
            if len(partes) > strip_parente:
                interno = Path(*partes[strip_parente:])
            else:
                interno = Path(*partes)
            t.add(p, arcname=str(interno).replace(os.sep, "/"), recursive=False)

    if verificar:
        with tarfile.open(saida, "r:xz") as t:
            # tarfile não tem testzip; tenta ler todos os membros
            for membro in t.getmembers():
                if membro.isfile():
                    try:
                        t.extractfile(membro).read(1)
                    except Exception as e:
                        raise ValueError(f"tar.xz gerado está corrompido: {saida} ({e})")

    mb = saida.stat().st_size / 1048576
    print(f"[ok] {saida.name} — {mb:.1f} MB")
    return saida


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

    if destino.stat().st_size < minimo:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"{nome} veio pequeno demais (link quebrou?)")

    if sha256 and sha_arquivo(tmp) != sha256:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"{nome}: sha256 divergente (descartado)")

    tmp.replace(destino)
    print(f"[ok] {nome} ({destino.stat().st_size // 1048576} MB)")
    return destino


# --------------------------------------------------------------------------
# Main para testes rápidos
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import tempfile
    from pathlib import Path
    # smoke test rápido
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "a.txt").write_text("hello")
        (tmp / "sub").mkdir()
        (tmp / "sub" / "b.txt").write_text("world")
        saida = tmp.parent / "teste.tar.xz"
        escrever_tarxz(tmp, saida, verificar=True)
        print("smoke OK:", saida, sha_arquivo(saida)[:16])
