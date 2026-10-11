"""Busca de faixas em bibliotecas públicas, sem chave e sem login.

Deezer e iTunes não exigem credencial; MusicBrainz exige só User-Agent
(1 chamada/s). Spotify continua no adaptador próprio (conta do usuário).
Tudo sob ação explícita, com cache e fallback offline.
"""
from __future__ import annotations

import re
import threading
import time
import urllib.parse

from bib_nucleo import online

PROVEDORES_MUSICA = ("deezer", "itunes", "musicbrainz")
NOMES = {"deezer": "Deezer", "itunes": "iTunes", "musicbrainz": "MusicBrainz",
         "spotify": "Spotify"}
_mb_lock = threading.Lock()
_mb_ultimo = 0.0


def _faixa(fonte, titulo, artista, album="", duracao_ms=0, capa_url="", url="", uri=""):
    titulo = re.sub(r"\s+", " ", str(titulo or "")).strip()
    if not titulo:
        return None
    return {"titulo": titulo, "artista": re.sub(r"\s+", " ", str(artista or "")).strip(),
            "album": re.sub(r"\s+", " ", str(album or "")).strip(),
            "duracao_ms": duracao_ms if isinstance(duracao_ms, int) and duracao_ms > 0 else 0,
            "capa_url": capa_url if online.url_https(capa_url) else "",
            "url": url if online.url_https(url) else "",
            "uri": uri or (url or f"{fonte}:{artista} - {titulo}"),
            "fonte": fonte, "nome_fonte": NOMES[fonte]}


def buscar_deezer(termo: str, limite=10) -> list[dict]:
    termo = (termo or "").strip()
    if len(termo) < 2:
        raise ValueError("Digite artista e/ou faixa para buscar.")
    dados = online.requisitar_json("https://api.deezer.com/search?" + urllib.parse.urlencode(
        {"q": termo, "limit": max(1, min(25, limite))}))
    out = []
    for t in (dados.get("data") or [])[:25]:
        if not isinstance(t, dict):
            continue
        art = (t.get("artist") or {}).get("name") if isinstance(t.get("artist"), dict) else ""
        alb = (t.get("album") or {}) if isinstance(t.get("album"), dict) else {}
        try:
            dur = int(t.get("duration") or 0) * 1000
        except (TypeError, ValueError):
            dur = 0
        item = _faixa("deezer", t.get("title"), art, alb.get("title"),
                      dur, alb.get("cover_xl") or alb.get("cover_big") or "",
                      t.get("link"), "deezer:track:" + str(t.get("id") or ""))
        if item:
            out.append(item)
    return out


def buscar_itunes(termo: str, limite=10) -> list[dict]:
    termo = (termo or "").strip()
    if len(termo) < 2:
        raise ValueError("Digite artista e/ou faixa para buscar.")
    dados = online.requisitar_json("https://itunes.apple.com/search?" + urllib.parse.urlencode(
        {"term": termo, "media": "music", "entity": "song", "limit": max(1, min(25, limite))}))
    out = []
    for t in (dados.get("results") or [])[:25]:
        if not isinstance(t, dict):
            continue
        try:
            dur = int(t.get("trackTimeMillis") or 0)
        except (TypeError, ValueError):
            dur = 0
        arte = re.sub(r"\d+x\d+bb", "600x600bb", str(t.get("artworkUrl100") or ""))
        item = _faixa("itunes", t.get("trackName"), t.get("artistName"), t.get("collectionName"),
                      dur, arte, t.get("trackViewUrl"), "itunes:track:" + str(t.get("trackId") or ""))
        if item:
            out.append(item)
    return out


def buscar_musicbrainz(termo: str, limite=5) -> list[dict]:
    global _mb_ultimo
    termo = (termo or "").strip()
    if len(termo) < 2:
        raise ValueError("Digite artista e/ou faixa para buscar.")
    url = "https://musicbrainz.org/ws/2/recording/?" + urllib.parse.urlencode(
        {"query": termo, "fmt": "json", "limit": max(1, min(10, limite))})
    with _mb_lock:
        time.sleep(max(0, 1.05 - (time.monotonic() - _mb_ultimo)))
        try:
            dados = online.requisitar_json(url)
        finally:
            _mb_ultimo = time.monotonic()
    out = []
    for r in (dados.get("recordings") or [])[:10]:
        if not isinstance(r, dict):
            continue
        artistas = " / ".join(a.get("name") or "" for a in r.get("artist-credit", [])
                              if isinstance(a, dict))
        lancamentos = r.get("releases")
        lanc = lancamentos[0] if isinstance(lancamentos, list) and lancamentos else {}
        item = _faixa("musicbrainz", r.get("title"), artistas,
                      lanc.get("title") if isinstance(lanc, dict) else "",
                      r.get("length") or 0, "", "https://musicbrainz.org/recording/" + str(r.get("id") or ""),
                      "musicbrainz:recording:" + str(r.get("id") or ""))
        if item:
            out.append(item)
    return out


_BUSCAS = {"deezer": buscar_deezer, "itunes": buscar_itunes, "musicbrainz": buscar_musicbrainz}


def buscar_musicas(termo: str, fonte="todas", atualizar=False) -> dict:
    fontes = PROVEDORES_MUSICA if fonte == "todas" else (fonte,)
    if any(f not in PROVEDORES_MUSICA for f in fontes):
        raise ValueError("Biblioteca de músicas inválida.")
    if len((termo or "").strip()) < 2:
        raise ValueError("Digite artista e/ou faixa para buscar.")
    itens, erros, caches = [], [], 0
    for f in fontes:
        alvo = online.cache_path("musicas-online", repr((f, termo.strip().lower())))
        cache = online.ler_json(alvo)
        if isinstance(cache, list) and cache and not atualizar:
            resultado, caches = cache, caches + 1
        else:
            try:
                resultado = _BUSCAS[f](termo)
                if resultado:
                    online.gravar_json(alvo, resultado)
            except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
                erros.append(NOMES[f] + ": " + str(e))
                resultado = cache if isinstance(cache, list) else []
                caches += int(bool(resultado))
        itens.extend(resultado)
    vistos, unicos = set(), []
    for item in itens:
        chave = (item.get("titulo", "").casefold(), item.get("artista", "").casefold())
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(item)
    return {"itens": unicos[:30], "erros": erros, "cache": bool(caches)}
