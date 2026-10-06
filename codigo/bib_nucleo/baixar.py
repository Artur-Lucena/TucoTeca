#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fila CSV → mp3 tal qual o Harmoni: lê Exportify e enfileira p/ baixar.

Fase A (sem rede): só parse + fila no banco (`downloads`, v14). O download
yt-dlp (Fase B) e o mp3/ffmpeg (Fase C) consomem esta fila depois.
"""
from __future__ import annotations

import csv
import os
from pathlib import Path

_COL_TRACK = "Track Name"
_COL_ALBUM = "Album Name"
_COL_ARTIST = "Artist Name(s)"
_COL_URI = "Track URI"


def primeiro_artista(campo: str) -> str:
    """`A;B;C` (Exportify) → `A` (o 1º, como a busca do Harmoni usa)."""
    return (campo or "").split(";")[0].strip()


def ler_csv_exportify(caminho: str | os.PathLike) -> dict:
    """{'itens': [{titulo, artista, album, uri}], 'ignorados': n, 'erros': []}.

    Só leitura, nunca levanta por arquivo estranho (vira `erros`).
    """
    p = Path(caminho)
    try:
        fh = p.open("r", encoding="utf-8-sig", newline="")
    except OSError as e:
        return {"itens": [], "ignorados": 0, "erros": [f"não abri: {e}"]}
    itens: list[dict] = []
    ignorados = 0
    erros: list[str] = []
    num = 1
    try:
        try:
            leitor = csv.DictReader(fh)
        except (csv.Error, UnicodeDecodeError) as e:
            return {"itens": [], "ignorados": 0, "erros": [f"csv inválido: {e}"]}
        if not leitor.fieldnames or _COL_TRACK not in leitor.fieldnames:
            return {"itens": [], "ignorados": 0,
                    "erros": ["não é um CSV Exportify (sem 'Track Name')"]}
        for num, lin in enumerate(leitor, start=2):
            tit = ((lin.get(_COL_TRACK) if isinstance(lin, dict) else "") or "")
            tit = tit.strip()
            if not tit:
                ignorados += 1
                continue
            art = lin.get(_COL_ARTIST) if isinstance(lin, dict) else ""
            alb = lin.get(_COL_ALBUM) if isinstance(lin, dict) else ""
            uri = lin.get(_COL_URI) if isinstance(lin, dict) else ""
            itens.append({"titulo": tit,
                          "artista": primeiro_artista(art or ""),
                          "album": (alb or "").strip(),
                          "uri": (uri or "").strip()})
    except (csv.Error, UnicodeDecodeError) as e:
        if len(erros) < 20:
            erros.append(f"linha {num}: {e}")
    finally:
        try:
            fh.close()
        except OSError:
            pass
    return {"itens": itens, "ignorados": ignorados, "erros": erros}


__all__ = ['primeiro_artista', 'ler_csv_exportify']
