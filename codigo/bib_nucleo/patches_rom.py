"""IPS/BPS locais com limites e CRC; a ROM original nunca é sobrescrita."""
from __future__ import annotations

import os
import struct
import tempfile
import zlib
from pathlib import Path

LIMITE_ROM = 512 * 1024 * 1024


def aplicar_ips(origem, patch, limite=LIMITE_ROM):
    if not patch.startswith(b"PATCH"):
        raise ValueError("Cabeçalho IPS inválido.")
    saida, pos = bytearray(origem), 5
    if len(saida) > limite:
        raise ValueError("ROM excede o limite.")
    while True:
        if pos + 3 > len(patch):
            raise ValueError("IPS truncado (sem EOF).")
        offset = patch[pos:pos + 3]
        pos += 3
        if offset == b"EOF":
            restante = patch[pos:]
            if len(restante) not in (0, 3):
                raise ValueError("Dados depois do EOF do IPS.")
            if restante:
                tamanho = int.from_bytes(restante, "big")
                if tamanho > limite:
                    raise ValueError("IPS excede o limite.")
                saida = saida[:tamanho] + b"\0" * max(0, tamanho - len(saida))
            return bytes(saida)
        offset = int.from_bytes(offset, "big")
        if pos + 2 > len(patch):
            raise ValueError("Registro IPS truncado.")
        tamanho = int.from_bytes(patch[pos:pos + 2], "big")
        pos += 2
        if tamanho:
            if pos + tamanho > len(patch):
                raise ValueError("Dados IPS truncados.")
            dados = patch[pos:pos + tamanho]
            pos += tamanho
        else:
            if pos + 3 > len(patch):
                raise ValueError("RLE IPS truncado.")
            tamanho = int.from_bytes(patch[pos:pos + 2], "big")
            dados = patch[pos + 2:pos + 3] * tamanho
            pos += 3
        fim = offset + tamanho
        if fim > limite:
            raise ValueError("IPS excede o limite.")
        if fim > len(saida):
            saida.extend(b"\0" * (fim - len(saida)))
        saida[offset:fim] = dados


class _LeitorBPS:
    def __init__(self, patch):
        self.patch, self.pos, self.fim = patch, 4, len(patch) - 12

    def ler(self, n):
        if n < 0 or self.pos + n > self.fim:
            raise ValueError("BPS truncado.")
        raw = self.patch[self.pos:self.pos + n]
        self.pos += n
        return raw

    def numero(self):
        valor, escala = 0, 1
        for _ in range(10):
            b = self.ler(1)[0]
            valor += (b & 127) * escala
            if b & 128:
                return valor
            escala <<= 7
            valor += escala
        raise ValueError("Inteiro BPS grande demais.")

    def deslocamento(self):
        n = self.numero()
        return -(n >> 1) if n & 1 else n >> 1


def aplicar_bps(origem, patch, limite=LIMITE_ROM):
    if not patch.startswith(b"BPS1") or len(patch) < 19:
        raise ValueError("Cabeçalho BPS inválido.")
    crc_src, crc_dst, crc_patch = struct.unpack("<III", patch[-12:])
    if zlib.crc32(patch[:-4]) != crc_patch:
        raise ValueError("CRC do patch BPS divergente.")
    if zlib.crc32(origem) != crc_src:
        raise ValueError("CRC da ROM original divergente: este patch é para outra ROM.")
    leitor = _LeitorBPS(patch)
    tamanho_src, tamanho_dst, meta = leitor.numero(), leitor.numero(), leitor.numero()
    if tamanho_src != len(origem) or tamanho_dst > limite:
        raise ValueError("Tamanho da ROM divergente ou acima do limite.")
    if meta > 16 * 1024 * 1024:
        raise ValueError("Metadados BPS grandes demais.")
    leitor.ler(meta)
    saida, rel_src, rel_dst = bytearray(), 0, 0
    while len(saida) < tamanho_dst:
        instrucao = leitor.numero()
        modo, n = instrucao & 3, (instrucao >> 2) + 1
        if n > tamanho_dst - len(saida):
            raise ValueError("Registro BPS ultrapassa a ROM de destino.")
        if modo == 0:
            offset = len(saida)
            if offset + n > len(origem):
                raise ValueError("SourceRead fora da ROM.")
            saida.extend(origem[offset:offset + n])
        elif modo == 1:
            saida.extend(leitor.ler(n))
        elif modo == 2:
            rel_src += leitor.deslocamento()
            if rel_src < 0 or rel_src + n > len(origem):
                raise ValueError("SourceCopy fora da ROM.")
            saida.extend(origem[rel_src:rel_src + n])
            rel_src += n
        else:
            rel_dst += leitor.deslocamento()
            if rel_dst < 0 or rel_dst >= len(saida):
                raise ValueError("TargetCopy fora da ROM.")
            for _ in range(n):
                saida.append(saida[rel_dst])
                rel_dst += 1
    if leitor.pos != leitor.fim or zlib.crc32(saida) != crc_dst:
        raise ValueError("CRC da ROM resultante ou tamanho do patch divergente.")
    return bytes(saida)


def aplicar_patch(rom, patch, destino, limite=LIMITE_ROM):
    rom, patch, destino = Path(rom), Path(patch), Path(destino)
    if destino.resolve() in (rom.resolve(), patch.resolve()) or destino.exists():
        raise ValueError("Escolha um arquivo novo; a ROM original não será sobrescrita.")
    if rom.stat().st_size > limite or patch.stat().st_size > limite:
        raise ValueError("ROM/patch excede o limite.")
    raw = patch.read_bytes()
    aplicar = aplicar_ips if raw.startswith(b"PATCH") else aplicar_bps
    saida = aplicar(rom.read_bytes(), raw, limite)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destino.parent, prefix=".rom-", delete=False) as f:
        tmp = Path(f.name)
        try:
            f.write(saida)
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            f.close()
            tmp.unlink(missing_ok=True)
            raise
    try:
        os.link(tmp, destino)  # publicação atômica sem substituir destino existente
    finally:
        tmp.unlink(missing_ok=True)
    return {"ok": True, "path": str(destino), "bytes": len(saida)}
