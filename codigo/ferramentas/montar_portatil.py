#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monta o HUB portátil Windows: Python embutido + tkinter + app, tudo num .zip.

    python codigo/ferramentas/montar_portatil.py [--sem-azahar]

Modelo: o .zip LEVA os emuladores instalados junto, 100% das vezes
(emuladores/Azahar/, com licença GPL (COPYING.txt), nota de fonte
(FONTE.txt) e user/ essencial: config + saves + mods LayeredFS — NUNCA
nand, sysdata com chaves, log ou shaders). Só com --sem-azahar o pacote
sai magro (net-install: o botão "Atualizar Azahar" baixa o build oficial
na primeira execução). O repo git nunca recebe binários.

Layout do portátil:
    BibliotecaHub.bat      abre a GUI sem console (pythonw)
    Debug-Console.bat      abre com console (ver erros)
    README-PORTATIL.txt
    app/                   bib_core.py, app_win.py, app_tui.py, README.md
    python/                Python embutido + tkinter transplantado
    dados/                 casa (db, backups, capas, presets, sessoes) via BIBLIOTECA_HOME

Só roda no Windows (o tkinter vem da instalação local).
"""
from __future__ import annotations

import argparse
import datetime
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = Path(__file__).resolve().parent / ".cache"
BUILD = Path(__file__).resolve().parent / ".build" / "hub"
DIST = REPO / "dist"
APP_ARQS = (("README.md", "README.md"),
             ("codigo/bib_core.py", "bib_core.py"),
             ("codigo/frontends/app_win.py", "app_win.py"),
              ("codigo/frontends/app_tui.py", "app_tui.py"),
               ("codigo/frontends/aparencia.py", "aparencia.py"),
               ("codigo/frontends/despacho.py", "despacho.py"),
               ("codigo/frontends/desktop.py", "desktop.py"),
               ("codigo/frontends/app_qt.py", "app_qt.py"),
                ("codigo/frontends/navegacao_controle.py", "navegacao_controle.py"),
                 ("codigo/frontends/qt_emulacao.py", "qt_emulacao.py"),
                ("codigo/ferramentas/__init__.py", "ferramentas/__init__.py"),
                ("codigo/ferramentas/diagnosticar.py", "ferramentas/diagnosticar.py"),
                ("codigo/ferramentas/empacotar_fontes.py", "ferramentas/empacotar_fontes.py"),
                 ("codigo/ferramentas/provar_qt_runtime.py", "provar_qt_runtime.py"),
                 ("codigo/ferramentas/provar_integracoes_locais.py", "provar_integracoes_locais.py"),
                ("codigo/ferramentas/provar_qbit_runtime.py", "provar_qbit_runtime.py"),

                 ("codigo/frontends/late.py", "late.py"),
                 ("codigo/frontends/app_win_base.py", "app_win_base.py"),
                 ("codigo/frontends/app_win_jogos.py", "app_win_jogos.py"),
                 ("codigo/frontends/app_win_musica.py", "app_win_musica.py"),
                 ("codigo/frontends/app_win_downloads.py", "app_win_downloads.py"),
                 ("codigo/frontends/app_win_desejos.py", "app_win_desejos.py"),
                 ("codigo/frontends/app_win_dialogos.py", "app_win_dialogos.py"),
                 ("codigo/frontends/app_win_scans.py", "app_win_scans.py"),
                 ("codigo/frontends/app_win_sistema.py", "app_win_sistema.py"),
                 ("codigo/frontends/app_win_midia.py", "app_win_midia.py"),
                 ("codigo/frontends/tui_base.py", "tui_base.py"),
                 ("codigo/frontends/tui_jogo.py", "tui_jogo.py"),
                 ("codigo/frontends/tui_menus.py", "tui_menus.py"),
                 ("codigo/frontends/tui_player.py", "tui_player.py"),
                 ("codigo/frontends/tui_scans.py", "tui_scans.py"))

# Pacotes-diretório do app (F2/F3 do O2): viajam como árvore, igual ao
# bib_nucleo, em vez de arquivo avulso. Novos pacotes entram aqui, não no
# APP_ARQS — os validadores expandem via arquivos_app().
APP_PACOTES = (("codigo/frontends/servicos_ui", "servicos_ui"),
               ("codigo/frontends/qt_bridge", "qt_bridge"))


def arquivos_app(repo=None):
    """Pares (origem, destino) de TODOS os arquivos do app/, expandindo pacotes."""
    repo = REPO if repo is None else Path(repo)
    for origem, destino in APP_ARQS:
        yield origem, destino
    for origem, destino in APP_PACOTES:
        base = repo / origem
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix not in (".pyc", ".pyo"):
                yield ((Path(origem) / p.relative_to(base)).as_posix(),
                       (Path(destino) / p.relative_to(base)).as_posix())

BAT_GUI = """@echo off
setlocal
set BIBLIOTECA_HOME=%~dp0
if exist "%~dp0dados\\dados\\biblioteca.db" set BIBLIOTECA_HOME=%~dp0dados
set BIBLIOTECA_AZAHAR_DIR=%~dp0emuladores\\Azahar
set BIBLIOTECA_DESMUME_DIR=%~dp0emuladores\\DeSmuME
set TCL_LIBRARY=%~dp0python\\tcl\\tcl{serie}
set TK_LIBRARY=%~dp0python\\tcl\\tk{serie}
start "BibliotecaHub" "%~dp0python\\pythonw.exe" "%~dp0app\\desktop.py" %*
"""

BAT_DEBUG = """@echo off
setlocal
set BIBLIOTECA_HOME=%~dp0
if exist "%~dp0dados\\dados\\biblioteca.db" set BIBLIOTECA_HOME=%~dp0dados
set BIBLIOTECA_AZAHAR_DIR=%~dp0emuladores\\Azahar
set BIBLIOTECA_DESMUME_DIR=%~dp0emuladores\\DeSmuME
set TCL_LIBRARY=%~dp0python\\tcl\\tcl{serie}
set TK_LIBRARY=%~dp0python\\tcl\\tk{serie}
"%~dp0python\\python.exe" "%~dp0app\\desktop.py" %*
if errorlevel 1 pause
"""

BAT_ATALHO = """@echo off
setlocal
set HUB=%~dp0
set HUB=%HUB:~0,-1%
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w = New-Object -ComObject WScript.Shell; $a = $w.CreateShortcut($env:USERPROFILE + '\\Desktop\\TucoTeca.lnk'); $a.TargetPath = '%HUB%\\TucoTeca.bat'; $a.WorkingDirectory = '%HUB%'; $a.WindowStyle = 7; $a.Description = 'TucoTeca (portatil)'; $a.Save()"
echo Atalho criado na Area de Trabalho.
pause
"""

LEIAME_PORTATIL = """TUCOTECA (portatil Windows) — sem instalar nada.

COMO USAR
1. Extraia esta pasta onde quiser (inclusive pendrive).
2. Duplo-clique em TucoTeca.bat (sem janela preta) ou rode
   Criar-Atalho.bat uma vez para ganhar um atalho na Area de Trabalho.
   BibliotecaHub.bat continua funcionando como alias legado.
3. O Azahar ja vem junto (emuladores/Azahar/, com seus mods e saves).
   Pacote magro (--sem-azahar)? Sidebar BANCO > "Atualizar Azahar".

ONDE FICA O QUE
- TucoTeca.bat ...... entrada principal (sem console); BibliotecaHub.bat e alias
- dados/ ........... sua casa: banco, backups, capas, presets, sessoes
- app/ ............. codigo do launcher (pode atualizar por cima)
- python/ .......... Python embutido (nao usa o do sistema)
- emuladores/ ...... Azahar + DeSmuME incluidos (pacote magro nao tem; use a seta de download)
   (DeSmuME: NDS; saves .dsv ficam ao lado das ROMs)
- Criar-Atalho.bat .. atalho na Area de Trabalho (duplo-clique, sem console)
- Debug-Console.bat  abre com janela de texto (para ver erros)
- manifesto-runtime.json  componentes, versoes, tamanhos e SHA-256

O botao "Atualizar Azahar" atualiza o emulador DENTRO do pacote.
Chaves (aes_keys.txt) nunca vem junto: dump do seu 3DS em
emuladores/Azahar/user/sysdata/ quando precisar.
Leve a pasta inteira para outra maquina, ou gere um .zip dela.
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
    # Build repetido/offline: aproveitar primeiro o par oficial já em cache.
    for tk_cache in sorted(CACHE.glob(f"tk-{tagbase}-*.tar.gz"), reverse=True):
        tag = tk_cache.name[len("tk-"):-len(".tar.gz")]
        tcl_cache = CACHE / f"tcl-{tag}.tar.gz"
        if not tcl_cache.is_file():
            continue
        try:
            _extrair_lib(tcl_cache, "library/init.tcl", tcl_dir / f"tcl{serie}")
            _extrair_lib(tk_cache, "library/tk.tcl", tcl_dir / f"tk{serie}")
            print(f"[cache] scripts Tcl/Tk {tag}")
            return serie
        except (OSError, ValueError, LookupError):
            continue
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


AZAHAR_USER_INCLUIR = ("config", "cheats", "sdmc", "states", "load")
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


DESMUME_URL = "https://github.com/TASEmulators/desmume"

def incluir_desmume(dest_base: Path) -> str:
    """Copia o DeSmuME instalado p/ emuladores/DeSmuME. Retorna a versão."""
    src = desmume_instalado_dir()
    dst = dest_base / "emuladores" / "DeSmuME"
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for item in sorted(src.iterdir()):
        if item.name == "user" or item.suffix.lower() in (".bak", ".log"):
            continue  # DeSmuME não tem user/; config vai ao lado do exe
        if item.is_dir():
            shutil.copytree(item, dst / item.name)
        else:
            shutil.copy2(item, dst / item.name)
    for cfg in ("desmume.ini",):
        s = src / cfg
        if s.is_file():
            shutil.copy2(s, dst / cfg)
    ver = ""
    varq = src / "desmume-versao.txt"
    if varq.is_file():
        try:
            ver = varq.read_text(encoding="utf-8", errors="ignore").strip()
        except OSError:
            pass
    (dst / "FONTE.txt").write_text(
        "DeSmuME \u2014 emulador de Nintendo DS (terceiros, sem modifica\u00e7\u00e3o).\n"
        f"Vers\u00e3o empacotada: {ver or 'desconhecida'}\n"
        f"Fonte: {DESMUME_URL} (c\u00f3digo-fonte e releases oficiais)\n"
        "Licen\u00e7a: GPL-2.0 (texto em COPYING.txt).\n"
        "\n"
        "Agrega\u00e7\u00e3o como no Azahar: o launcher apenas EXECUTA o\n"
        "emulador como processo filho. Saves .dsv ficam ao lado das ROMs.\n",
        encoding="utf-8")
    shutil.copy2(garantir_gpl(), dst / "COPYING.txt")
    mb = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file()) / 1048576
    print(f"[ok] DeSmuME {ver or '?'} embutido ({mb:.0f} MB)")
    return ver


def desmume_instalado_dir() -> Path:
    """Usa os mesmos overrides/raízes do app para o bundle Windows."""
    sys.path.insert(0, str(REPO / "codigo"))
    from bib_nucleo.emuladores import default_emu_nds
    exe = default_emu_nds()
    if exe and Path(exe).is_file():
        return Path(exe).parent
    raise SystemExit("DeSmuME instalado não achado (instale com o botão ⬇ primeiro).")


def copiar_app(app_dir: Path, repo: Path | None = None) -> None:
    """Layout único app/ para os três builders; inclui helpers dos frontends."""
    repo = REPO if repo is None else Path(repo)
    app_dir.mkdir(parents=True, exist_ok=True)
    for origem, destino in APP_ARQS:
        src = repo / origem
        if not src.is_file():
            raise SystemExit(f"arquivo do app ausente no repo: {origem}")
        alvo = app_dir / destino
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, alvo)
    for origem, destino in APP_PACOTES:
        src = repo / origem
        if not (src / "__init__.py").is_file():
            raise SystemExit(f"pacote do app ausente no repo: {origem}")
        shutil.copytree(src, app_dir / destino,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
                        dirs_exist_ok=True)
    nucleo = repo / "codigo" / "bib_nucleo"
    if not (nucleo / "__init__.py").is_file():
        raise SystemExit("pacote bib_nucleo ausente no repo.")
    shutil.copytree(nucleo, app_dir / "bib_nucleo",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
                    dirs_exist_ok=True)
    shutil.copytree(repo / "codigo/frontends/qml", app_dir / "qml", dirs_exist_ok=True)


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
            shutil.rmtree(u_dst / "load" / "textures", ignore_errors=True)
            # texturas HD (GBs) não viajam no instalador — mesmo trato dos
            # mods: ficam na máquina, fora do pacote portátil.
            for sub in ("sdmc", "states", "cheats"):
                (u_dst / sub).mkdir(parents=True, exist_ok=True)
            continue
        if item.suffix.lower() == ".appimage":
            continue  # AppImage é do Linux; portátil é só Windows
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
    print(f"[ok] Azahar {ver or '?'} embutido ({mb:.0f} MB; user/ só config+saves+mods)")
    return ver


def podar_dieta(build: Path) -> int:
    """Remove gordura do BUILD (__pycache__, *.pyc). Retorna bytes livres."""
    livres = 0
    for pycache in sorted(build.rglob("__pycache__")):
        try:
            livres += sum(f.stat().st_size for f in pycache.rglob("*")
                          if f.is_file())
            shutil.rmtree(pycache)
        except OSError:
            pass
    for pyc in sorted(p for p in build.rglob("*") if p.suffix.lower() in (".pyc", ".pyo")):
        try:
            livres += pyc.stat().st_size
            pyc.unlink()
        except OSError:
            pass
    if livres:
        print(f"[ok] dieta: {livres / 1048576:.1f} MB podados")
    return livres


def empacotar_zip(build: Path, sufixo: str = "") -> Path:
    """Portátil .zip clássico (ZIP_DEFLATED: abre em qualquer lugar)."""
    DIST.mkdir(parents=True, exist_ok=True)
    hoje = datetime.date.today().strftime("%Y%m%d")
    saida = DIST / f"tucoteca-portatil-{hoje}{sufixo}.zip"
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        for arq in sorted(build.rglob("*")):
            z.write(arq, arq.relative_to(build))
    print(f"[ok] {saida.name} — {saida.stat().st_size / 1048576:.1f} MB")
    return saida


def empacotar_tarxz(build: Path, nome: str) -> Path:
    """Payload .tar.xz (LZMA2 stdlib): base dos instaladores Win/Linux.

    tar.xz abre nativo no Linux (tar -xJf), no Windows (7-Zip) e no
    Mac (tar) — ~30-40% menor que o .zip com o mesmo conteúdo.
    """
    import tarfile
    DIST.mkdir(parents=True, exist_ok=True)
    saida = DIST / nome
    with tarfile.open(saida, "w:xz", preset=6, format=tarfile.PAX_FORMAT) as t:
        for arq in sorted(build.rglob("*")):
            t.add(arq, arq.relative_to(build), recursive=False)
    print(f"[ok] {saida.name} — {saida.stat().st_size / 1048576:.1f} MB")
    return saida


def _achar_iscc() -> str:
    env = (os.environ.get("ISCC_EXE") or "").strip()
    if env and Path(env).is_file():
        return env
    exe = shutil.which("iscc")
    if exe:
        return exe
    for cand in (Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
                 Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe"):
        if cand.is_file():
            return str(cand)
    raise SystemExit("ISCC.exe não achado — instale o Inno Setup 6 "
                     "(https://jrsoftware.org/isinfo.php) e rode de novo.")


def compilar_setup(iss: Path, build: Path, versao: str) -> Path:
    """Compila instalador.iss contra o BUILD. Retorna o Setup.exe."""
    iscc = _achar_iscc()
    DIST.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [iscc, f'/DBuildDir={build}', f'/DVersao={versao}',
         f'/O{ DIST}', str(iss)],
        capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise SystemExit(f"Inno falhou:\n{(r.stdout or '')[-1500:]}"
                         f"\n{(r.stderr or '')[-1500:]}")
    exes = sorted(DIST.glob("TucoTeca-Setup-*.exe"))
    if not exes:
        raise SystemExit("iscc rodou mas não gerou o Setup.exe.")
    print(f"[ok] {exes[-1].name} — {exes[-1].stat().st_size / 1048576:.1f} MB")
    return exes[-1]


def montar_base(sem_azahar: bool = False) -> tuple[Path, dict]:
    """Monta a árvore BUILD (portátil) e retorna (pasta, versões).

    As provas reais (tkinter no embutido + selftest + overrides) rodam
    aqui — todo empacotamento posterior (zip, tar.xz, setup) reaproveita.
    """
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

    copiar_app(app_dir, repo=REPO)
    (BUILD / "BibliotecaHub.bat").write_text(BAT_GUI.format(serie=serie), encoding="utf-8")
    (BUILD / "TucoTeca.bat").write_text(BAT_GUI.format(serie=serie), encoding="utf-8")
    (BUILD / "Debug-Console.bat").write_text(BAT_DEBUG.format(serie=serie), encoding="utf-8")
    (BUILD / "Criar-Atalho.bat").write_text(BAT_ATALHO, encoding="utf-8")
    (BUILD / "README-PORTATIL.txt").write_text(LEIAME_PORTATIL, encoding="utf-8")
    for sub in ("dados", "dados/backups", "dados/capas", "dados/presets", "dados/sessoes"):
        (BUILD / sub).mkdir(parents=True, exist_ok=True)
    azahar_ver = desmume_ver = ""
    if not sem_azahar:
        azahar_ver = incluir_azahar(BUILD)
        desmume_ver = incluir_desmume(BUILD)
    else:
        print("[aviso] pacote magro, sem emulador (--sem-azahar)")
    (BUILD / "VERSAO.txt").write_text(
        "TucoTeca — build " + datetime.date.today().strftime("%Y-%m-%d") + "\n"
        + "Python embutido: " + versao + "\n"
        + "Azahar: " + (azahar_ver or "ausente (--sem-azahar)") + "\n"
        + "DeSmuME: " + (desmume_ver or "ausente (--sem-azahar)") + "\n",
        encoding="utf-8")

    # prova real: o python embutido importa tkinter e monta a UI oculta
    py = py_dir / "python.exe"
    env = dict(os.environ)
    prova_contexto = tempfile.TemporaryDirectory(prefix="hub-prova-", dir=CACHE)
    prova_home = Path(prova_contexto.name)
    env["BIBLIOTECA_HOME"] = str(prova_home)
    env["TCL_LIBRARY"] = str(py_dir / "tcl" / f"tcl{serie}")
    env["TK_LIBRARY"] = str(py_dir / "tcl" / f"tk{serie}")
    r = subprocess.run([str(py), "-B", "-c",
                        "import tkinter; print('tk', tkinter.TkVersion)"],
                        capture_output=True, text=True, timeout=60, env=env)
    if r.returncode != 0:
        raise SystemExit(f"tkinter não subiu no embutido:\n{r.stderr[-2000:]}")
    print(f"[ok] {r.stdout.strip()} no Python embutido")
    r = subprocess.run([str(py), "-B", str(app_dir / "app_win.py"), "--selftest"],
                       capture_output=True, text=True, timeout=120, env=env)
    if r.returncode != 0 or "[ok] selftest" not in r.stdout:
        raise SystemExit(f"selftest falhou no portátil:\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    print(f"[ok] {r.stdout.strip()} (casa de prova: {prova_home.name}/)")
    if not (app_dir / "bib_nucleo" / "__init__.py").is_file():
        raise SystemExit("app/ sem bib_nucleo (shim bib_core.py não resolve).")
    print("[ok] app/ com bib_nucleo + shim bib_core.py")
    if not sem_azahar:
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
        dm = BUILD / "emuladores" / "DeSmuME"
        if not (dm / "desmume.exe").is_file() \
                or not (dm / "COPYING.txt").is_file() \
                or not (dm / "FONTE.txt").is_file():
            raise SystemExit("bundle incompleto: DeSmuME (exe/COPYING/FONTE).")
        print("[ok] bundle com DeSmuME + COPYING + FONTE")
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
        env2["BIBLIOTECA_DESMUME_DIR"] = str(BUILD / "emuladores" / "DeSmuME")
        env2.pop("BIBLIOTECA_EMULADOR_NDS", None)
        r = subprocess.run(
            [str(py), "-c",
             f"import sys; sys.path.insert(0, {str(app_dir)!r}); "
              "import bib_core as c; print(c.default_emu_nds())"],
            capture_output=True, text=True, timeout=60, env=env2)
        alvo_dm = str(BUILD / "emuladores" / "DeSmuME" / "desmume.exe")
        if r.returncode != 0 or alvo_dm not in (r.stdout or ""):
            raise SystemExit(f"override NDS não resolve:\n{r.stdout[-800:]}\n{r.stderr[-800:]}")
        print("[ok] BIBLIOTECA_DESMUME_DIR resolve o embutido")

    podar_dieta(BUILD)
    versoes = {"python": versao, "serie_tk": serie, "azahar": azahar_ver,
               "desmume": desmume_ver,
               "data": datetime.date.today().strftime("%Y%m%d"),
               "magro": sem_azahar}
    return BUILD, versoes


def montar(sem_azahar: bool = False, formato: str = "zip",
           setup: bool = False) -> list[Path]:
    """Compat + fluxo novo: monta a base e empacota. Retorna artefatos."""
    BUILD, v = montar_base(sem_azahar=sem_azahar)
    sufixo = "-slim" if v["magro"] else ""
    saidas: list[Path] = []
    if formato in ("zip", "todos"):
        saidas.append(empacotar_zip(BUILD, sufixo))
    if formato in ("tarxz", "todos"):
        saidas.append(empacotar_tarxz(
            BUILD, f"tucoteca-payload-{v['data']}{sufixo}.tar.xz"))
    if setup:
        iss = Path(__file__).resolve().parent / "instalador.iss"
        if not iss.is_file():
            raise SystemExit("instalador.iss sumiu de ferramentas/.")
        saidas.append(compilar_setup(iss, BUILD, v["data"] + sufixo))
    return saidas


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Monta o HUB portátil Windows.")
    ap.add_argument("--sem-azahar", action="store_true",
                    help="pacote magro sem emulador (só p/ iteração rápida)")
    ap.add_argument("--formato", default="zip", choices=("zip", "tarxz", "todos"),
                    help="empacotamento (padrão: zip)")
    ap.add_argument("--setup", action="store_true",
                    help="compila o instalador Windows (precisa do Inno Setup 6)")
    args = ap.parse_args(argv)
    try:
        montar(sem_azahar=args.sem_azahar, formato=args.formato, setup=args.setup)
    except SystemExit as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
