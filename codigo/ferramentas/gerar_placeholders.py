#!/usr/bin/env python3
"""Gera placeholders neutros para `midia/fontes-capas/`.

O repo não versiona arte de capas comerciais (risco de DMCA). Este script
cria PNGs placeholder (gradiente derivado do nome) para referência visual,
sem nenhuma dependência externa — somente biblioteca padrão.

Uso:
    py -3.14 codigo/ferramentas/gerar_placeholders.py [--x N] [--y N]
"""
from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path

PASTA = Path(__file__).resolve().parents[2] / "midia" / "fontes-capas"

NOMES = [
    "alpha-sapphire", "hades-ii", "megabonk-banner", "megabonk-box",
    "mewgenics", "omega-ruby", "pokemon-x", "pokemon-y",
    "ultra-moon", "ultra-sun",
]


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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--x", type=int, default=600)
    ap.add_argument("--y", type=int, default=800)
    ap.add_argument("--pasta", default=str(PASTA))
    args = ap.parse_args(argv)
    pasta = Path(args.pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    gerados = []
    for nome in NOMES:
        _png(pasta / f"{nome}.png", args.x, args.y, nome)
        gerados.append(f"{nome}.png")
    leiame = pasta / "LEIA-ME.md"
    leiame.write_text(
        "# Placeholders de referência\n\n"
        "Arte comercial **não** é versionada neste repositório (risco de DMCA).\n"
        "Estes PNGs são placeholders neutros gerados por\n"
        "`codigo/ferramentas/gerar_placeholders.py` (somente biblioteca padrão).\n"
        "O runtime do Hub não consome esta pasta.\n",
        encoding="utf-8")
    print(f"[ok] {len(gerados)} placeholder(s) em {pasta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
