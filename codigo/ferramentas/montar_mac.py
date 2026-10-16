#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monta o payload Mac: tucoteca-mac-<data>.tar.xz + Instalar-Mac.command.

    py -3.14 codigo/ferramentas/montar_mac.py

Fase 0 do Mac: GUI Qt Quick via python3 do sistema (PySide6), ROMs 3DS/NDS.
O instalador é um .command simples (o tar do macOS lê xz nativo) que
extrai p/ ~/Applications/TucoTeca. Sem AppImage/dmg: dmg só se monta
num Mac de verdade (fica p/ depois).
"""
from __future__ import annotations

import argparse
import datetime
import os
import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from build_utils import baixar_verificado, escrever_tarxz
from montar_portatil import DIST, REPO, copiar_app, podar_dieta

MAC_BUILD = AQUI / ".build" / "mac"
MAC_CACHE = AQUI / ".cache" / "mac"

# Arquivos oficiais p/ Mac (Intel+ARM, velho+novo). Tudo verificado nas
# fontes em 28/09/2026: python.org/downloads/macos + APIs GitHub
# (azahar-emu/azahar, TASEmulators/desmume).
MAC_ARQS = (
    # sha: GitHub digest (azahar) ou pin local do baixado (python,
    # desmume sem digest no release) — qualquer troca futura quebra alto.
    ("python-3.14.7-macos11.pkg",  # novo (mesma série do Montar Win)
     "https://www.python.org/ftp/python/3.14.7/python-3.14.7-macos11.pkg",
     20_000_000,
     "70c5239ad2d62925d2947e46921d0ddd3d35be3d2f0a2d50db33da507dbcb419"),
    ("python-3.10.11-macos11.pkg",  # antigo (mínimo suportado 3.10)
     "https://www.python.org/ftp/python/3.10.11/python-3.10.11-macos11.pkg",
     20_000_000,
     "767ed35ad688d28ea4494081ae96408a0318d0d5bb9ca0139d74d6247b231cfc"),
    ("azahar-macos-universal-2126.1.2.zip",  # novo (universal Intel+ARM)
     "https://github.com/azahar-emu/azahar/releases/download/2126.1.2/"
     "azahar-macos-universal-2126.1.2.zip",
     90_000_000,
     "085653f1a4c1879aef98235a0f258b1333e4a3a5e5a7e8bafe1ccddc952bb75d"),
    ("azahar-macos-universal-2126.1.1.zip",  # antigo (fallback)
     "https://github.com/azahar-emu/azahar/releases/download/2126.1.1/"
     "azahar-macos-universal-2126.1.1.zip",
     90_000_000,
     "46839e22772b75f76fc3021a5aed07c2fedb52cfa434f43030e48c3514a8aa1a"),
    ("desmume-0.9.13-macOS.dmg",
     "https://github.com/TASEmulators/desmume/releases/download/"
     "release_0_9_13/desmume-0.9.13-macOS.dmg",
     8_000_000,
     "d42e4bbf8f96b6bfdb3c8be6cf469b606a3b105352460636b1051b8dd0365ebc"),
)


def garantir_mac() -> Path:
    """Baixa (uma vez) os arquivos oficiais do Mac p/ .cache/mac/."""
    MAC_CACHE.mkdir(parents=True, exist_ok=True)
    for nome, url, minimo, sha in MAC_ARQS:
        baixar_verificado(url, nome, MAC_CACHE, sha256=sha, minimo=minimo, timeout=300)
    return MAC_CACHE

COMMAND_LAUNCHER = """#!/bin/sh
# TucoTeca (instalada no Mac) — duplo-clique abre a GUI.
HUB="$(cd "$(dirname "$0")" && pwd)"
export BIBLIOTECA_HOME="$HUB"
[ -f "$HUB/dados/dados/biblioteca.db" ] && export BIBLIOTECA_HOME="$HUB/dados"
exec python3 "$HUB/app/desktop.py" "$@"
"""

INSTALADOR = """#!/bin/sh
# TucoTeca no Mac — pacote completo offline ou variante leve.
AQUI="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/Applications/TucoTeca"
falha() { echo "ERRO: $1" >&2; exit 1; }
[ -d "$AQUI" ] || falha "pasta do instalador sumiu."

# 1. Python 3.10+ (python.org; o da App Store não traz PySide6/Tk)
if ! python3 -c 'import sys; assert sys.version_info>=(3,10)' 2>/dev/null; then
  echo "[hub] instalando o Python oficial (precisa da sua senha, uma vez só)..."
  [ -f "$AQUI/python-3.14.7-macos11.pkg" ] || falha "instale Python 3.10+ (python.org) e execute novamente."
  open "$AQUI"/python-3.14.7-macos11.pkg || falha "não abri o pkg do Python."
  echo "Termine a instalação do Python e rode este instalador de novo."
  exit 0
fi
python3 -c 'import PySide6' 2>/dev/null || {
  echo "[aviso] sem PySide6: a GUI não abre; instale com 'python3 -m pip install PySide6'."
}

# 2. App (código do Hub)
mkdir -p "$DEST" || falha "não criei $DEST."
tar -xJf "$AQUI/PAYLOAD" -C "$DEST" || falha "extração do app falhou."
HUB="$DEST/tucoteca"

# 3. Emuladores (.app oficiais, sem modificação)
deszipar() { # $1=zip $2=destino $3=versao-arq $4=versao
  mkdir -p "$2" || return 1
  rm -rf "$2/.zip"
  unzip -q -o "$1" -d "$2/.zip" || return 1
  APP="$(find "$2/.zip" -maxdepth 2 -name '*.app' | head -n 1)"
  [ -n "$APP" ] || return 1
  rm -rf "$2/$(basename "$APP")"
  ditto "$APP" "$2/$(basename "$APP")" || return 1
  rm -rf "$2/.zip"
  echo "$4" > "$2/$3"
}
montar_dmg() { # $1=dmg $2=destino $3=versao-arq $4=versao
  mkdir -p "$2" || return 1
  MNT="$(mktemp -d /tmp/tuco.XXXXXX)" || return 1
  hdiutil attach -nobrowse -mountpoint "$MNT" "$1" >/dev/null || {
    rmdir "$MNT" 2>/dev/null; return 1; }
  APP="$(find "$MNT" -maxdepth 2 -name '*.app' | head -n 1)"
  RC=1
  if [ -n "$APP" ] && [ -d "$APP" ]; then
    rm -rf "$2/$(basename "$APP")"
    ditto "$APP" "$2/$(basename "$APP")" && RC=0
  fi
  hdiutil detach "$MNT" >/dev/null || RC=1
  rmdir "$MNT" 2>/dev/null
  [ "$RC" = 0 ] || return 1
  echo "$4" > "$2/$3"
}
if [ -f "$AQUI/azahar-macos-universal-2126.1.2.zip" ]; then
  deszipar "$AQUI/azahar-macos-universal-2126.1.2.zip" "$HUB/emuladores/Azahar" \
    versao-azahar.txt 2126.1.2 || falha "Azahar não instalou."
else
  echo "[aviso] pacote leve: instale Azahar pelo botão ⬇ do app."
fi
mkdir -p "$HUB/emuladores/Azahar/user"
montar_dmg "$AQUI"/desmume-*.dmg "$HUB/emuladores/DeSmuME" \
  desmume-versao.txt release_0_9_13 || echo "[aviso] DeSmuME não instalou (use o botão ⬇ do app)."

chmod +x "$HUB/BibliotecaHubMac.command"
xattr -dr com.apple.quarantine "$HUB/emuladores" 2>/dev/null
echo "[ok] TucoTeca instalada em $HUB"
echo "     abrir: duplo-clique em BibliotecaHubMac.command"
echo "     (1ª vez: clique direito > Abrir, por causa do Gatekeeper)"
exit 0
"""

LEIAME_MAC = """TucoTeca no Mac (experimental — ainda não testado num Mac real).

INSTALAÇÃO (tudo offline, nesta pasta):
1. Duplo-clique em Instalar-Mac.command (1ª vez: clique direito > Abrir).
2. Ele pede o Python oficial se faltar (pkg incluído: python-3.14.7;
   tem o 3.10.11 p/ macs mais velhos — troque o nome no instalador).
3. Emuladores oficiais inclusos: Azahar 2126.1.2 (3DS),
   DeSmuME 0.9.13 (NDS).
4. A coleção fica em ~/Applications/TucoTeca/tucoteca/dados.

ATUALIZAR DEPOIS: botão ⬇ dentro do app (baixa build oficial sozinho).
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
    copiar_app(app, repo=REPO)
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


MAC_NAVIO = ("python-3.14.7-macos11.pkg", "python-3.10.11-macos11.pkg",
               "azahar-macos-universal-2126.1.2.zip",
               "desmume-0.9.13-macOS.dmg")


def empacotar_mac(build: Path, data: str, leve: bool = False) -> tuple[Path, Path]:
    """Monta dist/mac/: payload e, no pacote completo, Python + 2 emuladores.

    Retorna (payload .tar.xz, Instalar-Mac.command). O Azahar antigo fica
    só no cache (fallback manual); o resto viaja junto (100% offline).
    leve=True: só payload+instalador (mac baixa o resto pelo ⬇ do app).
    """
    cache = garantir_mac() if not leve else None
    pasta = DIST / "mac"
    if pasta.exists():
        shutil.rmtree(pasta)
    pasta.mkdir(parents=True)
    payload = pasta / f"tucoteca-mac-{data}.tar.xz"
    escrever_tarxz(build.parent, payload, strip_parente=0)
    if leve:
        print("[aviso] mac leve: sem Python/emuladores (baixa pelo ⬇ no Mac)")
    else:
        assert cache is not None  # leve=False sempre passa por garantir_mac()
        for nome in MAC_NAVIO:
            shutil.copy2(cache / nome, pasta / nome)
    inst = pasta / "Instalar-Mac.command"
    inst.write_text(INSTALADOR.replace("PAYLOAD", payload.name),
                    encoding="utf-8")
    (pasta / "LEIA-ME-MAC.txt").write_text(LEIAME_MAC, encoding="utf-8")
    try:
        os.chmod(inst, 0o755)
    except OSError:
        pass
    mb = sum(f.stat().st_size for f in pasta.rglob("*") if f.is_file()) / 1048576
    print(f"[ok] mac/ com {len(MAC_NAVIO)} oficiais ({mb:.0f} MB)")
    return payload, inst


def montar(leve: bool = False) -> tuple[Path, Path]:
    base, v = montar_base_mac()
    return empacotar_mac(base, v["data"], leve)


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
