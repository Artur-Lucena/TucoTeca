#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monta o instalador Linux: tucoteca-setup-<data>.run (auto-extraível,
100% offline — AppImage do Azahar + app + dados vazios).

    py -3.14 codigo/ferramentas/montar_linux.py [--formato run|tarxz|todos]

A árvore Linux é montada AQUI no Windows (só cópia de arquivos) e o
payload é o mesmo .tar.xz dos instaladores (LZMA2 stdlib). O stub .run
é shell POSIX: pergunta a pasta, checa python3+tk, extrai com tar -xJ,
cria o .desktop e o desinstalador. DeSmuME no Linux = pacote do
sistema ou AppImage próprio (o ⬇ do app resolve depois); o bundle leva
o que estiver instalado aqui.
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
from montar_portatil import (AZAHAR_URL,
                              AZAHAR_USER_INCLUIR, REPO, DIST, garantir_gpl,
                              copiar_app, podar_dieta)

LIN_BUILD = AQUI / ".build" / "lin"

SH_LAUNCHER = """#!/bin/sh
# TucoTeca (instalado) — abre o TUI; --gui abre a janela gráfica.
HUB="$(dirname "$(readlink -f "$0")")"
export BIBLIOTECA_HOME="$HUB"
[ -f "$HUB/dados/dados/biblioteca.db" ] && export BIBLIOTECA_HOME="$HUB/dados"
export BIBLIOTECA_AZAHAR_DIR="$HUB/emuladores/Azahar"
export BIBLIOTECA_DESMUME_DIR="$HUB/emuladores/DeSmuME"
if [ "$1" = "--gui" ]; then
  shift
  exec python3 "$HUB/app/app_win.py" "$@"
fi
exec python3 "$HUB/app/app_tui.py" "$@"
"""

DESKTOP = """[Desktop Entry]
Type=Application
Name=TucoTeca
Comment=Biblioteca pessoal de jogos
Exec={dest}/BibliotecaHub.sh
Terminal=true
Categories=Game;
Icon=applications-games
"""

DESINSTALAR = """#!/bin/sh
# Remove a TucoTeca instalada. Mantém a coleção? (dados/ só sai com --tudo)
HUB="$(dirname "$(readlink -f "$0")")"
if [ "$1" = "--tudo" ]; then
  rm -rf "$HUB"
else
  for d in app emuladores; do rm -rf "$HUB/$d"; done
  rm -f "$HUB/BibliotecaHub.sh" "$HUB/VERSAO.txt" "$HUB/desinstalar.sh"
  echo "app removido; coleção preservada em $HUB/dados"
  echo "(--tudo apaga a coleção junto)"
fi
rm -f "$HOME/.local/share/applications/tucoteca.desktop"
echo "TucoTeca desinstalada."
"""

STUB = r"""#!/bin/sh
# TucoTeca __VERSAO__ — instalador Linux (payload .tar.xz grudado no final).
# Uso: ./tucoteca-setup-*.run [--destino DIR] [--ajuda]
VERSAO="__VERSAO__"
OFFSET=__OFFSET__
DESTINO=""
for a in "$@"; do
  case "$a" in
    --destino=*) DESTINO="${a#--destino=}" ;;
    --ajuda|-h) echo "uso: $0 [--destino DIR]"; exit 0 ;;
  esac
done
falha() { echo "ERRO: $1" >&2; exit 1; }
command -v tar >/dev/null || falha "sem 'tar' no sistema."
tar --help 2>&1 | grep -q -- "-J" || falha "seu tar não lê xz (instale o xz)."
command -v python3 >/dev/null || falha "instale o Python 3.10+ (python3)."
PYV="$(python3 -c 'import sys; print(sys.version_info[0]*10+sys.version_info[1])')"
[ "$PYV" -ge 40 ] || falha "python3 antigo demais (precisa 3.10+)."
python3 -c 'import tkinter' 2>/dev/null || {
  echo "[aviso] sem tkinter: a GUI (--gui) não abre; o TUI funciona normal."
  echo "        Debian/Ubuntu: sudo apt install python3-tk | Fedora: sudo dnf install python3-tkinter"
}
if [ -z "$DESTINO" ]; then
  if [ "$(id -u)" = "0" ]; then DESTINO="/opt/tucoteca"; else DESTINO="$HOME/.local/tucoteca"; fi
  printf "Pasta de instalação [%s]: " "$DESTINO"
  read RESP
  [ -n "$RESP" ] && DESTINO="$RESP"
fi
case "$DESTINO" in "~"*) DESTINO="$HOME${DESTINO#\~}" ;; esac
mkdir -p "$DESTINO" || falha "não criei $DESTINO."
echo "[hub] extraindo em $DESTINO ..."
tail -c +$((OFFSET + 1)) "$0" | tar -xJf - -C "$DESTINO" || falha "extração falhou."
HUB="$DESTINO/tucoteca"
[ -d "$HUB" ] || falha "payload sem pasta tucoteca/."
chmod +x "$HUB/BibliotecaHub.sh" "$HUB/desinstalar.sh"
chmod +x "$HUB"/emuladores/Azahar/*.AppImage 2>/dev/null
APP_DIR="$HOME/.local/share/applications"
[ "$(id -u)" = "0" ] && APP_DIR="/usr/share/applications"
mkdir -p "$APP_DIR"
sed "s|{dest}|$HUB|" "$HUB/tucoteca.desktop" > "$APP_DIR/tucoteca.desktop"
rm -f "$HUB/tucoteca.desktop"
echo "[ok] TucoTeca $VERSAO instalada em $HUB"
echo "     abrir: $HUB/BibliotecaHub.sh (ou o ícone TucoTeca no menu)"
echo "     remover: $HUB/desinstalar.sh"
exit 0
__PAYLOAD_SEGUE__
"""


def azahar_linux_dir() -> Path | None:
    """De onde copiar o Azahar Linux (AppImage); None se ausente."""
    env = (os.environ.get("BIBLIOTECA_EMULADOR_3DS") or "").strip()
    if env and Path(env).is_file():
        return Path(env).parent
    for cand in (Path("D:/Games/Emuladores/Azahar"),
                 Path("/run/media/tuco/Games/Games/Emuladores/Azahar")):
        if list(cand.glob("azahar*.AppImage")):
            return cand
    return None


def incluir_azahar_linux(dest_base: Path) -> str:
    """Copia AppImage + user essencial p/ emuladores/Azahar. Retorna versão."""
    src = azahar_linux_dir()
    if src is None:
        raise SystemExit("Azahar Linux (AppImage) não achado.")
    dst = dest_base / "emuladores" / "Azahar"
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for item in sorted(src.iterdir()):
        if item.name == "user":
            u_dst = dst / "user"
            u_dst.mkdir()
            for sub in AZAHAR_USER_INCLUIR:
                s = src / "user" / sub
                if s.is_dir():
                    shutil.copytree(s, u_dst / sub)
            shutil.rmtree(u_dst / "load" / "textures", ignore_errors=True)
            # texturas HD (GBs) não viajam no instalador (vide montar_portatil).
            for sub in ("sdmc", "states", "cheats"):
                (u_dst / sub).mkdir(parents=True, exist_ok=True)
            continue
        if item.suffix.lower() != ".appimage" and item.name not in (
                "versao-azahar.txt", "FONTE-AppImage.txt"):
            continue  # bundle Linux: só AppImage (+versão/fonte)
        if item.is_file():
            shutil.copy2(item, dst / item.name)
    if not list(dst.glob("*.AppImage")):
        raise SystemExit("AppImage não copiou.")
    ver = ""
    varq = src / "versao-azahar.txt"
    if varq.is_file():
        try:
            ver = varq.read_text(encoding="utf-8", errors="ignore").strip()
        except OSError:
            pass
    (dst / "FONTE.txt").write_text(
        "Azahar — emulador de Nintendo 3DS (terceiros, sem modificação).\n"
        f"Versão empacotada: {ver or 'desconhecida'}\n"
        f"Fonte: {AZAHAR_URL} (código-fonte e releases oficiais)\n"
        "Licença: GPL-2.0-or-later (texto em COPYING.txt).\n",
        encoding="utf-8")
    shutil.copy2(garantir_gpl(), dst / "COPYING.txt")
    mb = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file()) / 1048576
    print(f"[ok] Azahar Linux {ver or '?'} embutido ({mb:.0f} MB)")
    return ver


def montar_base_linux(trab: Path | None = None) -> tuple[Path, dict]:
    """Monta a árvore tucoteca/ p/ Linux. Retorna (pasta, versões).

    trab: pasta de trabalho (padrão .build/lin; testes passam o tmp
    da sandbox, que veta escrita fora dela).
    """
    raiz = trab if trab is not None else LIN_BUILD
    if raiz.exists():
        shutil.rmtree(raiz)
    base = raiz / "tucoteca"
    app = base / "app"
    app.mkdir(parents=True)
    copiar_app(app, repo=REPO)
    (base / "BibliotecaHub.sh").write_text(SH_LAUNCHER, encoding="utf-8")
    (base / "tucoteca.desktop").write_text(DESKTOP, encoding="utf-8")
    (base / "desinstalar.sh").write_text(DESINSTALAR, encoding="utf-8")
    for sub in ("dados", "dados/backups", "dados/capas", "dados/presets",
                "dados/sessoes"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    azahar_ver = ""
    try:
        azahar_ver = incluir_azahar_linux(base)
    except SystemExit as e:
        print(f"[aviso] sem Azahar Linux no pacote: {e}")
    data = datetime.date.today().strftime("%Y%m%d")
    (base / "VERSAO.txt").write_text(
        f"TucoTeca Linux — build {data}\n"
        f"Azahar: {azahar_ver or 'ausente (use o ⬇ do app)'}\n"
        "DeSmuME: pacote do sistema ou AppImage próprio\n",
        encoding="utf-8")
    podar_dieta(base)
    return base, {"azahar": azahar_ver, "data": data}


def empacotar_tarxz_linux(build: Path, data: str) -> Path:
    """Payload .tar.xz da árvore Linux (mesmo formato do Windows)."""
    DIST.mkdir(parents=True, exist_ok=True)
    saida = DIST / f"tucoteca-linux-{data}.tar.xz"
    with tarfile.open(saida, "w:xz", preset=6, format=tarfile.PAX_FORMAT) as t:
        for arq in sorted(build.parent.rglob("*")):
            t.add(arq, arq.relative_to(build.parent), recursive=False)
    print(f"[ok] {saida.name} — {saida.stat().st_size / 1048576:.1f} MB")
    return saida


def empacotar_run(build: Path, versao: str, payload_nome: str) -> Path:
    """Gruda o stub + payload .tar.xz e gera o .run instalável."""
    DIST.mkdir(parents=True, exist_ok=True)
    tmp_xz = DIST / payload_nome
    with tarfile.open(tmp_xz, "w:xz", preset=6, format=tarfile.PAX_FORMAT) as t:
        for arq in sorted(build.parent.rglob("*")):
            t.add(arq, arq.relative_to(build.parent), recursive=False)
    stub = STUB.replace("__VERSAO__", versao)
    cabeca, marcador = stub.split("__PAYLOAD_SEGUE__\n")
    base = cabeca + "__PAYLOAD_SEGUE__\n"
    # ponto fixo: o nº do offset muda o tamanho do stub (raro, mas real)
    stub_final = base
    for _ in range(3):
        off = len(stub_final.replace("__OFFSET__", "0" * 10).encode("utf-8"))
        novo = base.replace("__OFFSET__", str(off))
        if novo == stub_final:
            break
        stub_final = novo
    assert "__OFFSET__" not in stub_final
    assert len(stub_final.encode("utf-8")) == off, "offset instável"
    saida = DIST / f"tucoteca-setup-{versao}.run"
    with open(saida, "wb") as f:
        f.write(stub_final.encode("utf-8"))
        f.write(tmp_xz.read_bytes())
    tmp_xz.unlink()
    try:
        os.chmod(saida, 0o755)
    except OSError:
        pass
    print(f"[ok] {saida.name} — {saida.stat().st_size / 1048576:.1f} MB")
    return saida


def montar(formato: str = "run") -> list[Path]:
    base, v = montar_base_linux()
    saidas: list[Path] = []
    if formato in ("tarxz", "todos"):
        saidas.append(empacotar_tarxz_linux(base, v["data"]))
    if formato in ("run", "todos"):
        saidas.append(empacotar_run(base, v["data"], "_payload-tmp.tar.xz"))
    return saidas


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Monta o instalador Linux.")
    ap.add_argument("--formato", default="run",
                    choices=("run", "tarxz", "todos"))
    args = ap.parse_args(argv)
    try:
        montar(formato=args.formato)
    except SystemExit as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
