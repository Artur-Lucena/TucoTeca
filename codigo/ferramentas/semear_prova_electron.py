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
import json
import os
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

JOGOS = [
    ("Hollow Knight", 42.5, "2026-10-15 20:10:00"),
    ("Celeste", 11.25, "2026-10-17 21:40:00"),
    ("Stardew Valley", 87.0, None),
]
MUSICAS = [
    ("Weightless", "Marconi Union", "semente-p1-0001"),
    ("Sunset Lover", "Petit Biscuit", "semente-p1-0002"),
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

    import bib_core as core
    import gerar_placeholders as placeholders

    core.garantir_dirs()
    con = core.get_db(core.DEFAULT_DB)
    try:
        for titulo, horas, ultima in JOGOS:
            probe = titulo == JOGO_DE_PROVA and _executavel_de_prova()
            jogo = core.criar_jogo(con, {
                "titulo": titulo,
                "executable_path": _executavel_de_prova() if probe else "",
                "launch_options": LAUNCH_PROVA if probe else ""})
            if horas:
                core.adicionar_horas(con, jogo["id"], horas)
            nome_capa = f"semente-{jogo['id']}.png"
            placeholders._png(core.CAPAS_DIR / nome_capa, 300, 400, titulo)
            con.execute("UPDATE jogos SET capa=? WHERE id=?", (nome_capa, jogo["id"]))
            if ultima:
                con.execute("UPDATE jogos SET ultima_execucao=? WHERE id=?",
                            (ultima, jogo["id"]))
        con.commit()
        for titulo, artista, sha in MUSICAS:
            core.criar_musica(con, {"titulo": titulo, "artista": artista, "musica_sha": sha})
        for titulo, appid in DESEJOS:
            core.adicionar_desejo(con, appid, titulo)
    finally:
        con.close()

    print(json.dumps({"home": str(destino), "jogos": len(JOGOS),
                      "musicas": len(MUSICAS), "desejos": len(DESEJOS)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
