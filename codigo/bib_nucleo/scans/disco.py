#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scans: disco (pastas, Steam manifests, exe) — raízes e preview."""
from __future__ import annotations

import os
import re
from pathlib import Path

from bib_nucleo.base import LINUX_ROOT, MAC_ROOT, WIN_ROOT, eh_mac
from bib_nucleo.scans.lojas import (
    _appid_de_manifest,
    _item_steam_manifest,
    pontuar,
)

# Scanner de disco (D:\Games, SteamLibrary, Riot...) + manifests Steam
# --------------------------------------------------------------------------

SKIP_DIRS = {
    "windowsapps", "system volume information", "$recycle.bin",
    ".pnpm-store", "msdownld.tmp", "found.000", "wpsystem",
    "backups", "capas", "presets", "sessoes", "saves", "mods", "musicas",
    "videos", "texturas", ".hub-lixo", "baixados", "cache-wav", "cache-provedores", "conquistas",
    ".git", ".build", ".cache", "__pycache__", "dist",
    "node_modules", ".venv", "venv", ".mypy_cache", ".pytest_cache",
}

SKIP_EXE_RE = re.compile(
    r"(?i)^(unins|uninstall|setup|dotnet|dxweb|quicksfv|visualcpp|"
    r"vc_?redist|dxsetup|oalinst|crash|crashhandler|bugreport|"
    r"unitycrashhandler|qt|python|hydra|redist|vcredist|eac|easyanticheat|"
    r"stockfish|cgef|f10\.)"
)

RIOT_EXE = {
    "leagueclient.exe": "League of Legends",
    "league of legends.exe": "League of Legends",
    "riotclientservices.exe": "Riot Client",
}

ACF_NAME_RE = re.compile(r'"name"\s+"([^"]+)"')

ACF_DIR_RE = re.compile(r'"installdir"\s+"([^"]+)"')


def default_scan_roots() -> list[str]:
    env = os.environ.get("BIBLIOTECA_SCAN_ROOTS")
    if env:
        return [r for r in re.split(r"[;\n]+", env) if r.strip()]
    if os.name == "nt":
        base = WIN_ROOT.rstrip("\\")
        return [f"{base}\\Games", f"{base}\\SteamLibrary", f"{base}\\Riot Games"]
    base = (MAC_ROOT if eh_mac() else LINUX_ROOT).rstrip("/")
    roots = [f"{base}/Games", f"{base}/SteamLibrary"]
    # Steam nativo (fora da partilha): só entra se existir
    for cand in (Path.home() / ".steam/steam/steamapps",
                 Path.home() / ".local/share/Steam/steamapps",
                 Path.home() / "Library/Application Support/Steam/steamapps"):
        if cand.is_dir():
            roots.append(str(cand))
    return roots


def _titulo_de_exe(p: Path) -> str:
    baixo = p.name.lower()
    if baixo in RIOT_EXE:
        return RIOT_EXE[baixo]
    stem = p.stem
    stem = re.sub(r"(?i)[-_ ]?(win64|win32|x64|shipping|game)$", "", stem)
    stem = stem.replace("_", " ").replace(".", " ").strip()
    # separa colados do exe ("HowManyDudes" -> "How Many Dudes", "Hades2" -> "Hades 2")
    stem = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", stem)
    stem = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", stem)
    return re.sub(r"\s+", " ", stem).strip() or p.stem


def scan_discos(roots: list[str], max_arquivos: int = 60_000, prof_max: int = 5,
                retornar_info: bool = False) -> list[dict] | tuple[list[dict], dict]:
    """Procura .exe e manifests Steam. Leitura apenas, com teto de arquivos.

    Se retornar_info, devolve (lista, {"vistos", "truncado", "raizes"}).
    "truncado" True = o teto estourou; a lista é parcial.
    """
    achados: dict[str, dict] = {}
    vistos = 0
    truncado = False

    def _final():
        res = sorted(achados.values(), key=lambda j: j["titulo"].lower())
        if retornar_info:
            return res, {"vistos": vistos, "truncado": truncado,
                         "raizes": [str(r) for r in roots if Path(r).is_dir()]}
        return res

    def registrar(item: dict):
        chave = f"{item['titulo'].lower()}\x00{item['executable_path'].lower()}"
        if chave not in achados:
            achados[chave] = item

    for raiz in roots:
        rp = Path(raiz)
        if not rp.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(rp):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            try:
                prof = len(Path(dirpath).relative_to(rp).parts)
            except ValueError:
                dirnames[:] = []
                continue
            if prof > prof_max:
                dirnames[:] = []
                continue
            for fn in filenames:
                if vistos >= max_arquivos:
                    truncado = True
                    return _final()
                baixo = fn.lower()
                full = str(Path(dirpath) / fn)
                if baixo.startswith("appmanifest_") and baixo.endswith(".acf"):
                    vistos += 1
                    try:
                        txt = Path(full).read_text(encoding="utf-8", errors="ignore")
                    except OSError:
                        continue
                    it = _item_steam_manifest(txt, dirpath, _appid_de_manifest(fn))
                    if it is not None:
                        registrar(it)
                elif baixo.endswith(".exe"):
                    vistos += 1
                    if SKIP_EXE_RE.search(fn):
                        continue
                    p = Path(full)
                    registrar({
                        "titulo": _titulo_de_exe(p), "executable_path": full,
                        "shop": "", "object_id": "",
                        "horas": 0.0, "origem": "scan-disco",
                    })
    return _final()


def preview_scan(roots: list[str] | None = None) -> tuple[list[str], list[dict], dict]:
    """(raízes_usadas, itens pontuados, info{vistos, truncado, raizes})."""
    roots = roots or default_scan_roots()
    from bib_nucleo.everything import buscar_executaveis
    instantaneos = buscar_executaveis(roots)
    if instantaneos is not None:
        itens = [{"titulo": _titulo_de_exe(Path(p)), "executable_path": p, "shop": "",
                  "object_id": "", "horas": 0.0, "origem": "scan-disco"}
                 for p in instantaneos if not SKIP_EXE_RE.search(Path(p).name)]
        return roots, [pontuar(j) for j in itens], {"vistos": len(instantaneos),
                "truncado": len(instantaneos) >= 60_000, "raizes": roots, "motor": "everything"}
    achados, info = scan_discos(roots, retornar_info=True)
    return roots, [pontuar(j) for j in achados], info


__all__ = ["SKIP_DIRS", "SKIP_EXE_RE", "RIOT_EXE", "ACF_NAME_RE", "ACF_DIR_RE",
           "default_scan_roots", "_titulo_de_exe", "scan_discos", "preview_scan"]
