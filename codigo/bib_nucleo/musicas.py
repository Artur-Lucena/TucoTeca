#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Selfhost de áudio: importa do Harmoni p/ `dados/musicas/` e toca no player.

Fonte: pasta `music/` do Harmoni (mp3 com ID3) + `tracks.json` opcional.
Sem rede, stdlib só, darwin-safe (sem checagem MZ/ELF em áudio; play por
ação explícita via player do SO, nunca no recarregar/desenhar).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

CAPA_MUSICA_ENV = "BIBLIOTECA_CAPA_MUSICA_AUTO"

_TXT_FRAME = {"TIT2": "titulo", "TPE1": "artista", "TALB": "album"}


def harmoni_dir() -> Path | None:
    """Pasta `music/` do Harmoni (env `BIBLIOTECA_MUSICA_DIR` ou padrão Win)."""
    env = os.environ.get("BIBLIOTECA_MUSICA_DIR")
    if env and Path(env).is_dir():
        return Path(env)
    if os.name == "nt":
        cand = (Path(os.environ.get("USERPROFILE", "")) / "Downloads"
                / "Harmoni-Windows" / "music")
        if cand.is_dir():
            return cand
    return None


def sugestao_harmoni_dir() -> str:
    """Caminho provável do `music/` do Harmoni, exista ou não (p/ diálogo).

    `harmoni_dir()` só devolve o que existe; este sugere onde procurar
    (guia de onboarding quando a pasta ainda não foi baixada).
    """
    env = (os.environ.get("BIBLIOTECA_MUSICA_DIR") or "").strip()
    if env:
        return env
    if os.name == "nt":
        base = Path(os.environ.get("USERPROFILE", ""))
        if str(base).strip():
            return str(base / "Downloads" / "Harmoni-Windows" / "music")
    return ""


def texto_musica(m: dict | None) -> str:
    """Rótulo único da faixa (`Artista — Título` ou só `Título`). GUI+TUI."""
    m = m or {}
    tit = str(m.get("titulo") or "").strip()
    art = str(m.get("artista") or "").strip()
    return f"{art} — {tit}" if art else tit


def _syncsafe(b: bytes) -> int:
    n = 0
    for x in b:
        n = (n << 7) | (x & 0x7F)
    return n


def _texto_frame(dados: bytes) -> str:
    if not dados:
        return ""
    enc, corpo = dados[0], dados[1:]
    try:
        if enc == 0:
            return corpo.split(b"\x00")[0].decode("latin-1").strip()
        if enc == 3:
            return corpo.split(b"\x00")[0].decode("utf-8").strip()
        if enc in (1, 2):
            raw = corpo.decode("utf-16" if enc == 1 else "utf-16-be")
            return raw.split("\x00")[0].strip().lstrip("\ufeff")
    except (UnicodeDecodeError, ValueError):
        pass
    return ""


def ler_tags(caminho: str | os.PathLike) -> dict:
    """{titulo, artista, album} do ID3v2; fallback `Artista - Titulo.ext`.

    Só leitura, nunca levanta por arquivo estranho (retorna fallback).
    """
    p = Path(caminho)
    base = p.stem.strip()
    fb = {"titulo": base, "artista": "", "album": ""}
    if " - " in base:
        art, tit = base.split(" - ", 1)
        fb = {"titulo": tit.strip() or base, "artista": art.strip(),
              "album": ""}
    try:
        with p.open("rb") as fh:
            head = fh.read(10)
            if len(head) < 10 or head[:3] != b"ID3":
                return fb
            ver, tamanho = head[3], _syncsafe(head[6:10])
            if ver not in (3, 4) or tamanho <= 0 or tamanho > 16_777_216:
                return fb
            corpo = fh.read(tamanho)
    except OSError:
        return fb
    tags = dict(fb)
    i = 0
    try:
        while i + 10 <= len(corpo):
            fid = corpo[i:i + 4]
            if fid == b"\x00\x00\x00\x00" or not fid.strip(b"\x00"):
                break
            try:
                nome = fid.decode("ascii")
            except UnicodeDecodeError:
                break
            if ver == 4:
                tam = _syncsafe(corpo[i + 4:i + 8])
            else:
                tam = int.from_bytes(corpo[i + 4:i + 8], "big")
            ini, fim = i + 10, i + 10 + tam
            if tam <= 0 or fim > len(corpo):
                break
            if nome in _TXT_FRAME:
                txt = _texto_frame(corpo[ini:fim])
                if txt:
                    tags[_TXT_FRAME[nome]] = txt
            i = fim
    except (IndexError, ValueError):
        pass
    if not tags["titulo"]:
        tags["titulo"] = base
    return tags


def _tracks_index(harmoni_music: Path) -> dict:
    """{(artista, titulo) -> album} do `tracks.json` vizinho (se existir)."""
    idx = {}
    for cand in (harmoni_music.parent / "data" / "tracks.json",
                 harmoni_music / "tracks.json"):
        try:
            if cand.is_file():
                dados = json.loads(cand.read_text(encoding="utf-8"))
                break
        except (OSError, ValueError):
            continue
    else:
        return idx
    itens = dados if isinstance(dados, list) \
        else (dados.get("tracks", []) if isinstance(dados, dict) else [])
    if not isinstance(itens, list):
        return idx
    for t in itens:
        if not isinstance(t, dict):
            continue
        art = str(t.get("artist") or t.get("artista") or "").strip().lower()
        tit = str(t.get("track") or t.get("titulo") or "").strip().lower()
        alb = str(t.get("album") or "").strip()
        if art and tit and alb:
            idx[(art, tit)] = alb
    return idx


def sha_arquivo(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1024 * 256), b""):
            h.update(bloco)
    return h.hexdigest()


def varrer_pasta(pasta: str | os.PathLike) -> list[dict]:
    """Lista áudio importável (ext de `MUSICA_EXTS`) com tags+sha. Só leitura."""
    from bib_nucleo.base import MUSICA_EXTS, slugify
    raiz = Path(pasta)
    try:
        arquivos = sorted(p for p in raiz.rglob("*")
                           if p.is_file() and not p.is_symlink()
                           and p.suffix.lower() in MUSICA_EXTS)
    except OSError:
        return []
    idx = _tracks_index(raiz)
    out = []
    for arq in arquivos:
        try:
            tags = ler_tags(arq)
            if not tags["album"]:
                alb = idx.get((tags["artista"].lower(), tags["titulo"].lower()))
                if alb:
                    tags["album"] = alb
            out.append({"path": str(arq), "titulo": tags["titulo"],
                        "artista": tags["artista"], "album": tags["album"],
                        "sha": sha_arquivo(arq),
                        "slug": slugify(f"{tags['artista']}-{tags['titulo']}"),
                        "mb": round(arq.stat().st_size / 1048576, 1)})
        except OSError:
            continue
    return out


def importar_musicas(con: sqlite3.Connection,
                     pasta: str | os.PathLike,
                     capa_auto: bool | None = None) -> dict:
    """Copia p/ `dados/musicas/<slug>.<ext>` com dedup por sha.

    Falha de um arquivo vira item em `erros`, nunca aborta o lote.
    `capa_auto`: tenta arte do álbum por faixa nova (None = env
    `BIBLIOTECA_CAPA_MUSICA_AUTO`, default ligado; rede falhou = sem
    capa, sem travar).
    """
    from bib_nucleo import banco as B
    from bib_nucleo.base import MUSICAS_DIR
    MUSICAS_DIR.mkdir(parents=True, exist_ok=True)
    novos = ignorados = 0
    capas = 0
    erros: list[str] = []
    auto = capa_musica_auto() if capa_auto is None else bool(capa_auto)
    vistos = {r["musica_sha"] for r in
              con.execute("SELECT musica_sha FROM musicas").fetchall()}
    for item in varrer_pasta(pasta):
        if not item["sha"] or item["sha"] in vistos:
            ignorados += 1
            continue
        src = Path(item["path"])
        dest = MUSICAS_DIR / f"{item['slug']}{src.suffix.lower()}"
        n = 1
        while dest.exists():
            n += 1
            dest = MUSICAS_DIR / f"{item['slug']}-{n}{src.suffix.lower()}"
        try:
            shutil.copy2(str(src), str(dest))
        except OSError as e:
            if len(erros) < 20:
                erros.append(f"'{item['titulo']}': {e}")
            ignorados += 1
            continue
        try:
            nova = B.criar_musica(con, {"titulo": item["titulo"],
                                        "artista": item["artista"],
                                        "album": item["album"],
                                        "musica_path": str(dest),
                                        "musica_sha": item["sha"],
                                        "origem": "harmoni"})
        except ValueError as e:
            try:
                dest.unlink()
            except OSError:
                pass
            if len(erros) < 20:
                erros.append(f"'{item['titulo']}': {e}")
            ignorados += 1
            continue
        vistos.add(item["sha"])
        novos += 1
        if auto:
            try:
                r = baixar_capa_album(con, nova["id"])
                capas += 1 if r.get("ok") else 0
            except Exception:
                pass
    return {"novos": novos, "ignorados": ignorados, "erros": erros,
            "capas": capas}


def tocar_musica(caminho: str) -> dict:
    """Abre no player padrão do SO. Só sob ação explícita (nunca em teste).

    Fallback: banco compartilhado entre SOs guarda path absoluto da máquina
    que importou; se o arquivo sumiu, tenta `MUSICAS_DIR/<nome>` (a pasta
    `dados/` é a mesma em Win/Linux/Mac).

    Lê base.MUSICAS_DIR ao vivo (import dentro da função, como
    importar_musicas) p/ acompanhar override de ambiente/patch.
    """
    p = resolver_musica(caminho)
    if not p:
        return {"ok": False, "erro": "arquivo não encontrado."}
    try:
        if os.name == "nt":
            os.startfile(p)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", p])
        else:
            subprocess.Popen(["xdg-open", p])
    except OSError as e:
        return {"ok": False, "erro": f"falha ao abrir: {e}"}
    return {"ok": True, "path": p}


def resolver_musica(caminho: str) -> str:
    """Arquivo local/traduzido ou basename em dados/musicas; só leitura."""
    from bib_nucleo.base import MUSICAS_DIR, nome_arquivo_portatil, traduzir_para_atual
    p = (caminho or "").strip()
    if not p or "\x00" in p:
        return ""
    try:
        for cand in (Path(p), Path(traduzir_para_atual(p)),
                     MUSICAS_DIR / nome_arquivo_portatil(p)):
            if cand.is_file():
                return str(cand)
    except (OSError, ValueError):
        pass
    return ""


# --------------------------------------------------------------------------
# Capas de álbum automáticas (iTunes Search, sem chave; molde _capa_steam)
# --------------------------------------------------------------------------

def capa_musica_auto() -> bool:
    """Auto-capa no import? Env `BIBLIOTECA_CAPA_MUSICA_AUTO` (default ligado)."""
    return (os.environ.get(CAPA_MUSICA_ENV, "1") or "").strip().lower() \
        not in ("0", "off", "false", "nao", "não", "no")


from bib_nucleo.rede.metadados import capa_album_url


def baixar_capa_album(con: sqlite3.Connection, mid: int,
                      timeout: int = 20) -> dict:
    """Baixa a arte do álbum p/ 1 faixa. Falha de rede vira pendente."""
    from bib_nucleo import banco as B
    row = con.execute("SELECT * FROM musicas WHERE id=?", (mid,)).fetchone()
    if not row:
        return {"ok": False, "erro": "música não encontrada"}
    d = dict(row)
    atual = d.get("musica_capa") or ""
    if atual:
        from bib_nucleo.base import CAPAS_DIR
        if (CAPAS_DIR / Path(atual).name).is_file():
            return {"ok": True, "capa": atual, "cache": True}
    try:
        url = capa_album_url(d.get("artista") or "", d.get("album") or "",
                             d.get("titulo") or "", timeout=timeout)
        if not url:
            return {"ok": False, "capa_pendente": True,
                    "erro": "sem arte/offline"}
        from bib_nucleo.rede.online import cache_path
        cache = cache_path("imagens", url, ".img")
        if cache.is_file():
            raw = cache.read_bytes()
        else:
            import urllib.request

            from bib_nucleo.rede import abrir_rede
            req = urllib.request.Request(url, headers={"User-Agent": "TucoTeca/1.0"})
            with abrir_rede(req, timeout=timeout) as r:
                raw = r.read(2_500_000)
        if len(raw) < 1024:
            return {"ok": False, "capa_pendente": True, "erro": "arte vazia"}
        return B.salvar_capa_musica_bytes(con, mid, f"capa-{mid}.jpg", raw)
    except Exception as e:
        return {"ok": False, "capa_pendente": True, "erro": str(e)[:160]}


def baixar_capas_faltantes(con: sqlite3.Connection, limite: int = 200) -> dict:
    """Arte p/ todas as faixas sem capa (botões GUI/TUI). Nunca levanta rede."""
    from bib_nucleo import banco as B
    novas = pendentes = 0
    erros: list[str] = []
    try:
        alvos = [m["id"] for m in B.listar_musicas(con)
                 if not m.get("musica_capa")]
    except Exception as e:
        return {"novas": 0, "pendentes": 0, "erros": [str(e)]}
    for mid in alvos[:max(0, limite)]:
        try:
            r = baixar_capa_album(con, mid)
        except Exception as e:
            r = {"ok": False, "erro": str(e)}
        if r.get("ok"):
            novas += 1
        elif r.get("capa_pendente"):
            pendentes += 1
        elif len(erros) < 20:
            erros.append(f"#{mid}: {r.get('erro')}")
    return {"novas": novas, "pendentes": pendentes, "erros": erros}


__all__ = ['harmoni_dir', 'sugestao_harmoni_dir', 'texto_musica',
           'capa_musica_auto', 'capa_album_url', 'baixar_capa_album',
           'baixar_capas_faltantes', 'ler_tags', 'sha_arquivo', 'varrer_pasta',
           'importar_musicas', 'tocar_musica', 'resolver_musica']
