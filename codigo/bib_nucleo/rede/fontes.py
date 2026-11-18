#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Catálogos de terceiros (busca SteamRIP/FitGirl) e wishlist da Steam.

Só busca: devolve título e link do post; abrir/baixar é com o usuário. Tudo
com `urllib` stdlib; rede falhou = erro claro em `erros`, nunca levanta cru.
"""
from __future__ import annotations

import html as _html
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

from bib_nucleo.rede import abrir_rede

STEAM_ID_ENV = "BIBLIOTECA_STEAM_ID"


def _parse_loginusers(texto: str) -> dict:
    """Conta principal do loginusers.vdf (maior Timestamp). Puro, testável."""
    melhor = None
    for m in re.finditer(r'"(765\d{10,})"\s*\{(.*?)\n\s*\}',
                         texto or "", re.DOTALL):
        bloco = m.group(2)
        ts = re.search(r'"Timestamp"\s+"(\d+)"', bloco)
        persona = re.search(r'"PersonaName"\s+"((?:[^"\\]|\\.)*)"', bloco)
        alt = (int(ts.group(1)) if ts else 0, m.group(1),
               persona.group(1) if persona else "")
        if melhor is None or alt[0] > melhor[0]:
            melhor = alt
    if not melhor:
        return {}
    return {"steamid": melhor[1], "persona": melhor[2]}


def steam_principal() -> dict:
    """Conta Steam principal do PC (loginusers.vdf). Só leitura, sem login.

    Retorna {'steamid', 'persona'} ou {} — override `BIBLIOTECA_STEAM_ID`.
    """
    env = (os.environ.get(STEAM_ID_ENV) or "").strip()
    if env.isdigit():
        return {"steamid": env, "persona": ""}
    cands = [Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
             / "Steam" / "config" / "loginusers.vdf"]
    if os.name != "nt":
        home = Path.home()
        cands += [home / ".steam/steam/config/loginusers.vdf",
                  home / ".local/share/Steam/config/loginusers.vdf",
                  home / "Library/Application Support/Steam/config/loginusers.vdf"]
    for arq in cands:
        try:
            if not arq.is_file():
                continue
            conta = _parse_loginusers(arq.read_text(encoding="utf-8",
                                                   errors="ignore"))
        except OSError:
            continue
        if conta:
            return conta
    return {}


def ler_wishlist(steamid: str, timeout: int = 20,
                 max_paginas: int = 20) -> dict:
    """[{'appid','titulo'}] da wishlist pública (paginado). Erro vira `erros`.

    HTML não é interpretado como lista vazia nem como prova de perfil privado.
    """
    steamid = (steamid or "").strip()
    if not steamid.isdigit():
        return {"itens": [], "erros": ["sem SteamID (BIBLIOTECA_STEAM_ID?)"]}
    itens: list[dict] = []
    vistos: set[str] = set()
    try:
        for pagina in range(max(1, max_paginas)):
            req = urllib.request.Request(
                "https://store.steampowered.com/wishlist/profiles/"
                f"{steamid}/wishlistdata/?p={pagina}", headers=_UA)
            with abrir_rede(req, timeout=timeout) as r:
                corpo = r.read(5_000_000).decode("utf-8", "replace")
            if corpo.lstrip()[:1] == "<":
                return {"itens": [], "erros": [
                    "O endpoint antigo da Steam devolveu uma página, não a lista. "
                    "Sincronização indisponível; use Adicionar ou um JSON exportado."]}
            try:
                dados = json.loads(corpo)
            except ValueError:
                return {"itens": [], "erros": ["resposta inválida da Steam"]}
            if not isinstance(dados, dict):
                return {"itens": itens, "erros": ["formato inesperado da Steam"]}
            if not dados:
                break
            for appid, info in dados.items():
                appid = str(appid).strip()
                if not appid.isdigit() or appid in vistos:
                    continue
                nome = ""
                if isinstance(info, dict):
                    nome = str(info.get("name") or "").strip()
                if not nome:
                    continue
                vistos.add(appid)
                itens.append({"appid": appid, "titulo": nome})
            if len(dados) < 100:
                break
    except Exception as e:
        return {"itens": itens, "erros": [f"wishlist falhou: {e}"]}
    return {"itens": itens, "erros": []}


def ler_wishlist_arquivo(caminho) -> dict:
    """[{'appid','titulo'}] de um wishlistdata/?p=N salvo no navegador.

    Aceita o JSON cru da Steam (dict appid→{name}) ou lista de
    {appid, name/titulo}. Erro vira `erros`, nunca levanta.
    """
    try:
        alvo = Path(caminho)
        try:
            if alvo.is_file() and alvo.stat().st_size > 8_000_000:
                return {"itens": [], "erros": ["arquivo grande demais (>8 MB)"]}
        except OSError:
            pass
        texto = alvo.read_text(encoding="utf-8-sig", errors="replace")
    except (OSError, ValueError, TypeError) as e:
        return {"itens": [], "erros": [f"arquivo ilegível: {e}"]}
    if texto.lstrip()[:1] == "<":
        return {"itens": [], "erros": [
            "O arquivo contém HTML, não uma lista JSON. "
            "Importe um JSON exportado ou use Adicionar."]}
    try:
        dados = json.loads(texto)
    except ValueError:
        return {"itens": [], "erros": ["arquivo não é um JSON válido"]}
    itens: list[dict] = []
    vistos: set[str] = set()
    pares = dados.items() if isinstance(dados, dict) else (
        enumerate(dados) if isinstance(dados, list) else [])
    for chave, info in pares:
        if isinstance(dados, dict):
            if not isinstance(info, dict):
                continue
            appid = str(chave).strip()
            nome = str(info.get("name") or info.get("titulo") or "").strip()
        elif isinstance(info, dict):
            appid = str(info.get("appid") or "").strip()
            nome = str(info.get("name") or info.get("titulo") or "").strip()
        else:
            continue
        if not appid.isdigit() or appid in vistos or not (nome or "").strip():
            continue
        vistos.add(appid)
        itens.append({"appid": appid, "titulo": str(nome).strip()})
    if not itens:
        return {"itens": [], "erros": ["nenhum jogo no arquivo"]}
    return {"itens": itens, "erros": []}


STEAMRIP_BASE = "https://steamrip.com"

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                       " AppleWebKit/537.36 (KHTML, like Gecko)"
                       " Chrome/126.0.0.0 Safari/537.36",
       "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                 "*/*;q=0.8",
       "Accept-Language": "en-US,en;q=0.9",
       "Referer": "https://www.google.com/",
       "Upgrade-Insecure-Requests": "1"}


def _ler(url: str, timeout: int = 20, limite: int = 2_000_000) -> str:
    req = urllib.request.Request(url, headers=_UA)
    with abrir_rede(req, timeout=timeout) as r:
        return r.read(limite).decode("utf-8", "replace")


def _limpar(texto: str) -> str:
    texto = re.sub(r"<[^>]+>", "", texto or "")
    return _html.unescape(re.sub(r"\s+", " ", texto)).strip()


_POST_IGNORADOS = ("search", "category", "tag", "author", "page", "feed",
                   "comments", "wp-admin", "wp-content", "wp-includes",
                   "wp-json", "steps-for-games", "how-to-run-games",
                   "request-games", "dmca", "privacy-policy", "contact")


def buscar_steamrip(termo: str, timeout: int = 20) -> dict:
    """[{'titulo', 'url'}] da busca (só posts de jogo). Erro vira `erros`."""
    termo = (termo or "").strip()
    if not termo:
        return {"itens": [], "erros": ["busca vazia"]}
    try:
        q = urllib.parse.urlencode({"s": termo})
        pagina = _ler(f"{STEAMRIP_BASE}/?{q}", timeout=timeout,
                      limite=1_500_000)
    except Exception as e:
        return {"itens": [], "erros": [f"busca falhou: {e}"]}
    itens: list[dict] = []
    vistos: set[str] = set()
    pats = [r"<h2[^>]*>\s*<a\s+href=\"([^\"]+)\"[^>]*>(.*?)</a>",
            r"<a\s+href=\"(https?://steamrip\.com/([^\"/]+)/)\"[^>]*>(.*?)</a>"]
    for pat in pats:
        try:
            achados = re.findall(pat, pagina, re.IGNORECASE | re.DOTALL)
        except re.error:
            continue
        for ach in achados:
            url, resto = ach[0], ach[-1]
            slug = (ach[1] if len(ach) == 3 else url.rstrip("/").rsplit("/", 1)[-1])
            slug = slug.strip().lower()
            if not slug or slug in _POST_IGNORADOS or slug.startswith("wp-"):
                continue
            url = urllib.parse.urljoin(STEAMRIP_BASE + "/", url.strip())
            if urllib.parse.urlsplit(url).hostname not in ("steamrip.com", "www.steamrip.com"):
                continue
            if url in vistos:
                continue
            titulo = _limpar(resto)
            if not titulo or len(titulo) < 3:
                continue
            vistos.add(url)
            itens.append({"titulo": titulo, "url": url})
        if itens:
            break
    return {"itens": itens[:30], "erros": []}


FITGIRL_BASE = "https://fitgirl-repacks.site"


def buscar_fitgirl(termo: str, timeout: int = 20) -> dict:
    """[{'titulo', 'url'}] da busca (posts de repack). Erro vira `erros`."""
    termo = (termo or "").strip()
    if not termo:
        return {"itens": [], "erros": ["busca vazia"]}
    try:
        q = urllib.parse.urlencode({"s": termo})
        pagina = _ler(f"{FITGIRL_BASE}/?{q}", timeout=timeout,
                      limite=1_500_000)
    except Exception as e:
        return {"itens": [], "erros": [f"busca falhou: {e}"]}
    itens: list[dict] = []
    vistos: set[str] = set()
    try:
        achados = re.findall(
            r'<h1 class="entry-title"><a href="([^"]+)"[^>]*>(.*?)</a>',
            pagina, re.IGNORECASE | re.DOTALL)
    except re.error:
        return {"itens": [], "erros": ["busca falhou: parse"]}
    for url, resto in achados:
        url = urllib.parse.urljoin(FITGIRL_BASE + "/", url.strip())
        if urllib.parse.urlsplit(url).hostname not in (
                "fitgirl-repacks.site", "www.fitgirl-repacks.site"):
            continue
        if url in vistos:
            continue
        titulo = _limpar(resto)
        if not titulo or len(titulo) < 3:
            continue
        vistos.add(url)
        itens.append({"titulo": titulo, "url": url})
    return {"itens": itens[:30], "erros": []}


__all__ = ['STEAMRIP_BASE', 'buscar_steamrip', 'FITGIRL_BASE', 'buscar_fitgirl',
            'steam_principal', 'ler_wishlist', 'ler_wishlist_arquivo']
