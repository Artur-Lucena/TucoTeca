#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monta o HUB portátil Windows: Python embutido + tkinter + app, tudo num .zip.

    python ferramentas/montar_portatil.py [--só-verificar]

Modelo net-install de propósito: o .zip NÃO leva emulador (binário GPL de
terceiros + chaves/sysdata que são dump pessoal e intransferíveis). Na
primeira execução, o botão "Atualizar Azahar" baixa o build oficial.

Layout do portátil:
    BibliotecaHub.bat      abre a GUI sem console (pythonw)
    Debug-Console.bat      abre com console (ver erros)
    README-PORTATIL.txt
    app/                   bib_core.py, app_win.py, app_tui.py, README.md
    python/                Python embutido + tkinter transplantado
    dados/                 casa (db, backups, capas, presets) via BIBLIOTECA_HOME

Só roda no Windows (o tkinter vem da instalação local).
"""
from __future__ import annotations

import argparse
import datetime
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CACHE = Path(__file__).resolve().parent / ".cache"
BUILD = Path(__file__).resolve().parent / ".build" / "hub"
DIST = REPO / "dist"
APP_ARQS = ("bib_core.py", "app_win.py", "app_tui.py", "README.md")

BAT_GUI = """@echo off
setlocal
set BIBLIOTECA_HOME=%~dp0dados
set TCL_LIBRARY=%~dp0python\\tcl\\tcl{serie}
set TK_LIBRARY=%~dp0python\\tcl\\tk{serie}
start "BibliotecaHub" "%~dp0python\\pythonw.exe" "%~dp0app\\app_win.py"
"""

BAT_DEBUG = """@echo off
setlocal
set BIBLIOTECA_HOME=%~dp0dados
set TCL_LIBRARY=%~dp0python\\tcl\\tcl{serie}
set TK_LIBRARY=%~dp0python\\tcl\\tk{serie}
"%~dp0python\\python.exe" "%~dp0app\\app_win.py" %*
if errorlevel 1 pause
"""

LEIAME_PORTATIL = """BIBLIOTECA HUB (portátil Windows) — sem instalar nada.

COMO USAR
1. Extraia esta pasta onde quiser (inclusive pendrive).
2. Duplo-clique em BibliotecaHub.bat.
3. Na primeira vez: sidebar BANCO > "Atualizar Azahar" (~60 MB, build
   oficial) e configure as chaves do seu próprio 3DS no emulador.

ONDE FICA O QUÊ
- dados/ ........... sua casa: banco, backups, capas, presets
- app/ ............. código do launcher (pode atualizar por cima)
- python/ .......... Python embutido (não usa o do sistema)
- Debug-Console.bat  abre com janela de texto (para ver erros)

Leve a pasta inteira para outra máquina, ou gere um .zip dela.
Emuladores e saves do Azahar ficam em dados/ se BIBLIOTECA_HOME apontar
para cá — por padrão o Azahar usa Games/Emuladores/Azahar na partilha.
"""


def baixar(url: str, destino: Path, minimo: int = 10_000_000) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.is_file() and destino.stat().st_size > minimo:
        print(f"[cache] {destino.name} ({destino.stat().st_size // 1048576} MB)")
        return
    print(f"[baixar] {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "biblioteca-hub"})
    with urllib.request.urlopen(req, timeout=120) as r, open(destino, "wb") as f:
        shutil.copyfileobj(r, f, 1024 * 256)
    print(f"[ok] {destino.stat().st_size // 1048576} MB")


def transplantar_tkinter(py_dir: Path) -> None:
    """Copia _tkinter + DLLs Tcl/Tk da instalação local p/ o Python embutido.

    (Os scripts tcl/tk vêm do fonte oficial em garantir_tcl_scripts, pois
    esta instalação embute o Tcl em zipfs — não há pasta tcl/ para copiar.)
    """
    base = Path(sys.base_prefix)
    pyd = base / "DLLs" / "_tkinter.pyd"
    if not pyd.is_file():
        raise SystemExit("esta instalação não tem _tkinter (reinstale o Python com Tcl/Tk).")
    shutil.copy2(pyd, py_dir / "_tkinter.pyd")
    dlls = sorted((base / "DLLs").glob("tcl*.dll")) + sorted((base / "DLLs").glob("tk*.dll"))
    if not dlls:
        raise SystemExit("DLLs tcl/tk não achadas em DLLs/.")
    for d in dlls:
        shutil.copy2(d, py_dir / d.name)
    # Tcl 9 linka dinâmico: bignum (tommath) + zipfs (zlib). Sem elas,
    # _tkinter falha com "módulo especificado não encontrado".
    extras = sorted((base / "DLLs").glob("libtommath*.dll")) \
        + sorted((base / "DLLs").glob("zlib*.dll"))
    for d in extras:
        shutil.copy2(d, py_dir / d.name)
    tk_src = base / "Lib" / "tkinter"
    if not (tk_src / "__init__.py").is_file():
        raise SystemExit("Lib/tkinter ausente na instalação.")
    shutil.copytree(tk_src, py_dir / "Lib" / "tkinter", dirs_exist_ok=True)
    print(f"[ok] tkinter: {pyd.name} + {len(dlls)} dll(s) tcl/tk "
          f"+ {len(extras)} dep(s) + Lib/tkinter")


def _extrair_lib(tgz: Path, marcador: str, destino: Path) -> None:
    """Extrai só */library/** do tarball fossil (trava anti-traversal)."""
    import tarfile
    achou = False
    with tarfile.open(tgz, "r:gz") as t:
        for m in t.getmembers():
            nome = m.name.replace("\\", "/")
            if ".." in nome.split("/") or nome.startswith("/"):
                continue
            if nome.split("/")[-1] == "license.terms" and nome.count("/") == 1:
                (destino.parent / f"LICENSE-{destino.name}.txt").write_bytes(
                    t.extractfile(m).read())
                continue
            idx = nome.find("/library/")
            if idx < 0:
                continue
            rel = nome[idx + len("/library/"):]
            if not rel:
                continue
            dest = destino / rel
            if m.isdir():
                dest.mkdir(parents=True, exist_ok=True)
            elif m.isfile():
                dest.parent.mkdir(parents=True, exist_ok=True)
                with t.extractfile(m) as fh:
                    dest.write_bytes(fh.read())
                achou = True
    if not achou:
        raise LookupError(f"sem {marcador} em {tgz.name}")


def garantir_tcl_scripts(py_dir: Path) -> str:
    """Scripts Tcl/Tk (BSD) do fonte oficial (fossil core.tcl-lang.org).

    Mesmo minor das DLLs locais; scripts valem dentro do minor, então tenta
    os patches do mais novo ao .0. Retorna a série ("9.0").
    """
    import re
    dll = next((Path(sys.base_prefix) / "DLLs").glob("tcl*.dll"), None)
    m = re.search(r"tcl(\d)(\d+)", dll.stem) if dll else None
    if not m:
        raise SystemExit("não deu p/ ler a versão do Tcl local.")
    serie = f"{m.group(1)}.{m.group(2)}"  # ex.: 9.0
    tagbase = f"core-{serie.replace('.', '-')}"  # ex.: core-9-0
    tcl_dir = py_dir / "tcl"
    for pt in ("9", "8", "7", "6", "5", "4", "3", "2", "1", "0"):
        tag = f"{tagbase}-{pt}"
        try:
            for proj, marcador, pasta in (
                    ("tcl", "library/init.tcl", f"tcl{serie}"),
                    ("tk", "library/tk.tcl", f"tk{serie}")):
                tgz = CACHE / f"{proj}-{tag}.tar.gz"
                baixar(f"https://core.tcl-lang.org/{proj}/tarball/{tag}/{proj}.tar.gz",
                       tgz, minimo=1_000_000)
                _extrair_lib(tgz, marcador, tcl_dir / pasta)
            if ((tcl_dir / f"tcl{serie}" / "init.tcl").is_file()
                    and (tcl_dir / f"tk{serie}" / "tk.tcl").is_file()):
                print(f"[ok] scripts Tcl/Tk {tag} (fonte oficial, BSD)")
                return serie
        except Exception as e:
            print(f"[tentar outra] {tag}: {str(e)[-160:]}")
            continue
    raise SystemExit("não consegui os scripts Tcl/Tk do fonte oficial.")


def montar() -> Path:
    if os.name != "nt":
        raise SystemExit("o portátil Windows só é montado no Windows.")
    vi = sys.version_info
    versao = f"{vi.major}.{vi.minor}.{vi.micro}"
    nodot = f"{vi.major}{vi.minor}"
    url = (f"https://www.python.org/ftp/python/{versao}/"
           f"python-{versao}-embed-amd64.zip")
    print(f"[hub] Python {versao} (igual ao que monta, p/ o tkinter casar)")
    CACHE.mkdir(parents=True, exist_ok=True)
    emb = CACHE / f"python-{versao}-embed-amd64.zip"
    try:
        baixar(url, emb)
    except Exception as e:
        raise SystemExit(f"falha ao baixar o Python embutido: {e}\n"
                         f"URL tentada: {url}")

    if BUILD.exists():
        shutil.rmtree(BUILD)
    py_dir, app_dir = BUILD / "python", BUILD / "app"
    py_dir.mkdir(parents=True)
    with zipfile.ZipFile(emb) as z:
        z.extractall(py_dir)
    transplantar_tkinter(py_dir)
    serie = garantir_tcl_scripts(py_dir)
    (py_dir / f"python{nodot}._pth").write_text(
        f"python{nodot}.zip\n.\nLib\n../app\n", encoding="utf-8")

    app_dir.mkdir(parents=True)
    for nome in APP_ARQS:
        src = REPO / nome
        if not src.is_file():
            raise SystemExit(f"arquivo do app ausente no repo: {nome}")
        shutil.copy2(src, app_dir / nome)
    (BUILD / "BibliotecaHub.bat").write_text(BAT_GUI.format(serie=serie), encoding="utf-8")
    (BUILD / "Debug-Console.bat").write_text(BAT_DEBUG.format(serie=serie), encoding="utf-8")
    (BUILD / "README-PORTATIL.txt").write_text(LEIAME_PORTATIL, encoding="utf-8")
    for sub in ("dados", "dados/backups", "dados/capas", "dados/presets"):
        (BUILD / sub).mkdir(parents=True, exist_ok=True)

    # prova real: o python embutido importa tkinter e monta a UI oculta
    py = py_dir / "python.exe"
    env = dict(os.environ)
    prova_home = Path(os.environ.get("TEMP", str(CACHE))) / "hub-prova"
    if prova_home.exists():
        shutil.rmtree(prova_home)
    env["BIBLIOTECA_HOME"] = str(prova_home)
    env["TCL_LIBRARY"] = str(py_dir / "tcl" / f"tcl{serie}")
    env["TK_LIBRARY"] = str(py_dir / "tcl" / f"tk{serie}")
    r = subprocess.run([str(py), "-c",
                        "import tkinter; print('tk', tkinter.TkVersion)"],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise SystemExit(f"tkinter não subiu no embutido:\n{r.stderr[-2000:]}")
    print(f"[ok] {r.stdout.strip()} no Python embutido")
    r = subprocess.run([str(py), str(app_dir / "app_win.py"), "--selftest"],
                       capture_output=True, text=True, timeout=120, env=env)
    if r.returncode != 0 or "[ok] selftest" not in r.stdout:
        raise SystemExit(f"selftest falhou no portátil:\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    print(f"[ok] {r.stdout.strip()} (casa de prova: {prova_home.name}/)")

    DIST.mkdir(parents=True, exist_ok=True)
    hoje = datetime.date.today().strftime("%Y%m%d")
    saida = DIST / f"BibliotecaHub-portatil-{hoje}.zip"
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        for arq in sorted(BUILD.rglob("*")):
            z.write(arq, arq.relative_to(BUILD))
    mb = saida.stat().st_size / 1048576
    print(f"[ok] {saida.name} — {mb:.1f} MB")
    return saida


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Monta o HUB portátil Windows.")
    ap.parse_args(argv)
    try:
        montar()
    except SystemExit as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
