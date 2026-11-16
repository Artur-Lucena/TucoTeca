"""Legendas locais: SRT → WebVTT (o `<track>` do navegador só lê VTT)."""
from __future__ import annotations

import re
from pathlib import Path

LIMITE = 2 * 1024 * 1024
_TEMPO_SRT = re.compile(r"(\d{1,2}:\d{2}:\d{2}),(\d{3})")


def ler_texto(caminho: str) -> str:
    p = Path(caminho)
    if p.suffix.lower() not in (".srt", ".vtt"):
        raise ValueError("Legenda precisa ser .srt ou .vtt.")
    raw = p.read_bytes()[:LIMITE + 1]
    if len(raw) > LIMITE:
        raise ValueError("Legenda maior que 2 MB.")
    for cod in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(cod)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def srt_para_vtt(texto: str) -> str:
    """Converte SRT (vírgula nos milissegundos, índices numéricos) em WebVTT."""
    texto = texto.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")
    if texto.lstrip().startswith("WEBVTT"):
        return texto
    blocos = []
    for bloco in re.split(r"\n{2,}", texto.strip()):
        linhas = bloco.split("\n")
        if linhas and linhas[0].strip().isdigit():
            linhas = linhas[1:]
        if not linhas or "-->" not in linhas[0]:
            continue
        linhas[0] = _TEMPO_SRT.sub(r"\1.\2", linhas[0])
        blocos.append("\n".join(linhas))
    return "WEBVTT\n\n" + "\n\n".join(blocos) + "\n"


def legenda_vtt(caminho: str) -> str:
    return srt_para_vtt(ler_texto(caminho))


__all__ = ["ler_texto", "srt_para_vtt", "legenda_vtt"]
