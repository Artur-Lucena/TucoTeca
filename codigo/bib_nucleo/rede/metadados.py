"""Catálogo Steam e capas iTunes; fachadas locais preservam os contratos antigos."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

from bib_nucleo.rede import abrir_rede, rede_ativa


def _capa_steam(appid: str, timeout: int = 15):
    from bib_nucleo.rede.online import url_https
    if not str(appid).isdigit():
        return None
    req = urllib.request.Request(f"https://store.steampowered.com/api/appdetails?appids={appid}",
                                 headers={"User-Agent": "TucoTeca/1.0"})
    with abrir_rede(req, timeout=timeout) as r:
        data = json.loads(r.read(2_000_001).decode("utf-8"))
    info = data.get(str(appid)) or {}
    if not info.get("success"):
        return None
    url = ((info.get("data") or {}).get("header_image") or "").split("?")[0]
    if not url_https(url):
        return None
    req = urllib.request.Request(url, headers={"User-Agent": "TucoTeca/1.0"})
    with abrir_rede(req, timeout=timeout) as r:
        raw = r.read(2_500_001)
    return raw if 1024 <= len(raw) <= 2_500_000 else None


def canonizar_steam(*candidatos: str, timeout: int = 15):
    """Match exato, no máximo três consultas; sem rede retorna vazio."""
    if not rede_ativa():
        return "", ""
    vistos, limpos = set(), []
    for cand in candidatos:
        alvo = re.sub(r"\s+", " ", (cand or "")).strip().lower()
        if len(alvo) >= 2 and alvo not in vistos:
            vistos.add(alvo)
            limpos.append(alvo)
    for alvo in limpos[:3]:
        try:
            q = urllib.parse.urlencode({"term": alvo, "l": "english", "cc": "US"})
            req = urllib.request.Request(f"https://store.steampowered.com/api/storesearch/?{q}",
                                         headers={"User-Agent": "TucoTeca/1.0"})
            with abrir_rede(req, timeout=timeout) as r:
                dados = json.loads(r.read(2_000_001).decode("utf-8"))
            for item in dados.get("items") or []:
                if not isinstance(item, dict):
                    continue
                nome = re.sub(r"\s+", " ", str(item.get("name") or "")).strip()
                appid = str(item.get("id") or "").strip()
                if appid.isdigit() and nome and nome.lower() in vistos:
                    return appid, nome
        except (ValueError, OSError, AttributeError, TypeError):
            continue
    return "", ""


def capa_album_url(artista: str, album: str, titulo: str, timeout: int = 15):
    """iTunes + fallback de capa; falha remota não invalida a importação local."""
    if not rede_ativa():
        return ""
    art, alb, tit = (re.sub(r"\s+", " ", (s or "")).strip() for s in (artista, album, titulo))
    consultas = ([f"{art} {alb}"] if art and alb else []) + ([f"{art} {tit}"] if art and tit else [])
    if not consultas:
        return ""
    try:
        from bib_nucleo.rede.online import url_https
        for q in consultas:
            qs = urllib.parse.urlencode({"term": q, "media": "music", "entity": "album", "limit": 5})
            req = urllib.request.Request(f"https://itunes.apple.com/search?{qs}",
                                         headers={"User-Agent": "TucoTeca/1.0"})
            with abrir_rede(req, timeout=timeout) as r:
                dados = json.loads(r.read(500_001).decode("utf-8"))
            for item in dados.get("results") or []:
                url = str(item.get("artworkUrl100") or "") if isinstance(item, dict) else ""
                if url_https(url):
                    return re.sub(r"\d+x\d+bb", "600x600bb", url)
    except (ValueError, OSError, AttributeError, TypeError):
        pass
    from bib_nucleo.capas import capa_musica_fallback
    return capa_musica_fallback(art, alb, tit)
