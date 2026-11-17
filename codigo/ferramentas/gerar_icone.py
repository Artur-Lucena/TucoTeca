#!/usr/bin/env python3
"""Gera o ícone do app (resources/icon.ico) só com a stdlib.

Desenho: quadrado arredondado com degradê roxo→azul e um "T" claro.
O ICO embute PNGs (16, 24, 32, 48, 64, 128, 256), formato aceito pelo
Windows Vista+ e pelo electron-builder. Reproduzível: mesma saída a cada
execução, então o binário versionado pode ser conferido regerando.

    py -3.14 -B codigo/ferramentas/gerar_icone.py
"""
from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DESTINO = REPO / "codigo/frontends/electron/resources"
TAMANHOS = (16, 24, 32, 48, 64, 128, 256)
TOPO = (124, 58, 237)    # roxo
BASE = (37, 99, 235)     # azul
LETRA = (248, 250, 252)


def _dentro_arredondado(x: float, y: float, raio: float) -> bool:
    """Quadrado unitário [0,1]² com cantos de raio `raio`."""
    cx = min(max(x, raio), 1 - raio)
    cy = min(max(y, raio), 1 - raio)
    return (x - cx) ** 2 + (y - cy) ** 2 <= raio ** 2


def _dentro_t(x: float, y: float) -> bool:
    barra = 0.22 <= x <= 0.78 and 0.22 <= y <= 0.36
    haste = 0.425 <= x <= 0.575 and 0.22 <= y <= 0.80
    return barra or haste


def _pixel(x: float, y: float) -> tuple[int, int, int, int]:
    if not _dentro_arredondado(x, y, 0.22):
        return (0, 0, 0, 0)
    if _dentro_t(x, y):
        return (*LETRA, 255)
    t = (x + y) / 2
    r, g, b = (round(de + (para - de) * t) for de, para in zip(TOPO, BASE))
    return (r, g, b, 255)


def renderizar(lado: int, amostras: int = 4) -> bytes:
    """RGBA linha a linha, com supersampling para bordas suaves."""
    linhas = bytearray()
    n = amostras * amostras
    for py in range(lado):
        linhas.append(0)  # filtro PNG "None"
        for px in range(lado):
            soma = [0, 0, 0, 0]
            for sy in range(amostras):
                for sx in range(amostras):
                    r, g, b, a = _pixel((px + (sx + 0.5) / amostras) / lado,
                                        (py + (sy + 0.5) / amostras) / lado)
                    soma[0] += r * a
                    soma[1] += g * a
                    soma[2] += b * a
                    soma[3] += a
            alfa = soma[3]
            if alfa == 0:
                linhas += b"\0\0\0\0"
            else:
                linhas += bytes((round(soma[0] / alfa), round(soma[1] / alfa),
                                 round(soma[2] / alfa), round(alfa / n)))
    return bytes(linhas)


def png(lado: int) -> bytes:
    def bloco(tipo: bytes, dados: bytes) -> bytes:
        return (struct.pack(">I", len(dados)) + tipo + dados
                + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF))
    cabecalho = struct.pack(">IIBBBBB", lado, lado, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", cabecalho)
            + bloco(b"IDAT", zlib.compress(renderizar(lado), 9)) + bloco(b"IEND", b""))


def ico(imagens: dict[int, bytes]) -> bytes:
    cabecalho = struct.pack("<HHH", 0, 1, len(imagens))
    deslocamento = 6 + 16 * len(imagens)
    diretorio, corpo = b"", b""
    for lado, dados in sorted(imagens.items()):
        dim = 0 if lado >= 256 else lado
        diretorio += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(dados), deslocamento)
        corpo += dados
        deslocamento += len(dados)
    return cabecalho + diretorio + corpo


def gerar(destino: Path = DESTINO) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    imagens = {lado: png(lado) for lado in TAMANHOS}
    saida = destino / "icon.ico"
    saida.write_bytes(ico(imagens))
    return [saida]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--destino", type=Path, default=DESTINO)
    args = ap.parse_args(argv)
    for caminho in gerar(args.destino):
        print(f"[ok] {caminho} ({caminho.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
