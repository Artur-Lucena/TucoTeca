#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monta o payload Mac: tucoteca-mac-<data>.tar.xz + Instalar-Mac.command.

    py -3.14 codigo/ferramentas/montar_mac.py

Fase 0 do Mac: GUI tkinter via python3 do sistema, ROMs 3DS/NDS. O
instalador é um .command simples (o tar do macOS lê xz nativo) que
extrai p/ ~/Applications/TucoTeca. Sem AppImage/dmg: dmg só se monta
num Mac de verdade (fica p/ depois).
"""
from __future__ import annotations

import argparse
import datetime
import os
import shutil
import sys
import tarfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from montar_portatil import REPO, DIST, podar_dieta

MAC_BUILD = AQUI / ".build" / "mac"

COMMAND_LAUNCHER = """#!/bin/sh
# TucoTeca (instalada no Mac) — duplo-clique abre a GUI.
HUB="$(cd "$(dirname "$0")" && pwd)"
export BIBLIOTECA_HOME="$HUB/dados"
exec python3 "$HUB/app/app_win.py" "$@"
"""

INSTALADOR = """#!/bin/sh
# Instala a TucoTeca no Mac (Fase 0: ROMs 3DS/NDS, GUI tkinter).
# Precisa do Python 3.10+ com tkinter (python.org ou brew install python-tk).
AQUI="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/Applications/TucoTeca"
command -v python3 >/dev/null || { echo "ERRO: instale o Python 3.10+ primeiro."; exit 1; }
python3 -c 'import tkinter' 2>/dev/null || {
  echo "[aviso] sem tkinter: instale o Python do python.org (o da App Store não traz Tk)."
}
mkdir -p "$DEST" || { echo "ERRO: não criei $DEST."; exit 1; }
tar -xJf "$AQUI/PAYLOAD" -C "$DEST" || { echo "ERRO: extração falhou."; exit 1; }
chmod +x "$DEST"/tucoteca/BibliotecaHubMac.command
echo "[ok] TucoTeca instalada em $DEST/tucoteca"
echo "     abrir: duplo-clique em BibliotecaHubMac.command"
exit 0
"""

LEIAME_MAC = """TucoTeca no Mac (Fase 0 — experimental).

1. Duplo-clique em Instalar-Mac.command (1ª vez: clique direito > Abrir).
2. Precisa do Python 3.10+ com tkinter: baixe em python.org.
3. Por enquanto: só ROMs 3DS/NDS (Azahar/Citron de Mac ainda não embutidos;
   use o botão ⬇ do app depois, ou aponte p/ o seu emulador).
4. A coleção fica em ~/Applications/TucoTeca/tucoteca/dados.
"""


def montar_base_mac(trab: Path | None = None) -> tuple[Path, dict]:
    """Monta a árvore tucoteca/ p/ Mac. Retorna (pasta, versões).

    trab: pasta de trabalho (padrão .build/mac; testes passam o tmp
    da sandbox, que veta escrita fora dela).
    """
    raiz = trab if trab is not None else MAC_BUILD
    if raiz.exists():
        shutil.rmtree(raiz)
    base = raiz / "tucoteca"
    app = base / "app"
    app.mkdir(parents=True)
    for origem in ("codigo/bib_core.py", "codigo/frontends/app_win.py",
                   "codigo/frontends/app_tui.py"):
        src = REPO / origem
        if not src.is_file():
            raise SystemExit(f"arquivo do app ausente no repo: {origem}")
        shutil.copy2(src, app / Path(origem).name)
    nucleo = REPO / "codigo" / "bib_nucleo"
    if not (nucleo / "__init__.py").is_file():
        raise SystemExit("pacote bib_nucleo ausente no repo.")
    shutil.copytree(nucleo, app / "bib_nucleo",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (base / "BibliotecaHubMac.command").write_text(COMMAND_LAUNCHER,
                                                   encoding="utf-8")
    for sub in ("dados", "dados/backups", "dados/capas", "dados/presets",
                "dados/sessoes"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    data = datetime.date.today().strftime("%Y%m%d")
    (base / "VERSAO.txt").write_text(f"TucoTeca Mac (Fase 0) — build {data}\n",
                                     encoding="utf-8")
    podar_dieta(base)
    return base, {"data": data}


def empacotar_mac(build: Path, data: str) -> tuple[Path, Path]:
    """Gera (payload .tar.xz, Instalar-Mac.command) em dist/mac/."""
    pasta = DIST / "mac"
    pasta.mkdir(parents=True, exist_ok=True)
    payload = pasta / f"tucoteca-mac-{data}.tar.xz"
    with tarfile.open(payload, "w:xz", preset=6,
                      format=tarfile.PAX_FORMAT) as t:
        for arq in sorted(build.parent.rglob("*")):
            t.add(arq, arq.relative_to(build.parent), recursive=False)
    inst = pasta / "Instalar-Mac.command"
    inst.write_text(INSTALADOR.replace("PAYLOAD", payload.name),
                    encoding="utf-8")
    (pasta / "LEIA-ME-MAC.txt").write_text(LEIAME_MAC, encoding="utf-8")
    try:
        os.chmod(inst, 0o755)
    except OSError:
        pass
    print(f"[ok] {payload.name} — {payload.stat().st_size / 1048576:.1f} MB")
    return payload, inst


def montar() -> tuple[Path, Path]:
    base, v = montar_base_mac()
    return empacotar_mac(base, v["data"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Monta o payload Mac.")
    ap.parse_args(argv)
    try:
        montar()
    except SystemExit as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
