#!/usr/bin/env python3
"""Gera os ícones do app (resources/icon.ico e icon.icns) só com a stdlib.

Desenho: quadrado arredondado com degradê roxo→azul e um "T" claro.
O ICO embute PNGs (16, 24, 32, 48, 64, 128, 256), formato aceito pelo
Windows Vista+ e pelo electron-builder. O ICNS (macOS) embute PNGs de 32 a
1024 com a margem da grade de ícones do macOS (o desenho ocupa ~80%).
Reproduzível: mesma saída a cada execução, então os binários versionados
podem ser conferidos regerando.

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
# tipo ICNS → lado do PNG (ic11..ic14 são as versões @2x de 16..256)
ICNS_TIPOS = (("ic11", 32), ("ic12", 64), ("ic07", 128), ("ic08", 256),
              ("ic13", 256), ("ic09", 512), ("ic14", 512), ("ic10", 1024))
MARGEM_MAC = 100 / 1024  # grade do macOS: 824 px de desenho num ícone de 1024
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


def _pixel_mac(x: float, y: float) -> tuple[int, int, int, int]:
    escala = 1 - 2 * MARGEM_MAC
    return _pixel((x - MARGEM_MAC) / escala, (y - MARGEM_MAC) / escala)


def renderizar(lado: int, amostras: int = 4, pixel=_pixel) -> bytes:
    """RGBA linha a linha, com supersampling para bordas suaves."""
    linhas = bytearray()
    n = amostras * amostras
    for py in range(lado):
        linhas.append(0)  # filtro PNG "None"
        for px in range(lado):
            soma = [0, 0, 0, 0]
            for sy in range(amostras):
                for sx in range(amostras):
                    r, g, b, a = pixel((px + (sx + 0.5) / amostras) / lado,
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


def png(lado: int, pixel=_pixel) -> bytes:
    def bloco(tipo: bytes, dados: bytes) -> bytes:
        return (struct.pack(">I", len(dados)) + tipo + dados
                + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF))
    cabecalho = struct.pack(">IIBBBBB", lado, lado, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", cabecalho)
            + bloco(b"IDAT", zlib.compress(renderizar(lado, 2 if lado >= 512 else 4, pixel), 9))
            + bloco(b"IEND", b""))


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


def icns(imagens: dict[int, bytes]) -> bytes:
    corpo = b"".join(tipo.encode("ascii") + struct.pack(">I", 8 + len(imagens[lado])) + imagens[lado]
                     for tipo, lado in ICNS_TIPOS)
    return b"icns" + struct.pack(">I", 8 + len(corpo)) + corpo


def gerar(destino: Path = DESTINO, mac: bool = True) -> list[Path]:
    """Escreve icon.ico e, com `mac`, icon.icns (o 1024 px leva segundos em Python puro)."""
    destino.mkdir(parents=True, exist_ok=True)
    saida = destino / "icon.ico"
    saida.write_bytes(ico({lado: png(lado) for lado in TAMANHOS}))
    if not mac:
        return [saida]
    icns_ = destino / "icon.icns"
    icns_.write_bytes(icns({lado: png(lado, _pixel_mac) for lado in {lado for _, lado in ICNS_TIPOS}}))
    return [saida, icns_]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--destino", type=Path, default=DESTINO)
    args = ap.parse_args(argv)
    for caminho in gerar(args.destino):
        print(f"[ok] {caminho} ({caminho.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
