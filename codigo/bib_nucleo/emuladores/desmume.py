#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emuladores: DeSmuME (Nintendo DS) — localização, gerenciador e config."""
from __future__ import annotations

import json
import shlex
from pathlib import Path

from bib_nucleo import emuladores as _E

# --------------------------------------------------------------------------
# DeSmuME (Nintendo DS): provider nº 2, mesma integração do Azahar
# --------------------------------------------------------------------------

DESMUME_API_LATEST = "https://api.github.com/repos/TASEmulators/desmume/releases/latest"
DESMUME_VERSAO_ARQ = "desmume-versao.txt"


def desmume_dir_override() -> Path | None:
    env = (_E.os.environ.get("BIBLIOTECA_DESMUME_DIR") or "").strip()
    if env:
        return Path(env)
    from bib_nucleo.ferramentas import emulador_local_dir
    return emulador_local_dir("DeSmuME")


def desmume_dir() -> Path:
    ov = _E.desmume_dir_override()
    if ov is not None:
        return ov
    if _E.os.name == "nt":
        return Path(_E.WIN_ROOT) / "Games/Emuladores/DeSmuME"
    if _E.eh_mac():
        return Path(_E.MAC_ROOT) / "Games/Emuladores/DeSmuME"
    return Path(_E.LINUX_ROOT) / "Games/Emuladores/DeSmuME"


def _asset_desmume_ok(nome: str) -> bool:
    """O asset do release serve p/ este SO? (testável sem rede)."""
    if _E.eh_mac():
        return "macos" in nome.lower() and nome.endswith(".dmg")
    if _E.os.name == "nt":
        return "-win64.zip" in nome
    return False  # Linux: sem asset oficial (AppImage manual)


def default_emu_nds() -> str:
    """Caminho do DeSmuME (BIBLIOTECA_EMULADOR_NDS > DIR > padrão)."""
    env = _E.os.environ.get("BIBLIOTECA_EMULADOR_NDS")
    if env:
        return env
    ov = _E.desmume_dir_override()
    if ov is not None:
        if _E.eh_mac():
            return _E._app_macos(ov)
        if _E.os.name == "nt":
            cand = ov / "desmume.exe"
            return str(cand) if cand.is_file() else ""
        return _E._appimage_na_pasta(ov, "desmume")
    if _E.eh_mac():
        return _E._app_macos(Path(_E.MAC_ROOT) / "Games/Emuladores/DeSmuME")
    if _E.os.name == "nt":
        cand = Path(_E.WIN_ROOT) / "Games/Emuladores/DeSmuME/desmume.exe"
        return str(cand) if cand.is_file() else ""
    pasta = Path(_E.LINUX_ROOT) / "Games/Emuladores/DeSmuME"
    img = _E._appimage_na_pasta(pasta, "desmume")
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
    if _E.os.name != "nt" and not _E.eh_mac():
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
        if _E._asset_desmume_ok(nome):
            digest = a.get("digest") or ""
            sha = digest.split(":", 1)[1].strip() if ":" in digest else ""
            return {"tag": tag, "nome": nome, "size": a.get("size") or 0,
                    "sha256": sha, "url": a.get("browser_download_url") or ""}
    return {"erro": "asset deste SO não encontrado no release"}


def desmume_instalar(info: dict, progresso=None) -> dict:
    """Baixa e instala o DeSmuME (transacional, como Azahar)."""
    from bib_nucleo.atualizacao import instalar
    if _E.eh_mac():
        return instalar(info, _E.desmume_dir(), progresso, plataforma="darwin",
                        versao_nome=DESMUME_VERSAO_ARQ)
    if _E.os.name != "nt":
        return {"ok": False, "erro": ("Instalação automática do DeSmuME só no Windows e no Mac. "
                                      "No Linux use AppImage manual.")}
    return instalar(info, _E.desmume_dir(), progresso, exe_nomes=("DeSmuME*.exe",),
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
    padrao = "--windowed-fullscreen" if _E.os.name == "nt" and not _E.eh_mac() else ""
    return shlex.split(_E.os.environ.get("BIBLIOTECA_DESMUME_FLAGS", padrao),
                       posix=(_E.os.name != "nt"))


__all__ = ["DESMUME_API_LATEST", "DESMUME_VERSAO_ARQ", "_asset_desmume_ok",
           "default_emu_nds", "desmume_config_atual", "desmume_dir",
           "desmume_dir_override", "desmume_flags", "desmume_instalar",
           "desmume_release_info", "desmume_user_dir", "desmume_versao_local"]
