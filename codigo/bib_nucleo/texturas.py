#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Texturas HD do Azahar (custom textures) com liga/desliga por jogo.

Ativas em `user/load/textures/<TITLE-ID>/`; desligadas como
`<TITLE-ID>.off` (rename — sem admin, sem cópia, vale nos 3 SOs).
Global: preset com `custom_textures=true` + `preload_textures=true`;
sem pasta ativa o flag não faz nada. Biblioteca extra pode morar em
`dados/texturas/` (fora do git, do scanner e dos instaladores — GBs,
mesmo trato dos mods).
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

# Os 6 Pokémon do Hub (title IDs lidos do header NCCH das ROMs).
TITULOS = {
    "0004000000055D00": "Pokémon X",
    "0004000000055E00": "Pokémon Y",
    "000400000011C400": "Pokémon Omega Ruby",
    "000400000011C500": "Pokémon Alpha Sapphire",
    "00040000001B5000": "Pokémon Ultra Sun",
    "00040000001B5100": "Pokémon Ultra Moon",
}

_TID_RE = re.compile(r"^[0-9A-Fa-f]{16}$")
_SUFIJO_OFF = ".off"


def titulo_ok(tid: str) -> str:
    """Normaliza e valida o title ID (16 hex). '' se inválido."""
    tid = (tid or "").strip().upper()
    return tid if _TID_RE.match(tid) else ""


def load_textures_dir() -> Path | None:
    """Pasta `user/load/textures` do Azahar (None se sem user/)."""
    from bib_nucleo import emuladores as EMU
    try:
        ud = EMU.azahar_user_dir()
    except (OSError, ValueError):
        return None
    if not ud:
        return None
    d = Path(ud) / "load" / "textures"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    return d


def _pastas(base: Path, tid: str) -> tuple[Path, Path]:
    return base / tid, base / (tid + _SUFIJO_OFF)


def _resumo(pasta: Path) -> tuple[int, int]:
    n = mb = 0
    try:
        for f in pasta.rglob("*"):
            if f.is_file() and not f.is_symlink():
                n += 1
                try:
                    mb += f.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return n, mb


def listar_texturas() -> list[dict]:
    """Toda pasta <tid>/ ou <tid>.off em load/textures (só TIDs válidos)."""
    base = load_textures_dir()
    if base is None:
        return []
    out = []
    try:
        filhos = sorted(base.iterdir())
    except OSError:
        return []
    for p in filhos:
        nome = p.name
        ativo = True
        if nome.endswith(_SUFIJO_OFF):
            nome, ativo = nome[: -len(_SUFIJO_OFF)], False
        tid = titulo_ok(nome)
        if not tid:
            continue
        try:
            eh_dir = p.is_dir() and not p.is_symlink()
        except OSError:
            continue
        if not eh_dir:
            continue
        n, mb = _resumo(p)
        out.append({"tid": tid, "nome": TITULOS.get(tid, tid),
                    "ativo": ativo, "arquivos": n,
                    "mb": round(mb / 1048576, 1)})
    return sorted(out, key=lambda d: d["tid"])


def definir_textura(tid: str, ativo: bool) -> dict:
    """Liga/desliga por rename. Nunca apaga PNG; erro se ausente dos 2 lados."""
    tid = titulo_ok(tid)
    if not tid:
        return {"ok": False, "erro": "title ID inválido."}
    base = load_textures_dir()
    if base is None:
        return {"ok": False, "erro": "pasta user/ do Azahar não encontrada."}
    on, off = _pastas(base, tid)
    try:
        tem_on = on.is_dir() and not on.is_symlink()
        tem_off = off.is_dir() and not off.is_symlink()
    except OSError as e:
        return {"ok": False, "erro": f"falha ao ler: {e}"}
    if ativo:
        if tem_on:
            return {"ok": True, "tid": tid, "ativo": True}
        if not tem_off:
            return {"ok": False, "erro": f"sem texturas p/ {tid}."}
        try:
            off.rename(on)
        except OSError as e:
            return {"ok": False, "erro": f"falha ao ligar: {e}"}
        return {"ok": True, "tid": tid, "ativo": True}
    if tem_off:
        return {"ok": True, "tid": tid, "ativo": False}
    if not tem_on:
        return {"ok": False, "erro": f"sem texturas p/ {tid}."}
    try:
        on.rename(off)
    except OSError as e:
        return {"ok": False, "erro": f"falha ao desligar: {e}"}
    return {"ok": True, "tid": tid, "ativo": False}


def alternar_textura(tid: str) -> dict:
    """Alterna o estado atual. Erro se o TID não está instalado."""
    tid = titulo_ok(tid)
    if not tid:
        return {"ok": False, "erro": "title ID inválido."}
    base = load_textures_dir()
    if base is None:
        return {"ok": False, "erro": "pasta user/ do Azahar não encontrada."}
    on, off = _pastas(base, tid)
    try:
        tem_on = on.is_dir() and not on.is_symlink()
        tem_off = off.is_dir() and not off.is_symlink()
    except OSError as e:
        return {"ok": False, "erro": f"falha ao ler: {e}"}
    if tem_on:
        return definir_textura(tid, False)
    if tem_off:
        return definir_textura(tid, True)
    return {"ok": False, "erro": f"sem texturas p/ {tid}."}


def tem_textura(tid: str) -> bool:
    """Há pasta ativa p/ este TID? (para exibir estado no play)."""
    tid = titulo_ok(tid)
    if not tid:
        return False
    base = load_textures_dir()
    if base is None:
        return False
    try:
        return (base / tid).is_dir() and not (base / tid).is_symlink()
    except OSError:
        return False


def estado_textura(tid: str) -> dict:
    """Estado de um TID: instalado/ativo + contagem (só esta pasta)."""
    tid = titulo_ok(tid)
    if not tid:
        return {"tid": "", "instalado": False, "ativo": False,
                "arquivos": 0, "mb": 0.0}
    base = load_textures_dir()
    if base is None:
        return {"tid": tid, "instalado": False, "ativo": False,
                "arquivos": 0, "mb": 0.0}
    on, off = _pastas(base, tid)
    try:
        tem_on = on.is_dir() and not on.is_symlink()
        tem_off = off.is_dir() and not off.is_symlink()
    except OSError:
        return {"tid": tid, "instalado": False, "ativo": False,
                "arquivos": 0, "mb": 0.0}
    pasta = on if tem_on else (off if tem_off else None)
    if pasta is None:
        return {"tid": tid, "instalado": False, "ativo": False,
                "arquivos": 0, "mb": 0.0}
    n, mb = _resumo(pasta)
    return {"tid": tid, "nome": TITULOS.get(tid, tid), "instalado": True,
            "ativo": tem_on, "arquivos": n, "mb": round(mb / 1048576, 1)}


def flag_custom_textures() -> bool | None:
    """`custom_textures` global do ini live (None se ilegível)."""
    import configparser
    from bib_nucleo import emuladores as EMU
    try:
        cfg = EMU.config_atual_emu("azahar")
        if cfg is None:
            return None
        ini = configparser.ConfigParser()
        ini.optionxform = str  # type: ignore[assignment]
        ini.read(cfg, encoding="utf-8")
        return ini.get("Utility", "custom_textures").strip().lower() == "true"
    except (OSError, ValueError, configparser.Error):
        return None


def instalar_textura(tid: str, origem: str | os.PathLike) -> dict:
    """Move pasta extraída p/ `load/textures/<TID>/`. Valida PNGs, sem rede.

    Origem some (move); destino não pode existir (nem `.off`). Para trocar
    versão, apague a atual primeiro (rename p/ `.off` não libera o nome).
    """
    tid = titulo_ok(tid)
    if not tid:
        return {"ok": False, "erro": "title ID inválido."}
    src = Path(origem)
    try:
        if not src.is_dir():
            return {"ok": False, "erro": "origem não é pasta."}
        pngs = [p for p in src.rglob("*.png") if p.is_file()]
    except OSError as e:
        return {"ok": False, "erro": f"falha ao ler origem: {e}"}
    if not pngs:
        return {"ok": False, "erro": "pasta sem nenhum .png."}
    base = load_textures_dir()
    if base is None:
        return {"ok": False, "erro": "pasta user/ do Azahar não encontrada."}
    on, off = _pastas(base, tid)
    try:
        if on.exists() or off.exists():
            return {"ok": False,
                    "erro": f"{tid} já instalado (desligue/apague antes)."}
        shutil.move(str(src), str(on))
    except OSError as e:
        return {"ok": False, "erro": f"falha ao instalar: {e}"}
    return {"ok": True, "tid": tid, "ativo": True, "arquivos": len(pngs)}


__all__ = ['TITULOS', 'titulo_ok', 'load_textures_dir', 'listar_texturas',
           'estado_textura', 'flag_custom_textures',
           'definir_textura', 'alternar_textura', 'tem_textura',
           'instalar_textura']
