#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Videoteca local da 2.0: importa vídeos p/ `dados/videos/` e abre nos players.

Espelho de `musicas.py` para vídeo: varre extensões de `VIDEO_EXTS`,
dedup por sha, `criar_video`/`listar_videos` no banco (v18). Sem rede,
stdlib só, darwin-safe. Download do YouTube mora em `videos_youtube.py`;
aqui só arquivo local + resolução + abertura.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
from pathlib import Path

from bib_nucleo.arquivos import destino_temporario


def sha_arquivo_video(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1024 * 256), b""):
            h.update(bloco)
    return h.hexdigest()


def varrer_videos(pasta: str | os.PathLike) -> list[dict]:
    """Lista vídeos importáveis com sha. Só leitura, nunca levanta."""
    from bib_nucleo.base import VIDEO_EXTS
    raiz = Path(pasta)
    try:
        arquivos = sorted(p for p in raiz.rglob("*")
                           if p.is_file() and not p.is_symlink()
                           and p.suffix.lower() in VIDEO_EXTS)
    except OSError:
        return []
    out = []
    for arq in arquivos:
        try:
            titulo = arq.stem.strip() or arq.name
            out.append({"path": str(arq), "titulo": titulo, "canal": "",
                        "sha": sha_arquivo_video(arq),
                        "mb": round(arq.stat().st_size / 1048576, 1)})
        except OSError:
            continue
    return out


def importar_videos(con: sqlite3.Connection,
                    pasta: str | os.PathLike) -> dict:
    """Copia p/ `dados/videos/` com dedup por sha. Falha vira `erros`."""
    from bib_nucleo import banco as B
    from bib_nucleo.base import VIDEOS_DIR, slugify
    novos = ignorados = 0
    erros: list[str] = []
    try:
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        vistos = {r.get("video_sha") for r in B.listar_videos(con)}
    except (OSError, sqlite3.Error) as e:
        return {"novos": 0, "ignorados": 0, "erros": [f"Videoteca indisponível: {e}"]}
    for item in varrer_videos(pasta):
        if not item["sha"] or item["sha"] in vistos:
            ignorados += 1
            continue
        src = Path(item["path"])
        base = slugify(item["titulo"]) or "video"
        dest = VIDEOS_DIR / f"{base}{src.suffix.lower()}"
        n = 1
        while dest.exists():
            n += 1
            dest = VIDEOS_DIR / f"{base}-{n}{src.suffix.lower()}"
        try:
            with destino_temporario(dest) as tmp:
                shutil.copy2(src, tmp)
                if sha_arquivo_video(tmp) != item["sha"]:
                    raise ValueError("arquivo de origem mudou durante a cópia")
        except (OSError, ValueError) as e:
            if len(erros) < 20:
                erros.append(f"'{item['titulo']}': {e}")
            ignorados += 1
            continue
        try:
            B.criar_video(con, {"titulo": item["titulo"], "canal": "",
                                "video_path": str(dest),
                                "video_sha": item["sha"], "origem": "local"})
        except (OSError, sqlite3.Error, ValueError) as e:
            try:
                dest.unlink()
            except OSError:
                pass
            if len(erros) < 20:
                erros.append(f"'{item['titulo']}': {e}")
            ignorados += 1
            continue
        vistos.add(item["sha"])
        novos += 1
    return {"novos": novos, "ignorados": ignorados, "erros": erros}


__all__ = ["sha_arquivo_video", "varrer_videos",
           "importar_videos"]
