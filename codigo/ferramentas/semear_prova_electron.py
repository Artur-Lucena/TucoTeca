#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Semeia uma coleção SINTÉTICA para as provas do desktop Electron.

Nada aqui toca a coleção real: o script exige um --destino de prova e recusa
a raiz do repositório (ou acima dela). Uso:

    py -3.14 -B codigo/ferramentas/semear_prova_electron.py --destino .provas/electron/home-f0

Depois, rode o selftest do Electron com BIBLIOTECA_HOME apontando para lá.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import struct
import sys
import wave
import zlib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

JOGOS = [
    ("Hollow Knight", 42.5, "2026-10-15 20:10:00"),
    ("Celeste", 11.25, "2026-10-17 21:40:00"),
    ("Stardew Valley", 87.0, None),
]
MUSICAS = [
    ("Weightless", "Marconi Union", "Weightless", 440.0),
    ("Sunset Lover", "Petit Biscuit", "Presence", 523.25),
]
DESEJOS = [("428: Shibuya Scramble", 310360), ("Hollow Knight: Silksong", 1030300)]
# Jogo de prova: um processo inofensivo que "joga" por ~35 s (ping local em
# loopback, sem jogo, sem rede externa). Passa do limiar de sessão rastreada
# (LIMIAR_SESSAO_S = 30 do núcleo) para as horas contarem de verdade.
JOGO_DE_PROVA = "Stardew Valley"
LAUNCH_PROVA = "-n 36 127.0.0.1"


def _executavel_de_prova() -> str:
    """Binário do sistema usado como 'jogo' sintético (só no Windows)."""
    if os.name != "nt":
        return ""
    return str(Path(os.environ.get("SystemRoot", r"C:\Windows"))
               / "System32" / "ping.exe")


def _wav(caminho: Path, freq: float, segundos: float = 2.0, taxa: int = 8000) -> str:
    """Grava um WAV sintético (seno) dentro da coleção de prova; devolve o sha256."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        quadros = bytearray()
        for n in range(int(segundos * taxa)):
            quadros += struct.pack("<h", int(12000 * math.sin(2 * math.pi * freq * n / taxa)))
        w.writeframes(bytes(quadros))
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


# capa sintética: degradê estável derivado do título (só stdlib)
def _cor(nome: str, deslocamento: int = 0) -> tuple[int, int, int]:
    h = 0
    for ch in nome:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    r = (h >> (deslocamento * 8)) & 0xFF
    g = (h >> ((deslocamento + 2) * 8)) & 0xFF
    b = (h >> ((deslocamento + 4) * 8)) & 0xFF
    # mantém médio-escuro e saturação discreta para uso como fundo
    return (64 + r % 128, 64 + g % 96, 96 + b % 128)


def _png(caminho: Path, largura: int, altura: int, nome: str) -> None:
    c1, c2 = _cor(nome, 0), _cor(nome, 3)
    linhas = []
    for y in range(altura):
        linha = bytearray()
        linha.append(0)  # filtro None
        for x in range(largura):
            t = (x / max(1, largura - 1) + y / max(1, altura - 1)) / 2
            linha.append(int(c1[0] + (c2[0] - c1[0]) * t))
            linha.append(int(c1[1] + (c2[1] - c1[1]) * t))
            linha.append(int(c1[2] + (c2[2] - c1[2]) * t))
        linhas.append(bytes(linha))
    raw = b"".join(linhas)

    def bloco(tipo: bytes, dados: bytes) -> bytes:
        return (struct.pack(">I", len(dados)) + tipo + dados
                + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", largura, altura, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", ihdr)
           + bloco(b"IDAT", zlib.compress(raw, 9))
           + bloco(b"IEND", b""))
    caminho.write_bytes(png)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Semeia coleção sintética p/ provas do Electron")
    ap.add_argument("--destino", required=True, help="pasta de prova (fora da coleção real)")
    ap.add_argument("--limpar", action="store_true", help="apaga o destino antes de semear")
    args = ap.parse_args(argv)

    destino = Path(args.destino).resolve()
    if destino == RAIZ or destino in RAIZ.parents:
        raise SystemExit("destino de prova não pode ser a raiz do repositório nem acima dela")
    if args.limpar and destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True, exist_ok=True)

    os.environ["BIBLIOTECA_HOME"] = str(destino)
    for caminho in (str(RAIZ / "codigo"), str(Path(__file__).resolve().parent)):
        if caminho not in sys.path:
            sys.path.insert(0, caminho)

    from bib_nucleo import banco, base

    base.garantir_dirs()
    con = banco.get_db(base.DEFAULT_DB)
    try:
        for titulo, horas, ultima in JOGOS:
            probe = titulo == JOGO_DE_PROVA and _executavel_de_prova()
            jogo = banco.criar_jogo(con, {
                "titulo": titulo,
                "executable_path": _executavel_de_prova() if probe else "",
                "launch_options": LAUNCH_PROVA if probe else ""})
            if horas:
                banco.adicionar_horas(con, jogo["id"], horas)
            nome_capa = f"semente-{jogo['id']}.png"
            _png(base.CAPAS_DIR / nome_capa, 300, 400, titulo)
            con.execute("UPDATE jogos SET capa=? WHERE id=?", (nome_capa, jogo["id"]))
            if ultima:
                con.execute("UPDATE jogos SET ultima_execucao=? WHERE id=?",
                            (ultima, jogo["id"]))
        con.commit()
        for indice, (titulo, artista, album, freq) in enumerate(MUSICAS, start=1):
            wav = base.MUSICAS_DIR / f"semente-p1-{indice:04d}.wav"
            sha = _wav(wav, freq)
            banco.criar_musica(con, {"titulo": titulo, "artista": artista, "album": album,
                                    "musica_path": str(wav), "musica_sha": sha})
        for titulo, appid in DESEJOS:
            banco.adicionar_desejo(con, appid, titulo)
    finally:
        con.close()

    print(json.dumps({"home": str(destino), "jogos": len(JOGOS),
                      "musicas": len(MUSICAS), "desejos": len(DESEJOS)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
