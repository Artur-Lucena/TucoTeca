#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scans: lojas e detectores (Hydra, Steam, Epic, GOG, Riot, Windows)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from bib_nucleo.base import existe_aqui_ou_traduzido, traduzir_para_atual

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


from bib_nucleo.scans_hydra import (
    EXEC_RE,
    OBJID_RE,
    PLAYTIME_RE,
    SHOP_RE,
    TITLE_RE,
    _unescape,
    scan_hydra_db,
)

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
    from bib_nucleo.scans.disco import default_scan_roots
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
    from bib_nucleo.scans.disco import ACF_DIR_RE, ACF_NAME_RE, SKIP_EXE_RE
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
    from bib_nucleo.scans.disco import default_scan_roots
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
    from bib_nucleo.scans.disco import SKIP_DIRS, default_scan_roots
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
    from bib_nucleo.scans.analise import fundir_duplicados
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


__all__ = ["SHOPS_CONHECIDAS", "pontuar", "hydra_db_candidates", "find_hydra_db",
           "TITLE_RE", "EXEC_RE", "SHOP_RE", "OBJID_RE", "PLAYTIME_RE",
           "_unescape", "scan_hydra_db", "JUNK_PROG_RE", "_detector_hydra",
           "_steamapps_dirs", "_appid_de_manifest", "_item_steam_manifest",
           "_detector_steam", "_detector_epic", "_detector_gog",
           "_detector_riot", "_detector_windows", "ler_do_disco"]
