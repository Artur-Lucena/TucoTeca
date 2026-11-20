#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emuladores: saves (backup) e presets por jogo (mescla no ini antes de lançar)."""
from __future__ import annotations

import configparser
import datetime
import shutil
import zipfile
from pathlib import Path

from bib_nucleo.base import BACKUP_DIR, PRESETS_DIR, slugify
from bib_nucleo.emuladores.azahar import azahar_config_atual
from bib_nucleo.emuladores.desmume import desmume_config_atual
from bib_nucleo.emuladores.provedores import provedores


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


def salvar_preset_de_atual(nome: str, chave: str = "azahar") -> dict:
    """Fotografa o ini atual como presets/<provider>/<nome>.ini."""
    cfg = config_atual_emu(chave)
    if cfg is None:
        return {"ok": False,
                "erro": f"config não encontrada (abra o {chave} uma vez)."}
    slug = slugify(nome) if (nome or "").strip() else ""  # slugify("") devolve "capa"
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


__all__ = ["_alvo_preset", "aplicar_preset",
           "backup_saves_emu", "config_atual_emu", "listar_presets",
           "presets_dir", "presets_prov_dir", "salvar_preset_de_atual"]
