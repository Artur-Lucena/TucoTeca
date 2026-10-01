#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repacks baixados (.rar/.zip/.7z/.iso…): extrai, organiza, acha o exe e importa.

Procedimento padrão do Hub (ex-Piratas, agora em código): extrair com 7z
(Win) ou stdlib (zip), limpar sobras (Read_Me, .url, _redist, setup
redundante), achar o executável principal e importar sem duplicar.
O archive é apagado após verificação do exe. Sem rede, darwin-safe.
"""
from __future__ import annotations

import os
import re
import shutil
import sqlite3
import subprocess
import zipfile
from pathlib import Path

ARQUIVO_EXTS = {".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".tbz",
                ".txz", ".iso"}

_LIXO_NOMES = re.compile(
    r"(?i)^(read_?me.*|.*\.url|_redist_readme.*|desktop\.ini|thumbs\.db)$")

_SETUP_RE = re.compile(r"(?i)^setup")


def pasta_piratas() -> Path:
    """Destino padrão dos repacks (override `BIBLIOTECA_PIRATAS`)."""
    from bib_nucleo.base import LINUX_ROOT, WIN_ROOT
    env = os.environ.get("BIBLIOTECA_PIRATAS")
    if env:
        return Path(env)
    if os.name == "nt":
        return Path(f"{str(WIN_ROOT).rstrip(chr(92))}\\Games\\Piratas")
    return Path(f"{str(LINUX_ROOT).rstrip('/')}/Games/Piratas")


def ferramenta_7z() -> Path | None:
    """7z p/ rar/7z/iso (override `BIBLIOTECA_7Z`; None = sem extrator)."""
    env = os.environ.get("BIBLIOTECA_7Z")
    if env:
        cand = Path(env)
        return cand if cand.is_file() else None
    if os.name == "nt":
        from bib_nucleo.base import WIN_ROOT
        cand = Path(f"{str(WIN_ROOT).rstrip(chr(92))}\\Games\\ferramentas\\7z.exe")
        if cand.is_file():
            return cand
        for nome in ("7z.exe", "7z"):
            achado = shutil.which(nome)
            if achado:
                return Path(achado)
        return None
    for nome in ("7zr", "7z", "p7zip"):
        achado = shutil.which(nome)
        if achado:
            return Path(achado)
    return None


def eh_pacote_hub(caminho: str | os.PathLike) -> bool:
    """Zip é pacote portátil do Hub (tem biblioteca.json)? Só leitura."""
    from bib_nucleo.pacotes import PACOTE_JSON
    p = Path(caminho)
    if p.suffix.lower() != ".zip" or not p.is_file():
        return False
    try:
        with zipfile.ZipFile(p) as z:
            return any(i.filename == PACOTE_JSON for i in z.infolist())
    except (OSError, zipfile.BadZipFile):
        return False


def extrair_arquivo(origem: str | os.PathLike, destino: Path) -> dict:
    """Extrai p/ `destino` (cria). .zip via stdlib; resto via 7z.

    Nuncaexecuta nada extraído; zip com traversal é rejeitado.
    """
    src = Path(origem)
    if not src.is_file():
        return {"ok": False, "erro": "arquivo não encontrado."}
    try:
        destino.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return {"ok": False, "erro": f"falha ao criar destino: {e}"}
    if src.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(src) as z:
                for i in z.infolist():
                    partes = Path(i.filename.replace("\\", "/")).parts
                    if (not partes or ".." in partes
                            or i.filename.startswith(("/", "\\"))):
                        return {"ok": False,
                                "erro": "zip com caminho inválido."}
                z.extractall(destino)
        except (OSError, zipfile.BadZipFile) as e:
            return {"ok": False, "erro": f"zip inválido: {e}"}
        return {"ok": True, "destino": str(destino)}
    exe7z = ferramenta_7z()
    if exe7z is None:
        return {"ok": False,
                "erro": ("sem extrator p/ este formato (instale o 7-Zip "
                         "ou defina BIBLIOTECA_7Z).")}
    try:
        r = subprocess.run([str(exe7z), "x", str(src), f"-o{destino}", "-y"],
                           capture_output=True, text=True, timeout=3600)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "erro": f"falha ao extrair: {e}"}
    if r.returncode != 0:
        detalhe = (r.stderr or r.stdout or "")[-300:]
        return {"ok": False, "erro": f"extrator falhou: {detalhe}"}
    return {"ok": True, "destino": str(destino)}


def organizar_extraido(raiz: Path) -> dict:
    """Desembrulha pasta única, limpa sobras. Retorna {pasta, avisos, ...}.

    Mantém `_CommonRedist` do jogo, OSTs, `.bak`s e saves; apaga `Read_Me`,
    `.url`, `_redist_readme`, `_CommonRedist` duplicado da raiz e `setup_*`
    redundante (só quando já há exe jogável — senão o jogo precisa instalar
    e o setup é preservado com aviso).
    """
    avisos: list[str] = []
    pasta = Path(raiz)
    # desce enquanto houver só 1 subpasta e nenhum exe no nível
    while True:
        try:
            filhos = list(pasta.iterdir())
        except OSError:
            break
        exes = [f for f in filhos
                if f.is_file() and f.suffix.lower() == ".exe"]
        dirs = [f for f in filhos if f.is_dir() and not f.is_symlink()]
        if len(dirs) == 1 and not exes and not any(
                f.is_file() for f in filhos):
            pasta = dirs[0]
        else:
            break
    removidos = 0
    try:
        for p in sorted(pasta.rglob("*")):
            if p.is_symlink() or not p.is_file():
                continue
            if _LIXO_NOMES.match(p.name):
                try:
                    p.unlink()
                    removidos += 1
                except OSError:
                    pass
    except OSError:
        pass
    if removidos:
        avisos.append(f"{removidos} sobra(s) apagada(s).")
    # _CommonRedist duplicado da raiz: mantém os mais fundos
    try:
        redists = [d for d in pasta.rglob("*")
                   if d.is_dir() and not d.is_symlink()
                   and d.name.lower() == "_commonredist"]
    except OSError:
        redists = []
    if len(redists) > 1:
        fundo = max(len(d.relative_to(pasta).parts) for d in redists)
        for d in redists:
            if len(d.relative_to(pasta).parts) < fundo:
                try:
                    shutil.rmtree(d, ignore_errors=True)
                    avisos.append("_CommonRedist duplicado da raiz apagado.")
                except OSError:
                    pass
                break
    return {"pasta": str(pasta), "avisos": avisos}


_REP_TAGS = re.compile(
    r"(?i)\s+(steam\s*rip(\s*com)?|fitgirl(\s+repack)?|dodi(\s+repacks?)?|"
    r"xatab|gog|tinyrepacks|rune|codex|plaza|skidrow|fairlight|"
    r"elamigos|kaoskrew|corepack|vankevil|repack(\s+\w+)?)$")


def _titulo_pasta(pasta: Path) -> str:
    """Título da pasta limpo de tags de repack ([FitGirl], -SteamRIP...)."""
    nome = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", pasta.name)
    nome = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", nome)
    nome = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", nome)
    nome = nome.replace("_", " ").replace(".", " ").replace("-", " ")
    nome = re.sub(r"\s+", " ", nome).strip()
    nome = _REP_TAGS.sub("", nome).strip()
    return re.sub(r"\s+", " ", nome).strip()


def _pontuar_exe(p: Path, pasta: Path) -> float:
    from bib_nucleo.scans import SKIP_EXE_RE
    nome = p.name
    if SKIP_EXE_RE.search(nome):
        return -1.0
    pontos = 0.0
    try:
        pontos += min(50.0, p.stat().st_size / (50 * 1024 * 1024))
    except OSError:
        pass
    slug_pasta = re.sub(r"[^a-z0-9]+", "", pasta.name.lower())
    slug_exe = re.sub(r"[^a-z0-9]+", "", p.stem.lower())
    if slug_pasta and (slug_pasta in slug_exe or slug_exe in slug_pasta):
        pontos += 30.0
    try:
        rel = len(p.relative_to(pasta).parts)
    except ValueError:
        rel = 9
    pontos -= min(9.0, float(max(0, rel - 1)) * 3.0)
    return pontos


def achar_exe(pasta: str | os.PathLike) -> dict:
    """Melhor .exe jogável (fora _CommonRedist e instaladores). Só leitura."""
    base = Path(pasta)
    cands: list[tuple[float, Path]] = []
    try:
        arquivos = [p for p in base.rglob("*.exe")
                    if p.is_file() and not p.is_symlink()]
    except OSError as e:
        return {"ok": False, "erro": f"falha ao varrer: {e}"}
    for exe in arquivos:
        if "commonredist" in (part.lower() for part in exe.parts):
            continue
        nota = _pontuar_exe(exe, base)
        if nota >= 0:
            cands.append((nota, exe))
    if not cands:
        # sem exe jogável: há setup? (jogo precisa instalar)
        setups = [p for p in arquivos
                  if _SETUP_RE.search(p.name) and p.is_file()]
        if setups:
            return {"ok": False, "precisa_instalar": True,
                    "erro": ("só há instalador (setup) — instale o jogo "
                             "antes de importar.")}
        return {"ok": False, "erro": "nenhum executável jogável achado."}
    cands.sort(key=lambda t: -t[0])
    return {"ok": True, "exe": str(cands[0][1]),
            "candidatos": len(cands)}


def _apagar_setups_redundantes(pasta: Path) -> int:
    """Apaga `setup_*` quando já há exe jogável. Retorna quantos."""
    n = 0
    try:
        alvos = [p for p in pasta.rglob("*")
                 if p.is_file() and not p.is_symlink()
                 and _SETUP_RE.search(p.name)
                 and p.suffix.lower() == ".exe"]
    except OSError:
        return 0
    for p in alvos:
        try:
            p.unlink()
            n += 1
        except OSError:
            pass
    return n


def importar_repack(con: sqlite3.Connection, arquivo: str | os.PathLike,
                    destino_raiz: str | os.PathLike | None = None) -> dict:
    """Pipeline completo: extrai → organiza → acha exe → importa → apaga arq.

    O archive original é apagado SÓ após exe verificado e importação ok.
    """
    from bib_nucleo import banco as B
    from bib_nucleo.base import slugify
    from bib_nucleo.scans import _titulo_de_exe, importar_lista, pontuar
    src = Path((str(arquivo) or "").strip())
    if not src.is_file():
        return {"ok": False, "erro": "arquivo não encontrado."}
    if src.suffix.lower() not in ARQUIVO_EXTS:
        return {"ok": False,
                "erro": f"extensão '{src.suffix}' não é pacote de jogo."}
    raiz = Path(destino_raiz) if destino_raiz else pasta_piratas()
    nome = slugify(src.stem) or "jogo"
    dest = raiz / nome
    if dest.exists():
        n = 1
        while (raiz / f"{nome}-{n}").exists():
            n += 1
        dest = raiz / f"{nome}-{n}"
    r = extrair_arquivo(src, dest)
    if not r.get("ok"):
        try:
            shutil.rmtree(dest, ignore_errors=True)
        except OSError:
            pass
        return {"ok": False, "erro": r["erro"]}
    try:
        org = organizar_extraido(dest)
        pasta = Path(org["pasta"])
        ach = achar_exe(pasta)
        if not ach.get("ok"):
            return {"ok": False, "erro": ach["erro"],
                    "pasta": str(pasta),
                    "precisa_instalar": bool(ach.get("precisa_instalar")),
                    "avisos": org["avisos"]}
        apagados = _apagar_setups_redundantes(pasta)
        exe = Path(ach["exe"])
        titulo = _titulo_de_exe(exe)
        pasta_limpo = _titulo_pasta(pasta)
        alnum = re.sub(r"[^a-z0-9]+", "", pasta_limpo.lower())
        if len(pasta_limpo) > len(titulo) and alnum.startswith(
                re.sub(r"[^a-z0-9]+", "", titulo.lower())):
            titulo = pasta_limpo  # pasta diz mais ("CoolGame" > "Cool")
        if titulo.lower() in ("setup", "install", "") or len(titulo) < 2:
            titulo = pasta_limpo or pasta.name
        item = pontuar({"titulo": titulo, "executable_path": str(exe),
                        "shop": "", "object_id": "", "horas": 0.0,
                        "origem": "repack"})
        res = importar_lista(con, [item])
        try:
            src.unlink()
            apagou_arq = True
        except OSError:
            apagou_arq = False
        out = {"ok": True, "pasta": str(pasta), "exe": str(exe),
               "titulo": titulo, "novos": res.get("novos", 0),
               "ignorados": res.get("ignorados", 0),
               "erros": res.get("erros", []),
               "capa_pendente": not bool(
                   B.listar_jogos(con, q=titulo)[0].get("capa"))
               if res.get("novos") else False,
               "apagou_arquivo": apagou_arq,
               "setups_apagados": apagados,
               "avisos": org["avisos"]}
        if not res.get("novos"):
            out["capa_pendente"] = False
        return out
    except Exception as e:
        return {"ok": False, "erro": f"{type(e).__name__}: {e}",
                "pasta": str(dest)}


__all__ = ['ARQUIVO_EXTS', 'pasta_piratas', 'ferramenta_7z', 'eh_pacote_hub',
           'extrair_arquivo', 'organizar_extraido', 'achar_exe',
           'importar_repack']
