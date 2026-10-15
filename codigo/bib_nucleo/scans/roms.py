#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scans: ROMs (3DS/NDS) — raízes, scanner e preview por provider."""
from __future__ import annotations

import os
import re
from pathlib import Path

from bib_nucleo.base import LINUX_ROOT, WIN_ROOT
from bib_nucleo.emuladores import (
    default_emu_3ds,
    default_emu_nds,
    provedor_por_extensao,
    provedores,
)
from bib_nucleo.scans.disco import SKIP_DIRS
from bib_nucleo.scans.lojas import pontuar

# --------------------------------------------------------------------------
# ROMs (ex.: 3DS no Azahar) — scanner + raízes + emulador padrão
# --------------------------------------------------------------------------

def default_roms_roots() -> list[str]:
    env = os.environ.get("BIBLIOTECA_ROMS_ROOTS")
    if env:
        return [r for r in re.split(r"[;\n]+", env) if r.strip()]
    if os.name == "nt":
        base = WIN_ROOT.rstrip("\\")
        return [f"{base}\\Games\\Roms", f"{base}\\Games\\Roms\\3DS"]
    base = LINUX_ROOT.rstrip("/")
    return [f"{base}/Games/Roms", f"{base}/Games/Roms/3DS"]


ROM_TAGS_LIXO_RE = re.compile(
    r"\s*\((USA|EUR|JPN|JAP|KOR|CHN|TWN|AUS|BRA|World|"
    r"En(?:,[A-Za-z]{2})+|Rev\s*\d+|v\d+[\.\d]*|Decrypted|Trimmed|NDSi Enhanced"
    r"|(?:USA|EUR|JPN)(?:,\s*[A-Za-z]+)+)\)", re.IGNORECASE)


def _titulo_de_rom(p: Path) -> str:
    nome = p.stem.replace("_", " ").replace(".", " ").replace("-", " ").strip()
    nome = ROM_TAGS_LIXO_RE.sub("", nome)  # "Pokemon X (USA) (En,Ja…)" -> "Pokemon X"
    return re.sub(r"\s+", " ", nome).strip() or p.stem


def _item_rom(full: str, emu_exe: str = "", prov=None) -> dict:
    """Um achado de ROM (título/código/região lidos de dentro do arquivo)."""
    if prov is None:
        prov = provedor_por_extensao(Path(full).suffix) or provedores()["azahar"]
    item = {
        "titulo": _titulo_de_rom(Path(full)),
        "executable_path": emu_exe,
        "launch_options": full,
        "shop": "", "object_id": "",
        "horas": 0.0, "origem": prov["origem"],
        "rom_path": full,
        "game_code": "", "regiao": "",
        "tem_metadados": False,
    }
    try:
        m = prov["ler_metadados"](full)
    except Exception:
        m = {}
    if m.get("titulo"):
        item["titulo"] = m["titulo"]
        item["tem_metadados"] = True
    if m.get("game_code"):
        item["game_code"] = m["game_code"]
    if m.get("regiao"):
        item["regiao"] = m["regiao"]
    return item


def scan_roms(roots: list[str], emu_exe: str = "", prof_max: int = 4,
              retornar_info: bool = False, prov_chave: str = "azahar"
              ) -> list[dict] | tuple[list[dict], dict]:
    """Procura ROMs do provider. Leitura apenas. Itens já vêm com o emu em executable_path."""
    prov = provedores()[prov_chave]
    exts = prov["rom_exts"]
    achados: dict[str, dict] = {}
    vistos = 0
    truncado = False

    def _final():
        res = sorted(achados.values(), key=lambda j: j["titulo"].lower())
        if retornar_info:
            return res, {"vistos": vistos, "truncado": truncado,
                         "raizes": [str(r) for r in roots if Path(r).is_dir()]}
        return res

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
                if vistos >= 60_000:
                    truncado = True
                    return _final()
                if Path(fn).suffix.lower() not in exts:
                    continue
                vistos += 1
                full = str(Path(dirpath) / fn)
                chave = full.lower()
                if chave not in achados:
                    achados[chave] = _item_rom(full, emu_exe, prov)
    return _final()


def default_roms_nds_roots() -> list[str]:
    env = os.environ.get("BIBLIOTECA_ROMS_NDS_ROOTS")
    if env:
        return [r for r in re.split(r"[;\n]+", env) if r.strip()]
    if os.name == "nt":
        base = WIN_ROOT.rstrip("\\")
        return [f"{base}\\Games\\Roms", f"{base}\\Games\\Roms\\NDS",
                f"{base}\\Games\\Roms NDs"]
    base = LINUX_ROOT.rstrip("/")
    return [f"{base}/Games/Roms", f"{base}/Games/Roms/NDS", f"{base}/Games/Roms NDs"]


def preview_roms(roots: list[str] | None = None,
                 emu_exe: str | None = None, prov_chave: str = "azahar"
                 ) -> tuple[list[str], list[dict], dict, str]:
    """(raízes, itens pontuados, info, emu_usado)."""
    if roots is None:
        if prov_chave == "azahar":
            roots = default_roms_roots()
        else:
            roots = default_roms_nds_roots()
    if emu_exe is None:
        if prov_chave == "azahar":
            emu = default_emu_3ds()
        else:
            emu = default_emu_nds()
    else:
        emu = emu_exe
    achados, info = scan_roms(roots, emu_exe=emu, retornar_info=True,
                              prov_chave=prov_chave)
    return roots, [pontuar(j) for j in achados], info, emu


__all__ = ["default_roms_roots", "ROM_TAGS_LIXO_RE", "_titulo_de_rom", "_item_rom",
           "scan_roms", "default_roms_nds_roots", "preview_roms"]
