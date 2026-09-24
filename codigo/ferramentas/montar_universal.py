#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monta o pacote universal: 1 pasta (ou 1 .zip) com os 3 instaladores +
INSTALAR.html que abre em qualquer navegador, detecta o SO e aponta
o instalador certo.

    py -3.14 codigo/ferramentas/montar_universal.py [--sem-zip]

Pega o Setup.exe mais novo, o .run mais novo e o trio Mac de dist/
(gera o Mac na hora, que é instantâneo). Windows/Linux precisam ter
sido montados antes (montar_portatil.py --setup / montar_linux.py).
Tudo 100% offline. O .zip externo usa deflate de propósito: abre em
qualquer SO sem ferramenta extra (o peso já foi podado dentro).
"""
from __future__ import annotations

import argparse
import datetime
import shutil
import sys
import zipfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from montar_portatil import DIST
from montar_mac import montar as montar_mac

HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>TucoTeca — instalar</title>
<style>
body{font-family:sans-serif;max-width:640px;margin:40px auto;padding:0 16px;color:#222}
h1{font-size:1.6em}.sub{color:#666;margin-top:-10px}
.card{border:2px solid #ccc;border-radius:12px;padding:16px;margin:12px 0}
.card.eu{border-color:#2a7}
.badge{display:inline-block;background:#2a7;color:#fff;border-radius:8px;
padding:2px 10px;font-size:.8em;margin-left:8px}
a.btn{display:inline-block;background:#25d;color:#fff;border-radius:8px;
padding:10px 18px;text-decoration:none;font-weight:bold;margin-top:8px}
ol{margin:8px 0}li{margin:4px 0}.nota{color:#666;font-size:.9em}
</style>
</head>
<body>
<h1>🎮 TucoTeca __VERSAO__</h1>
<p class="sub">Escolha o instalador do seu sistema. Tudo offline, nada baixa nada.</p>
<div class="card" id="c-win">
<h2>🪟 Windows<span class="badge" id="b-win" hidden>este computador</span></h2>
<ol><li>Abra a pasta <b>windows</b></li>
<li>Duplo-clique em <b>__EXE__</b> e siga o wizard (sem admin)</li></ol>
</div>
<div class="card" id="c-lin">
<h2>🐧 Linux<span class="badge" id="b-lin" hidden>este computador</span></h2>
<ol><li>Abra um terminal na pasta <b>linux</b></li>
<li>Rode <b>./__RUN__</b> e informe a pasta (padrão: ~/.local/tucoteca)</li></ol>
</div>
<div class="card" id="c-mac">
<h2>🍎 Mac (experimental)<span class="badge" id="b-mac" hidden>este computador</span></h2>
<ol><li>Abra a pasta <b>mac</b></li>
<li>Duplo-clique em <b>Instalar-Mac.command</b> (precisa do Python 3.10+ do python.org)</li></ol>
<p class="nota">Fase 0: só ROMs 3DS/NDS, sem emulador embutido.</p>
</div>
<p class="nota">Prefere portátil sem instalar? O .zip clássico de Windows continua saindo do montar_portatil.py.</p>
<script>
var p=navigator.platform||"",eu="";
// Windows: Win32/Win64 | Linux: Linux (x86_64, aarch64) | Mac: MacIntel/MacPPC
if(/^Win/.test(p)){eu="win"}else if(/^Linux/.test(p)){eu="lin"}else if(/^Mac/.test(p)){eu="mac"}
if(eu){document.getElementById("c-"+eu).className+=" eu";document.getElementById("b-"+eu).hidden=false}
</script>
</body>
</html>
"""

LEIAME = """TucoTeca — pacote universal (Windows + Linux + Mac), 100% offline.

COMO INSTALAR
- O jeito fácil: abra INSTALAR.html em qualquer navegador e siga o
  instalador do seu sistema (ele detecta sozinho).
- O jeito direto: entre na pasta do seu sistema e rode o instalador:
    windows/  TucoTeca-Setup-*.exe   (wizard, sem admin)
    linux/    tucoteca-setup-*.run   (./tucoteca-setup-*.run no terminal)
    mac/      Instalar-Mac.command   (experimental, precisa Python 3.10+)

O QUE VAI EM CADA UM
- Windows: Python embutido + Azahar + DeSmuME (+Citron, se montado junto).
- Linux: app + Azahar (AppImage). DeSmuME/Citron: pacote do sistema.
- Mac (Fase 0): só o app; emuladores ficam p/ depois.
"""


def mais_novo(padrao: str) -> Path | None:
    cands = sorted(DIST.glob(padrao))
    return cands[-1] if cands else None


def montar(sem_zip: bool = False) -> Path:
    data = datetime.date.today().strftime("%Y%m%d")
    uni = DIST / f"tucoteca-universal-{data}"
    if uni.exists():
        shutil.rmtree(uni)
    avisos: list[str] = []
    exe = mais_novo("TucoTeca-Setup-*.exe")
    run = mais_novo("tucoteca-setup-*.run")
    if exe is None:
        avisos.append("sem Setup.exe em dist/ (rode montar_portatil.py --setup)")
    else:
        (uni / "windows").mkdir(parents=True)
        shutil.copy2(exe, uni / "windows" / exe.name)
    if run is None:
        avisos.append("sem .run em dist/ (rode montar_linux.py)")
    else:
        (uni / "linux").mkdir(parents=True)
        shutil.copy2(run, uni / "linux" / run.name)
    payload_mac, inst_mac = montar_mac()
    (uni / "mac").mkdir(parents=True)
    for arq in (payload_mac, inst_mac, payload_mac.parent / "LEIA-ME-MAC.txt"):
        shutil.copy2(arq, uni / "mac" / arq.name)
    (uni / "INSTALAR.html").write_text(
        HTML.replace("__VERSAO__", data)
        .replace("__EXE__", exe.name if exe else "TucoTeca-Setup-*.exe")
        .replace("__RUN__", run.name if run else "tucoteca-setup-*.run"),
        encoding="utf-8")
    (uni / "LEIA-ME.txt").write_text(LEIAME, encoding="utf-8")
    for a in avisos:
        print(f"[aviso] pacote incompleto: {a}")
    if sem_zip:
        print(f"[ok] pasta {uni.name}/")
        return uni
    saida = DIST / f"{uni.name}.zip"
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        for arq in sorted(uni.rglob("*")):
            z.write(arq, arq.relative_to(DIST))
    mb = saida.stat().st_size / 1048576
    print(f"[ok] {saida.name} — {mb:.1f} MB")
    return saida


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Monta o pacote universal.")
    ap.add_argument("--sem-zip", action="store_true",
                    help="só a pasta, sem zzipar")
    args = ap.parse_args(argv)
    try:
        montar(sem_zip=args.sem_zip)
    except SystemExit as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
