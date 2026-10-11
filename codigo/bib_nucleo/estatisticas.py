"""Histórico local de sessões e uso de disco, sem Steam ou telemetria."""
from __future__ import annotations

import math
import os
from datetime import datetime, timedelta
from pathlib import Path


def garantir_historico(con):
    con.execute("""CREATE TABLE IF NOT EXISTS sessoes_historico (
        id INTEGER PRIMARY KEY, jogo_uuid TEXT NOT NULL, titulo TEXT NOT NULL,
        perfil TEXT NOT NULL, inicio TEXT NOT NULL, fim TEXT NOT NULL, horas REAL NOT NULL)""")


def registrar(con, jogo, horas, perfil, *, commit=True):
    horas = float(horas)
    if not math.isfinite(horas) or horas <= 0 or perfil not in ("Tuco", "Isa"):
        raise ValueError("Sessão/perfil inválidos.")
    fim = datetime.now()
    try:
        inicio = fim - timedelta(hours=horas)
    except OverflowError:
        raise ValueError("Horas de sessão acima do limite de datas.") from None
    garantir_historico(con)
    con.execute("INSERT INTO sessoes_historico(jogo_uuid,titulo,perfil,inicio,fim,horas) VALUES(?,?,?,?,?,?)",
                (jogo["uuid"], jogo["titulo"], perfil, inicio.isoformat(),
                 fim.isoformat(), horas))
    if commit:
        con.commit()


def resumo_ano(con, ano=None, perfil=""):
    ano = int(ano or datetime.now().year)
    if not 1 <= ano <= 9998:
        raise ValueError("Ano inválido.")
    garantir_historico(con)
    rows = con.execute("SELECT * FROM sessoes_historico WHERE fim>=? AND fim<?",
                       (f"{ano:04d}-01-01", f"{ano + 1:04d}-01-01")).fetchall()
    meses, jogos = [0.0] * 12, {}
    for r in rows:
        if perfil and r["perfil"] != perfil:
            continue
        meses[int(r["fim"][5:7]) - 1] += r["horas"]
        chave = r["jogo_uuid"]
        item = jogos.setdefault(chave, {"titulo": r["titulo"], "horas": 0.0})
        item["horas"] += r["horas"]
    return {"ano": ano, "meses": [round(h, 2) for h in meses],
            "total_horas": round(sum(meses), 2),
            "jogos": sorted(jogos.values(), key=lambda j: j["horas"], reverse=True)}


def tamanho_pasta(pasta, limite_arquivos=500_000):
    raiz = Path(pasta)
    if not raiz.is_dir() or raiz == Path(raiz.anchor):
        raise ValueError("Pasta de jogo inválida.")
    total = arquivos = 0
    for base, dirs, nomes in os.walk(raiz, followlinks=False):
        dirs[:] = [d for d in dirs if not Path(base, d).is_symlink() and not
                   getattr(Path(base, d).lstat(), "st_file_attributes", 0) & 0x400]
        for nome in nomes:
            p = Path(base, nome)
            if p.is_symlink():
                continue
            total += p.stat().st_size
            arquivos += 1
            if arquivos >= limite_arquivos:
                return {"bytes": total, "arquivos": arquivos, "parcial": True}
    return {"bytes": total, "arquivos": arquivos, "parcial": False}
