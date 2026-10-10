#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Controles (Xbox/PlayStation/Switch Pro) no Hub: detectar, mapear e aplicar.

- Detecta via winmm+XInput (Win), `/proc/bus/input/devices` (Linux), nada
  (outros — darwin-safe: nenhum import win32 no topo).
- Gera o perfil `[Controls]` do Azahar com binds `engine:sdl` (GUIDs
  verificados no SDL_GameControllerDB) + fotografa/aplica presets Hub em
  `dados/presets/controles/`. Aplique com o Azahar fechado (ele lê no boot
  e reescreve o arquivo ao sair).
- Testa apertos por polling (viewer), sem rede, stdlib só.
"""
from __future__ import annotations

import configparser
import os
import shutil
import sys
import time
from pathlib import Path

# GUIDs SDL de fallback (gamecontrollerdb; o guid REAL varia por sistema —
# use `detectar_sdl()`, que lê o guid gravado pelo próprio Azahar).
GUIDS = {
    "xbox360": "030000005e0400008e02000000000000",
    "xboxone": "030000005e040000d102000000000000",
    "ps4": "030000004c050000c405000000000000",
    "dualsense": "030000004c050000e60c000000000000",
    "switchpro": "030000007e0500000920000000000000",
}

NOMES_TIPO = {
    "xbox360": "Xbox 360",
    "xboxone": "Xbox One/Series",
    "ps4": "PlayStation 4",
    "dualsense": "PlayStation 5",
    "switchpro": "Switch Pro",
}

# 3DS <- pad (posicional; índices = enum SDL_GameControllerButton, uniforme
# nas 3 famílias via mapeamento padrão do SDL). Gatilhos variam por família.
# ("btn", indice, "Rótulo") | ("eixo", indice, "+/-", "Rótulo").
MAPAS = {
    "xbox360": {"button_b": ("btn", 0, "A"), "button_a": ("btn", 1, "B"),
                "button_y": ("btn", 2, "X"), "button_x": ("btn", 3, "Y"),
                "button_l": ("btn", 9, "LB"), "button_r": ("btn", 10, "RB"),
                "button_zl": ("eixo", 2, "+", "Left Trigger"),
                "button_zr": ("eixo", 2, "-", "Right Trigger"),
                "button_start": ("btn", 6, "Start"),
                "button_select": ("btn", 4, "Back/Select"),
                "button_home": ("btn", 5, "Guide/Home")},
    "xboxone": {"button_b": ("btn", 0, "A"), "button_a": ("btn", 1, "B"),
                "button_y": ("btn", 2, "X"), "button_x": ("btn", 3, "Y"),
                "button_l": ("btn", 9, "LB"), "button_r": ("btn", 10, "RB"),
                "button_zl": ("eixo", 2, "+", "Left Trigger"),
                "button_zr": ("eixo", 5, "+", "Right Trigger"),
                "button_start": ("btn", 6, "Start"),
                "button_select": ("btn", 4, "Back/Select"),
                "button_home": ("btn", 5, "Guide/Home")},
    "ps4": {"button_b": ("btn", 1, "Cross"), "button_a": ("btn", 2, "Circle"),
            "button_y": ("btn", 0, "Square"),
            "button_x": ("btn", 3, "Triangle"),
            "button_l": ("btn", 9, "L1"), "button_r": ("btn", 10, "R1"),
            "button_zl": ("eixo", 3, "+", "L2"),
            "button_zr": ("eixo", 4, "+", "R2"),
            "button_start": ("btn", 9, "Options"),
            "button_select": ("btn", 8, "Share"),
            "button_home": ("btn", 12, "PS")},
    "dualsense": {"button_b": ("btn", 1, "Cross"),
                  "button_a": ("btn", 2, "Circle"),
                  "button_y": ("btn", 0, "Square"),
                  "button_x": ("btn", 3, "Triangle"),
                  "button_l": ("btn", 9, "L1"),
                  "button_r": ("btn", 10, "R1"),
                  "button_zl": ("eixo", 3, "+", "L2"),
                  "button_zr": ("eixo", 4, "+", "R2"),
                  "button_start": ("btn", 9, "Options"),
                  "button_select": ("btn", 8, "Create"),
                  "button_home": ("btn", 12, "PS")},
    "switchpro": {"button_b": ("btn", 0, "B"), "button_a": ("btn", 1, "A"),
                  "button_y": ("btn", 2, "Y"), "button_x": ("btn", 3, "X"),
                  "button_l": ("btn", 9, "L"),
                  "button_r": ("btn", 10, "R"),
                  "button_zl": ("btn", 6, "ZL"),
                  "button_zr": ("btn", 7, "ZR"),
                  "button_start": ("btn", 9, "+"),
                  "button_select": ("btn", 8, "-"),
                  "button_home": ("btn", 12, "Home")},
}

# DPad e sticks: idênticos nas 3 famílias (padrão SDL).
DPAD = {"button_up": ("btn", 11, "D-Pad Up"),
        "button_down": ("btn", 12, "D-Pad Down"),
        "button_left": ("btn", 13, "D-Pad Left"),
        "button_right": ("btn", 14, "D-Pad Right")}
STICK_ESQ = (0, 1, "Left Stick X", "Left Stick Y")
STICK_DIR = (2, 3, "Right Stick X", "Right Stick Y")

BOTOES_3DS = ("button_a", "button_b", "button_x", "button_y", "button_l",
              "button_r", "button_zl", "button_zr", "button_start",
              "button_select", "button_home")


def _serializar(pares: list[tuple[str, str]]) -> str:
    return ",".join(f"{k}:{v}" for k, v in pares)


def bind_botao(guid: str, port: int, indice: int, rotulo: str) -> str:
    """Bind digital no formato exato do Azahar 2126 (amostra real)."""
    return _serializar([("api", "controller"), ("button", str(indice)),
                        ("engine", "sdl"), ("guid", guid),
                        ("maptype", "guid+port"), ("name", rotulo),
                        ("port", str(port))])


def bind_eixo(guid: str, port: int, eixo: int, direcao: str,
              rotulo: str) -> str:
    """Gatilho analógico como botão (ex.: ZL/ZR)."""
    return _serializar([("api", "controller"), ("axis", str(eixo)),
                        ("direction", direcao), ("engine", "sdl"),
                        ("guid", guid), ("maptype", "guid+port"),
                        ("name", rotulo), ("port", str(port)),
                        ("threshold", "0.500000")])


def bind_analogico(guid: str, port: int, eixo_x: int, eixo_y: int,
                   rotulo_x: str, rotulo_y: str) -> str:
    """Stick real, plano (sem sub-binds aninhados — amostra real)."""
    return _serializar([("api", "controller"), ("axis_x", str(eixo_x)),
                        ("axis_y", str(eixo_y)), ("deadzone", "0.100000"),
                        ("engine", "sdl"), ("guid", guid),
                        ("maptype", "guid+port"), ("name_x", rotulo_x),
                        ("name_y", rotulo_y), ("port", str(port))])


def gerar_perfil(tipo: str, guid: str = "", port: int = 0,
                 rotulos: dict | None = None) -> dict:
    """Mapa 3DS completo p/ chaves `profiles\\1\\*` do ini (puro, testável).

    Calibrado com amostra real do Azahar 2126 (perfil fotografado).
    `guid` vazio = fallback da tabela (prefira o `detectar_sdl()`).
    `rotulos` = {(kind, idx[, dir]): nome} do `nomes_sdl()`; sem ele valem
    os genéricos (o Azahar pode ignorar nomes desconhecidos).
    """
    if tipo not in MAPAS:
        raise ValueError(f"tipo desconhecido: {tipo}")
    guid = guid or GUIDS[tipo]
    rotulos = rotulos or {}
    mapa = MAPAS[tipo]

    def rot(kind, *a, padrao):
        return rotulos.get((kind, *a), padrao)

    perfil = {}
    for chave in BOTOES_3DS:
        spec = mapa[chave]
        if spec[0] == "btn":
            perfil[f"profiles\\1\\{chave}"] = bind_botao(
                guid, port, spec[1], rot("btn", spec[1], padrao=spec[2]))
        else:
            perfil[f"profiles\\1\\{chave}"] = bind_eixo(
                guid, port, spec[1], spec[2],
                rot("eixo", spec[1], spec[2], padrao=spec[3]))
    for chave, spec in DPAD.items():
        perfil[f"profiles\\1\\{chave}"] = bind_botao(
            guid, port, spec[1], rot("btn", spec[1], padrao=spec[2]))
    ex, ey, rx, ry = (*STICK_ESQ[:2], *STICK_DIR[:2])
    perfil["profiles\\1\\circle_pad"] = bind_analogico(
        guid, port, ex, ey,
        rotulos.get(("stick", "x"), STICK_ESQ[2]),
        rotulos.get(("stick", "y"), STICK_ESQ[3]))
    perfil["profiles\\1\\c_stick"] = bind_analogico(
        guid, port, rx, ry,
        rotulos.get(("rstick", "x"), STICK_DIR[2]),
        rotulos.get(("rstick", "y"), STICK_DIR[3]))
    return perfil


def detectar_sdl() -> list[dict]:
    """Dispositivos sdl já gravados nos perfis ([{guid, nome, port, perfil}]).

    Fonte da verdade p/ gerar/aplicar (guid real do SDL, não da tabela).
    """
    import re as _re
    ini, _ = _ler_controls()
    out = []
    if not ini.has_section("Controls"):
        return out
    for chave, valor in ini.items("Controls"):
        m = _re.search(r"guid:([0-9a-fA-F]{32})", valor)
        if not m or "engine:sdl" not in valor:
            continue
        mn = _re.search(r"name:([^,]+),port:(\d+)", valor)
        if mn is None:
            mn = _re.search(r"name_x:([^,]+),", valor)
        prof = chave.split("\\")[0] if "\\" in chave else ""
        item = {"guid": m.group(1).lower(),
                "nome": mn.group(1) if mn else "",
                "port": int(mn.group(2)) if mn and mn.lastindex == 2 else 0,
                "perfil": prof}
        if not any(o["guid"] == item["guid"] and o["port"] == item["port"]
                   for o in out):
            out.append(item)
    return out


def nomes_sdl() -> dict:
    """Tabela {(tipo, indice[, dir]): rótulo} dos binds sdl live.

    Rótulos reais do Azahar p/ o gerador (ex.: ('btn', 0) -> 'A / ?').
    Vazio se nenhum bind sdl gravado.
    """
    import re as _re
    ini, _ = _ler_controls()
    tab: dict = {}
    sticks = 0
    if not ini.has_section("Controls"):
        return tab
    for _, valor in ini.items("Controls"):
        if "engine:sdl" not in valor:
            continue
        v = valor.strip()
        if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
            v = v[1:-1]
        mn = _re.search(r"name:([^,]+),port:", v)
        rot = mn.group(1) if mn else ""
        mb = _re.search(r",button:(\d+),", v)
        if mb and rot:
            tab[("btn", int(mb.group(1)))] = rot
            continue
        ma = _re.search(r",axis:(\d+),direction:([+-]),", v)
        if ma and rot:
            tab[("eixo", int(ma.group(1)), ma.group(2))] = rot
            continue
        mx = _re.search(r"axis_x:(\d+),axis_y:(\d+)", v)
        if mx:
            prefixo = "stick" if sticks == 0 else "rstick"
            sticks += 1
            for suf, chave in (("name_x", "x"), ("name_y", "y")):
                m2 = _re.search(rf"{suf}:([^,]+),", v)
                if m2:
                    tab[(prefixo, chave)] = m2.group(1)
    return tab


def perfil_ativo(ini: configparser.ConfigParser | None = None) -> int:
    """Índice 0-based do perfil ativo (`profile`, padrão 0)."""
    if ini is None:
        ini, _ = _ler_controls()
    try:
        if ini.has_section("Controls") and ini.has_option("Controls",
                                                           "profile"):
            return max(0, int(ini.get("Controls", "profile")))
    except (ValueError, configparser.Error):
        pass
    return 0


def _prefixo_origem(novo: configparser.ConfigParser) -> str:
    """Prefixo `profiles\\N\\` único do preset (padrão `profiles\\1\\`)."""
    if novo.has_section("Controls"):
        for k, _ in novo.items("Controls"):
            partes = k.split("\\")
            if len(partes) >= 3 and partes[0] == "profiles" \
                    and partes[1].isdigit():
                return f"profiles\\{partes[1]}\\"
    return "profiles\\1\\"


def _presets_dir() -> Path:
    from bib_nucleo.base import PRESETS_DIR
    d = PRESETS_DIR / "controles"
    d.mkdir(parents=True, exist_ok=True)
    return d


def listar_presets_controle() -> list[str]:
    try:
        return sorted(p.stem for p in _presets_dir().glob("*.ini")
                      if p.is_file())
    except OSError:
        return []


def _ler_controls() -> tuple[configparser.ConfigParser, Path | None]:
    from bib_nucleo import emuladores as EMU
    cfg = EMU.config_atual_emu("azahar")
    ini = configparser.ConfigParser()
    ini.optionxform = str  # type: ignore[assignment]
    if cfg is None:
        return ini, None
    try:
        ini.read(cfg, encoding="utf-8")
    except (OSError, configparser.Error):
        pass
    return ini, cfg


def ler_perfil_atual() -> dict:
    """Perfil `[Controls]` live como {chave: valor} ({} sem config)."""
    ini, _ = _ler_controls()
    if not ini.has_section("Controls"):
        return {}
    return dict(ini.items("Controls"))


def fotografar_perfil(nome: str) -> dict:
    """Guarda o perfil ATIVO como preset Hub (template `profiles\\1`)."""
    from bib_nucleo.base import slugify
    if not (nome or "").strip():
        return {"ok": False, "erro": "nome de preset vazio."}
    slug = slugify(nome)
    ini, _ = _ler_controls()
    if not ini.has_section("Controls"):
        return {"ok": False,
                "erro": "config do Azahar não encontrada (abra-o uma vez)."}
    origem = f"profiles\\{perfil_ativo(ini) + 1}\\"
    dest = _presets_dir() / f"{slug}.ini"
    foto = configparser.ConfigParser()
    foto.optionxform = str  # type: ignore[assignment]
    foto.add_section("Controls")
    for k, v in ini.items("Controls"):
        if not k.startswith(origem) or "\\default" in k:
            continue  # flags o Azahar regenera; evita `X\default\default`
        curto = k[len(origem):]
        if curto in ("name", "input_maptype"):
            continue  # identidade do slot, não bind
        foto.set("Controls", "profiles\\1\\" + curto, v)
    try:
        with open(dest, "w", encoding="utf-8") as fh:
            foto.write(fh)
    except OSError as e:
        return {"ok": False, "erro": f"falha ao gravar: {e}"}
    return {"ok": True, "preset": slug, "arquivo": str(dest)}


def higienizar_controles() -> dict:
    """Limpa crud que quebra a leitura dos perfis pelo Azahar.

    Remove linhas `X\\default\\default` (lixo que o próprio Azahar grava
    ao re-salvar) e chaves duplicadas exatas (vale a 1ª). Descoberto por
    bisseção: arquivo limpo = seleção e binds estáveis no game-boot.
    Só mexe no texto; nunca reordena nem reformatta o resto.
    """
    from bib_nucleo import emuladores as EMU
    cfg = EMU.config_atual_emu("azahar")
    if cfg is None:
        return {"ok": False, "erro": "config do Azahar não encontrada."}
    try:
        linhas = cfg.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        return {"ok": False, "erro": f"falha ao ler: {e}"}
    vistas, limpas, removidas = set(), [], 0
    secao = ""
    for l in linhas:
        if l.strip().startswith("[") and l.strip().endswith("]"):
            secao = l.strip()[1:-1]
            vistas.clear()
        if secao != "Controls" or "=" not in l or l.lstrip().startswith(("#", ";")):
            limpas.append(l)
            continue
        k = l.split("=", 1)[0].strip()
        if k.endswith("\\default\\default") or k in vistas:
            removidas += 1
            continue
        vistas.add(k)
        limpas.append(l)
    if not removidas:
        return {"ok": True, "removidas": 0}
    try:
        cfg.write_text("\n".join(limpas) + "\n", encoding="utf-8")
    except OSError as e:
        return {"ok": False, "erro": f"falha ao gravar: {e}"}
    return {"ok": True, "removidas": removidas}


def aplicar_preset_controle(nome: str, perfil: int | None = None) -> dict:
    """Mescla preset Hub no perfil live (Azahar fechado!).

    `perfil` = índice 0-based alvo (None = o ativo). Garante `profile=`,
    `profiles\\size` e remove o veneno `profile\\default`.

    Cirurgia por linhas no estilo nativo do Azahar (`chave="valor"` +
    `chave\\default=false`): o Qt descarta binds fora desse padrão,
    então NÃO reescrevemos o arquivo via configparser.
    """
    from bib_nucleo.base import slugify
    slug = slugify(nome or "")
    alvo = _presets_dir() / f"{slug}.ini"
    try:
        dentro = alvo.resolve().parent == _presets_dir().resolve()
    except OSError:
        dentro = False
    if not dentro or alvo.suffix.lower() != ".ini" or not alvo.is_file():
        return {"ok": False, "erro": f"preset '{nome}' não existe."}
    ini, cfg = _ler_controls()
    if cfg is None:
        return {"ok": False, "erro": "config do Azahar não encontrada."}
    try:
        bak = cfg.with_name(cfg.name + ".bak")
        if not bak.is_file():
            shutil.copy2(str(cfg), str(bak))
        higiene = higienizar_controles()
        if not higiene.get("ok"):
            return higiene
        ini, _ = _ler_controls()  # seleção do perfil após reparar duplicatas
        novo = configparser.ConfigParser()
        novo.optionxform = str  # type: ignore[assignment]
        novo.read(alvo, encoding="utf-8")
        if not novo.has_section("Controls"):
            return {"ok": False, "erro": "preset sem seção Controls."}
        origem = _prefixo_origem(novo)
        alvo_idx = perfil if perfil is not None else perfil_ativo(ini)
        if alvo_idx < 0:
            return {"ok": False, "erro": "índice de perfil inválido."}
        destino = f"profiles\\{alvo_idx + 1}\\"
        ativo = alvo_idx + 1
        pares = []
        for k, v in novo.items("Controls"):
            if not k.startswith(origem):
                continue
            v = v.strip()
            if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                v = v[1:-1]  # preset herdou as aspas literais do Azahar
            pares.append((destino + k[len(origem):], v))
        if not pares:
            return {"ok": False, "erro": "preset sem binds de perfil."}
        linhas = cfg.read_text(encoding="utf-8").splitlines()
        try:
            ini_sec = next(i for i, l in enumerate(linhas)
                           if l.strip() == "[Controls]")
        except StopIteration:
            linhas.append("[Controls]")
            ini_sec = len(linhas) - 1
        fim_sec = next((i for i in range(ini_sec + 1, len(linhas))
                        if linhas[i].strip().startswith("[")),
                       len(linhas))
        alvos = {chave for chave, _ in pares}
        alvos |= {ch + "\\default" for ch, _ in pares}
        corpo = [l for l in linhas[ini_sec + 1:fim_sec]
                 if l.split("=", 1)[0] not in alvos]
        novas = []
        for chave, valor in pares:
            novas.append(f"{chave}\\default=false")
            novas.append(f'{chave}="{valor}"')
        antes, depois = linhas[:ini_sec + 1], linhas[fim_sec:]
        linhas = corpo + novas  # todas as cirurgias seguintes são só de Controls
        # o Azahar REGENERA no game-boot todo perfil chamado "Default":
        # garante nome próprio p/ não perder os binds aplicados.
        nome_chave = f"profiles\\{ativo}\\name"
        for i, l in enumerate(linhas):
            if l.split("=", 1)[0] != nome_chave or "=" not in l:
                continue
            atual = l.split("=", 1)[1].strip().strip('"')
            if atual in ("", "Default"):
                linhas[i] = f'{nome_chave}="{slug}"'
                if f"{nome_chave}\\default" not in {
                        x.split("=", 1)[0] for x in linhas}:
                    linhas.insert(i + 1, f"{nome_chave}\\default=false")
            break
        else:
            linhas.insert(0, f'{nome_chave}="{slug}"')
            linhas.insert(1, f"{nome_chave}\\default=false")
        # `profile\default=true` trava o perfil 0 p/ sempre (fonte: config.cpp
        # ReadSetting): sem ele com ativo>0, e `profile=<ativo>` garantido.
        linhas = [l for l in linhas
                 if l.split("=", 1)[0] != "profile\\default"]
        tem_profile = False
        for i, l in enumerate(linhas):
            if l.split("=", 1)[0] != "profile" or "=" not in l:
                continue
            tem_profile = True
            linhas[i] = f"profile={ativo - 1}"
            break
        if not tem_profile:
            linhas.insert(0, f"profile={ativo - 1}")
        # o Azahar ignora perfis além de profiles\size: garante cobertura
        for i, l in enumerate(linhas):
            if l.split("=", 1)[0] != "profiles\\size" or "=" not in l:
                continue
            try:
                if int(l.split("=", 1)[1]) < ativo:
                    linhas[i] = f"profiles\\size={ativo}"
            except ValueError:
                linhas[i] = f"profiles\\size={ativo}"
            break
        else:
            linhas.insert(len(linhas),
                            f"profiles\\size={ativo}")
        cfg.write_text("\n".join(antes + linhas + depois) + "\n", encoding="utf-8")
    except (OSError, configparser.Error) as e:
        return {"ok": False, "erro": f"falha ao mesclar: {e}"}
    return {"ok": True, "preset": slug, "config": str(cfg),
            "chaves": len(pares)}


def salvar_mapa_gerado(tipo: str, guid: str = "", port: int = 0,
                       nome: str = "", rotulos: dict | None = None) -> dict:
    """Gera o mapa padrão e grava como preset Hub (sem tocar no live).

    `rotulos` = tabela do `nomes_sdl()` (rótulos reais do Azahar);
    sem ela valem os genéricos.
    """
    from bib_nucleo.base import slugify
    try:
        perfil = gerar_perfil(tipo, guid, port, rotulos=rotulos)
    except ValueError as e:
        return {"ok": False, "erro": str(e)}
    slug = slugify(nome or f"{tipo}-padrao") or f"{tipo}-padrao"
    foto = configparser.ConfigParser()
    foto.optionxform = str  # type: ignore[assignment]
    foto.add_section("Controls")
    for k, v in perfil.items():
        foto.set("Controls", k, v)
    dest = _presets_dir() / f"{slug}.ini"
    try:
        with open(dest, "w", encoding="utf-8") as fh:
            foto.write(fh)
    except OSError as e:
        return {"ok": False, "erro": f"falha ao gravar: {e}"}
    return {"ok": True, "preset": slug, "arquivo": str(dest),
            "chaves": len(perfil)}


# --------------------------------------------------------------------------
# Detecção (Win: winmm+XInput+OEM; Linux: /proc; resto: [])
# --------------------------------------------------------------------------

def _oem_nome(chave_reg: str) -> str:
    if os.name != "nt" or not chave_reg:
        return ""
    try:
        import winreg
        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                "System\\CurrentControlSet\\Control\\MediaProperties"
                "\\PrivateProperties\\Joystick\\OEM\\" + chave_reg) as hk:
            nome, _ = winreg.QueryValueEx(hk, "OEMName")
            return str(nome or "")
    except OSError:
        return ""


def _xinput_slots() -> dict[int, dict]:
    """Estados XInput (Win). {} sem driver/dispositivo. Nunca levanta."""
    import ctypes
    if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
        return {}
    from ctypes import wintypes
    for dll in ("xinput1_4.dll", "xinput9_1_0.dll", "xinput1_3.dll"):
        try:
            xi = ctypes.WinDLL(dll, use_last_error=True)
            break
        except OSError:
            continue
    else:
        return {}

    class _ST(ctypes.Structure):
        _fields_ = [("n", wintypes.DWORD), ("b", wintypes.WORD),
                    ("lt", wintypes.BYTE), ("rt", wintypes.BYTE),
                    ("lx", ctypes.c_short), ("ly", ctypes.c_short),
                    ("rx", ctypes.c_short), ("ry", ctypes.c_short)]

    xi.XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(_ST)]
    xi.XInputGetState.restype = wintypes.DWORD
    out = {}
    for i in range(4):
        st = _ST()
        try:
            r = xi.XInputGetState(i, ctypes.byref(st))
        except OSError:
            continue
        if r == 0:
            out[i] = {"botoes": st.b, "lt": st.lt, "rt": st.rt,
                      "lx": st.lx, "ly": st.ly, "rx": st.rx, "ry": st.ry}
    return out


def listar_controles() -> list[dict]:
    """Controles conectados: [{nome, botoes, eixos, xinput, familia}]."""
    if os.name == "nt":
        return _listar_win()
    if sys.platform.startswith("linux"):
        return _listar_linux()
    return []


def _familia_por_nome(nome: str, xinput: bool) -> str:
    n = (nome or "").lower().replace("-", "")
    if any(k in n for k in ("dualsense", "ps5", "playstation 5")):
        return "dualsense"
    if any(k in n for k in ("dualshock", "ps4", "playstation 4", "sony")):
        return "ps4"
    if any(k in n for k in ("switch pro", "pro controller", "nintendo")):
        return "switchpro"
    if any(k in n for k in ("xbox one", "xbox series", "xbox élite",
                            "xbox elite")):
        return "xboxone"
    if "xbox 360" in n or "xbox" in n:
        return "xbox360"
    if xinput:
        return "xbox360"  # XInput ativo = padrão Xbox
    if any(k in n for k in ("8bitdo", "8bit-do")):
        return "switchpro"  # modo Switch mais comum
    return ""


def _listar_win() -> list[dict]:
    import ctypes
    from ctypes import wintypes

    class _CAP(ctypes.Structure):
        _fields_ = [("mid", wintypes.WORD), ("pid", wintypes.WORD),
                    ("nome", wintypes.WCHAR * 32),
                    ("xmin", wintypes.UINT), ("xmax", wintypes.UINT),
                    ("ymin", wintypes.UINT), ("ymax", wintypes.UINT),
                    ("zmin", wintypes.UINT), ("zmax", wintypes.UINT),
                    ("nb", wintypes.UINT), ("pmin", wintypes.UINT),
                    ("pmax", wintypes.UINT), ("rmin", wintypes.UINT),
                    ("rmax", wintypes.UINT), ("umin", wintypes.UINT),
                    ("umax", wintypes.UINT), ("vmin", wintypes.UINT),
                    ("vmax", wintypes.UINT), ("caps", wintypes.UINT),
                    ("maxaxes", wintypes.UINT), ("naxes", wintypes.UINT),
                    ("maxb", wintypes.UINT),
                    ("reg", wintypes.WCHAR * 32),
                    ("oemvxd", wintypes.WCHAR * 260)]

    try:
        winmm = ctypes.WinDLL("winmm.dll", use_last_error=True)
    except OSError:
        return []
    winmm.joyGetNumDevs.restype = wintypes.UINT
    winmm.joyGetDevCapsW.argtypes = [wintypes.UINT,
                                     ctypes.POINTER(_CAP), wintypes.UINT]
    winmm.joyGetDevCapsW.restype = wintypes.UINT
    try:
        total = winmm.joyGetNumDevs()
    except OSError:
        return []
    try:
        xis = _xinput_slots()
    except OSError:
        xis = {}
    out = []
    for i in range(min(total, 16)):
        cap = _CAP()
        try:
            if winmm.joyGetDevCapsW(i, ctypes.byref(cap),
                                    ctypes.sizeof(cap)) != 0:
                continue
        except OSError:
            continue
        oem = _oem_nome(cap.reg)
        nome = oem or cap.nome
        out.append({"indice": i, "nome": nome,
                    "botoes": cap.nb, "eixos": cap.naxes,
                    "xinput": i in xis,
                    "familia": _familia_por_nome(nome, i in xis)})
    if not out and xis:
        for i in sorted(xis):
            out.append({"indice": i, "nome": "Controle XInput",
                        "botoes": 14, "eixos": 6, "xinput": True,
                        "familia": "xbox360"})
    return out


def _eh_js(token: str) -> bool:
    """Token de joystick em Handlers (`js0`, `js1`…; `js` nu por tolerância)."""
    return token == "js" or (token.startswith("js") and token[2:].isdigit())


def _parse_devices(texto: str) -> list[dict]:
    """Nomes com joystick em /proc/bus/input/devices (puro, testável)."""
    out = []
    nome, tem_js = "", False

    def descarrega():
        nonlocal nome, tem_js
        if nome and tem_js:
            out.append({"indice": len(out), "nome": nome, "botoes": 0,
                        "eixos": 0, "xinput": False,
                        "familia": _familia_por_nome(nome, False)})
        nome, tem_js = "", False

    for linha in (texto or "").splitlines():
        if linha.startswith("N: Name="):
            descarrega()
            nome = linha.split("=", 1)[1].strip().strip('"')
        elif linha.startswith("H: Handlers=") and any(
                _eh_js(t) for t in linha.split()):
            tem_js = True
        elif not linha.strip():
            descarrega()
    descarrega()
    return out


def _listar_linux() -> list[dict]:
    """Nomes de joypads via /proc (sem polling: exige evdev)."""
    try:
        texto = Path("/proc/bus/input/devices").read_text(encoding="utf-8",
                                                           errors="ignore")
    except OSError:
        return []
    return _parse_devices(texto)


# --------------------------------------------------------------------------
# Teste por polling (viewer): poll() -> {botoes:set/int, eixos:{}, pov}
# --------------------------------------------------------------------------

def ler_estado_xinput(slot: int = 0) -> dict | None:
    """Estado instantâneo XInput (None se ausente). Para o viewer/teste."""
    try:
        xis = _xinput_slots()
    except OSError:
        return None
    st = xis.get(slot)
    if st is None:
        return None
    return {"botoes": {i for i in range(16) if st["botoes"] >> i & 1},
            "lt": st["lt"], "rt": st["rt"],
            "lx": st["lx"], "ly": st["ly"], "rx": st["rx"], "ry": st["ry"]}


# Bits do wButtons XInput -> nome (A=0x1000=bit 12, ...). Não confundir
# com os índices SDL (0-14) usados nos binds do Azahar.
XINPUT_NOMES = {12: "A", 13: "B", 14: "X", 15: "Y", 8: "LB", 9: "RB",
                4: "Start", 5: "Back", 6: "L3", 7: "R3", 10: "Guia",
                0: "↑", 1: "↓", 2: "←", 3: "→"}

# Bit XInput -> índice enum SDL_GameControllerButton (p/ futuro wizard).
XINPUT_PARA_SDL = {12: 0, 13: 1, 14: 2, 15: 3, 5: 4, 10: 5, 4: 6,
                   6: 7, 7: 8, 8: 9, 9: 10, 0: 11, 1: 12, 2: 13, 3: 14}


def xinput_para_sdl(bit: int) -> int | None:
    """Traduz bit XInput p/ índice SDL (None se sem equivalente digital)."""
    return XINPUT_PARA_SDL.get(bit)


def resumir_estado(estado: dict | None) -> str:
    """Uma linha legível do estado (viewer TUI/GUI)."""
    if not estado:
        return "—"
    partes = [XINPUT_NOMES.get(b, f"b{b}") for b in sorted(estado["botoes"])]
    if estado.get("lt", 0) > 30:
        partes.append(f"LT:{estado['lt']}")
    if estado.get("rt", 0) > 30:
        partes.append(f"RT:{estado['rt']}")
    for eixo in ("lx", "ly", "rx", "ry"):
        v = estado.get(eixo, 0) or 0
        if abs(v) > 8000:
            partes.append(f"{eixo}:{v}")
    return " ".join(partes) if partes else "(neutro)"


def capturar(poll, timeout: float = 10.0, limiar_eixo: int = 16000) -> dict:
    """Aguarda UM aperto/movimento: {tipo, indice/direção}. Puro e testável.

    poll() -> {"botoes": set[int], "eixos": {nome: valor}}. Índices de
    botão saem crus (ex.: bits XInput) — traduza com `xinput_para_sdl()`.
    """
    descr = {"lx": (0, "esquerdo"), "rx": (2, "direito")}
    fim = time.monotonic() + max(1.0, timeout)
    while time.monotonic() < fim:
        try:
            est = poll()
        except Exception:
            return {"ok": False, "erro": "falha de leitura."}
        if not isinstance(est, dict):
            time.sleep(0.05)
            continue
        for b in sorted(est.get("botoes") or ()):
            return {"ok": True, "tipo": "botao", "indice": b}
        for nome, (eixo, _rot) in descr.items():
            v = (est.get("eixos") or {}).get(nome, 0) or 0
            if abs(v) >= limiar_eixo:
                return {"ok": True, "tipo": "eixo",
                        "indice": eixo, "direcao": "+" if v > 0 else "-"}
        pov = est.get("pov", 65535)
        if pov is not None and pov != 65535:
            return {"ok": True, "tipo": "chapeu", "indice": 0,
                    "direcao": str(pov)}
        time.sleep(0.05)
    return {"ok": False, "erro": "tempo esgotado."}


__all__ = ['GUIDS', 'NOMES_TIPO', 'MAPAS', 'BOTOES_3DS', 'DPAD',
           'gerar_perfil', 'bind_botao', 'bind_eixo', 'bind_analogico',
           'detectar_sdl', 'nomes_sdl', 'perfil_ativo', 'higienizar_controles',
           'listar_controles',
           'ler_perfil_atual', 'fotografar_perfil', 'listar_presets_controle',
           'aplicar_preset_controle', 'salvar_mapa_gerado', 'ler_estado_xinput',
           'XINPUT_NOMES', 'XINPUT_PARA_SDL', 'xinput_para_sdl',
            'resumir_estado']
