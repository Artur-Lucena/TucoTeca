"""Leitura bruta do catálogo local Hydra (sem rede e sem mutação)."""
from __future__ import annotations

import json
import re
from pathlib import Path

TITLE_RE = re.compile(r'"title"\s*:\s*"((?:[^"\\]|\\.)+)"')
EXEC_RE = re.compile(r'"executablePath"\s*:\s*(null|"((?:[^"\\]|\\.)*)")')
SHOP_RE = re.compile(r'"shop"\s*:\s*"((?:[^"\\]|\\.)+)"')
OBJID_RE = re.compile(r'"objectId"\s*:\s*"((?:[^"\\]|\\.)+)"')
PLAYTIME_RE = re.compile(r'"playTimeInMilliseconds"\s*:\s*(\d+)')


def _unescape(s):
    try:
        return json.loads(f'"{s}"')
    except ValueError:
        return s


def scan_hydra_db(db_dir: Path, limite_bytes_por_arquivo=20_000_000):
    achados = {}
    for arq in db_dir.rglob("*"):
        if not arq.is_file() or arq.suffix.lower() not in (".log", ".ldb", ".sst", ".db", ""):
            continue
        try:
            if arq.stat().st_size > limite_bytes_por_arquivo:
                continue
            texto = arq.read_bytes().decode("utf-8", errors="ignore")
        except OSError:
            continue
        matches = list(TITLE_RE.finditer(texto))
        for i, m in enumerate(matches):
            fim = min(m.start() + 8000, matches[i + 1].start() if i + 1 < len(matches) else len(texto))
            janela = texto[m.start():fim]
            if not any(k in janela for k in ("objectId", "executablePath", "shop")):
                continue
            titulo = _unescape(m.group(1)).strip()
            if not titulo or len(titulo) > 200:
                continue
            me, ms, mo, mp = (p.search(janela) for p in (EXEC_RE, SHOP_RE, OBJID_RE, PLAYTIME_RE))
            exe = _unescape(me.group(2) or "") if me and me.group(1) != "null" else ""
            horas = round(int(mp.group(1)) / 3_600_000, 2) if mp else 0.0
            chave = f"{titulo}\x00{exe}"
            if chave not in achados:
                achados[chave] = {"titulo": titulo, "executable_path": exe,
                    "shop": _unescape(ms.group(1)) if ms else "",
                    "object_id": _unescape(mo.group(1)) if mo else "", "horas": horas, "origem": "hydra"}
            else:
                achados[chave]["horas"] = max(horas, achados[chave]["horas"])
    return sorted(achados.values(), key=lambda j: j["titulo"].lower())
