"""Prova nativa isolada do qBittorrent: API, torrent local, pausa/retomada."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import bib_core as core
from bib_nucleo import qbit as Q


def _benc(valor):
    if isinstance(valor, int):
        return b"i" + str(valor).encode() + b"e"
    if isinstance(valor, bytes):
        return str(len(valor)).encode() + b":" + valor
    if isinstance(valor, dict):
        return b"d" + b"".join(_benc(k) + _benc(valor[k]) for k in sorted(valor)) + b"e"
    raise ValueError("tipo de fixture inválido")


def esperar(trabalho, pronto, timeout=25):
    limite = time.monotonic() + timeout
    ultimo = None
    while time.monotonic() < limite:
        try:
            ultimo = trabalho()
            if pronto(ultimo):
                return ultimo
        except Exception as e:
            ultimo = str(e)
        time.sleep(0.2)
    raise RuntimeError("qBittorrent não respondeu como esperado: " + str(ultimo))


def provar():
    inicio = core.qbit_iniciar()
    if not inicio["ok"]:
        raise RuntimeError(inicio["erro"])
    handle = None
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.OpenProcess.restype = wintypes.HANDLE
        k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = k.OpenProcess(0x100001, False, inicio["pid"])
    try:
        ver = esperar(lambda: Q.qbit_request("app/version"), lambda s: s.startswith("v"))
        raw = b"offline-proof" * 1024
        nome = b"offline-proof.bin"
        info = {b"name": nome, b"length": len(raw), b"piece length": 16384,
                b"pieces": hashlib.sha1(raw).digest()}
        h = hashlib.sha1(_benc(info)).hexdigest()
        dest = Path(inicio["destino"])
        (dest / nome.decode()).write_bytes(raw)
        arq = dest.parent / "offline-proof.torrent"
        arq.write_bytes(_benc({b"info": info}))
        adicionar = core.qbit_iniciar(str(arq))
        if not adicionar["ok"]:
            raise RuntimeError(adicionar["erro"])
        r = esperar(core.qbit_listar, lambda r: any(t["hash"] == h and t["completo"] for t in r["torrents"]))
        t = next(t for t in r["torrents"] if t["hash"] == h)
        assert t["pct"] == 100 and Path(t["save_path"]) == dest / nome.decode(), t
        assert core.qbit_controlar(h, "pausar")["ok"]
        esperar(core.qbit_listar, lambda r: any(t["hash"] == h and t["estado"] == "stoppedUP" for t in r["torrents"]))
        assert core.qbit_controlar(h, "retomar")["ok"]
        esperar(core.qbit_listar, lambda r: any(t["hash"] == h and t["estado"] != "stoppedUP" for t in r["torrents"]))
        return {"versao": ver, "pct": t["pct"], "pausa_retomada": True, "destino": "perfil temporário"}
    finally:
        try:
            Q.qbit_request("app/shutdown", {})
        except Exception:
            pass
        if handle:
            if k.WaitForSingleObject(handle, 8000) == 0x102:
                k.TerminateProcess(handle, 1)  # exclusivamente o processo desta prova
                k.WaitForSingleObject(handle, 5000)
            k.CloseHandle(handle)
        else:
            time.sleep(2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--configurar-offline", action="store_true")
    args = ap.parse_args()
    if args.configurar_offline:
        # Só o perfil explicitamente passado pelo builder, nunca o perfil do PC.
        cfg = Q.qbit_preparar_perfil()
        texto = cfg.read_text(encoding="utf-8")
        texto = texto.replace("[BitTorrent]\n", "[BitTorrent]\nSession\\DHTEnabled=false\nSession\\LSDEnabled=false\nSession\\PeXEnabled=false\n")
        cfg.write_text(texto, encoding="utf-8")
    print(json.dumps(provar()))
