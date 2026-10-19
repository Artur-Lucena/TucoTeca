"""Capas de múltiplas bibliotecas. Pesquisa explícita, seleção e cache local."""
from __future__ import annotations

import re
import threading
import time
import urllib.parse

from bib_nucleo import online

_mb_lock = threading.Lock()
_mb_ultimo = 0.0
PROVEDORES_JOGOS = ("steam", "steamgriddb", "wikipedia", "libretro")
PROVEDORES_MUSICAS = ("itunes", "musicbrainz", "deezer")
NOMES = {"steam": "Steam", "steamgriddb": "SteamGridDB", "wikipedia": "Wikipedia",
         "itunes": "iTunes", "musicbrainz": "MusicBrainz / Cover Art Archive", "deezer": "Deezer",
         "libretro": "LibRetro Thumbnails"}


def _item(provedor, titulo, url, **extra):
    return {"provedor": provedor, "fonte": NOMES[provedor], "titulo": str(titulo),
            "url": str(url), **extra}


def _steam(item):
    from bib_nucleo.scans import canonizar_steam
    appid = str(item.get("object_id") or "") if item.get("shop") == "steam" else ""
    if not appid.isdigit():
        appid, _ = canonizar_steam(item.get("titulo") or "")
    if not appid:
        return []
    dados = online.requisitar_json("https://store.steampowered.com/api/appdetails?" +
                                  urllib.parse.urlencode({"appids": appid}))
    app = dados.get(appid, {})
    if not app.get("success"):
        return []
    info = app.get("data") or {}
    nome = info.get("name") or item.get("titulo") or appid
    out = [_item("steam", nome + " · pôster", f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_600x900_2x.jpg",
                 appid=appid)]
    if online.url_https(info.get("header_image") or ""):
        out.append(_item("steam", nome + " · banner", info["header_image"], appid=appid))
    return out


def _steamgriddb(item):
    chave = online.chave_provedor("steamgriddb_key")
    if not chave:
        raise ValueError("Configure a chave SteamGridDB em Provedores online.")
    headers = {"Authorization": "Bearer " + chave}
    base = "https://www.steamgriddb.com/api/v2"
    dados = online.requisitar_json(base + "/search/autocomplete/" +
                                  urllib.parse.quote(item.get("titulo") or "", safe=""), headers=headers)
    out = []
    for jogo in (dados.get("data") or [])[:3]:
        ident = str(jogo.get("id") or "")
        if not ident.isdigit():
            continue
        artes = online.requisitar_json(base + f"/grids/game/{ident}?dimensions=600x900&types=static",
                                       headers=headers)
        for arte in (artes.get("data") or [])[:4]:
            out.append(_item("steamgriddb", jogo.get("name") or "Arte", arte.get("url") or ""))
    return out


def _wikipedia(item):
    titulo = (item.get("titulo") or "").strip().replace(" ", "_")
    if not titulo:
        return []
    dados = online.requisitar_json("https://en.wikipedia.org/api/rest_v1/page/summary/" +
                                  urllib.parse.quote(titulo, safe=""))
    imagem = dados.get("originalimage") or dados.get("thumbnail") or {}
    return [_item("wikipedia", dados.get("title") or titulo, imagem.get("source") or "")]


def _itunes(item):
    artista = item.get("artista") or ""
    termo = " ".join(x for x in (artista, item.get("album") or item.get("titulo")) if x)
    if not termo:
        return []
    dados = online.requisitar_json("https://itunes.apple.com/search?" + urllib.parse.urlencode(
        {"term": termo, "media": "music", "entity": "album", "limit": 6}))
    return [_item("itunes", (r.get("artistName") or "") + " — " + (r.get("collectionName") or "Álbum"),
                  re.sub(r"\d+x\d+bb", "600x600bb", r.get("artworkUrl100") or ""))
            for r in (dados.get("results") or []) if isinstance(r, dict)]


def _musicbrainz(item):
    global _mb_ultimo
    artista, album = item.get("artista") or "", item.get("album") or ""
    if not artista or not album:
        return []
    def esc(texto):
        return texto.replace("\\", "\\\\").replace('"', '\\"')
    url = "https://musicbrainz.org/ws/2/release-group/?" + urllib.parse.urlencode(
        {"query": f'artist:"{esc(artista)}" AND releasegroup:"{esc(album)}"', "fmt": "json", "limit": 5})
    with _mb_lock:
        time.sleep(max(0, 1.05 - (time.monotonic() - _mb_ultimo)))
        try:
            dados = online.requisitar_json(url)
        finally:
            _mb_ultimo = time.monotonic()
    out = []
    for grupo in (dados.get("release-groups") or []):
        mbid = str(grupo.get("id") or "")
        if not re.fullmatch(r"[0-9a-fA-F-]{36}", mbid):
            continue
        autores = " / ".join(a.get("name") or "" for a in grupo.get("artist-credit", []) if isinstance(a, dict))
        out.append(_item("musicbrainz", autores + " — " + (grupo.get("title") or album),
                         f"https://coverartarchive.org/release-group/{mbid}/front-500"))
    return out


def _deezer(item):
    artista = (item.get("artista") or "").split(";")[0].strip()
    album = item.get("album") or item.get("titulo") or ""
    if not artista or not album:
        return []
    termo = f'artist:"{artista.replace(chr(34), "")}" album:"{album.replace(chr(34), "")}"'
    dados = online.requisitar_json("https://api.deezer.com/search/album?" +
                                  urllib.parse.urlencode({"q": termo, "limit": 6}))
    return [_item("deezer", ((r.get("artist") or {}).get("name") or "") + " — " + (r.get("title") or album),
                  r.get("cover_xl") or r.get("cover_big") or "")
            for r in (dados.get("data") or []) if isinstance(r, dict) and
            str((r.get("artist") or {}).get("name") or "").strip().casefold() == artista.casefold()]


def _libretro(item):
    from bib_nucleo.banco import plataforma_jogo
    from bib_nucleo.rede.capas_libretro import url_boxart
    plataforma = item.get("plataforma") or plataforma_jogo(item)
    if plataforma not in ("3DS", "NDS"):
        return []
    return [_item("libretro", item["titulo"] + " · nome No-Intro", url_boxart(plataforma, item["titulo"]))]


_BUSCAS = {"steam": _steam, "steamgriddb": _steamgriddb, "wikipedia": _wikipedia, "libretro": _libretro,
           "itunes": _itunes, "musicbrainz": _musicbrainz, "deezer": _deezer}


def buscar_capas(tipo: str, item: dict, provedor="todos", atualizar=False) -> dict:
    permitidos = PROVEDORES_JOGOS if tipo in ("jogos", "desejos") else PROVEDORES_MUSICAS if tipo == "musicas" else ()
    provedor = provedor or "todos"
    fontes = permitidos if provedor == "todos" else (provedor,)
    if not permitidos or any(p not in permitidos for p in fontes):
        raise ValueError("Provedor de capas inválido para esta categoria.")
    itens, erros = [], []
    caches = 0
    for fonte in fontes:
        if fonte == "steamgriddb" and not online.chave_provedor("steamgriddb_key") and provedor == "todos":
            continue
        chave = repr((fonte, item.get("titulo"), item.get("artista"), item.get("album"), item.get("object_id")))
        alvo = online.cache_path("capas", chave)
        cache = online.ler_json(alvo)
        if isinstance(cache, list) and cache and not atualizar:
            resultado = cache
            caches += 1
        else:
            try:
                resultado = [r for r in _BUSCAS[fonte](item) if online.url_https(r.get("url") or "")]
                if resultado:
                    online.gravar_json(alvo, resultado)
            except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
                erros.append(NOMES[fonte] + ": " + str(e))
                resultado = cache if isinstance(cache, list) else []
                caches += int(bool(resultado))
        itens.extend(resultado)
    vistos = set()
    unicos = []
    for r in itens:
        if r["url"] not in vistos:
            vistos.add(r["url"])
            caminho = online.cache_path("imagens", r["url"], ".img")
            unicos.append(dict(r, preview_url=caminho.resolve().as_uri() if caminho.is_file() else r["url"]))
    return {"itens": unicos[:24], "erros": erros, "cache": bool(caches)}


def salvar_capa_provedor(con, tipo, ident, candidato):
    from bib_nucleo import banco
    raw, ext, _ = online.baixar_imagem(candidato["url"])
    nome = "provedor-" + candidato["provedor"] + ext
    salvar = banco.salvar_capa_bytes if tipo == "jogos" else banco.salvar_capa_musica_bytes
    return salvar(con, ident, nome, raw)


def capa_musica_fallback(artista, album, titulo) -> str:
    item = {"artista": artista, "album": album, "titulo": titulo}
    for fonte in ("musicbrainz", "deezer"):
        resultado = buscar_capas("musicas", item, fonte)
        for candidato in resultado["itens"]:
            try:
                online.baixar_imagem(candidato["url"])
                return candidato["url"]
            except ValueError:
                continue
    return ""
