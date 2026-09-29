#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Controles (Xbox/PlayStation/Switch Pro) no Hub: detectar, mapear e aplicar.

- Detecta via winmm+XInput (Win), `/proc/bus/input/devices` (Linux), nada
  (outros — darwin-safe: nenhum import win32 no topo).
- Gera o perfil `[Controls]` do Azahar com binds `engine:sdl` (GUIDs
  verificados no SDL_GameControllerDB) + fotografa/aplica presets Hub em
  `dados/presets/controles/`. Azahar lê no boot — aplique com ele fechado
  (o play do Hub aplica sozinho, como os presets gráficos).
- Testa apertos por polling (viewer), sem rede, stdlib só.
"""
from __future__ import annotations

import configparser
import os
import shutil
import sys
import time
from pathlib import Path

# GUIDs SDL verificados (gamecontrollerdb, platform Windows).
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

# 3DS <- pad (posicional: B=baixo, A=direita, Y=esquerda, X=cima).
# ("btn", i) | ("eixo", i, "+/-") | ("chapeu", 0, "up/down/left/right").
MAPAS = {
    "xbox360": {"button_b": ("btn", 0), "button_a": ("btn", 1),
                "button_y": ("btn", 2), "button_x": ("btn", 3),
                "button_l": ("btn", 4), "button_r": ("btn", 5),
                "button_zl": ("eixo", 2, "+"), "button_zr": ("eixo", 2, "-"),
                "button_start": ("btn", 7), "button_select": ("btn", 6),
                "button_home": ("btn", 5),
                "dpad": ("chapeu", 0), "analog_esq": (0, 1),
                "analog_dir": (3, 4)},
    "xboxone": {"button_b": ("btn", 0), "button_a": ("btn", 1),
                "button_y": ("btn", 2), "button_x": ("btn", 3),
                "button_l": ("btn", 4), "button_r": ("btn", 5),
                "button_zl": ("eixo", 2, "+"), "button_zr": ("eixo", 5, "+"),
                "button_start": ("btn", 7), "button_select": ("btn", 6),
                "button_home": ("btn", 5),
                "dpad": ("chapeu", 0), "analog_esq": (0, 1),
                "analog_dir": (3, 4)},
    "ps4": {"button_b": ("btn", 1), "button_a": ("btn", 2),
            "button_y": ("btn", 0), "button_x": ("btn", 3),
            "button_l": ("btn", 4), "button_r": ("btn", 5),
            "button_zl": ("eixo", 3, "+"), "button_zr": ("eixo", 4, "+"),
            "button_start": ("btn", 9), "button_select": ("btn", 8),
            "button_home": ("btn", 12),
            "dpad": ("chapeu", 0), "analog_esq": (0, 1),
            "analog_dir": (2, 5)},
    "dualsense": {"button_b": ("btn", 1), "button_a": ("btn", 2),
                  "button_y": ("btn", 0), "button_x": ("btn", 3),
                  "button_l": ("btn", 4), "button_r": ("btn", 5),
                  "button_zl": ("eixo", 3, "+"),
                  "button_zr": ("eixo", 4, "+"),
                  "button_start": ("btn", 9), "button_select": ("btn", 8),
                  "button_home": ("btn", 12),
                  "dpad": ("chapeu", 0), "analog_esq": (0, 1),
                  "analog_dir": (2, 5)},
    "switchpro": {"button_b": ("btn", 0), "button_a": ("btn", 1),
                  "button_y": ("btn", 2), "button_x": ("btn", 3),
                  "button_l": ("btn", 4), "button_r": ("btn", 5),
                  "button_zl": ("btn", 6), "button_zr": ("btn", 7),
                  "button_start": ("btn", 9), "button_select": ("btn", 8),
                  "button_home": ("btn", 12),
                  "dpad": ("chapeu", 0), "analog_esq": (0, 1),
                  "analog_dir": (2, 3)},
}

BOTOES_3DS = ("button_a", "button_b", "button_x", "button_y", "button_l",
              "button_r", "button_zl", "button_zr", "button_start",
              "button_select", "button_home")

DIRECOES = (("up", "-y"), ("down", "+y"), ("left", "-x"), ("right", "+x"))


def _escapar(texto: str) -> str:
    """Escape ParamPackage aninhado (`$`->`$0`, `:`->`$`, `,`->`$1`).

    Confirmado nos inis do próprio Azahar (`modifier:code$068$1engine...`
    = `{code:68, engine:keyboard}`).
    """
    return texto.replace("$", "$0").replace(":", "$").replace(",", "$1")


def _serializar(pares: list[tuple[str, str]]) -> str:
    return ",".join(f"{k}:{v}" for k, v in pares)


def bind_botao(guid: str, port: int, spec: tuple) -> str:
    """Bind digital/hat/eixo no formato `engine:sdl` do Azahar."""
    if spec[0] == "btn":
        return _serializar([("button", str(spec[1])), ("engine", "sdl"),
                            ("guid", guid), ("port", str(port))])
    if spec[0] == "eixo":
        return _serializar([("axis", str(spec[1])),
                            ("direction", spec[2]), ("engine", "sdl"),
                            ("guid", guid), ("port", str(port)),
                            ("threshold", "0.5")])
    if spec[0] == "chapeu":
        return _serializar([("direction", spec[2]), ("engine", "sdl"),
                            ("guid", guid), ("hat", str(spec[1])),
                            ("port", str(port))])
    raise ValueError(f"spec inválida: {spec!r}")


def bind_analogico(guid: str, port: int, eixo_x: int, eixo_y: int) -> str:
    """Analog real como 4 sub-binds (padrão `SetAnalogButton` do Azahar)."""
    subs = []
    for nome, par in (("up", (eixo_y, "-")), ("down", (eixo_y, "+")),
                      ("left", (eixo_x, "-")), ("right", (eixo_x, "+"))):
        subs.append((nome, _escapar(_serializar(
            [("axis", str(par[0])), ("direction", par[1]),
             ("engine", "sdl"), ("guid", guid), ("port", str(port)),
             ("threshold", "0.5")]))))
    return _serializar([("engine", "analog_from_button")] + subs
                       + [("deadzone", "0.15"), ("modifier_scale", "0.5")])


def gerar_perfil(tipo: str, guid: str = "", port: int = 0) -> dict:
    """Mapa 3DS completo p/ chaves `profiles\\1\\*` do ini (puro, testável).

    EXPERIMENTAL: GUIDs/índices verificados no SDL_GameControllerDB, mas o
    Azahar 2126 resetou binds `engine:sdl` de teste p/ teclado em 5 boots
    (detalhe no `.md`). Fluxo confiável hoje: mapear 1x no Azahar e usar
    `fotografar_perfil()` — o gerador serve de ponto de partida/inspeção.
    """
    if tipo not in MAPAS:
        raise ValueError(f"tipo desconhecido: {tipo}")
    guid = guid or GUIDS[tipo]
    mapa = MAPAS[tipo]
    perfil = {}
    for chave in BOTOES_3DS:
        perfil[f"profiles\\1\\{chave}"] = bind_botao(guid, port, mapa[chave])
    hat = mapa["dpad"][1]
    perfil["profiles\\1\\button_up"] = bind_botao(
        guid, port, ("chapeu", hat, "up"))
    perfil["profiles\\1\\button_down"] = bind_botao(
        guid, port, ("chapeu", hat, "down"))
    perfil["profiles\\1\\button_left"] = bind_botao(
        guid, port, ("chapeu", hat, "left"))
    perfil["profiles\\1\\button_right"] = bind_botao(
        guid, port, ("chapeu", hat, "right"))
    ex, ey = mapa["analog_esq"]
    dx, dy = mapa["analog_dir"]
    perfil["profiles\\1\\circle_pad"] = bind_analogico(guid, port, ex, ey)
    perfil["profiles\\1\\c_stick"] = bind_analogico(guid, port, dx, dy)
    return perfil


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
    """Guarda o `[Controls]` atual como preset Hub (molde salvar_preset)."""
    from bib_nucleo.base import slugify
    if not (nome or "").strip():
        return {"ok": False, "erro": "nome de preset vazio."}
    slug = slugify(nome)
    ini, _ = _ler_controls()
    if not ini.has_section("Controls"):
        return {"ok": False,
                "erro": "config do Azahar não encontrada (abra-o uma vez)."}
    dest = _presets_dir() / f"{slug}.ini"
    foto = configparser.ConfigParser()
    foto.optionxform = str  # type: ignore[assignment]
    foto.add_section("Controls")
    for k, v in ini.items("Controls"):
        foto.set("Controls", k, v)
    try:
        with open(dest, "w", encoding="utf-8") as fh:
            foto.write(fh)
    except OSError as e:
        return {"ok": False, "erro": f"falha ao gravar: {e}"}
    return {"ok": True, "preset": slug, "arquivo": str(dest)}


def aplicar_preset_controle(nome: str) -> dict:
    """Mescla preset Hub sobre o `[Controls]` live (Azahar fechado!)."""
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
        novo = configparser.ConfigParser()
        novo.optionxform = str  # type: ignore[assignment]
        novo.read(alvo, encoding="utf-8")
        if not ini.has_section("Controls"):
            ini.add_section("Controls")
        if novo.has_section("Controls"):
            for k, valor in novo.items("Controls"):
                ini.set("Controls", k, valor)
        with cfg.open("w", encoding="utf-8") as fh:
            ini.write(fh)
    except (OSError, configparser.Error) as e:
        return {"ok": False, "erro": f"falha ao mesclar: {e}"}
    return {"ok": True, "preset": slug, "config": str(cfg)}


def salvar_mapa_gerado(tipo: str, guid: str = "", port: int = 0,
                       nome: str = "") -> dict:
    """Gera o mapa padrão e grava como preset Hub (sem tocar no live)."""
    from bib_nucleo.base import slugify
    try:
        perfil = gerar_perfil(tipo, guid, port)
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
    import ctypes
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
    n = (nome or "").lower()
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


def _listar_linux() -> list[dict]:
    """Nomes de joypads via /proc (sem polling: exige evdev)."""
    out = []
    try:
        texto = Path("/proc/bus/input/devices").read_text(encoding="utf-8",
                                                           errors="ignore")
    except OSError:
        return []
    nome, tem_js = "", False
    for linha in texto.splitlines():
        if linha.startswith("N: Name="):
            nome = linha.split("=", 1)[1].strip().strip('"')
            tem_js = False
        elif linha.startswith("H: Handlers=") and "js" in linha.split():
            tem_js = True
        elif not linha.strip() and nome and tem_js:
            out.append({"indice": len(out), "nome": nome, "botoes": 0,
                        "eixos": 0, "xinput": False,
                        "familia": _familia_por_nome(nome, False)})
            nome, tem_js = "", False
    return out


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


XINPUT_NOMES = {0: "A", 1: "B", 2: "X", 3: "Y", 4: "Start", 5: "Guia",
                6: "Back", 7: "L3", 8: "R3", 9: "LB", 10: "RB",
                12: "↑", 13: "↓", 14: "←", 15: "→"}


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

    poll() -> {"botoes": set[int], "eixos": {nome: valor}}.
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
        pov = (est.get("pov", 65535) or 65535)
        if pov != 65535:
            return {"ok": True, "tipo": "chapeu", "indice": 0,
                    "direcao": str(pov)}
        time.sleep(0.05)
    return {"ok": False, "erro": "tempo esgotado."}


__all__ = ['GUIDS', 'NOMES_TIPO', 'MAPAS', 'BOTOES_3DS', 'gerar_perfil',
           'bind_botao', 'bind_analogico', 'listar_controles',
           'ler_perfil_atual', 'fotografar_perfil', 'listar_presets_controle',
           'aplicar_preset_controle', 'salvar_mapa_gerado', 'ler_estado_xinput',
           'resumir_estado', 'capturar']
