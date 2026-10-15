#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emuladores: Azahar (Nintendo 3DS) — localização, gerenciador e config."""
from __future__ import annotations

import json
import shlex
from pathlib import Path

from bib_nucleo import emuladores as _E


def azahar_dir_override() -> Path | None:
    """Destino explícito do portátil, inclusive antes da primeira instalação."""
    env = (_E.os.environ.get("BIBLIOTECA_AZAHAR_DIR") or "").strip()
    if env:
        return Path(env)
    from bib_nucleo.ferramentas import emulador_local_dir
    return emulador_local_dir("Azahar")


def default_emu_3ds() -> str:
    """Caminho do Azahar neste SO (BIBLIOTECA_EMULADOR_3DS > BIBLIOTECA_AZAHAR_DIR > padrão)."""
    env = _E.os.environ.get("BIBLIOTECA_EMULADOR_3DS")
    if env:
        return env
    ov = _E.azahar_dir_override()
    if ov is not None:
        if _E.eh_mac():
            return _E._app_macos(ov)
        if _E.os.name == "nt":
            cand = ov / "azahar.exe"
            return str(cand) if cand.is_file() else ""
        return _E._appimage_na_pasta(ov, "azahar")
    if _E.eh_mac():
        return _E._app_macos(Path(_E.MAC_ROOT) / "Games/Emuladores/Azahar")
    if _E.os.name == "nt":
        cand = Path(_E.WIN_ROOT) / "Games/Emuladores/Azahar/azahar.exe"
        return str(cand) if cand.is_file() else ""
    pasta = Path(_E.LINUX_ROOT) / "Games/Emuladores/Azahar"
    if pasta.is_dir():
        return _E._appimage_na_pasta(pasta, "azahar")
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
        if _E.eh_mac():  # .app: user/ fica ao lado do bundle (até 3 acima)
            for cima in list(Path(exe).parents[1:4]):
                port = cima / "user"
                if port.is_dir():
                    return str(port)
    if _E.eh_mac():
        cand = Path(_E.MAC_ROOT) / "Games/Emuladores/Azahar/user"
        if cand.is_dir():
            return str(cand)
        return ""
    if _E.os.name == "nt":
        base = Path(_E.os.environ.get("APPDATA", "")) / "Azahar"
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
    ov = _E.azahar_dir_override()
    if ov is not None:
        return ov  # bundle: atualiza o emulador dentro do pacote
    if _E.os.name == "nt":
        return Path(_E.WIN_ROOT) / "Games/Emuladores/Azahar"
    if _E.eh_mac():
        return Path(_E.MAC_ROOT) / "Games/Emuladores/Azahar"
    return Path(_E.LINUX_ROOT) / "Games/Emuladores/Azahar"


def _asset_azahar_ok(nome: str) -> bool:
    """O asset do release serve p/ este SO? (testável sem rede)."""
    if _E.eh_mac():
        return nome.startswith("azahar-macos-universal-") and nome.endswith(".zip")
    if _E.os.name == "nt":
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
        if _E._asset_azahar_ok(nome):
            digest = a.get("digest") or ""
            sha = digest.split(":", 1)[1].strip() if ":" in digest else ""
            return {"tag": tag, "nome": nome, "size": a.get("size") or 0,
                    "sha256": sha, "url": a.get("browser_download_url") or ""}
    return {"erro": "asset deste SO não encontrado no release"}


def azahar_instalar(info: dict, progresso=None) -> dict:
    """Atualiza o runtime atual com backup, diário e verificação SHA-256."""
    from bib_nucleo.atualizacao import instalar
    if _E.eh_mac():
        return instalar(info, _E._emu_dir(), progresso, plataforma="darwin")
    return instalar(info, _E._emu_dir(), progresso)


def azahar_flags() -> list[str]:
    """Flags extras ao bootar ROM (padrão -f fullscreen; vazio desliga)."""
    return shlex.split(_E.os.environ.get("BIBLIOTECA_AZAHAR_FLAGS", "-f"),
                       posix=(_E.os.name != "nt"))


def azahar_config_atual() -> Path | None:
    ud = _E.azahar_user_dir()
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


def azahar_mods_dir() -> str:
    """user/load/mods do Azahar atual ('' se emulador ausente)."""
    ud = _E.azahar_user_dir()
    if not ud:
        return ""
    return str(Path(ud) / "load" / "mods")


def azahar_tem_chaves() -> bool:
    ud = _E.azahar_user_dir()
    return bool(ud) and (Path(ud) / "sysdata" / "aes_keys.txt").is_file()


__all__ = ["AZAHAR_API_LATEST", "AZAHAR_VERSAO_ARQ", "_asset_azahar_ok",
           "_emu_dir", "azahar_config_atual", "azahar_dir_override",
           "azahar_flags", "azahar_instalar", "azahar_mods_dir",
           "azahar_release_info", "azahar_status", "azahar_tem_chaves",
           "azahar_user_dir", "azahar_versao_local", "default_emu_3ds"]
