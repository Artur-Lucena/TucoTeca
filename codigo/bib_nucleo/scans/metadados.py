#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scans: metadados internos de ROMs (3DS SMDH, NDS banner) + PNG."""
from __future__ import annotations

import re
import struct
import zlib
from pathlib import Path

# --------------------------------------------------------------------------
# Metadados internos de ROMs 3DS (NCSD/CCI, NCCH/CXI, 3DSX + SMDH)
# --------------------------------------------------------------------------

SMDH_IDIOMAS = ("Japonês", "Inglês", "Francês", "Alemão", "Italiano", "Espanhol",
                "Chinês Simplificado", "Coreano", "Holandês", "Português",
                "Russo", "Chinês Tradicional")

SMDH_REGIOES = ("Japão", "América do Norte", "Europa", "Austrália", "China",
                "Coreia", "Taiwan")


def _u32(buf: bytes, off: int) -> int:
    return int.from_bytes(buf[off:off + 4], "little")


def _parse_smdh(smdh: bytes) -> dict:
    if len(smdh) < 0x201C or smdh[:4] != b"SMDH":
        return {}
    nomes: list[str] = []
    for i in range(12):
        # Campo UTF-16LE de tamanho fixo: decodifica TUDO e corta no 1º NUL.
        # (Separar os BYTES por b"\x00\x00" quebra no meio do último char.)
        raw = smdh[0x8 + i * 0x200:0x8 + i * 0x200 + 0x80]
        try:
            nomes.append(raw.decode("utf-16-le").split("\x00")[0].strip())
        except Exception:
            nomes.append("")
    titulo, idioma = "", ""
    for i in (1, 0):
        if nomes[i]:
            titulo, idioma = nomes[i], SMDH_IDIOMAS[i]
            break
    if not titulo:
        for i, t in enumerate(nomes):
            if t:
                titulo, idioma = t, SMDH_IDIOMAS[i]
                break
    regs = [SMDH_REGIOES[b] for b in range(7) if _u32(smdh, 0x2018) & (1 << b)]
    out: dict = {}
    if titulo:
        out["titulo"] = titulo
        out["idioma_titulo"] = idioma
    if regs:
        out["regiao"] = "Livre" if len(regs) == 7 else ", ".join(regs)
    return out


def _ler_icon_bin(caminho: str) -> bytes:
    """Extrai o icon.bin (SMDH) bruto da ROM, ou b"" se não der."""
    p = Path(caminho)
    if not p.is_file():
        return b""
    with p.open("rb") as f:
        head = f.read(0x400)
        if len(head) < 0x204:
            return b""
        if head[:4] == b"3DSX":  # homebrew: SMDH ao final do cabeçalho
            if len(head) < 0x28:
                return b""
            off, size = _u32(head, 0x20), _u32(head, 0x24)
            if not off or not size or off > 64 * 1024 * 1024:
                return b""
            f.seek(off)
            return f.read(min(size, 0x4000))
        if head[0x100:0x104] == b"NCSD":  # .cci/.3ds
            if len(head) < 0x128:
                return b""
            base = _u32(head, 0x120) * 0x200
        elif head[0x100:0x104] == b"NCCH":  # .cxi
            base = 0
        else:
            return b""
        f.seek(base)
        ncch = f.read(0x300)
        if len(ncch) < 0x300 or ncch[0x100:0x104] != b"NCCH":
            return b""
        ex_off = base + _u32(ncch, 0x1A0) * 0x200
        if ex_off > 16 * 1024 ** 3:
            return b""
        f.seek(ex_off)
        exeh = f.read(0x200)
        if len(exeh) < 0x200:
            return b""
        for i in range(10):
            e = exeh[i * 16:(i + 1) * 16]
            if e[:8].rstrip(b"\x00") in (b"icon", b"icon.bin"):
                fo, fs = _u32(e, 8), _u32(e, 12)
                if not fs or fs > 0x4000:
                    return b""
                f.seek(ex_off + 0x200 + fo)
                return f.read(min(fs, 0x4000))
    return b""


def ler_metadados_3ds(caminho: str) -> dict:
    """Lê título/código/região de dentro da ROM. {} se não der (usa nome do arquivo)."""
    try:
        p = Path(caminho)
        if not p.is_file():
            return {}
        meta: dict = {}
        with p.open("rb") as f:
            head = f.read(0x400)
            if len(head) < 0x204:
                return {}
            if head[:4] == b"3DSX":
                pass  # sem product code; só SMDH abaixo
            elif head[0x100:0x104] == b"NCSD":
                if len(head) < 0x128:
                    return {}
                base = _u32(head, 0x120) * 0x200
                f.seek(base)
                ncch = f.read(0x300)
                if len(ncch) < 0x300 or ncch[0x100:0x104] != b"NCCH":
                    return {}
                code = ncch[0x150:0x160].split(b"\x00")[0].decode("ascii", "ignore").strip()
                if code:
                    meta["game_code"] = code
            elif head[0x100:0x104] == b"NCCH":
                f.seek(0)
                ncch = f.read(0x300)
                if len(ncch) >= 0x300 and ncch[0x100:0x104] == b"NCCH":
                    code = ncch[0x150:0x160].split(b"\x00")[0].decode("ascii", "ignore").strip()
                    if code:
                        meta["game_code"] = code
            else:
                return {}
        meta.update(_parse_smdh(_ler_icon_bin(caminho)))
        return meta
    except (OSError, ValueError, OverflowError):
        return {}


NDS_REGIOES = {"E": "América do Norte", "P": "Europa", "J": "Japão",
               "K": "Coreia", "D": "Alemanha", "F": "França", "I": "Itália",
               "S": "Espanha", "U": "Austrália"}


def _rgb555(v: int) -> bytes:
    return bytes((((v & 31) * 255 // 31), (((v >> 5) & 31) * 255 // 31),
                  (((v >> 10) & 31) * 255 // 31)))


def _ler_banner_nds(caminho: str) -> bytes:
    """Devolve o banner NDS (ícone + títulos) ou b''."""
    try:
        with Path(caminho).open("rb") as f:
            head = f.read(0x200)
            if len(head) < 0x200:
                return b""
            off = _u32(head, 0x68)
            if not off or off > 64 * 1024 * 1024:
                return b""
            f.seek(off)
            return f.read(0x2000)
    except (OSError, ValueError, OverflowError):
        return b""


def ler_metadados_nds(caminho: str) -> dict:
    """Lê título/código/região do header + banner NDS. {} se não der."""
    try:
        p = Path(caminho)
        if not p.is_file():
            return {}
        meta: dict = {}
        with p.open("rb") as f:
            head = f.read(0x200)
        if len(head) < 0x200:
            return {}
        titulo = head[:12].split(b"\x00")[0].decode("ascii", "ignore").strip()
        code = head[0x0C:0x10].split(b"\x00")[0].decode("ascii", "ignore").strip()
        if code:
            meta["game_code"] = code
            reg = NDS_REGIOES.get(code[-1:])
            if reg:
                meta["regiao"] = reg
        banner = _ler_banner_nds(caminho)
        if len(banner) >= 0x340:
            nomes = []
            for i in range(6):
                raw = banner[0x240 + i * 0x100:0x240 + i * 0x100 + 0x100]
                try:
                    txt = raw.decode("utf-16-le").split("\x00")[0]
                    txt = re.sub(r"\s+", " ", txt.replace("\u2028", " ")).strip()
                    nomes.append(txt)
                except Exception:
                    nomes.append("")
            def _limpa_nome_nds(s):
                s = re.sub(r"\s+Nintendo$", "", s).strip()  # última linha é a publisher
                return s

            for i in (1, 0):
                if i < len(nomes) and nomes[i]:
                    meta["titulo"] = _limpa_nome_nds(nomes[i])
                    meta["tem_metadados"] = True
                    break
            else:
                for t in nomes:
                    if t:
                        meta["titulo"] = _limpa_nome_nds(t)
                        meta["tem_metadados"] = True
                        break
        if titulo and "titulo" not in meta:
            meta["titulo"] = titulo
        return meta
    except (OSError, ValueError, OverflowError):
        return {}


def icone_nds_para_png(caminho: str, alvo_px: int = 96) -> bytes | None:
    """Decodifica o ícone 32x32 do banner NDS e devolve PNG (None se não der)."""
    try:
        banner = _ler_banner_nds(caminho)
        if len(banner) < 0x240:
            return None
        pal = [_rgb555(banner[0x220 + i * 2] | (banner[0x221 + i * 2] << 8))
               for i in range(16)]
        dados = banner[0x20:0x220]
        if len(dados) < 0x200:
            return None
        lado = 32
        rgb = bytearray(lado * lado * 3)
        for ty in range(4):
            for tx in range(4):
                base_t = (ty * 4 + tx) * 32  # tile 8x8 4bpp = 32 bytes
                for y in range(8):
                    for x in range(8):
                        b = dados[base_t + (y * 8 + x) // 2]
                        v = (b & 0x0F) if x % 2 == 0 else (b >> 4)
                        dst = ((ty * 8 + y) * lado + (tx * 8 + x)) * 3
                        rgb[dst:dst + 3] = pal[v]
        rgb = bytes(rgb)
        fator = max(1, alvo_px // lado)
        if fator > 1:
            amp = bytearray(lado * fator * lado * fator * 3)
            W = lado * fator
            for y in range(lado):
                for x in range(lado):
                    px = rgb[(y * lado + x) * 3:(y * lado + x) * 3 + 3]
                    for dy in range(fator):
                        base = ((y * fator + dy) * W + x * fator) * 3
                        amp[base:base + fator * 3] = px * fator
            rgb, lado = bytes(amp), W
        return _png_rgb(lado, lado, rgb)
    except Exception:
        return None


def _morton(x: int, y: int) -> int:
    z = 0
    for i in range(4):
        z |= ((x >> i) & 1) << (2 * i)
        z |= ((y >> i) & 1) << (2 * i + 1)
    return z


def _desembaralha_rgb565(dados: bytes, lado: int) -> bytes:
    """SMDH guarda o ícone em tiles 8x8 (ordem Morton). Devolve RGB888 linear."""
    n = lado * lado
    if len(dados) < n * 2:
        raise ValueError("ícone curto")
    rgb = bytearray(n * 3)
    tiles = lado // 8
    for ty in range(tiles):
        for tx in range(tiles):
            base_t = (ty * tiles + tx) * 64
            for y in range(8):
                for x in range(8):
                    src = (base_t + _morton(x, y)) * 2
                    v = dados[src] | (dados[src + 1] << 8)
                    r = ((v >> 11) & 31) * 255 // 31
                    g = ((v >> 5) & 63) * 255 // 63
                    b = (v & 31) * 255 // 31
                    dst = ((ty * 8 + y) * lado + (tx * 8 + x)) * 3
                    rgb[dst:dst + 3] = bytes((r, g, b))
    return bytes(rgb)


def _png_rgb(larg: int, alt: int, rgb: bytes) -> bytes:
    def bloco(tipo: bytes, dado: bytes) -> bytes:
        c = tipo + dado
        return struct.pack(">I", len(dado)) + c + struct.pack(
            ">I", zlib.crc32(c) & 0xFFFFFFFF)

    cab = struct.pack(">IIBBBBB", larg, alt, 8, 2, 0, 0, 0)
    corpo = b"".join(b"\x00" + rgb[y * larg * 3:(y + 1) * larg * 3]
                     for y in range(alt))
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", cab)
            + bloco(b"IDAT", zlib.compress(corpo)) + bloco(b"IEND", b""))


def icone_rom_para_png(caminho: str, alvo_px: int = 144) -> bytes | None:
    """Decodifica o ícone SMDH da ROM e devolve PNG RGB (None se não der).

    Ordem de tiles documentada (Morton 8x8); conferir visualmente na 1ª ROM real.
    """
    try:
        icon = _ler_icon_bin(caminho)
        if len(icon) >= 0x1680:
            rgb, lado = _desembaralha_rgb565(icon[:0x1200], 48), 48
        elif len(icon) >= 0x480:
            rgb, lado = _desembaralha_rgb565(icon[0x1200:0x1200 + 0x480], 24), 24
        else:
            return None
        fator = max(1, alvo_px // lado)
        if fator > 1:  # amplia por vizinho mais próximo (pixel nítido)
            amp = bytearray(lado * fator * lado * fator * 3)
            W = lado * fator
            for y in range(lado):
                for x in range(lado):
                    px = rgb[(y * lado + x) * 3:(y * lado + x) * 3 + 3]
                    for dy in range(fator):
                        base = ((y * fator + dy) * W + x * fator) * 3
                        amp[base:base + fator * 3] = px * fator
            rgb, lado = bytes(amp), W
        return _png_rgb(lado, lado, rgb)
    except Exception:
        return None


__all__ = ["SMDH_IDIOMAS", "SMDH_REGIOES", "_u32", "_parse_smdh", "_ler_icon_bin",
           "ler_metadados_3ds", "NDS_REGIOES", "_rgb555", "_ler_banner_nds",
           "ler_metadados_nds", "icone_nds_para_png", "_morton",
           "_desembaralha_rgb565", "_png_rgb", "icone_rom_para_png"]
