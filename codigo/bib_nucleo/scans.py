#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Achados: confiança, Hydra, disco, fontes, ROMs 3DS e importação."""
from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import struct
import uuid as uuid_mod
import zlib
from pathlib import Path

from bib_nucleo.banco import (STATUS_VALIDOS, chave_dedup, normalizar_etiquetas, normalizar_mods,
                                salvar_capa_bytes)
from bib_nucleo.base import (LINUX_ROOT, WIN_ROOT, agora_iso,
                             existe_aqui_ou_traduzido, slugify, traduzir_para_atual,
                             win_para_linux)
from bib_nucleo.emuladores import (default_emu_3ds, default_emu_nds,
                                     provedores,
                                     provedor_por_extensao, provedor_por_origem)


# --------------------------------------------------------------------------
# Confiança (preview de importação)
# --------------------------------------------------------------------------

SHOPS_CONHECIDAS = {
    "steam", "gog", "epic", "fitgirl", "steamrip",
    "dodi", "online-fix", "onlinefix", "xbox", "riot",
}


def pontuar(item: dict) -> dict:
    """Enriquece um achado com score 0..1, motivos e existência do exe."""
    score = 0.0
    motivos: list[str] = []
    exe = (item.get("executable_path") or "").strip()
    existe, traduzido = existe_aqui_ou_traduzido(exe)
    if exe and existe and traduzido == exe:
        score += 0.5
        motivos.append("executável existe neste SO")
    elif existe:
        score += 0.3
        motivos.append("executável existe no outro SO (traduzido)")
    elif exe:
        motivos.append("executável não encontrado em nenhum SO")
    shop = (item.get("shop") or "").strip().lower()
    if shop in SHOPS_CONHECIDAS:
        score += 0.15
        motivos.append(f"loja conhecida ({shop})")
    elif shop:
        score += 0.05
        motivos.append(f"loja: {shop}")
    if (item.get("object_id") or "").strip():
        score += 0.1
        motivos.append("tem objectId")
    try:
        horas = float(item.get("horas") or 0)
    except (TypeError, ValueError):
        horas = 0.0
    if horas > 0:
        score += 0.15
        motivos.append(f"{horas}h jogadas")
    if (item.get("origem") or "") in ("steam-manifest", "epic", "gog", "riot"):
        score += 0.1
        motivos.append("manifesto da loja")
    if (item.get("origem") or "").startswith("rom-"):
        rp = ((item.get("rom_path") or "").strip()
              or (item.get("launch_options") or "").strip())
        if rp:
            if Path(rp).exists():
                score += 0.5
                motivos.append("ROM existe neste SO")
            else:
                tr = traduzir_para_atual(rp)
                if tr != rp and Path(tr).exists():
                    score += 0.3
                    motivos.append("ROM existe no outro SO (traduzida)")
    if item.get("tem_metadados"):
        score += 0.1
        motivos.append("metadados internos lidos")
    out = dict(item)
    out["score"] = round(min(1.0, score), 2)
    out["motivos"] = motivos
    out["exe_existe"] = existe
    out["exe_traduzido"] = traduzido
    return out


def hydra_db_candidates() -> list[Path]:
    cands: list[Path] = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        cands.append(Path(appdata) / "hydralauncher" / "hydra-db")
        cands.append(Path(appdata) / "hydra" / "hydra-db")
    home = Path.home()
    cands.append(home / ".config" / "hydralauncher" / "hydra-db")
    cands.append(home / ".config" / "hydra" / "hydra-db")
    cands.append(home / ".var" / "app" / "io.github.hydralauncher.hydra" / "config" / "hydralauncher" / "hydra-db")
    cands.append(home / ".var" / "app" / "io.github.hydralauncher.hydra" / "config" / "hydra" / "hydra-db")
    if appdata:
        cands.append(Path(appdata) / "hydralauncher" / "hydra-db-staging")
        cands.append(Path(appdata) / "hydra" / "hydra-db-staging")
    cands.append(home / ".config" / "hydralauncher" / "hydra-db-staging")
    cands.append(home / ".config" / "hydra" / "hydra-db-staging")
    env = os.environ.get("HYDRA_DB_PATH")
    if env:
        cands.insert(0, Path(env))
    return cands


def find_hydra_db() -> Path | None:
    for p in hydra_db_candidates():
        try:
            if p.is_dir() and any(p.iterdir()):
                return p
        except OSError:
            continue
    return None


TITLE_RE = re.compile(r'"title"\s*:\s*"((?:[^"\\]|\\.)+)"')

EXEC_RE = re.compile(r'"executablePath"\s*:\s*(null|"((?:[^"\\]|\\.)*)")')

SHOP_RE = re.compile(r'"shop"\s*:\s*"((?:[^"\\]|\\.)+)"')

OBJID_RE = re.compile(r'"objectId"\s*:\s*"((?:[^"\\]|\\.)+)"')

PLAYTIME_RE = re.compile(r'"playTimeInMilliseconds"\s*:\s*(\d+)')


def _unescape(s: str) -> str:
    try:
        return json.loads(f'"{s}"')
    except Exception:
        return s


def scan_hydra_db(db_dir: Path, limite_bytes_por_arquivo: int = 20_000_000) -> list[dict]:
    """Varredura bruta dos arquivos do LevelDB. Retorna [{'titulo', ...}]."""
    achados: dict[str, dict] = {}
    arquivos = [p for p in db_dir.rglob("*") if p.is_file() and p.suffix.lower() in (".log", ".ldb", ".sst", ".db", "")]
    for arq in arquivos:
        try:
            if arq.stat().st_size > limite_bytes_por_arquivo:
                continue
            data = arq.read_bytes()
        except OSError:
            continue
        texto = data.decode("utf-8", errors="ignore")
        matches = list(TITLE_RE.finditer(texto))
        for i, m in enumerate(matches):
            fim_janela = m.start() + 8000
            if i + 1 < len(matches):
                fim_janela = min(fim_janela, matches[i + 1].start())
            janela = texto[m.start():fim_janela]
            if "objectId" not in janela and "executablePath" not in janela and "shop" not in janela:
                continue
            titulo = _unescape(m.group(1)).strip()
            if not titulo or len(titulo) > 200:
                continue
            me = EXEC_RE.search(janela)
            exe = ""
            if me:
                exe = "" if me.group(1) == "null" else _unescape(me.group(2) or "")
            ms = SHOP_RE.search(janela)
            shop = _unescape(ms.group(1)) if ms else ""
            mo = OBJID_RE.search(janela)
            objid = _unescape(mo.group(1)) if mo else ""
            mp = PLAYTIME_RE.search(janela)
            horas = round(int(mp.group(1)) / 3_600_000, 2) if mp else 0.0
            chave = f"{titulo}\x00{exe}"
            if chave not in achados:
                achados[chave] = {
                    "titulo": titulo,
                    "executable_path": exe or "",
                    "shop": shop,
                    "object_id": objid,
                    "horas": horas,
                    "origem": "hydra",
                }
            elif horas > achados[chave].get("horas", 0):
                achados[chave]["horas"] = horas
    return sorted(achados.values(), key=lambda j: j["titulo"].lower())


# Scanner de disco (D:\\Games, SteamLibrary, Riot...) + manifests Steam
# --------------------------------------------------------------------------

SKIP_DIRS = {
    "windowsapps", "system volume information", "$recycle.bin",
    ".pnpm-store", "msdownld.tmp", "found.000", "wpsystem",
    "backups", "capas", "presets", "sessoes", "saves", "mods", "musicas",
    "texturas", ".hub-lixo", "baixados",
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
    base = LINUX_ROOT.rstrip("/")
    roots = [f"{base}/Games", f"{base}/SteamLibrary"]
    # Steam nativo do Linux (fora da partilha): só entra se existir
    for cand in (Path.home() / ".steam/steam/steamapps",
                 Path.home() / ".local/share/Steam/steamapps"):
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
    achados, info = scan_discos(roots, retornar_info=True)
    return roots, [pontuar(j) for j in achados], info


# --------------------------------------------------------------------------
# Ler do disco: todas as fontes de jogos instalados (não só o Hydra)
# --------------------------------------------------------------------------

JUNK_PROG_RE = re.compile(
    r"(?i)(redistributable|\bredist\b|\bsdk\b|driver|update for |security update|"
    r"hotfix|\bkb\d{6,}|\blanguage pack\b|help viewer|visual studio|\bdotnet\b|"
    r"directx|vulkan|physx|anticheat|easyanticheat|\beac\b|prerequisites)"
)


def _detector_hydra() -> tuple[str, list[dict], str]:
    db = find_hydra_db()
    if db is None:
        return "Hydra", [], "ausente neste PC"
    try:
        itens = scan_hydra_db(db)
    except Exception as e:
        return "Hydra", [], f"falha ao ler: {e}"
    for it in itens:
        it["fonte"] = "Hydra"
    return "Hydra", itens, f"{len(itens)} em {db}"


def _steamapps_dirs() -> list[Path]:
    cands: list[Path] = []
    if os.name == "nt":
        pf86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        pf = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        cands += [pf86 / "Steam/steamapps", pf / "Steam/steamapps"]
    else:
        h = Path.home()
        cands += [h / ".local/share/Steam/steamapps", h / ".steam/steam/steamapps"]
    for r in default_scan_roots():
        cands.append(Path(r) / "steamapps")
        cands.append(Path(r))  # a raiz pode SER o steamapps
    vistas: list[Path] = []
    for c in cands:
        try:
            if c.is_dir() and c not in vistas:
                vistas.append(c)
        except OSError:
            pass
    # libraryfolders.vdf revela bibliotecas fora do padrão
    extras: list[Path] = []
    for c in vistas:
        vdf = c / "libraryfolders.vdf"
        try:
            txt = vdf.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in re.finditer(r'"path"\s+"((?:[^"\\]|\\.)+)"', txt):
            p = Path(_unescape(m.group(1)))
            cand = p / "steamapps" if (p / "steamapps").is_dir() else p
            try:
                if cand.is_dir() and cand not in vistas and cand not in extras:
                    extras.append(cand)
            except OSError:
                pass
    return vistas + extras


def _appid_de_manifest(nome_arq: str) -> str:
    m = re.search(r"appmanifest_(\d+)\.acf$", (nome_arq or "").lower())
    return m.group(1) if m else ""


def _item_steam_manifest(txt: str, dirpath: str, appid: str = "") -> dict | None:
    mn = ACF_NAME_RE.search(txt)
    md = ACF_DIR_RE.search(txt)
    nome = mn.group(1).strip() if mn else None
    if not nome or ("Steam" in nome and "Runtime" in nome):
        return None
    if "redistributable" in nome.lower():
        return None  # Steamworks Common Redistributables etc.: só suporte
    exe = ""
    if md:
        cand_dir = Path(dirpath) / "common" / md.group(1).strip()
        if cand_dir.is_dir():
            try:
                exes = sorted(
                    x for x in cand_dir.iterdir()
                    if x.is_file() and x.suffix.lower() == ".exe"
                    and not SKIP_EXE_RE.search(x.name)
                )
                if exes:
                    exe = str(exes[0])
            except OSError:
                pass
    return {"titulo": nome, "executable_path": exe, "shop": "steam",
            "object_id": appid, "horas": 0.0, "origem": "steam-manifest",
            "fonte": "Steam"}


def _detector_steam(steamapps: list[Path] | None = None) -> tuple[str, list[dict], str]:
    alvos = steamapps if steamapps is not None else _steamapps_dirs()
    # fora o que o scan de disco já cobre (evita duplicar no preview)
    cobertas = [Path(r) for r in default_scan_roots()]
    noveis = [c for c in alvos
              if not any(c == b or b in c.parents for b in cobertas)]
    achados: dict[str, dict] = {}
    olhadas = 0
    for c in noveis:
        try:
            acfs = sorted(c.glob("appmanifest_*.acf"))
        except OSError:
            continue
        if not acfs:
            continue
        olhadas += 1
        for arq in acfs:
            try:
                txt = arq.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            it = _item_steam_manifest(txt, str(c), _appid_de_manifest(arq.name))
            if it:
                achados.setdefault(f"{it['titulo'].lower()}\x00{it['executable_path'].lower()}", it)
    det = f"{len(achados)} em {olhadas} biblioteca(s)" if olhadas else "Steam ausente"
    return "Steam", list(achados.values()), det


def _detector_epic(manifests: Path | None = None) -> tuple[str, list[dict], str]:
    if manifests is None:
        if os.name == "nt":
            pd = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
            manifests = pd / "Epic/EpicGamesLauncher/Data/Manifests"
        else:
            return "Epic", [], "só no Windows"
    achados: dict[str, dict] = {}
    try:
        arquivos = sorted(manifests.glob("*.item")) if manifests.is_dir() else []
    except OSError:
        arquivos = []
    if not arquivos:
        return "Epic", [], "sem manifestos"
    for arq in arquivos:
        try:
            d = json.loads(arq.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict):
            continue
        nome = (d.get("DisplayName") or "").strip()
        if not nome:
            continue
        inst = (d.get("InstallLocation") or "").strip()
        exe = ""
        lan = (d.get("LaunchExecutable") or "").strip().replace("/", os.sep)
        if inst and lan:
            cand = str(Path(inst) / lan)
            exe = cand
        achados.setdefault(nome.lower(), {
            "titulo": nome, "executable_path": exe, "shop": "epic",
            "object_id": (d.get("AppName") or "").strip(),
            "horas": 0.0, "origem": "epic", "fonte": "Epic",
        })
    return "Epic", list(achados.values()), f"{len(achados)} manifesto(s)"


def _detector_gog(roots: list[str] | None = None) -> tuple[str, list[dict], str]:
    alvos = roots if roots is not None else default_scan_roots()
    achados: dict[str, dict] = {}
    vistos = 0
    for raiz in alvos:
        rp = Path(raiz)
        if not rp.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(rp):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            try:
                if len(Path(dirpath).relative_to(rp).parts) > 4:
                    dirnames[:] = []
                    continue
            except ValueError:
                dirnames[:] = []
                continue
            for fn in filenames:
                if vistos >= 20_000:
                    break
                if not fn.lower().startswith("goggame-") or not fn.lower().endswith(".info"):
                    continue
                vistos += 1
                full = Path(dirpath) / fn
                try:
                    d = json.loads(full.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if not isinstance(d, dict):
                    continue
                nome = (d.get("name") or "").strip() or full.parent.name
                exe = ""
                try:
                    tasks = d.get("playTasks") or []
                    rel = (tasks[0].get("path") or "").strip().replace("/", os.sep).lstrip("\\/")
                    if rel:
                        exe = str(full.parent / rel)
                except (IndexError, AttributeError, TypeError):
                    pass
                achados.setdefault(nome.lower(), {
                    "titulo": nome, "executable_path": exe, "shop": "gog",
                    "object_id": str(d.get("gameId") or ""), "horas": 0.0,
                    "origem": "gog", "fonte": "GOG",
                })
    det = f"{len(achados)} jogo(s)" if achados else "sem goggame-*.info nas raízes"
    return "GOG", list(achados.values()), det


def _detector_riot(arqs: list[Path] | None = None) -> tuple[str, list[dict], str]:
    if arqs is None:
        arqs = []
        if os.name == "nt":
            pd = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
            arqs.append(pd / "Riot Games/RiotClientInstalls.json")
    achados: dict[str, dict] = {}
    achou_arq = False
    for arq in arqs:
        try:
            d = json.loads(arq.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict):
            continue
        achou_arq = True
        dirs: dict[str, str] = {}
        assoc = d.get("associated_client")
        if isinstance(assoc, dict):
            dirs.update({str(k): str(v) for k, v in assoc.items()})
        for k in ("rc_default", "rc_live"):
            if d.get(k):
                dirs.setdefault(k, str(d[k]))
        for _nome, inst in dirs.items():
            inst = (inst or "").strip()
            if not inst:
                continue
            exe = inst if inst.lower().endswith(".exe") else str(
                Path(inst) / "RiotClientServices.exe")
            if os.name == "nt":
                exe = exe.replace("/", "\\")  # json vem com /; dedupe + exibe igual
            achados.setdefault(exe.lower(), {
                "titulo": "Riot Client", "executable_path": exe,
                "shop": "riot", "object_id": "", "horas": 0.0,
                "origem": "riot", "fonte": "Riot",
            })
    det = f"{len(achados)} instalação(ões)" if achou_arq else "Riot ausente"
    return "Riot", list(achados.values()), det


def _detector_windows() -> tuple[str, list[dict], str]:
    if os.name != "nt":
        return "Windows", [], "só no Windows"
    import winreg
    chaves = [
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    achados: dict[str, dict] = {}
    for raiz, sub in chaves:
        try:
            h = winreg.OpenKey(raiz, sub)
        except OSError:
            continue
        try:
            n = winreg.QueryInfoKey(h)[0]
            for i in range(min(n, 5000)):
                try:
                    nome_sub = winreg.EnumKey(h, i)
                except OSError:
                    continue
                try:
                    with winreg.OpenKey(h, nome_sub) as k:
                        def _sv(campo):
                            try:
                                v, _t = winreg.QueryValueEx(k, campo)
                                return v
                            except OSError:
                                return None
                        if _sv("SystemComponent"):
                            continue
                        titulo = (_sv("DisplayName") or "").strip()
                        if not titulo or JUNK_PROG_RE.search(titulo):
                            continue
                        exe = ""
                        icon = (_sv("DisplayIcon") or "").strip()
                        if icon:
                            cand = icon.split(",")[0].strip().strip('"')
                            base = cand.lower()
                            if base.endswith(".exe") and not re.match(
                                    r"(?i)^(unins|uninstall|setup)",
                                    Path(base).name):
                                exe = cand  # desinstalador não é jogo
                        achados.setdefault(titulo.lower(), {
                            "titulo": titulo, "executable_path": exe,
                            "shop": "", "object_id": "",
                            "horas": 0.0, "origem": "win",
                            "fonte": "Windows",
                        })
                except OSError:
                    continue
        finally:
            try:
                winreg.CloseKey(h)
            except OSError:
                pass
    return "Windows", list(achados.values()), f"{len(achados)} programa(s)"


def ler_do_disco() -> tuple[list[dict], dict]:
    """Todas as fontes de jogos instalados, de uma vez (só leitura).

    (itens pontuados ordenados, info{fontes:[{fonte, ok, n, detalhe}], total}).
    Nunca levanta: fonte que falha entra como ok=False.
    """
    detectores = (("Hydra", _detector_hydra), ("Steam", _detector_steam),
                  ("Epic", _detector_epic), ("GOG", _detector_gog),
                  ("Riot", _detector_riot), ("Windows", _detector_windows))
    itens: list[dict] = []
    fontes: list[dict] = []
    for nome, det in detectores:
        try:
            fonte, achados, detalhe = det()
            fontes.append({"fonte": fonte, "ok": True, "n": len(achados),
                           "detalhe": detalhe})
            itens.extend(achados)
        except Exception as e:
            fontes.append({"fonte": nome, "ok": False, "n": 0,
                           "detalhe": f"falha: {e}"})
    pont = fundir_duplicados(itens)
    pont.sort(key=lambda j: j["titulo"].lower())
    return pont, {"fontes": fontes, "total": len(pont)}


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


EXE_IMPORTAVEIS = {".exe", ".lnk", ".bat", ".cmd", ".sh", ".AppImage"}


def analisar_arquivo(caminho: str) -> dict:
    """Classifica UM caminho p/ a importação unificada. Só leitura.

    Retorna {"tipo", "item", "provedor", "detalhe", "aviso"} onde tipo é
    'pasta' | 'rom' | 'jogo' | 'json' | 'pacote' | 'arquivo-jogo' |
    'desconhecido'. 'pacote' é só o portátil do Hub (com biblioteca.json);
    outro .zip/.rar/.7z/.iso é repack (extrai p/ Piratas e importa).
    Emulador ausente NÃO bloqueia: a ROM importa e o aviso orienta (⬇).
    """
    vazio = {"tipo": "desconhecido", "item": None, "provedor": None,
             "detalhe": "", "aviso": None}
    p = Path((caminho or "").strip())
    if not p.exists():
        return {**vazio, "detalhe": "caminho não existe."}
    if p.is_dir():
        return {**vazio, "tipo": "pasta",
                "detalhe": f"pasta: varre jogos de PC + ROMs ({p})."}
    ext = p.suffix.lower()
    if ext == ".json":
        return {**vazio, "tipo": "json", "detalhe": "lista de jogos (JSON)."}
    from bib_nucleo.repacks import ARQUIVO_EXTS, eh_pacote_hub  # sem ciclo
    if ext == ".zip" and eh_pacote_hub(p):
        return {**vazio, "tipo": "pacote",
                "detalhe": "pacote portátil (.zip) — tenta restaurar."}
    if ext in ARQUIVO_EXTS:
        return {**vazio, "tipo": "arquivo-jogo",
                "detalhe": (f"repack ({p.name}): extrai p/ Piratas, organiza, "
                            "acha o exe e importa.")}
    prov = provedor_por_extensao(ext)
    if prov is not None:
        emu = prov["exe"]() or ""
        item = pontuar(_item_rom(str(p), emu, prov))
        aviso = None
        if not emu:
            aviso = (f"{prov['nome']} não instalado — a ROM importa mesmo assim; "
                     f"depois instale com 'Atualizar {prov['nome']}'.")
        return {"tipo": "rom", "item": item, "provedor": prov["chave"],
                "detalhe": (f"ROM { '/'.join(prov['sistemas'])} → {prov['nome']} "
                            f"· '{item['titulo']}'"),
                "aviso": aviso}
    if ext in EXE_IMPORTAVEIS or not ext:
        item = pontuar({
            "titulo": _titulo_de_exe(p), "executable_path": str(p),
            "shop": "", "object_id": "",
            "horas": 0.0, "origem": "scan-disco",
        })
        aviso = None
        if SKIP_EXE_RE.search(p.name):
            aviso = "parece instalador/suporte (setup, redist…) — confira antes."
        return {"tipo": "jogo", "item": item, "provedor": None,
                "detalhe": f"jogo de PC (roda direto, sem emulador) · '{item['titulo']}'",
                "aviso": aviso}
    return {**vazio, "detalhe": (f"extensão '{ext or '?'}' não suportada "
                                 "(exe, ROM, .json, .zip ou pasta).")}


def preview_pasta(roots: list[str] | None = None) -> tuple[list[str], list[dict], dict]:
    """Uma varredura só: jogos de PC + ROMs nas mesmas raízes.

    (raízes_usadas, itens pontuados mistos e sem duplicatas,
    info{vistos, truncado, raizes, emu}).
    ROMs sem emulador vêm com exe vazio (importam; o play orienta).
    """
    if not roots:
        vistas: list[str] = []
        for r in default_scan_roots() + default_roms_roots() + default_roms_nds_roots():
            if r not in vistas:
                vistas.append(r)
        roots = vistas
    roots_u, itens_disco, info_d = preview_scan(roots)
    _r, itens_rom, info_r, emu = preview_roms(roots, None)
    _r, itens_nds, info_n, emu_nds = preview_roms(roots, None, "desmume")
    itens = sorted(fundir_duplicados(itens_disco + itens_rom + itens_nds),
                   key=lambda j: j["titulo"].lower())
    info = {"vistos": info_d["vistos"] + info_r["vistos"] + info_n["vistos"],
            "truncado": info_d["truncado"] or info_r["truncado"] or info_n["truncado"],
            "raizes": info_d["raizes"], "emu": emu, "emu_nds": emu_nds}
    return roots_u, itens, info


def _norm_titulo(t) -> str:
    return " ".join((t or "").casefold().split())


def _norm_caminho(c) -> str:
    """Mesmo arquivo em SOs distintos compara igual (D:\… == /run/media/…)."""
    c = (c or "").strip()
    if not c:
        return ""
    return win_para_linux(c).lower()


def _dobrar_fundido(atual: dict, novo: dict) -> None:
    """Funde `novo` dentro de `atual` (mesmo jogo, outra fonte)."""
    exe_a, exe_n = (atual.get("executable_path") or ""), (novo.get("executable_path") or "")
    # o exe que existe neste ou no outro SO vence; senão, o não-vazio
    troca = False
    for cand in (exe_n, exe_a):
        if cand and existe_aqui_ou_traduzido(cand)[0]:
            if cand != exe_a:
                atual["executable_path"] = cand
                atual["launch_options"] = novo.get("launch_options") or atual.get("launch_options")
                troca = True
            break
    else:
        if exe_n and not exe_a:
            atual["executable_path"] = exe_n
            atual["launch_options"] = novo.get("launch_options") or atual.get("launch_options")
            troca = True
    if (novo.get("horas") or 0) > (atual.get("horas") or 0):
        atual["horas"] = novo["horas"]
    for campo in ("shop", "object_id", "game_code", "regiao", "rom_path"):
        if not (atual.get(campo) or "") and (novo.get(campo) or ""):
            atual[campo] = novo[campo]
    if novo.get("tem_metadados"):
        atual["tem_metadados"] = True
    for f in novo.get("fontes", [novo.get("fonte") or novo.get("origem") or "?"]):
        if f and f not in atual["fontes"]:
            atual["fontes"].append(f)
    atual["fonte"] = "+".join(atual["fontes"])


def _compativel(atual: dict, novo: dict) -> bool:
    """Podem ser o mesmo jogo? ROMs: mesma rom. PC: exe igual ou ausente."""
    if (atual.get("origem") or "").startswith("rom-"):
        return _norm_caminho(atual.get("rom_path")) == _norm_caminho(novo.get("rom_path"))
    ea, en = _norm_caminho(atual.get("executable_path")), _norm_caminho(novo.get("executable_path"))
    return (not ea) or (not en) or (ea == en)


def fundir_duplicados(itens: list[dict]) -> list[dict]:
    """Junta achados repetidos do preview (mesmo jogo em N fontes).

    Grupo = mesmo título normalizado + mesmo kind (rom/pc). Dentro do grupo,
    exes diferentes e não-vazios = instalações distintas (separa); resto funde:
    herda o melhor exe, soma fontes/horas e re-pontua. Itens já pontuados são
    re-pontuados (idempotente).
    """
    grupos: dict[tuple, list[dict]] = {}
    ordem: list[tuple] = []
    for it in itens:
        t = _norm_titulo(it.get("titulo"))
        kind = "rom" if (it.get("origem") or "").startswith("rom-") else "pc"
        chave = (kind, t) if t else ("unico", id(it))
        if chave not in grupos:
            grupos[chave] = []
            ordem.append(chave)
        grupos[chave].append(dict(it))
    saidas: list[dict] = []
    for chave in ordem:
        fundidos: list[dict] = []
        for it in grupos[chave]:
            it["fontes"] = [it.get("fonte") or it.get("origem") or "?"]
            for f in fundidos:
                if _compativel(f, it):
                    _dobrar_fundido(f, it)
                    break
            else:
                fundidos.append(it)
        for f in fundidos:
            f["fonte"] = "+".join(f["fontes"])
            saida = pontuar(f)
            if len(f["fontes"]) > 1:
                saida["motivos"] = [*saida.get("motivos", []),
                                    f"achado também em: {', '.join(f['fontes'][1:])}"]
            saidas.append(saida)
    return saidas


# --------------------------------------------------------------------------
# Metadados internos de ROMs 3DS (NCSD/CCI, NCCH/CXI, 3DSX + SMDH)
# --------------------------------------------------------------------------

SMDH_IDIOMAS = ("Japonês", "Inglês", "Francês", "Alemão", "Italiano", "Espanhol",
                "Chinês Simplificado", "Coreano", "Holandês", "Português",
                "Russo", "Chinês Tradicional")

SMDH_REGIOES = ("Japão", "América do Norte", "Europa", "Austrália", "China",
                "Coreia", "Taiwan")


def _u32(buf: bytes, off: int) -> int:
    return int.from_bytes(buf[off:off + 4], "little")


def _parse_smdh(smdh: bytes) -> dict:
    if len(smdh) < 0x201C or smdh[:4] != b"SMDH":
        return {}
    nomes: list[str] = []
    for i in range(12):
        # Campo UTF-16LE de tamanho fixo: decodifica TUDO e corta no 1º NUL.
        # (Separar os BYTES por b"\x00\x00" quebra no meio do último char.)
        raw = smdh[0x8 + i * 0x200:0x8 + i * 0x200 + 0x80]
        try:
            nomes.append(raw.decode("utf-16-le").split("\x00")[0].strip())
        except Exception:
            nomes.append("")
    titulo, idioma = "", ""
    for i in (1, 0):
        if nomes[i]:
            titulo, idioma = nomes[i], SMDH_IDIOMAS[i]
            break
    if not titulo:
        for i, t in enumerate(nomes):
            if t:
                titulo, idioma = t, SMDH_IDIOMAS[i]
                break
    regs = [SMDH_REGIOES[b] for b in range(7) if _u32(smdh, 0x2018) & (1 << b)]
    out: dict = {}
    if titulo:
        out["titulo"] = titulo
        out["idioma_titulo"] = idioma
    if regs:
        out["regiao"] = "Livre" if len(regs) == 7 else ", ".join(regs)
    return out


def _ler_icon_bin(caminho: str) -> bytes:
    """Extrai o icon.bin (SMDH) bruto da ROM, ou b"" se não der."""
    p = Path(caminho)
    if not p.is_file():
        return b""
    with p.open("rb") as f:
        head = f.read(0x400)
        if len(head) < 0x204:
            return b""
        if head[:4] == b"3DSX":  # homebrew: SMDH ao final do cabeçalho
            if len(head) < 0x28:
                return b""
            off, size = _u32(head, 0x20), _u32(head, 0x24)
            if not off or not size or off > 64 * 1024 * 1024:
                return b""
            f.seek(off)
            return f.read(min(size, 0x4000))
        if head[0x100:0x104] == b"NCSD":  # .cci/.3ds
            if len(head) < 0x128:
                return b""
            base = _u32(head, 0x120) * 0x200
        elif head[0x100:0x104] == b"NCCH":  # .cxi
            base = 0
        else:
            return b""
        f.seek(base)
        ncch = f.read(0x300)
        if len(ncch) < 0x300 or ncch[0x100:0x104] != b"NCCH":
            return b""
        ex_off = base + _u32(ncch, 0x1A0) * 0x200
        if ex_off > 16 * 1024 ** 3:
            return b""
        f.seek(ex_off)
        exeh = f.read(0x200)
        if len(exeh) < 0x200:
            return b""
        for i in range(10):
            e = exeh[i * 16:(i + 1) * 16]
            if e[:8].rstrip(b"\x00") in (b"icon", b"icon.bin"):
                fo, fs = _u32(e, 8), _u32(e, 12)
                if not fs or fs > 0x4000:
                    return b""
                f.seek(ex_off + 0x200 + fo)
                return f.read(min(fs, 0x4000))
    return b""


def ler_metadados_3ds(caminho: str) -> dict:
    """Lê título/código/região de dentro da ROM. {} se não der (usa nome do arquivo)."""
    try:
        p = Path(caminho)
        if not p.is_file():
            return {}
        meta: dict = {}
        with p.open("rb") as f:
            head = f.read(0x400)
            if len(head) < 0x204:
                return {}
            if head[:4] == b"3DSX":
                pass  # sem product code; só SMDH abaixo
            elif head[0x100:0x104] == b"NCSD":
                if len(head) < 0x128:
                    return {}
                base = _u32(head, 0x120) * 0x200
                f.seek(base)
                ncch = f.read(0x300)
                if len(ncch) < 0x300 or ncch[0x100:0x104] != b"NCCH":
                    return {}
                code = ncch[0x150:0x160].split(b"\x00")[0].decode("ascii", "ignore").strip()
                if code:
                    meta["game_code"] = code
            elif head[0x100:0x104] == b"NCCH":
                f.seek(0)
                ncch = f.read(0x300)
                if len(ncch) >= 0x300 and ncch[0x100:0x104] == b"NCCH":
                    code = ncch[0x150:0x160].split(b"\x00")[0].decode("ascii", "ignore").strip()
                    if code:
                        meta["game_code"] = code
            else:
                return {}
        meta.update(_parse_smdh(_ler_icon_bin(caminho)))
        return meta
    except (OSError, ValueError, OverflowError):
        return {}


NDS_REGIOES = {"E": "América do Norte", "P": "Europa", "J": "Japão",
               "K": "Coreia", "D": "Alemanha", "F": "França", "I": "Itália",
               "S": "Espanha", "U": "Austrália"}


def _rgb555(v: int) -> bytes:
    return bytes((((v & 31) * 255 // 31), (((v >> 5) & 31) * 255 // 31),
                  (((v >> 10) & 31) * 255 // 31)))


def _ler_banner_nds(caminho: str) -> bytes:
    """Devolve o banner NDS (ícone + títulos) ou b''."""
    try:
        with Path(caminho).open("rb") as f:
            head = f.read(0x200)
            if len(head) < 0x200:
                return b""
            off = _u32(head, 0x68)
            if not off or off > 64 * 1024 * 1024:
                return b""
            f.seek(off)
            return f.read(0x2000)
    except (OSError, ValueError, OverflowError):
        return b""


def ler_metadados_nds(caminho: str) -> dict:
    """Lê título/código/região do header + banner NDS. {} se não der."""
    try:
        p = Path(caminho)
        if not p.is_file():
            return {}
        meta: dict = {}
        with p.open("rb") as f:
            head = f.read(0x200)
        if len(head) < 0x200:
            return {}
        titulo = head[:12].split(b"\x00")[0].decode("ascii", "ignore").strip()
        code = head[0x0C:0x10].split(b"\x00")[0].decode("ascii", "ignore").strip()
        if code:
            meta["game_code"] = code
            reg = NDS_REGIOES.get(code[-1:])
            if reg:
                meta["regiao"] = reg
        banner = _ler_banner_nds(caminho)
        if len(banner) >= 0x340:
            nomes = []
            for i in range(6):
                raw = banner[0x240 + i * 0x100:0x240 + i * 0x100 + 0x100]
                try:
                    txt = raw.decode("utf-16-le").split("\x00")[0]
                    txt = re.sub(r"\s+", " ", txt.replace("\u2028", " ")).strip()
                    nomes.append(txt)
                except Exception:
                    nomes.append("")
            def _limpa_nome_nds(s):
                s = re.sub(r"\s+Nintendo$", "", s).strip()  # última linha é a publisher
                return s

            for i in (1, 0):
                if i < len(nomes) and nomes[i]:
                    meta["titulo"] = _limpa_nome_nds(nomes[i])
                    meta["tem_metadados"] = True
                    break
            else:
                for t in nomes:
                    if t:
                        meta["titulo"] = _limpa_nome_nds(t)
                        meta["tem_metadados"] = True
                        break
        if titulo and "titulo" not in meta:
            meta["titulo"] = titulo
        return meta
    except (OSError, ValueError, OverflowError):
        return {}


def icone_nds_para_png(caminho: str, alvo_px: int = 96) -> bytes | None:
    """Decodifica o ícone 32x32 do banner NDS e devolve PNG (None se não der)."""
    try:
        banner = _ler_banner_nds(caminho)
        if len(banner) < 0x240:
            return None
        pal = [_rgb555(banner[0x220 + i * 2] | (banner[0x221 + i * 2] << 8))
               for i in range(16)]
        dados = banner[0x20:0x220]
        if len(dados) < 0x200:
            return None
        lado = 32
        rgb = bytearray(lado * lado * 3)
        for ty in range(4):
            for tx in range(4):
                base_t = (ty * 4 + tx) * 32  # tile 8x8 4bpp = 32 bytes
                for y in range(8):
                    for x in range(8):
                        b = dados[base_t + (y * 8 + x) // 2]
                        v = (b & 0x0F) if x % 2 == 0 else (b >> 4)
                        dst = ((ty * 8 + y) * lado + (tx * 8 + x)) * 3
                        rgb[dst:dst + 3] = pal[v]
        rgb = bytes(rgb)
        fator = max(1, alvo_px // lado)
        if fator > 1:
            amp = bytearray(lado * fator * lado * fator * 3)
            W = lado * fator
            for y in range(lado):
                for x in range(lado):
                    px = rgb[(y * lado + x) * 3:(y * lado + x) * 3 + 3]
                    for dy in range(fator):
                        base = ((y * fator + dy) * W + x * fator) * 3
                        amp[base:base + fator * 3] = px * fator
            rgb, lado = bytes(amp), W
        return _png_rgb(lado, lado, rgb)
    except Exception:
        return None


def _morton(x: int, y: int) -> int:
    z = 0
    for i in range(4):
        z |= ((x >> i) & 1) << (2 * i)
        z |= ((y >> i) & 1) << (2 * i + 1)
    return z


def _desembaralha_rgb565(dados: bytes, lado: int) -> bytes:
    """SMDH guarda o ícone em tiles 8x8 (ordem Morton). Devolve RGB888 linear."""
    n = lado * lado
    if len(dados) < n * 2:
        raise ValueError("ícone curto")
    rgb = bytearray(n * 3)
    tiles = lado // 8
    for ty in range(tiles):
        for tx in range(tiles):
            base_t = (ty * tiles + tx) * 64
            for y in range(8):
                for x in range(8):
                    src = (base_t + _morton(x, y)) * 2
                    v = dados[src] | (dados[src + 1] << 8)
                    r = ((v >> 11) & 31) * 255 // 31
                    g = ((v >> 5) & 63) * 255 // 63
                    b = (v & 31) * 255 // 31
                    dst = ((ty * 8 + y) * lado + (tx * 8 + x)) * 3
                    rgb[dst:dst + 3] = bytes((r, g, b))
    return bytes(rgb)


def _png_rgb(larg: int, alt: int, rgb: bytes) -> bytes:
    def bloco(tipo: bytes, dado: bytes) -> bytes:
        c = tipo + dado
        return struct.pack(">I", len(dado)) + c + struct.pack(
            ">I", zlib.crc32(c) & 0xFFFFFFFF)

    cab = struct.pack(">IIBBBBB", larg, alt, 8, 2, 0, 0, 0)
    corpo = b"".join(b"\x00" + rgb[y * larg * 3:(y + 1) * larg * 3]
                     for y in range(alt))
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", cab)
            + bloco(b"IDAT", zlib.compress(corpo)) + bloco(b"IEND", b""))


def icone_rom_para_png(caminho: str, alvo_px: int = 144) -> bytes | None:
    """Decodifica o ícone SMDH da ROM e devolve PNG RGB (None se não der).

    Ordem de tiles documentada (Morton 8x8); conferir visualmente na 1ª ROM real.
    """
    try:
        icon = _ler_icon_bin(caminho)
        if len(icon) >= 0x1680:
            rgb, lado = _desembaralha_rgb565(icon[:0x1200], 48), 48
        elif len(icon) >= 0x480:
            rgb, lado = _desembaralha_rgb565(icon[0x1200:0x1200 + 0x480], 24), 24
        else:
            return None
        fator = max(1, alvo_px // lado)
        if fator > 1:  # amplia por vizinho mais próximo (pixel nítido)
            amp = bytearray(lado * fator * lado * fator * 3)
            W = lado * fator
            for y in range(lado):
                for x in range(lado):
                    px = rgb[(y * lado + x) * 3:(y * lado + x) * 3 + 3]
                    for dy in range(fator):
                        base = ((y * fator + dy) * W + x * fator) * 3
                        amp[base:base + fator * 3] = px * fator
            rgb, lado = bytes(amp), W
        return _png_rgb(lado, lado, rgb)
    except Exception:
        return None


# --------------------------------------------------------------------------
# Importação / backup / capas
# --------------------------------------------------------------------------

def _capa_steam(appid: str, timeout: int = 15) -> bytes | None:
    """Baixa o header oficial da Steam (só leitura). None se offline/sem arte."""
    import urllib.request
    api = f"https://store.steampowered.com/api/appdetails?appids={appid}"
    req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    info = data.get(str(appid)) or {}
    if not info.get("success"):
        return None
    url = ((info.get("data") or {}).get("header_image") or "").split("?")[0]
    if not url.startswith("http"):
        return None
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(2_500_000)
    return raw if len(raw) >= 1024 else None


def _appid_steam_por_titulo(titulo: str, timeout: int = 15) -> str:
    """Acha o appid Steam pelo nome exato (normalizado). '' se nada.

    Nunca levanta (rede falhou = sem capa automática, sem travar import).
    """
    import urllib.parse
    import urllib.request
    alvo = re.sub(r"\s+", " ", (titulo or "")).strip().lower()
    if not alvo:
        return ""
    try:
        q = urllib.parse.urlencode({"term": titulo.strip(), "l": "english",
                                    "cc": "US"})
        req = urllib.request.Request(
            f"https://store.steampowered.com/api/storesearch/?{q}",
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            dados = json.loads(r.read().decode("utf-8"))
        for item in (dados.get("items") or []):
            if not isinstance(item, dict):
                continue
            nome = re.sub(r"\s+", " ", str(item.get("name") or "")).strip()
            if nome.lower() == alvo:
                appid = str(item.get("id") or "").strip()
                if appid.isdigit():
                    return appid
    except Exception:
        pass
    return ""


def importar_lista(con: sqlite3.Connection, itens: list[dict]) -> dict:
    """Importa jogos. Itens com uuid existente ATUALIZAM progresso (restore);
    sem uuid (scans) inserem. Retorna relatório (novos/atualizados/ignorados/erros)."""
    antes = con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()["n"]
    agora = agora_iso()
    novos = atualizados = ignorados = 0
    erros: list[str] = []
    avisos: list[str] = []
    vistos = {chave_dedup(r["titulo"], r["executable_path"], r["launch_options"])
              for r in con.execute(
                  "SELECT titulo, executable_path, launch_options, origem FROM jogos").fetchall()}
    # mesmo exe+lançamento com título diferente também é duplicata
    # (título de scan muda: "Hades2" virou "Hades 2" no exe do "Hades II")
    vistos_exe = {(t[1], t[2]) for t in vistos}
    # ROMs: o emulador muda por SO (azahar.exe × AppImage), então o par
    # (título, ROM) dedupa sozinho, sem o exe
    vistos_rom = set()
    for r in con.execute(
            "SELECT titulo, launch_options, origem FROM jogos").fetchall():
        if (r["origem"] or "").startswith("rom-") and (r["launch_options"] or "").strip():
            vistos_rom.add(chave_dedup(r["titulo"], "", r["launch_options"]))

    def _ignorar(motivo: str):
        nonlocal ignorados
        ignorados += 1
        if len(erros) < 20:
            erros.append(motivo)

    def _mods_seguro(v) -> str:
        try:
            return normalizar_mods(v)
        except ValueError:
            return "[]"

    for pos, j in enumerate(itens):
        if not isinstance(j, dict):
            _ignorar(f"item {pos}: não é objeto")
            continue
        j = {k: (v.replace("\x00", "") if isinstance(v, str) else v)
             for k, v in j.items()}
        if not isinstance(j.get("titulo"), str):
            _ignorar(f"item {pos}: título inválido")
            continue
        titulo = j["titulo"].strip()
        if not titulo:
            _ignorar(f"item {pos}: sem título")
            continue
        try:
            nota = j.get("nota")
            nota = None if nota in (None, "") else int(nota)
            if nota is not None and not 0 <= nota <= 10:
                nota = None
            horas = float(j.get("horas") or 0)
            if not math.isfinite(horas):
                raise ValueError("horas não finitas")
            if horas < 0:
                horas = 0.0
            confianca = float(j.get("score") or j.get("confianca") or 0)
            if not math.isfinite(confianca):
                raise ValueError("confiança não finita")
        except (TypeError, ValueError):
            _ignorar(f"'{titulo}': nota/horas inválidos")
            continue
        try:
            uid = (j.get("uuid") or "").strip() or None
            if uid is not None:
                alvo = con.execute("SELECT * FROM jogos WHERE uuid=?",
                                   (uid,)).fetchone()
            else:
                alvo = None
            if alvo is not None:
                # restore: progresso volta; identidade/caminhos ficam locais.
                # etiquetas voltam se o pacote as trouxe (scans não mandam).
                ultima = j.get("ultima_execucao", alvo["ultima_execucao"])
                etiq_alvo = alvo["etiquetas"] if "etiquetas" in alvo.keys() else ""
                con.execute(
                    """UPDATE jogos SET horas=?, ultima_execucao=?, status=?, nota=?,
                       favorito=?, observacoes=?, azahar_preset=?, etiquetas=?, atualizado_em=? WHERE id=?""",
                    (horas if "horas" in j else alvo["horas"], ultima,
                     j.get("status") if j.get("status") in STATUS_VALIDOS else alvo["status"],
                     nota if "nota" in j else alvo["nota"],
                     int(bool(j.get("favorito"))) if "favorito" in j else alvo["favorito"],
                     j.get("observacoes", alvo["observacoes"]),
                     j.get("azahar_preset", alvo["azahar_preset"]),
                     normalizar_etiquetas(j["etiquetas"]) if "etiquetas" in j else etiq_alvo,
                     j.get("atualizado_em") or agora, alvo["id"]),
                )
                atualizados += 1
                continue
            if uid is None:
                uid = uuid_mod.uuid4().hex
            chave = chave_dedup(titulo, (j.get("executable_path") or ""),
                                (j.get("launch_options") or ""))
            if chave in vistos or (chave[1] and (chave[1], chave[2]) in vistos_exe):
                ignorados += 1
                continue
            if ((j.get("origem") or "").startswith("rom-")
                    and (j.get("launch_options") or "").strip()
                    and chave_dedup(titulo, "", j.get("launch_options") or "") in vistos_rom):
                ignorados += 1
                continue
            cur = con.execute(
                   """INSERT OR IGNORE INTO jogos
                   (titulo, executable_path, exe_win, exe_linux, exe_mac, wine_prefix, launch_options,
                    status, nota, favorito, horas, ultima_execucao, observacoes, origem, shop, object_id,
                    game_code, regiao, azahar_preset, uuid, etiquetas, azahar_mods, azahar_mods_off,
                    confianca, criado_em, atualizado_em)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (titulo, (j.get("executable_path") or "").strip(),
                 (j.get("exe_win") or "").strip(), (j.get("exe_linux") or "").strip(),
                 (j.get("exe_mac") or "").strip(),
                 (j.get("wine_prefix") or ""), (j.get("launch_options") or ""),
                 j.get("status") if j.get("status") in STATUS_VALIDOS else "backlog",
                 nota, 1 if j.get("favorito") else 0,
                 horas, (j.get("ultima_execucao") or "").strip() or None,
                 (j.get("observacoes") or ""),
                 j.get("origem") or "manual", (j.get("shop") or ""),
                 (j.get("object_id") or ""), (j.get("game_code") or "").strip(),
                 (j.get("regiao") or "").strip(), (j.get("azahar_preset") or "").strip(),
                  uid, normalizar_etiquetas(j.get("etiquetas") or ""),
                  _mods_seguro(j.get("azahar_mods")),
                  1 if j.get("azahar_mods_off") else 0,
                  confianca, j.get("criado_em") or agora, j.get("atualizado_em") or agora),
            )
            novos += cur.rowcount
            if not cur.rowcount:
                ignorados += 1
            else:
                vistos.add(chave)
                vistos_exe.add((chave[1], chave[2]))
                if ((j.get("origem") or "").startswith("rom-")
                        and (j.get("launch_options") or "").strip()):
                    vistos_rom.add(chave_dedup(titulo, "", j.get("launch_options") or ""))
            prov_rom = provedor_por_origem(j.get("origem") or "")
            if cur.rowcount and prov_rom is not None:
                try:  # capa automática: ícone de dentro da própria ROM
                    rom = ((j.get("rom_path") or "").strip()
                           or (j.get("launch_options") or "").strip())
                    png = prov_rom["icone"](rom) if rom else None
                    if png:
                        salvar_capa_bytes(con, cur.lastrowid,
                                          slugify(titulo) + ".png", png)
                    elif len(avisos) < 20:
                        avisos.append(f"'{titulo}': sem ícone extraível na ROM")
                except Exception as e:
                    if len(avisos) < 20:
                        avisos.append(f"'{titulo}': capa falhou ({type(e).__name__})")
            if cur.rowcount and prov_rom is None:
                appid = ((j.get("object_id") or "").strip()
                         if (j.get("shop") or "").strip().lower() == "steam" else "")
                if appid and appid.isdigit():
                    try:  # capa automática: header oficial da Steam
                        raw = _capa_steam(appid)
                        if raw:
                            salvar_capa_bytes(con, cur.lastrowid,
                                              slugify(titulo) + ".jpg", raw)
                    except Exception as e:
                        if len(avisos) < 20:
                            avisos.append(f"'{titulo}': capa Steam falhou ({type(e).__name__})")
        except Exception as e:
            _ignorar(f"'{titulo}': {type(e).__name__}: {e}")
            continue
    con.commit()
    depois = con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()["n"]
    return {"novos": novos, "atualizados": atualizados, "ignorados": ignorados,
            "erros": erros, "avisos": avisos,
            "total_no_banco": depois, "antes": antes}


def resumo_importacao(res: dict) -> str:
    texto = (f"Novos: {res.get('novos', 0)} · atualizados: {res.get('atualizados', 0)} · "
             f"ignorados: {res.get('ignorados', 0)} · erros: {len(res.get('erros', []))}")
    if res.get("erros"):
        texto += "\n" + "\n".join(res["erros"][:5])
    if res.get("avisos"):
        texto += "\n" + "\n".join(res["avisos"][:5])
    return texto

__all__ = ['SHOPS_CONHECIDAS', 'pontuar', 'hydra_db_candidates', 'find_hydra_db', 'TITLE_RE', 'EXEC_RE', 'SHOP_RE', 'OBJID_RE', 'PLAYTIME_RE', 'scan_hydra_db', 'SKIP_DIRS', 'SKIP_EXE_RE', 'RIOT_EXE', 'ACF_NAME_RE', 'ACF_DIR_RE', 'default_scan_roots', 'scan_discos', 'preview_scan', 'JUNK_PROG_RE', 'ler_do_disco', 'default_roms_roots', 'ROM_TAGS_LIXO_RE', 'scan_roms', 'preview_roms', 'EXE_IMPORTAVEIS', 'analisar_arquivo', 'preview_pasta', 'fundir_duplicados', 'SMDH_IDIOMAS', 'SMDH_REGIOES', 'NDS_REGIOES', 'ler_metadados_nds', 'icone_nds_para_png', 'ler_metadados_3ds', 'icone_rom_para_png', 'importar_lista']
__all__ += ['resumo_importacao']
