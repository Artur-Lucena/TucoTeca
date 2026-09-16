#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monta o HUB portátil Windows: Python embutido + tkinter + app, tudo num .zip.

    python ferramentas/montar_portatil.py [--só-verificar]

Modelo: por padrão o .zip NÃO leva emulador (net-install: o botão
"Atualizar Azahar" baixa o build oficial na primeira execução). Com
--com-azahar, o Azahar instalado é copiado para dentro do pacote
(emuladores/Azahar/), com licença GPL (COPYING.txt), nota de fonte
(FONTE.txt) e esqueleto de user/ (config + saves; NUNCA nand, sysdata
com chaves, log ou shaders). O repo git nunca recebe binários.

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
set BIBLIOTECA_AZAHAR_DIR=%~dp0emuladores\\Azahar
set TCL_LIBRARY=%~dp0python\\tcl\\tcl{serie}
set TK_LIBRARY=%~dp0python\\tcl\\tk{serie}
start "BibliotecaHub" "%~dp0python\\pythonw.exe" "%~dp0app\\app_win.py"
"""

BAT_DEBUG = """@echo off
setlocal
set BIBLIOTECA_HOME=%~dp0dados
set BIBLIOTECA_AZAHAR_DIR=%~dp0emuladores\\Azahar
set TCL_LIBRARY=%~dp0python\\tcl\\tcl{serie}
set TK_LIBRARY=%~dp0python\\tcl\\tk{serie}
"%~dp0python\\python.exe" "%~dp0app\\app_win.py" %*
if errorlevel 1 pause
"""

LEIAME_PORTATIL = """BIBLIOTECA HUB (portátil Windows) — sem instalar nada.

COMO USAR
1. Extraia esta pasta onde quiser (inclusive pendrive).
2. Duplo-clique em BibliotecaHub.bat.
3. Sem emulador junto? Sidebar BANCO > "Atualizar Azahar" (~60 MB, build
   oficial). Com emulador junto (emuladores/Azahar/): já sai jogando.

ONDE FICA O QUÊ
- dados/ ........... sua casa: banco, backups, capas, presets
- app/ ............. código do launcher (pode atualizar por cima)
- python/ .......... Python embutido (não usa o do sistema)
- emuladores/ ...... Azahar incluído, se o pacote veio --com-azahar
- Debug-Console.bat  abre com janela de texto (para ver erros)

O botão "Atualizar Azahar" atualiza o emulador DENTRO do pacote.
Chaves (aes_keys.txt) nunca vêm junto: dump do seu 3DS em
emuladores/Azahar/user/sysdata/ quando precisar.
Leve a pasta inteira para outra máquina, ou gere um .zip dela.
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


AZAHAR_USER_INCLUIR = ("config", "cheats", "sdmc", "states")
AZAHAR_USER_EXCLUIR = ("nand", "sysdata", "log", "shaders")
GPL_URL = "https://www.gnu.org/licenses/gpl-2.0.txt"
AZAHAR_URL = "https://github.com/azahar-emu/azahar"


def azahar_instalado_dir() -> Path:
    """De onde copiar o Azahar (instalação real; nunca o bundle)."""
    env = (os.environ.get("BIBLIOTECA_EMULADOR_3DS") or "").strip()
    if env and Path(env).is_file():
        return Path(env).parent
    if os.name == "nt":
        cand = Path("D:/Games/Emuladores/Azahar")
        if (cand / "azahar.exe").is_file():
            return cand
    else:
        cand = Path("/run/media/tuco/Games/Games/Emuladores/Azahar")
        if list(cand.glob("azahar*.AppImage")):
            return cand
    raise SystemExit("Azahar instalado não achado (instale com o botão ⬇ primeiro).")


def garantir_gpl() -> Path:
    """Texto da GPL-2.0 (acompanha o binário redistribuído)."""
    dest = CACHE / "gpl-2.0.txt"
    if dest.is_file() and dest.stat().st_size > 10_000:
        return dest
    try:
        req = urllib.request.Request(GPL_URL, headers={"User-Agent": "biblioteca-hub"})
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f, 1024 * 64)
    except Exception as e:
        raise SystemExit(f"sem a GPL-2.0 não dá p/ redistribuir: {e}")
    if dest.stat().st_size < 10_000:
        raise SystemExit("GPL-2.0 baixada veio curta demais.")
    return dest


def incluir_azahar(dest_base: Path) -> str:
    """Copia o Azahar instalado p/ emuladores/Azahar. Retorna a versão."""
    src = azahar_instalado_dir()
    dst = dest_base / "emuladores" / "Azahar"
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for item in sorted(src.iterdir()):
        if item.name == "user":
            u_dst = dst / "user"
            u_dst.mkdir()
            src_user = src / "user"
            for sub in AZAHAR_USER_INCLUIR:
                s = src_user / sub
                if s.is_dir():
                    shutil.copytree(s, u_dst / sub)
            for sub in ("sdmc", "states", "cheats"):
                (u_dst / sub).mkdir(parents=True, exist_ok=True)
            continue
        if item.is_dir():
            shutil.copytree(item, dst / item.name)
        else:
            shutil.copy2(item, dst / item.name)
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
        "Licença: GPL-2.0-or-later (texto em COPYING.txt).\n"
        "\n"
        "Este pacote agrega dois programas SEPARADOS: o launcher próprio\n"
        "(código neste repo) e o Azahar. O launcher apenas EXECUTA o\n"
        "emulador como processo filho (mere aggregation).\n"
        "\n"
        "NÃO acompanha: chaves (aes_keys.txt), sysdata da NAND, shaders ou\n"
        "log — dump pessoal e intransferível. ROMs criptografadas exigem as\n"
        "SUAS chaves (GodMode9) em emuladores/Azahar/user/sysdata/.\n",
        encoding="utf-8")
    shutil.copy2(garantir_gpl(), dst / "COPYING.txt")
    mb = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file()) / 1048576
    print(f"[ok] Azahar {ver or '?'} embutido ({mb:.0f} MB; user/ só config+saves)")
    return ver


def montar(com_azahar: bool = False) -> Path:
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
    if com_azahar:
        incluir_azahar(BUILD)

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
    if com_azahar:
        az = BUILD / "emuladores" / "Azahar" / (
            "azahar.exe" if os.name == "nt" else "azahar.AppImage")
        exe_ok = az.is_file() if os.name == "nt" else bool(
            list((BUILD / "emuladores" / "Azahar").glob("azahar*.AppImage")))
        if not exe_ok or not (BUILD / "emuladores" / "Azahar" / "COPYING.txt").is_file() \
                or not (BUILD / "emuladores" / "Azahar" / "FONTE.txt").is_file():
            raise SystemExit("bundle --com-azahar incompleto (exe/COPYING/FONTE).")
        if (BUILD / "emuladores" / "Azahar" / "user" / "nand").exists():
            raise SystemExit("nand vazou para o bundle!")
        print("[ok] bundle com Azahar + COPYING + FONTE, sem nand")
        env2 = dict(env)
        env2.pop("BIBLIOTECA_EMULADOR_3DS", None)  # override perde p/ exe explícito
        env2["BIBLIOTECA_AZAHAR_DIR"] = str(BUILD / "emuladores" / "Azahar")
        r = subprocess.run(
            [str(py), "-c",
             f"import sys; sys.path.insert(0, {str(app_dir)!r}); "
             "import bib_core as c; print(c.default_emu_3ds())"],
            capture_output=True, text=True, timeout=60, env=env2)
        alvo = str(BUILD / "emuladores" / "Azahar" / "azahar.exe")
        if r.returncode != 0 or alvo not in (r.stdout or ""):
            raise SystemExit(f"override não resolve o embutido:\n{r.stdout[-800:]}\n{r.stderr[-800:]}")
        print("[ok] BIBLIOTECA_AZAHAR_DIR resolve o embutido")

    DIST.mkdir(parents=True, exist_ok=True)
    hoje = datetime.date.today().strftime("%Y%m%d")
    sufixo = "-com-azahar" if com_azahar else ""
    saida = DIST / f"BibliotecaHub-portatil-{hoje}{sufixo}.zip"
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        for arq in sorted(BUILD.rglob("*")):
            z.write(arq, arq.relative_to(BUILD))
    mb = saida.stat().st_size / 1048576
    print(f"[ok] {saida.name} — {mb:.1f} MB")
    return saida


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Monta o HUB portátil Windows.")
    ap.add_argument("--com-azahar", action="store_true",
                    help="embute o Azahar instalado (GPL: leva COPYING+FONTE)")
    args = ap.parse_args(argv)
    try:
        montar(com_azahar=args.com_azahar)
    except SystemExit as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
