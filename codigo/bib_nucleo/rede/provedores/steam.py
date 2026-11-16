"""Steam (sem chave): descrição em pt-BR, gêneros, estúdio, lançamento, arte e screenshots."""
from __future__ import annotations

import urllib.parse

from bib_nucleo.rede import online
from bib_nucleo.rede.provedores._apoio import html_para_texto, obter, respeitar_ritmo

CDN = "https://cdn.cloudflare.steamstatic.com/steam/apps"
VALIDADE = 7 * 86400


def appdetails(appid: str) -> dict:
    """`data` do appdetails (pt-BR), em cache por 7 dias; {} se a Steam não conhece."""
    appid = str(appid or "").strip()
    if not appid.isdigit():
        return {}

    def buscar():
        respeitar_ritmo("store.steampowered.com", 1.5)
        return online.requisitar_json("https://store.steampowered.com/api/appdetails?" +
                                      urllib.parse.urlencode({"appids": appid, "l": "brazilian"}))
    dados = obter("steam-appdetails", appid, VALIDADE, buscar)
    app = (dados or {}).get(appid) or {}
    return (app.get("data") or {}) if app.get("success") else {}


def resolver_appid(jogo: dict, meta: dict) -> str:
    appid = str(meta.get("steam_appid") or "")
    if appid.isdigit():
        return appid
    if jogo.get("shop") == "steam" and str(jogo.get("object_id") or "").isdigit():
        return str(jogo["object_id"])
    from bib_nucleo.rede.metadados import canonizar_steam
    appid, _ = canonizar_steam(jogo.get("titulo") or "")
    return appid


def buscar(jogo: dict, meta: dict) -> dict:
    appid = resolver_appid(jogo, meta)
    if not appid:
        return {}
    info = appdetails(appid)
    if not info:
        return {"steam_appid": appid}
    data_lanc = (info.get("release_date") or {}).get("date") or ""
    site = str(info.get("website") or "")
    return {
        "steam_appid": appid,
        "resumo": html_para_texto(info.get("short_description") or "", 600),
        "descricao": html_para_texto(info.get("about_the_game") or info.get("detailed_description") or ""),
        "generos": [str(g.get("description")) for g in (info.get("genres") or [])
                    if isinstance(g, dict) and g.get("description")][:8],
        "desenvolvedora": ", ".join(str(d) for d in (info.get("developers") or [])[:3]),
        "publicadora": ", ".join(str(d) for d in (info.get("publishers") or [])[:3]),
        "lancamento": str(data_lanc),
        "site": site if online.url_https(site) else "",
        "hero_url": f"{CDN}/{appid}/library_hero.jpg",
        "logo_url": f"{CDN}/{appid}/logo.png",
        "screenshots_urls": [s["path_thumbnail"] for s in (info.get("screenshots") or [])
                             if isinstance(s, dict) and online.url_https(s.get("path_thumbnail") or "")][:6],
    }


def candidatos_arte(appid: str, tipo: str) -> list[str]:
    """URLs de arte oficial pela CDN (sem consulta à API)."""
    if not str(appid).isdigit():
        return []
    nome = {"hero": "library_hero.jpg", "logo": "logo.png", "capa": "library_600x900_2x.jpg"}.get(tipo)
    return [f"{CDN}/{appid}/{nome}"] if nome else []


__all__ = ["appdetails", "resolver_appid", "buscar", "candidatos_arte"]
