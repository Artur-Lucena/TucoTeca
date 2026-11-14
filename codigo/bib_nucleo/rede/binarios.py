"""Download limitado de ferramentas oficiais; publicação ocorre após SHA-256."""
from __future__ import annotations

import urllib.request

from bib_nucleo.rede import abrir_rede
from bib_nucleo.versao import user_agent


def _baixar_bin(url: str, minimo: int, progresso=None, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent()})
    with abrir_rede(req, timeout=timeout) as r:
        total = int(r.headers.get("Content-Length") or 0)
        if total > 500_000_000:
            raise ValueError("download grande demais (aborto)")
        blocos, feito = [], 0
        for parte in iter(lambda: r.read(256 * 1024), b""):
            feito += len(parte)
            if feito > 500_000_000:
                raise ValueError("download grande demais (aborto)")
            blocos.append(parte)
            if progresso:
                try:
                    progresso(feito, total)
                except Exception:
                    pass
    if total and feito != total:
        raise ValueError(f"download incompleto ({feito}/{total} B)")
    if feito < minimo:
        raise ValueError(f"download curto ({feito} B, esperado >{minimo})")
    return b"".join(blocos)
