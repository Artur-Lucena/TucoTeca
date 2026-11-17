#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emuladores: registro de provedores (um registro, N emuladores)."""
from __future__ import annotations

from bib_nucleo import emuladores as _E
from bib_nucleo.base import ROM_EXTS_3DS


def _aplicar_preset(nome: str, chave: str = "azahar") -> dict:
    """Acesso tardio a presets.aplicar_preset (evita ciclo presets<->provedores)."""
    from bib_nucleo.emuladores.presets import aplicar_preset
    return aplicar_preset(nome, chave)


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
        "exe": _E.default_emu_3ds,          # () -> str (via pacote: patchável)
        "user_dir": _E.azahar_user_dir,     # (exe="") -> str (via pacote: patchável)
        "saves_subs": ("sdmc", "states"),
        "pacote_subs": ("sdmc",),        # states travam à versão: fora do pacote
        "rom_exts": ROM_EXTS_3DS,
        "flags": _E.azahar_flags,           # () -> list[str] (via pacote: patchável)
        "aplicar_preset": _aplicar_preset,  # (nome) -> dict
        "ler_metadados": ler_metadados_3ds,
        "icone": icone_rom_para_png,
        "release_info": _E.azahar_release_info,
        "versao_local": _E.azahar_versao_local,
        "instalar": _E.azahar_instalar,
        "dica_instalacao": ("Azahar não encontrado — instale em "
                            "Games/Emuladores/Azahar ou defina BIBLIOTECA_EMULADOR_3DS."),
    }


def _prov_desmume() -> dict:
    from bib_nucleo.scans import icone_nds_para_png, ler_metadados_nds
    return {
        "chave": "desmume",
        "nome": "DeSmuME",
        "sistemas": ("Nintendo DS",),
        "origens": ("rom-nds",),
        "origem": "rom-nds",
        "exe": _E.default_emu_nds,           # () -> str (via pacote: patchável)
        "user_dir": _E.desmume_user_dir,     # (exe="") -> str (via pacote: patchável)
        "saves_subs": (),                 # .dsv mora ao lado da ROM
        "pacote_subs": (),
        "rom_exts": {".nds", ".dsi"},
        "flags": _E.desmume_flags,           # () -> list[str] (via pacote: patchável)
        "aplicar_preset": lambda nome: _aplicar_preset(nome, "desmume"),
        "release_info": _E.desmume_release_info,
        "versao_local": _E.desmume_versao_local,
        "instalar": _E.desmume_instalar,
        "ler_metadados": ler_metadados_nds,
        "icone": icone_nds_para_png,
        "dica_instalacao": ("DeSmuME não encontrado — instale em "
                            "Games/Emuladores/DeSmuME (Win: desmume.exe, "
                            "Linux: desmume*.AppImage) ou defina BIBLIOTECA_EMULADOR_NDS."),
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


def jogos_do_provedor(jogos: list[dict], chave: str) -> list[dict]:
    """Só os jogos que o provider consegue rodar (p/ filtro da UI)."""
    return [j for j in (jogos or [])
            if (provedor_por_origem(j.get("origem") or "") or {}).get("chave") == chave]


__all__ = ["_aplicar_preset", "_prov_azahar", "_prov_desmume", "jogos_do_provedor", "provedor_por_extensao", "provedor_por_origem",
           "provedores"]
