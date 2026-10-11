#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Providers, Azahar (manager/install/presets) e execução com vigia."""
from __future__ import annotations

import configparser
import datetime
import json
import os
import shlex
import shutil
import sqlite3
import subprocess
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

from bib_nucleo.base import (BACKUP_DIR, LINUX_ROOT, MAC_ROOT, PRESETS_DIR, ROM_EXTS_3DS,
                               WIN_ROOT, eh_mac, existe_aqui_ou_traduzido,
                               resolver_exe, slugify, traduzir_para_atual)
from bib_nucleo.banco import contar_por_origem
from bib_nucleo.cheats import titulo_ok


def azahar_dir_override() -> Path | None:
    """Destino explícito do portátil, inclusive antes da primeira instalação."""
    env = (os.environ.get("BIBLIOTECA_AZAHAR_DIR") or "").strip()
    if env:
        return Path(env)
    from bib_nucleo.ferramentas import emulador_local_dir
    return emulador_local_dir("Azahar")


def _app_macos(pasta: Path) -> str:
    """Binário dentro de *.app (macOS): bundle -> Contents/MacOS/<bin>.

    Ordem: nome exato do .app > prefixo do nome > maior arquivo (helpers
    tipo *-room nunca vencem um binário da família). Qualquer emulador
    (Azahar, DeSmuME) resolve pelo mesmo caminho.
    """
    try:
        if not pasta.is_dir():
            return ""
        for app in sorted(pasta.glob("*.app")):
            macos = app / "Contents" / "MacOS"
            if not macos.is_dir():
                continue
            bins = [b for b in macos.iterdir() if b.is_file()]
            if not bins:
                continue
            alvo = app.stem.lower()
            exatos = [b for b in bins if b.name.lower() == alvo]
            if exatos:
                return str(exatos[0])
            familia = [b for b in bins if b.name.lower().startswith(alvo)]
            cands = familia or bins
            try:
                return str(max(cands, key=lambda b: b.stat().st_size))
            except OSError:
                return str(cands[0])
        return ""
    except OSError:
        return ""


def default_emu_3ds() -> str:
    """Caminho do Azahar neste SO (BIBLIOTECA_EMULADOR_3DS > BIBLIOTECA_AZAHAR_DIR > padrão)."""
    env = os.environ.get("BIBLIOTECA_EMULADOR_3DS")
    if env:
        return env
    ov = azahar_dir_override()
    if ov is not None:
        if eh_mac():
            return _app_macos(ov)
        if os.name == "nt":
            cand = ov / "azahar.exe"
            return str(cand) if cand.is_file() else ""
        return _appimage_na_pasta(ov, "azahar")
    if eh_mac():
        return _app_macos(Path(MAC_ROOT) / "Games/Emuladores/Azahar")
    if os.name == "nt":
        cand = Path(WIN_ROOT) / "Games/Emuladores/Azahar/azahar.exe"
        return str(cand) if cand.is_file() else ""
    pasta = Path(LINUX_ROOT) / "Games/Emuladores/Azahar"
    if pasta.is_dir():
        return _appimage_na_pasta(pasta, "azahar")
    return ""


def azahar_user_dir(exe: str = "") -> str:
    """Pasta user do Azahar (portátil ao lado do exe vence os padrões do SO).

    No Mac, user/ mora na pasta do emulador (estilo portátil, criado pelo
    instalador) — .app não guarda estado dentro do bundle.
    """
    exe = exe or default_emu_3ds()
    if exe:
        port = Path(exe).parent / "user"
        if port.is_dir():
            return str(port)
        if eh_mac():  # .app: user/ fica ao lado do bundle (até 3 acima)
            for cima in list(Path(exe).parents[1:4]):
                port = cima / "user"
                if port.is_dir():
                    return str(port)
    if eh_mac():
        cand = Path(MAC_ROOT) / "Games/Emuladores/Azahar/user"
        if cand.is_dir():
            return str(cand)
        return ""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", "")) / "Azahar"
    else:
        base = Path.home() / ".local/share/azahar-emu"
    return str(base) if base.is_dir() else ""


def azahar_status() -> dict:
    """Saúde do Azahar sem abrir nada: instalado, user dir, configurado, chaves."""
    exe = default_emu_3ds()
    st = {"instalado": bool(exe), "exe": exe, "user_dir": "",
          "configurado": False, "chaves": False,
          "versao_local": azahar_versao_local()}
    if not exe:
        return st
    ud = azahar_user_dir(exe)
    st["user_dir"] = ud
    if ud:
        st["configurado"] = (Path(ud) / "config" / "qt-config.ini").is_file()
        st["chaves"] = (Path(ud) / "sysdata" / "aes_keys.txt").is_file()
    return st


# --------------------------------------------------------------------------
# Gerenciador do Azahar: verifica, baixa, confere sha256 e instala sozinho
# --------------------------------------------------------------------------

AZAHAR_API_LATEST = "https://api.github.com/repos/azahar-emu/azahar/releases/latest"

AZAHAR_VERSAO_ARQ = "versao-azahar.txt"


def _emu_dir() -> Path:
    ov = azahar_dir_override()
    if ov is not None:
        return ov  # bundle: atualiza o emulador dentro do pacote
    if os.name == "nt":
        return Path(WIN_ROOT) / "Games/Emuladores/Azahar"
    if eh_mac():
        return Path(MAC_ROOT) / "Games/Emuladores/Azahar"
    return Path(LINUX_ROOT) / "Games/Emuladores/Azahar"


def _asset_azahar_ok(nome: str) -> bool:
    """O asset do release serve p/ este SO? (testável sem rede)."""
    if eh_mac():
        return nome.startswith("azahar-macos-universal-") and nome.endswith(".zip")
    if os.name == "nt":
        return nome.startswith("azahar-windows-msys2-") and nome.endswith(".zip")
    return nome == "azahar.AppImage"


def azahar_versao_local() -> str:
    arq = _emu_dir() / AZAHAR_VERSAO_ARQ
    try:
        if arq.is_file():
            return arq.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return ""


def azahar_release_info(timeout: int = 25) -> dict:
    """{'tag','nome','size','sha256','url'} do asset deste SO, ou {'erro':...}."""
    try:
        from bib_nucleo.rede import abrir_rede
        with abrir_rede(AZAHAR_API_LATEST, timeout=timeout) as r:
            rel = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"erro": f"falha de rede: {type(e).__name__}: {e}"}
    tag = (rel.get("tag_name") or "").strip()
    for a in rel.get("assets", []):
        nome = a.get("name") or ""
        if _asset_azahar_ok(nome):
            digest = a.get("digest") or ""
            sha = digest.split(":", 1)[1].strip() if ":" in digest else ""
            return {"tag": tag, "nome": nome, "size": a.get("size") or 0,
                    "sha256": sha, "url": a.get("browser_download_url") or ""}
    return {"erro": "asset deste SO não encontrado no release"}


def azahar_instalar(info: dict, progresso=None) -> dict:
    """Atualiza o runtime atual com backup, diário e verificação SHA-256."""
    from bib_nucleo.atualizacao import instalar
    if eh_mac():
        return instalar(info, _emu_dir(), progresso, plataforma="darwin")
    return instalar(info, _emu_dir(), progresso)


# --------------------------------------------------------------------------
# DeSmuME (Nintendo DS): provider nº 2, mesma integração do Azahar
# --------------------------------------------------------------------------

DESMUME_API_LATEST = "https://api.github.com/repos/TASEmulators/desmume/releases/latest"
DESMUME_VERSAO_ARQ = "desmume-versao.txt"


def desmume_dir_override() -> Path | None:
    env = (os.environ.get("BIBLIOTECA_DESMUME_DIR") or "").strip()
    if env:
        return Path(env)
    from bib_nucleo.ferramentas import emulador_local_dir
    return emulador_local_dir("DeSmuME")


def desmume_dir() -> Path:
    ov = desmume_dir_override()
    if ov is not None:
        return ov
    if os.name == "nt":
        return Path(WIN_ROOT) / "Games/Emuladores/DeSmuME"
    if eh_mac():
        return Path(MAC_ROOT) / "Games/Emuladores/DeSmuME"
    return Path(LINUX_ROOT) / "Games/Emuladores/DeSmuME"


def _asset_desmume_ok(nome: str) -> bool:
    """O asset do release serve p/ este SO? (testável sem rede)."""
    if eh_mac():
        return "macos" in nome.lower() and nome.endswith(".dmg")
    if os.name == "nt":
        return "-win64.zip" in nome
    return False  # Linux: sem asset oficial (AppImage manual)


def _appimage_na_pasta(pasta: Path, prefixo: str) -> str:
    """Acha prefixo*.AppImage sem depender de caixa (ext4 é case-sensitive)."""
    try:
        if not pasta.is_dir():
            return ""
        alvos = [p for p in pasta.iterdir()
                 if p.is_file() and p.name.lower().startswith(prefixo.lower())
                 and p.name.lower().endswith(".appimage")]
        if not alvos:
            return ""
        return str(sorted(alvos, key=lambda p: p.name.lower())[-1])
    except OSError:
        return ""


def default_emu_nds() -> str:
    """Caminho do DeSmuME (BIBLIOTECA_EMULADOR_NDS > DIR > padrão)."""
    env = os.environ.get("BIBLIOTECA_EMULADOR_NDS")
    if env:
        return env
    ov = desmume_dir_override()
    if ov is not None:
        if eh_mac():
            return _app_macos(ov)
        if os.name == "nt":
            cand = ov / "desmume.exe"
            return str(cand) if cand.is_file() else ""
        return _appimage_na_pasta(ov, "desmume")
    if eh_mac():
        return _app_macos(Path(MAC_ROOT) / "Games/Emuladores/DeSmuME")
    if os.name == "nt":
        cand = Path(WIN_ROOT) / "Games/Emuladores/DeSmuME/desmume.exe"
        return str(cand) if cand.is_file() else ""
    pasta = Path(LINUX_ROOT) / "Games/Emuladores/DeSmuME"
    img = _appimage_na_pasta(pasta, "desmume")
    if img:
        return img
    # sem AppImage: aceita DeSmuME do sistema (pacote/flatpak/snap)
    # apt Ubuntu instala como `desmume-cli` em /usr/games; outros, `desmume`
    import shutil
    for cand in (shutil.which("desmume"), shutil.which("desmume-cli"),
                 "/usr/games/desmume", "/usr/games/desmume-cli",
                 str(Path.home() / ".local/share/flatpak/exports/bin/org.desmume.DeSmuME"),
                 "/var/lib/flatpak/exports/bin/org.desmume.DeSmuME",
                 "/snap/bin/desmume", "/snap/bin/desmume-emulator"):
        if cand and Path(cand).is_file():
            return cand
    return ""


def desmume_user_dir(exe: str = "") -> str:
    """DeSmuME é portátil por natureza: config (desmume.ini) mora ao lado do exe.

    No Linux com DeSmuME do sistema, a config fica em ~/.config/desmume.
    """
    exe = exe or default_emu_nds()
    if exe:
        base = Path(exe).parent
        if (base / "desmume.ini").is_file():
            return str(base)
        cfg = Path.home() / ".config" / "desmume"
        if (cfg / "desmume.ini").is_file():
            return str(cfg)
        if base.is_dir():
            return str(base)
    return ""


def desmume_versao_local() -> str:
    arq = desmume_dir() / DESMUME_VERSAO_ARQ
    try:
        if arq.is_file():
            return arq.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return ""


def desmume_release_info(timeout: int = 25) -> dict:
    """{'tag','nome','size','sha256','url'} do asset deste SO, ou {'erro':...}."""
    if os.name != "nt" and not eh_mac():
        return {"erro": ("Atualização automática do DeSmuME só no Windows e no Mac. "
                         "No Linux, baixe o AppImage manual para Games/Emuladores/DeSmuME "
                         "ou defina BIBLIOTECA_EMULADOR_NDS.")}
    try:
        from bib_nucleo.rede import abrir_rede
        with abrir_rede(DESMUME_API_LATEST, timeout=timeout) as r:
            rel = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"erro": f"falha de rede: {type(e).__name__}: {e}"}
    tag = (rel.get("tag_name") or "").strip()
    for a in rel.get("assets", []):
        nome = a.get("name") or ""
        if _asset_desmume_ok(nome):
            digest = a.get("digest") or ""
            sha = digest.split(":", 1)[1].strip() if ":" in digest else ""
            return {"tag": tag, "nome": nome, "size": a.get("size") or 0,
                    "sha256": sha, "url": a.get("browser_download_url") or ""}
    return {"erro": "asset deste SO não encontrado no release"}


def desmume_instalar(info: dict, progresso=None) -> dict:
    """Baixa e instala o DeSmuME (transacional, como Azahar)."""
    from bib_nucleo.atualizacao import instalar
    if eh_mac():
        return instalar(info, desmume_dir(), progresso, plataforma="darwin",
                        versao_nome=DESMUME_VERSAO_ARQ)
    if os.name != "nt":
        return {"ok": False, "erro": ("Instalação automática do DeSmuME só no Windows e no Mac. "
                                      "No Linux use AppImage manual.")}
    return instalar(info, desmume_dir(), progresso, exe_nomes=("DeSmuME*.exe",),
                    deps=(), renomear_exe="desmume.exe",
                    versao_nome=DESMUME_VERSAO_ARQ)


def desmume_config_atual() -> Path | None:
    ud = desmume_user_dir()
    if ud:
        cfg = Path(ud) / "desmume.ini"
        if cfg.is_file():
            return cfg
    return None


def desmume_flags() -> list[str]:
    """Flags NDS explícitas; fullscreen é padrão somente da build Windows.

    GTK/SDL do Linux e o bundle Mac não compartilham as flags da build Win.
    Sem override, esses frontends recebem apenas o caminho da ROM.
    """
    padrao = "--windowed-fullscreen" if os.name == "nt" and not eh_mac() else ""
    return shlex.split(os.environ.get("BIBLIOTECA_DESMUME_FLAGS", padrao),
                       posix=(os.name != "nt"))


def _prov_desmume() -> dict:
    from bib_nucleo.scans import icone_nds_para_png, ler_metadados_nds
    return {
        "chave": "desmume",
        "nome": "DeSmuME",
        "sistemas": ("Nintendo DS",),
        "origens": ("rom-nds",),
        "origem": "rom-nds",
        "exe": default_emu_nds,           # () -> str
        "user_dir": desmume_user_dir,     # (exe="") -> str
        "saves_subs": (),                 # .dsv mora ao lado da ROM
        "pacote_subs": (),
        "rom_exts": {".nds", ".dsi"},
        "flags": desmume_flags,           # () -> list[str]
        "aplicar_preset": lambda nome: aplicar_preset(nome, "desmume"),
        "release_info": desmume_release_info,
        "versao_local": desmume_versao_local,
        "instalar": desmume_instalar,
        "ler_metadados": ler_metadados_nds,
        "icone": icone_nds_para_png,
        "dica_instalacao": ("DeSmuME não encontrado — instale em "
                            "Games/Emuladores/DeSmuME (Win: desmume.exe, "
                            "Linux: desmume*.AppImage) ou defina BIBLIOTECA_EMULADOR_NDS."),
    }

# --------------------------------------------------------------------------
# Execução de jogos (Windows + Linux)
# --------------------------------------------------------------------------

def _eh_elevacao_necessaria(e: Exception) -> bool:
    return isinstance(e, OSError) and getattr(e, "winerror", None) == 740


def executar_elevado(executable_path: str, launch_options: str = "") -> dict:
    """Relança via UAC (ShellExecute 'runas'). Só Windows. Abre o prompt do UAC."""
    if os.name == "nt":
        import ctypes
        exe = traduzir_para_atual((executable_path or "").strip())
        p = Path(exe)
        if not p.exists():
            return {"ok": False, "erro": f"Executável não encontrado: {exe}"}
        cwd = str(p.parent) if p.parent.exists() else None
        try:
            extra = _argumentos_lancamento(launch_options)
            params = subprocess.list2cmdline(extra) or None
            from ctypes import wintypes
            shell = ctypes.WinDLL("shell32", use_last_error=True)
            shell.ShellExecuteW.argtypes = [wintypes.HWND, wintypes.LPCWSTR,
                                            wintypes.LPCWSTR, wintypes.LPCWSTR,
                                            wintypes.LPCWSTR, ctypes.c_int]
            shell.ShellExecuteW.restype = wintypes.HINSTANCE
            rc = shell.ShellExecuteW(
                None, "runas", str(p), params, cwd, 1)
            if int(rc or 0) <= 32:
                return {"ok": False, "erro": f"UAC recusou/falhou (código {int(rc or 0)})"}
            return {"ok": True, "modo": "runas-uac"}
        except Exception as e:
            return {"ok": False, "erro": f"{type(e).__name__}: {e}"}
    return {"ok": False, "erro": "elevação só existe no Windows"}


def _tem_nvidia() -> str:
    """Nome da GPU NVIDIA discreta ou ''. Só liga o PRIME+DXVK se houver."""
    import shutil
    import subprocess
    try:
        if shutil.which("nvidia-smi") is not None:
            out = subprocess.run(["nvidia-smi", "--query-gpu=name",
                                  "--format=csv,noheader"],
                                 capture_output=True, text=True, timeout=10)
            nomes = (out.stdout or "").strip().splitlines()
            if out.returncode == 0 and nomes:
                return nomes[0].strip()
    except Exception:
        pass
    try:
        if Path("/usr/share/vulkan/icd.d/nvidia_icd.json").is_file():
            return "NVIDIA"
    except OSError:
        pass
    return ""


def prefixo_wine_hub() -> str:
    """Prefixo Wine do HUB (`dados/saves/wine`); cria na primeira chamada."""
    from bib_nucleo.base import WINE_PREFIXO
    try:
        WINE_PREFIXO.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return str(WINE_PREFIXO)


def _argumentos_lancamento(opcoes: str) -> list[str]:
    extra = shlex.split(opcoes, posix=(os.name != "nt")) if opcoes.strip() else []
    if os.name == "nt":
        extra = [(a[1:-1] if len(a) >= 2 and a[0] == a[-1] and a[0] in "\"'" else a)
                 for a in extra]
    return extra


def _lancar(executable_path: str, wine_prefix: str = "", launch_options: str = "",
            elevar: bool = False) -> tuple[dict, object | None]:
    """Núcleo do lançamento. Retorna (resultado, Popen|None).

    Processo None = sem handle rastreável (startfile, UAC, erro, sem exe).
    """
    exe = (executable_path or "").strip()
    if not exe:
        return {"ok": False, "erro": "Jogo sem caminho de executável cadastrado."}, None
    if elevar:
        return executar_elevado(exe, launch_options), None
    exe = traduzir_para_atual(exe)  # gravado num SO, executando no outro
    p = Path(exe)
    if not p.exists():
        return {"ok": False, "erro": f"Executável não encontrado: {exe}"}, None

    env = os.environ.copy()
    if wine_prefix.strip():
        env["WINEPREFIX"] = wine_prefix.strip()

    # Aspas são só agrupamento p/ o split (Popen recebe lista e cita sozinho):
    # "C:\com espaco\jogo.cci" vira um arg limpo, sem aspas literais.
    try:
        extra = _argumentos_lancamento(launch_options)
        cwd = str(p.parent) if p.parent.exists() else None
        if os.name == "nt":
            ext = p.suffix.lower()
            if ext in (".lnk", ".url") or p.is_dir():
                os.startfile(str(p))  # type: ignore[attr-defined]
                return {"ok": True, "modo": "startfile"}, None
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            proc = subprocess.Popen([str(p), *extra], cwd=cwd, env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL, creationflags=creationflags,
                                    close_fds=True)
            return {"ok": True, "modo": "popen-windows"}, proc
        else:
            ext = p.suffix.lower()
            nome_so = "Mac" if eh_mac() else "Linux"
            if ext in (".lnk", ".url") or p.is_dir():
                return {"ok": False,
                        "erro": f"Atalho/pasta Windows não executa no {nome_so}: {exe}"}, None
            if ext in (".exe", ".bat", ".cmd"):
                vinho = shutil.which("wine") or shutil.which("wine64")
                if vinho:
                    if wine_prefix.strip():
                        env["WINEPREFIX"] = traduzir_para_atual(wine_prefix.strip())
                    else:
                        env["WINEPREFIX"] = prefixo_wine_hub()  # saves no HUB
                    # híbrido Intel+NVIDIA: jogo na discreta via PRIME com o
                    # DXVK filtrado para ela; sem NVIDIA, Wine decide sozinho
                    gpu = _tem_nvidia()
                    if gpu:
                        env.setdefault("__NV_PRIME_RENDER_OFFLOAD", "1")
                        env.setdefault("__GLX_VENDOR_LIBRARY_NAME", "nvidia")
                        env.setdefault("__VK_LAYER_NV_optimus", "NVIDIA_only_1")
                        env.setdefault("DXVK_FILTER_DEVICE_NAME", gpu)
                    cmd = [vinho, str(p), *extra]
                    try:
                        proc = subprocess.Popen(cmd, cwd=cwd, env=env,
                                                stdout=subprocess.DEVNULL,
                                                stderr=subprocess.DEVNULL,
                                                stdin=subprocess.DEVNULL,
                                                start_new_session=True,
                                                close_fds=True)
                    except Exception as e:
                        return {"ok": False,
                                "erro": f"{type(e).__name__}: {e}"}, None
                    return {"ok": True, "modo": "wine-linux"}, proc
                if eh_mac():
                    return {"ok": False,
                            "erro": (f"Jogo Windows não executa no Mac: {exe} "
                                     "(sem Wine no Mac; cadastre exe_mac nativo)")}, None
                return {"ok": False,
                        "erro": (f"Jogo Windows no Linux sem Wine: {exe} "
                                 "(instale o wine ou cadastre exe_linux nativo)")}, None
            if not os.access(str(p), os.X_OK):
                return {"ok": False,
                        "erro": f"Sem permissão de execução: {exe} (rode chmod +x?)"}, None
            cmd = [str(p), *extra]
            proc = subprocess.Popen(cmd, cwd=cwd, env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL, start_new_session=True,
                                    close_fds=True)
            return {"ok": True, "modo": "popen-mac" if eh_mac() else "popen-linux"}, proc
    except Exception as e:
        if _eh_elevacao_necessaria(e):
            return {"ok": False, "requer_elevacao": True,
                    "erro": f"{type(e).__name__}: {e} — o executável exige administrador."}, None
        return {"ok": False, "erro": f"{type(e).__name__}: {e}"}, None


def _lancar_jogo_dict(jogo: dict, elevar: bool = False) -> tuple[dict, object | None]:
    """Resolve o exe do SO atual (exe_win/exe_linux vencem) e lança.

    Origens com provider (ex.: rom-3ds) usam o exe e as flags do provider.
    """
    origem = (jogo.get("origem") or "")
    prov = provedor_por_origem(origem)
    exe, _origem = resolver_exe(jogo)
    if prov is not None:
        from bib_nucleo.atualizacao import recuperar
        exe_prov = prov["exe"]() or ""
        # diário do provider atual (não do Azahar fixo): update interrompido
        # de qualquer emulador bloqueia o play com erro claro
        alvo_rec = Path(exe_prov).parent if exe_prov else None
        if alvo_rec is not None:
            recuperacao = recuperar(alvo_rec)
            if not recuperacao["ok"]:
                return {"ok": False, "erro": recuperacao["erro"]}, None
    if not exe and prov is not None:
        exe = prov["exe"]() or ""  # linha sem emu (ou apagado): o instalado vale
    if not exe and prov is not None:
        return {"ok": False, "erro": prov["dica_instalacao"]}, None
    launch = (jogo.get("launch_options") or "")
    if prov is not None and launch.strip():
        launch = montar_launch_rom(prov, traduzir_para_atual(launch))
    return _lancar(exe, (jogo.get("wine_prefix") or ""), launch, elevar=elevar)


def executar_jogo_dict(jogo: dict, elevar: bool = False) -> dict:
    """Resolve o exe do SO atual (exe_win/exe_linux vencem) e executa."""
    res, _proc = _lancar_jogo_dict(jogo, elevar)
    return res


def diagnosticar_exe(jogo: dict) -> dict:
    """Para o perguntar-antes: o exe gravado existe? E o do provider atual?

    estados: 'ok' | 'sem-exe' | 'trocou-emulador' | 'ausente'.
    'trocou-emulador' = gravado sumiu mas o provider atual tem exe válido.
    """
    exe, _origem = resolver_exe(jogo)
    if not exe:
        return {"estado": "sem-exe", "gravado": "", "atual": ""}
    if existe_aqui_ou_traduzido(exe)[0]:
        return {"estado": "ok", "gravado": exe, "atual": exe}
    prov = provedor_por_origem((jogo.get("origem") or ""))
    atual = ""
    if prov is not None:
        try:
            atual = prov["exe"]() or ""
        except Exception:
            atual = ""
    if atual and Path(atual).is_file():
        return {"estado": "trocou-emulador", "gravado": exe, "atual": atual,
                "provider": prov["chave"], "nome": prov["nome"]}
    return {"estado": "ausente", "gravado": exe, "atual": ""}


def diagnosticar_rom(jogo: dict) -> dict:
    """A ROM (launch_options) existe? Se não, procura candidatas pelo nome."""
    launch = (jogo.get("launch_options") or "").strip().strip("\"'")
    if provedor_por_origem(jogo.get("origem") or "") is None:
        return {"estado": "nao-rom", "candidatos": []}
    if not launch:
        return {"estado": "nao-rom", "candidatos": []}
    if provedor_por_extensao(Path(launch).suffix) is None:
        return {"estado": "nao-rom", "candidatos": []}  # flags de PC, não arquivo
    if existe_aqui_ou_traduzido(launch)[0]:
        return {"estado": "ok", "candidatos": []}
    base = launch.replace("\\", "/").rsplit("/", 1)[-1]
    return {"estado": "rom-ausente", "candidatos": procurar_rom(base) if base else []}


def procurar_rom(nome_arquivo: str, roots: list[str] | None = None,
                 max_resultados: int = 20) -> list[str]:
    """Acha arquivos pelo nome-base nas raízes de ROMs+scan (p/ religar).

    Só leitura, com teto. Compara case-insensitive pelo nome do arquivo.
    """
    from bib_nucleo.scans import (SKIP_DIRS, default_roms_nds_roots,
                                   default_roms_roots, default_scan_roots)
    alvo = (nome_arquivo or "").strip().lower()
    if not alvo:
        return []
    if roots is None:
        vistas: list[str] = []
        for r in default_roms_roots() + default_roms_nds_roots() + default_scan_roots():
            if r not in vistas:
                vistas.append(r)
        roots = vistas
    achados: list[str] = []
    caminhos_vistos = set()
    vistos = 0
    for raiz in roots:
        rp = Path(raiz)
        if not rp.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(rp):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            try:
                if len(Path(dirpath).relative_to(rp).parts) > 6:
                    dirnames[:] = []
                    continue
            except ValueError:
                dirnames[:] = []
                continue
            for fn in filenames:
                vistos += 1
                if vistos > 30_000 or len(achados) >= max_resultados:
                    return sorted(achados)
                if fn.lower() == alvo:
                    try:
                        p = (Path(dirpath) / fn).resolve()
                    except (OSError, RuntimeError):
                        continue
                    if p not in caminhos_vistos:
                        caminhos_vistos.add(p)
                        achados.append(str(p))
    return sorted(achados)


def azahar_flags() -> list[str]:
    """Flags extras ao bootar ROM (padrão -f fullscreen; vazio desliga)."""
    return shlex.split(os.environ.get("BIBLIOTECA_AZAHAR_FLAGS", "-f"),
                       posix=(os.name != "nt"))


# --------------------------------------------------------------------------
# Sessões rastreadas: horas automáticas (mede o processo lançado)
# --------------------------------------------------------------------------

LIMIAR_SESSAO_S = 30  # sessões mais curtas não contam (clique de teste)


def _vigiar_processo(proc, limiar_s: float, ao_fim) -> None:
    t0 = time.monotonic()
    try:
        proc.wait()
    except Exception:
        pass  # processo já morreu ou handle inválido: conta o decorrido
    decorrido = time.monotonic() - t0
    sessao = round(decorrido / 3600.0, 2) if decorrido >= limiar_s else 0.0
    try:
        ao_fim(sessao, True)
    except Exception:
        pass


def executar_monitorado(jogo: dict, ao_fim=None,
                        limiar_s: float = LIMIAR_SESSAO_S) -> dict:
    """Lança e, havendo handle (Popen), vigia o fim em thread daemon.

    ao_fim(sessao_horas, rastreado) roda na thread vigia — o frontend deve
    despachar para a thread de UI. Sem handle (startfile/UAC) e com ok:
    abre sessão manual (arquivo em dados/sessoes/) e chama ao_fim(0.0, False).
    Se o launcher fechar, a sessão manual sobrevive e pode ser reconciliada.
    """
    from bib_nucleo.base import SESSOES_DIR
    res, proc = _lancar_jogo_dict(jogo)
    rastreavel = bool(res.get("ok")) and proc is not None
    res["rastreado"] = rastreavel
    if ao_fim is None:
        if bool(res.get("ok")) and not rastreavel:
            try:
                iniciar_sessao_manual(int(jogo.get("id") or 0),
                                      str(jogo.get("titulo") or ""))
            except Exception:
                pass
        return res
    if rastreavel:
        threading.Thread(target=_vigiar_processo, args=(proc, limiar_s, ao_fim),
                         daemon=True).start()
    elif res.get("ok"):
        try:
            iniciar_sessao_manual(int(jogo.get("id") or 0),
                                  str(jogo.get("titulo") or ""))
        except Exception:
            pass
        ao_fim(0.0, False)
    return res


from bib_nucleo.sessoes_manuais import (iniciar_sessao_manual, listar_sessoes_pendentes,
                                      encerrar_sessao_manual)


# --------------------------------------------------------------------------
# Provedores de emulação (HUB): um registro, N emuladores
#
# Cada provider descreve UM emulador: que origens de jogo ele atende, onde
# está o exe, onde ficam config/saves, como montar a linha de lançamento e
# como aplicar preset. Azahar é o provider nº 1; o próximo (ex.: NDS, GBA)
# entra aqui sem tocar em lançamento, pacote ou frontends.
# --------------------------------------------------------------------------

def _prov_azahar() -> dict:
    from bib_nucleo.scans import icone_rom_para_png, ler_metadados_3ds
    return {
        "chave": "azahar",
        "nome": "Azahar",
        "sistemas": ("Nintendo 3DS",),
        "origens": ("rom-3ds",),
        "origem": "rom-3ds",
        "exe": default_emu_3ds,          # () -> str
        "user_dir": azahar_user_dir,     # (exe="") -> str
        "saves_subs": ("sdmc", "states"),
        "pacote_subs": ("sdmc",),        # states travam à versão: fora do pacote
        "rom_exts": ROM_EXTS_3DS,
        "flags": azahar_flags,           # () -> list[str]
        "aplicar_preset": aplicar_preset,  # (nome) -> dict
        "ler_metadados": ler_metadados_3ds,
        "icone": icone_rom_para_png,
        "release_info": azahar_release_info,
        "versao_local": azahar_versao_local,
        "instalar": azahar_instalar,
        "dica_instalacao": ("Azahar não encontrado — instale em "
                            "Games/Emuladores/Azahar ou defina BIBLIOTECA_EMULADOR_3DS."),
    }


def provedores() -> dict:
    """chave -> spec. Construído sob demanda (as funções existem no import)."""
    return {"azahar": _prov_azahar(), "desmume": _prov_desmume()}


def provedor_por_origem(origem: str) -> dict | None:
    for prov in provedores().values():
        if (origem or "") in prov["origens"]:
            return prov
    return None


def provedor_por_extensao(ext: str) -> dict | None:
    """Provider que abre essa extensão de ROM ('.3ds' -> Azahar). None = PC."""
    ext = (ext or "").strip().lower()
    if not ext.startswith("."):
        ext = "." + ext
    for prov in provedores().values():
        if ext in prov.get("rom_exts", ()):
            return prov
    return None


def provedor_nome(jogo_ou_origem) -> str:
    """'Azahar · Nintendo 3DS' p/ ROMs; origem crua p/ jogos de PC."""
    origem = jogo_ou_origem.get("origem") if isinstance(jogo_ou_origem, dict) \
        else jogo_ou_origem
    prov = provedor_por_origem(origem or "")
    if prov is None:
        return origem or ""
    return f"{prov['nome']} · {'/'.join(prov['sistemas'])}"


def jogos_do_provedor(jogos: list[dict], chave: str) -> list[dict]:
    """Só os jogos que o provider consegue rodar (p/ filtro da UI)."""
    return [j for j in (jogos or [])
            if (provedor_por_origem(j.get("origem") or "") or {}).get("chave") == chave]


def provedores_resumo(con: sqlite3.Connection) -> list[dict]:
    """Um item por provider: chave, nome, sistemas, nº de jogos, instalado."""
    cont = contar_por_origem(con)
    out = []
    for chave, prov in provedores().items():
        n = sum(cont.get(o, 0) for o in prov["origens"])
        try:
            exe = prov["exe"]() or ""
        except Exception:
            exe = ""
        out.append({"chave": chave, "nome": prov["nome"],
                    "sistemas": prov["sistemas"], "n": n,
                    "instalado": bool(exe)})
    return out


def montar_launch_rom(prov: dict, rom_path: str) -> str:
    """flags do provider + ROM entre aspas quando tem espaço."""
    rom = (rom_path or "").strip()
    if " " in rom and not (rom.startswith('"') and rom.endswith('"')):
        rom = f'"{rom}"'
    flags = " ".join(prov["flags"]())
    return (flags + " " if flags else "") + rom


def backup_saves_emu(chave: str, manter: int = 10) -> dict:
    """Zipa as pastas de save do provider em backups/. Retorna dict (sempre)."""
    prov = provedores().get(chave)
    if prov is None:
        return {"ok": False, "erro": f"emulador '{chave}' desconhecido"}
    ud = prov["user_dir"]() or ""
    if not ud:
        return {"ok": False, "erro": f"{prov['nome']} não instalado"}
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"{chave}-saves-{ts}.zip"
    n = 0
    try:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for sub in prov["saves_subs"]:
                d = Path(ud) / sub
                if not d.is_dir():
                    continue
                for f in sorted(d.rglob("*")):
                    if f.is_file():
                        try:
                            z.write(f, f.relative_to(ud))
                            n += 1
                        except OSError:
                            pass
    except OSError as e:
        return {"ok": False, "erro": f"falha ao zipar: {e}"}
    if n == 0:
        try:
            dest.unlink()
        except OSError:
            pass
        return {"ok": False, "erro": "sem saves ainda (saves vazios ou ausentes)"}
    for padrao in (f"{chave}-saves-*.zip", "azahar-saves-*.zip"):
        arqs = sorted(BACKUP_DIR.glob(padrao), key=lambda p: p.name, reverse=True)
        for velho in arqs[manter:]:
            try:
                velho.unlink()
            except OSError:
                pass
    return {"ok": True, "arquivo": str(dest), "arquivos": n}


def backup_saves_azahar(manter: int = 10) -> dict:
    """Zipa sdmc/ + states/ do Azahar em backups/. Retorna dict (sempre)."""
    return backup_saves_emu("azahar", manter)


# --------------------------------------------------------------------------
# Presets por jogo do Azahar (mescla no qt-config.ini antes de lançar)
# --------------------------------------------------------------------------

def presets_dir() -> Path:
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    return PRESETS_DIR


def presets_prov_dir(chave: str) -> Path:
    d = presets_dir() / chave
    d.mkdir(parents=True, exist_ok=True)
    return d


def listar_presets(chave: str = "azahar") -> list[str]:
    try:
        nomes = [p.stem for p in presets_prov_dir(chave).glob("*.ini") if p.is_file()]
        if chave == "azahar":  # legado: presets/*.ini na raiz valem p/ Azahar
            nomes += [p.stem for p in presets_dir().glob("*.ini") if p.is_file()]
        return sorted(set(nomes))
    except OSError:
        return []


def azahar_config_atual() -> Path | None:
    ud = azahar_user_dir()
    if ud:
        cfgdir = Path(ud) / "config"
        cfg = cfgdir / "qt-config.ini"
        if cfg.is_file():
            return cfg
        try:
            alts = sorted(p for p in cfgdir.glob("*.ini") if p.is_file())
        except OSError:
            alts = []
        if alts:
            return alts[0]
    return None


def salvar_preset_de_atual(nome: str, chave: str = "azahar") -> dict:
    """Fotografa o ini atual como presets/<provider>/<nome>.ini."""
    cfg = config_atual_emu(chave)
    if cfg is None:
        return {"ok": False,
                "erro": f"config não encontrada (abra o {chave} uma vez)."}
    slug = slugify(nome or "")
    if not slug:
        return {"ok": False, "erro": "nome de preset vazio."}
    dest = presets_prov_dir(chave) / f"{slug}.ini"
    try:
        shutil.copy2(str(cfg), str(dest))
    except OSError as e:
        return {"ok": False, "erro": f"falha ao copiar: {e}"}
    return {"ok": True, "preset": slug, "arquivo": str(dest)}


def config_atual_emu(chave: str) -> Path | None:
    if chave == "desmume":
        return desmume_config_atual()
    return azahar_config_atual()


def _alvo_preset(nome: str, chave: str):
    base = presets_prov_dir(chave)
    alvo = base / Path(nome).name
    if not alvo.suffix:
        alvo = alvo.with_name(alvo.name + ".ini")  # aceita stem ou "x.ini"
    if chave == "azahar" and not alvo.is_file():
        leg = presets_dir() / alvo.name  # legado na raiz
        if leg.suffix.lower() == ".ini" and leg.is_file():
            alvo, base = leg, presets_dir()
    try:
        dentro = alvo.resolve().parent == base.resolve()
    except OSError:
        dentro = False
    if not dentro or alvo.suffix.lower() != ".ini" or not alvo.is_file():
        return None
    return alvo


def aplicar_preset(nome: str, chave: str = "azahar") -> dict:
    """Mescla presets/<provider>/<nome>.ini sobre o ini atual (backup .bak uma vez)."""
    nome = (nome or "").strip()
    if not nome:
        return {"ok": False, "erro": "sem preset"}
    alvo = _alvo_preset(nome, chave)
    if alvo is None:
        return {"ok": False, "erro": f"preset '{nome}' não existe."}
    cfg = config_atual_emu(chave)
    if cfg is None:
        return {"ok": False, "erro": "config do emulador não encontrada."}
    try:
        bak = cfg.with_name(cfg.name + ".bak")
        if not bak.is_file():
            shutil.copy2(str(cfg), str(bak))  # estado pré-preset, uma única vez
        atual, novo = configparser.ConfigParser(), configparser.ConfigParser()
        atual.optionxform = str  # type: ignore[assignment]  # preserva maiúsculas
        novo.optionxform = str  # type: ignore[assignment]
        atual.read(cfg, encoding="utf-8")
        novo.read(alvo, encoding="utf-8")
        for sec in novo.sections():
            if not atual.has_section(sec):
                atual.add_section(sec)
            for k, valor in novo.items(sec):
                atual.set(sec, k, valor)
        with cfg.open("w", encoding="utf-8") as fh:
            atual.write(fh)
    except (OSError, configparser.Error) as e:
        return {"ok": False, "erro": f"falha ao mesclar: {e}"}
    return {"ok": True, "preset": alvo.stem, "config": str(cfg)}


# --------------------------------------------------------------------------
# Mods do Azahar (LayeredFS): biblioteca no HUB + ativação via junction
#
# Biblioteca: dados/mods/azahar/<title-id>/<mod>/{romfs,exefs,code.ips}.
# O Azahar lê tudo em user/load/mods/<title-id>/; o play apaga só os
# links do HUB e recria os ativos (pastas reais nunca são removidas).
# --------------------------------------------------------------------------

def title_id_da_rom(rom_path: str) -> str:
    """Title ID (16 hex) lido do header NCCH; '' se ilegível."""
    rom = (rom_path or "").strip().strip("\"'")
    if not rom:
        return ""
    try:
        with Path(rom).open("rb") as f:
            head = f.read(0x200)
            if len(head) < 0x200:
                return ""
            if head[0x100:0x104] == b"NCSD":
                base = int.from_bytes(head[0x120:0x124], "little") * 0x200
                f.seek(base)
                head = f.read(0x200)
                if len(head) < 0x200:
                    return ""
            if head[0x100:0x104] != b"NCCH":
                return ""
            return head[0x118:0x120][::-1].hex().upper()
    except (OSError, ValueError):
        return ""


def mods_lib_dir() -> Path:
    from bib_nucleo.base import MODS_DIR
    d = MODS_DIR / "azahar"
    d.mkdir(parents=True, exist_ok=True)
    return d


def mods_titulo_dir(title_id: str) -> Path:
    tid = titulo_ok(title_id)
    if not tid:
        raise ValueError("title ID inválido")
    d = mods_lib_dir() / tid
    d.mkdir(parents=True, exist_ok=True)
    return d


def _k32():
    """kernel32 com assinaturas explícitas (sem elas, ctypes trunca ponteiro)."""
    import ctypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetFileAttributesW.argtypes = [ctypes.c_wchar_p]
    k32.GetFileAttributesW.restype = ctypes.c_uint32
    k32.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32,
                                ctypes.c_uint32, ctypes.c_void_p,
                                ctypes.c_uint32, ctypes.c_uint32,
                                ctypes.c_void_p]
    k32.CreateFileW.restype = ctypes.c_void_p
    k32.DeviceIoControl.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                    ctypes.c_void_p, ctypes.c_uint32,
                                    ctypes.c_void_p, ctypes.c_uint32,
                                    ctypes.POINTER(ctypes.c_ulong),
                                    ctypes.c_void_p]
    k32.DeviceIoControl.restype = ctypes.c_bool
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    k32.CloseHandle.restype = ctypes.c_bool
    return k32


def _eh_reparse(p: Path) -> bool:
    """É junction/symlink (link do HUB) e não pasta real?"""
    try:
        if os.name == "nt":
            attrs = _k32().GetFileAttributesW(str(p))
            return attrs != 0xFFFFFFFF and bool(attrs & 0x400)
        return p.is_symlink()
    except OSError:
        return False


def remover_link(link: str) -> None:
    """Remove junction/symlink sem tocar no alvo. Só age em reparse point."""
    l = Path(link)
    if _eh_reparse(l):
        try:
            if l.is_symlink():
                l.unlink()
            else:
                os.rmdir(l)  # junction NTFS
        except OSError as e:
            raise OSError(f"não removi {link}: {e}")


def _eh_mod_valido(p: Path) -> bool:
    try:
        if not p.is_dir() or _eh_reparse(p):
            return False
        return ((p / "romfs").is_dir() or (p / "exefs").is_dir()
                or (p / "code.ips").is_file())
    except OSError:
        return False


def listar_mods(title_id: str) -> list[str]:
    """Nomes dos mods na biblioteca p/ este title ID (ordenados)."""
    tid = titulo_ok(title_id)
    if not tid:
        return []
    try:
        base = mods_lib_dir() / tid
        if not base.is_dir():
            return []
        return sorted(p.name for p in base.iterdir() if _eh_mod_valido(p))
    except OSError:
        return []


def remover_mod(title_id: str, nome: str) -> dict:
    """Apaga um mod da biblioteca (só dentro dela; nunca no Azahar)."""
    tid = titulo_ok(title_id)
    if not tid:
        return {"ok": False, "erro": "title ID inválido"}
    alvo = mods_lib_dir() / tid / Path(nome or "").name
    try:
        dentro = alvo.resolve().parent == (mods_lib_dir() / tid).resolve()
    except OSError:
        dentro = False
    if not dentro or not alvo.is_dir() or _eh_reparse(alvo):
        return {"ok": False, "erro": f"mod '{nome}' não existe na biblioteca."}
    try:
        shutil.rmtree(alvo)
    except OSError as e:
        return {"ok": False, "erro": f"falha ao apagar: {e}"}
    return {"ok": True, "mod": alvo.name}


def azahar_mods_dir() -> str:
    """user/load/mods do Azahar atual ('' se emulador ausente)."""
    ud = azahar_user_dir()
    if not ud:
        return ""
    return str(Path(ud) / "load" / "mods")


def mods_ativos(jogo: dict) -> list[str]:
    from bib_nucleo.banco import mods_de
    return mods_de(jogo)


def _ler_manifesto(pasta: Path) -> dict:
    """Manifesto do HUB (.hub-mods.json): {'mods': [...], 'arquivos': [...] }."""
    import json as _json
    try:
        d = _json.loads((pasta / ".hub-mods.json").read_text(encoding="utf-8"))
        if isinstance(d, dict) and isinstance(d.get("mods"), list) \
                and isinstance(d.get("arquivos"), list):
            return {"mods": [m for m in d["mods"] if isinstance(m, str)],
                    "arquivos": [a for a in d["arquivos"] if isinstance(a, str)],
                    "fontes": d.get("fontes"), "completo": d.get("completo", False)}
    except (OSError, ValueError):
        pass
    return {"mods": [], "arquivos": [], "fontes": None, "completo": False}


def _gravar_manifesto(pasta: Path, mods: list[str], arquivos: list[str],
                     fontes=None, completo=False) -> None:
    """Grava (ou remove, se vazio) o manifesto do HUB. Nunca levanta."""
    import json as _json
    alvo = pasta / ".hub-mods.json"
    try:
        if not mods and not arquivos:
            try:
                alvo.unlink()
            except OSError:
                pass
            return
        tmp = pasta / ".hub-mods.tmp"
        tmp.write_text(_json.dumps({"mods": mods, "arquivos": arquivos,
                                   "fontes": fontes, "completo": completo},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(alvo)
    except OSError:
        pass


def _limpar_hub(pasta: Path, disponiveis: set[str]) -> list[str]:
    """Remove junctions legadas do HUB e arquivos do manifesto anterior.

    Pastas/arquivos do usuário (fora do manifesto, sem ser link com nome
    de mod da biblioteca) nunca são tocados. Retorna avisos.
    """
    avisos: list[str] = []
    mani = _ler_manifesto(pasta)
    for rel in mani["arquivos"]:
        alvo = pasta / Path(*Path(rel).parts)
        try:
            dentro = alvo.resolve().parent == pasta.resolve() \
                or pasta.resolve() in alvo.resolve().parents
        except OSError:
            dentro = False
        if not dentro or _eh_reparse(alvo):
            continue
        try:
            if alvo.is_file():
                alvo.unlink()
        except OSError as e:
            avisos.append(f"resto '{rel}' não saiu ({e})")
    try:
        for item in sorted(pasta.iterdir()):
            if item.name in (".hub-mods.json", ".hub-mods.tmp"):
                continue
            if _eh_reparse(item) and item.name in disponiveis:
                try:
                    remover_link(str(item))
                except OSError as e:
                    avisos.append(f"link antigo '{item.name}' não saiu ({e})")
                    continue
            try:
                if item.is_dir() and not any(item.iterdir()):
                    item.rmdir()  # dir vazio (sobra de link/junction): some
            except OSError:
                pass
    except OSError as e:
        avisos.append(f"limpeza incompleta ({e})")
    _gravar_manifesto(pasta, [], [])
    return avisos


def aplicar_mods(jogo: dict) -> dict:
    """Copia os mods ativos p/ load/mods/<tid>/ (flat, como o Azahar lê).

    Nunca bloqueia o play. Retorna {'aplicados': [...], 'aviso': None|str}.
    Mods empilham na ordem da lista (o último vence por arquivo). Arquivos
    do usuário fora do manifesto nunca são removidos.
    """
    from bib_nucleo.base import traduzir_para_atual
    if provedor_por_origem((jogo.get("origem") or "")) is None:
        return {"aplicados": [], "aviso": None}
    launch = ((jogo.get("launch_options") or "").strip()
              .strip("\"'"))
    if provedor_por_extensao(Path(launch).suffix) is None:
        return {"aplicados": [], "aviso": None}
    tid = title_id_da_rom(traduzir_para_atual(launch))
    if not tid:
        return {"aplicados": [], "aviso": None}
    destino = azahar_mods_dir()
    if not destino:
        return {"aplicados": [],
                "aviso": "Azahar não encontrado — mods não aplicados."}
    avisos: list[str] = []
    aplicados: list[str] = []
    try:
        pasta = Path(destino) / tid
        pasta.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return {"aplicados": [], "aviso": f"pasta de mods inacessível ({e})"}
    disponiveis = set(listar_mods(tid))
    anterior = _ler_manifesto(pasta)
    try:
        desligados = int(jogo.get("azahar_mods_off") or 0) != 0
    except (TypeError, ValueError):
        desligados = False
    pedidos = [] if desligados else [m for m in mods_ativos(jogo)]
    for nome in pedidos:
        if nome not in disponiveis:
            avisos.append(f"mod '{nome}' marcado mas fora da biblioteca")
    pedidos = [m for m in pedidos if m in disponiveis]
    fontes = []
    try:
        for nome in pedidos:
            origem = mods_lib_dir() / tid / nome
            for arq in sorted(origem.rglob("*")):
                if arq.is_file() and not _eh_reparse(arq):
                    st = arq.stat()
                    fontes.append([nome, arq.relative_to(origem).as_posix(), st.st_size, st.st_mtime_ns])
    except OSError as e:
        return {"aplicados": anterior["mods"], "aviso": f"Mods não atualizados: {e}"}
    if (pedidos and anterior["mods"] == pedidos and anterior["completo"]
            and anterior["fontes"] == fontes
            and all((pasta / a).is_file() for a in anterior["arquivos"])):
        return {"aplicados": list(pedidos), "aviso": "; ".join(avisos) or None}
    gerenciados = set(anterior["arquivos"])
    avisos += _limpar_hub(pasta, disponiveis)
    if not pedidos:
        return {"aplicados": [], "aviso": "; ".join(avisos) or None}
    arquivos: list[str] = []
    vistos: set[str] = set()
    for nome in pedidos:
        src = mods_lib_dir() / tid / nome
        try:
            for arq in sorted(src.rglob("*")):
                if not arq.is_file() or _eh_reparse(arq):
                    continue
                try:
                    rel = arq.relative_to(src).as_posix()
                except ValueError:
                    continue
                dest = pasta / Path(*Path(rel).parts)
                try:
                    if dest.exists() and rel not in gerenciados and rel not in vistos:
                        avisos.append(f"mod '{nome}': '{rel}' já existe fora do Hub; preservado")
                        continue
                    if pasta.resolve() not in dest.resolve().parents or _eh_reparse(dest):
                        avisos.append(f"mod '{nome}': destino de '{rel}' é um link; preservado")
                        continue
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(arq, dest)
                except OSError as e:
                    avisos.append(f"mod '{nome}': {rel} não copiou ({e})")
                    continue
                if rel not in vistos:
                    vistos.add(rel)
                    arquivos.append(rel)
            aplicados.append(nome)
        except OSError as e:
            avisos.append(f"mod '{nome}' não ativou ({e})")
    _gravar_manifesto(pasta, pedidos, arquivos, fontes=fontes, completo=not avisos)
    return {"aplicados": aplicados, "aviso": "; ".join(avisos) or None}


def _bin_7z() -> str:
    """7z do Hub (Windows) ou do sistema; '' se ausente."""
    if os.name == "nt":
        cand = Path(WIN_ROOT) / "Games/ferramentas/7z.exe"
        if cand.is_file():
            return str(cand)
    return shutil.which("7z") or shutil.which("7zz") or ""


def _extrair_arquivo(arq: str, destino: Path) -> None:
    baixo = arq.lower()
    if baixo.endswith(".zip"):
        import zipfile
        with zipfile.ZipFile(arq) as z:
            for m in z.namelist():
                alvo = (destino / m)
                if not str(alvo.resolve()).startswith(str(destino.resolve())):
                    raise OSError(f"entrada suspeita no zip: {m}")
            z.extractall(destino)
        return
    sete = _bin_7z()
    if not sete:
        raise OSError("archive precisa do 7z (só .zip sem ele"
                      + ("; no Linux instale o p7zip" if os.name != "nt" else "") + ")")
    r = subprocess.run([sete, "x", arq, f"-o{destino}", "-y"],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise OSError(f"7z falhou ({r.returncode}): {(r.stderr or '').strip()[:200]}")


def _raiz_layeredfs(base: Path) -> tuple[Path | None, str]:
    """(pasta do mod, title-id do caminho luma|) procurando até 3 níveis.

    Ordem: caminho luma/titles/<id> vence; depois raiz com arquivos;
    depois qualquer raiz; por fim conteúdo nu (ex.: 'a/' sem romfs/).
    """
    cands: list[tuple[Path, str, bool]] = []
    nu: Path | None = None
    for raiz, _dirs, _arqs in os.walk(base):
        try:
            rel = Path(raiz).relative_to(base)
        except ValueError:
            continue
        if len(rel.parts) > 3:
            continue
        p = Path(raiz)
        try:
            baixo = {q.name.lower() for q in p.iterdir()}
        except OSError:
            continue
        tid = ""
        partes = p.parts
        if "luma" in partes and "titles" in partes:
            try:
                i = list(partes).index("titles")
                cand = str(partes[i + 1]).upper()
                if len(cand) == 16 and all(c in "0123456789ABCDEF" for c in cand):
                    tid = cand
            except IndexError:
                pass
        if "romfs" in baixo or "exefs" in baixo or "code.ips" in baixo or tid:
            try:
                tem = any(f.is_file() for f in p.rglob("*"))
            except OSError:
                tem = False
            cands.append((p, tid, tem))
        elif nu is None and _tem_conteudo_nu(p):
            nu = p
    for p, tid, _tem in cands:
        if tid:
            return p, tid
    for p, _tid, tem in cands:
        if tem:
            return p, ""
    if cands:
        return cands[0][0], cands[0][1]
    if nu is not None:
        return nu, ""
    return None, ""


def _tem_conteudo_nu(p: Path) -> bool:
    """Pasta parece conteúdo de romfs sem o invólucro (ex.: 'a/' do Pokémon)?"""
    try:
        for item in p.iterdir():
            n = item.name.lower()
            if item.is_dir() and n in ("a", "sound", "m", "data"):
                return True
            if item.is_file() and n.endswith((".cro", ".crr", ".moflex", ".bcstm", ".bcsar")):
                return True
    except OSError:
        pass
    return False


def importar_mod(origem: str, title_id: str = "", nome: str = "") -> dict:
    """Copia pasta ou extrai archive p/ a biblioteca. Retorna dict (sempre).

    Detecta a raiz LayeredFS (romfs/exefs/code.ips, luma/titles/<id> ou
    conteúdo nu como 'a/') e normaliza. title_id vem do caminho luma ou
    deve ser informado (o jogo de destino).
    """
    import tempfile
    src = Path((origem or "").strip().strip("\"'"))
    if not src.exists():
        return {"ok": False, "erro": f"origem não encontrada: {origem}"}
    tid = (title_id or "").strip().upper()
    if tid and (len(tid) != 16 or any(c not in "0123456789ABCDEF" for c in tid)):
        return {"ok": False, "erro": f"title ID inválido: {title_id}"}
    rotulo = (nome or "").strip().replace("/", "-").replace("\\", "-")[:60].strip()
    if not rotulo:
        rotulo = src.stem.strip()[:60].strip()
    if not rotulo or rotulo in (".", ".."):
        return {"ok": False, "erro": "nome de mod vazio."}
    tmp = Path(tempfile.mkdtemp(prefix="hub-mod-"))
    try:
        if src.is_dir():
            shutil.copytree(src, tmp / "m")
        elif src.is_file():
            _extrair_arquivo(str(src), tmp / "m")
        else:
            return {"ok": False, "erro": f"origem inválida: {origem}"}
        raiz, tid_luma = _raiz_layeredfs(tmp / "m")
        if raiz is None:
            return {"ok": False, "erro": "estrutura LayeredFS não encontrada (sem romfs/exefs/code.ips)."}
        tid = tid or tid_luma
        if not tid:
            return {"ok": False, "erro": "informe o jogo (title ID) deste mod."}
        dest = mods_titulo_dir(tid) / rotulo
        if dest.exists():
            return {"ok": False, "erro": f"mod '{rotulo}' já existe na biblioteca."}
        if _tem_conteudo_nu(raiz) and not (raiz / "romfs").is_dir() and not (raiz / "exefs").is_dir():
            dest.mkdir(parents=True)
            rf = dest / "romfs"
            rf.mkdir()
            for item in sorted(raiz.iterdir()):
                if item.name.lower() == "code.ips":
                    continue  # vai p/ raiz do mod (Azahar só lê lá)
                if item.suffix.lower() in (".txt", ".md") and item.is_file():
                    continue
                shutil.move(str(item), str(rf / item.name))
            if (raiz / "code.ips").is_file():
                shutil.move(str(raiz / "code.ips"), str(dest / "code.ips"))
        else:
            shutil.copytree(raiz, dest)
        n = sum(1 for _p in dest.rglob("*") if _p.is_file())
        if not _eh_mod_valido(dest):
            shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "erro": "nada aproveitável (sem romfs/exefs/code.ips)."}
        return {"ok": True, "mod": rotulo, "title_id": tid, "arquivos": n}
    except OSError as e:
        return {"ok": False, "erro": f"{type(e).__name__}: {e}"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def preparar_lancamento(jogo: dict) -> dict:
    """Aplica preset + mods do provider do jogo. Nunca bloqueia o play."""
    origem = (jogo.get("origem") or "")
    prov = provedor_por_origem(origem)
    if prov is None:
        return {"preset_aplicado": None, "mods_aplicados": [], "aviso": None}
    avisos: list[str] = []
    aplicado = None
    campo = "azahar_preset"
    nome = (jogo.get(campo) or "").strip()
    if nome:
        r = prov["aplicar_preset"](nome)
        if r.get("ok"):
            aplicado = r["preset"]
        else:
            avisos.append(f"Preset '{nome}' falhou ({r['erro']}); abrindo com config atual.")
    launch = (jogo.get("launch_options") or "").strip()
    mods_ok: list[str] = []
    if (launch and prov.get("chave") == "azahar"
            and provedor_por_extensao(Path(launch).suffix) is not None):
        if rom_parece_criptografada(launch) and not azahar_tem_chaves():
            avisos.append("ROM parece criptografada e o Azahar está sem aes_keys.txt "
                          "— o jogo não vai abrir. Faça o dump das chaves do seu 3DS "
                          "(GodMode9) para user/sysdata/aes_keys.txt.")
        mr = aplicar_mods(jogo)
        mods_ok = mr["aplicados"]
        if mr["aviso"]:
            avisos.append(mr["aviso"])
        try:  # texturas HD: pasta ativa sem flag global = HD invisível
            from bib_nucleo import texturas as _TEX
            tid_tex = title_id_da_rom(traduzir_para_atual(launch))
            if tid_tex and _TEX.tem_textura(tid_tex):
                if _TEX.flag_custom_textures() is False:
                    avisos.append("Texturas HD ligadas mas o preset está sem "
                                  "custom textures — troque p/ hd2x.")
        except Exception:
            pass
    return {"preset_aplicado": aplicado, "mods_aplicados": mods_ok,
            "aviso": " ".join(avisos) or None}


def rom_parece_criptografada(rom_path: str) -> bool:
    """ExeFS sem ícone extraível = quase sempre ROM criptografada."""
    rom = (rom_path or "").strip()
    if not rom or not Path(rom).is_file():
        return False  # ausente é outro erro (o play já reporta)
    try:
        with Path(rom).open("rb") as f:
            head = f.read(0x200)
            if head[0x100:0x104] == b"NCSD":
                f.seek(int.from_bytes(head[0x120:0x124], "little") * 0x200)
                head = f.read(0x200)
            return (len(head) >= 0x200 and head[0x100:0x104] == b"NCCH"
                    and not bool(head[0x18F] & 0x04))
    except Exception:
        return False


def azahar_tem_chaves() -> bool:
    ud = azahar_user_dir()
    return bool(ud) and (Path(ud) / "sysdata" / "aes_keys.txt").is_file()

__all__ = ['azahar_dir_override', 'default_emu_3ds', 'desmume_dir_override', 'desmume_dir', 'default_emu_nds', 'desmume_user_dir', 'desmume_versao_local', 'desmume_release_info', 'desmume_instalar', 'desmume_config_atual', 'desmume_flags', 'config_atual_emu', 'presets_prov_dir', 'azahar_user_dir', 'azahar_status', 'AZAHAR_API_LATEST', 'AZAHAR_VERSAO_ARQ', 'azahar_versao_local', 'azahar_release_info', 'azahar_instalar', 'executar_elevado', 'executar_jogo_dict', 'diagnosticar_exe', 'diagnosticar_rom', 'procurar_rom', 'azahar_flags', 'LIMIAR_SESSAO_S', 'executar_monitorado', 'iniciar_sessao_manual', 'listar_sessoes_pendentes', 'encerrar_sessao_manual', 'provedores', 'provedor_por_origem', 'provedor_por_extensao', 'provedor_nome', 'jogos_do_provedor', 'provedores_resumo', 'montar_launch_rom', 'backup_saves_emu', 'backup_saves_azahar', 'presets_dir', 'listar_presets', 'azahar_config_atual', 'salvar_preset_de_atual', 'aplicar_preset', 'preparar_lancamento', 'rom_parece_criptografada', 'azahar_tem_chaves',
 'title_id_da_rom', 'mods_lib_dir', 'mods_titulo_dir', 'remover_link', 'listar_mods', 'remover_mod', 'azahar_mods_dir', 'mods_ativos', 'aplicar_mods', 'importar_mod']
