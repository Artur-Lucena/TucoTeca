"""Catálogo da loja Steam (sem chave, sem conta): destaques, busca e página do jogo.

Só leitura pública da loja, em pt-BR e preços do Brasil, com cache curto.
A Steam continua sendo catálogo/referência: nada aqui instala ou abre jogos.
"""
from __future__ import annotations

import urllib.parse

from bib_nucleo.rede import online
from bib_nucleo.rede.provedores._apoio import html_para_texto, obter, respeitar_ritmo
from bib_nucleo.rede.provedores.steam import CDN, appdetails

LOJA = "https://store.steampowered.com"
SECOES = (("specials", "Em promoção"), ("top_sellers", "Mais vendidos"),
          ("new_releases", "Lançamentos"), ("coming_soon", "Em breve"))


def _get(caminho: str, **params) -> dict:
    respeitar_ritmo("store.steampowered.com", 1.0)
    q = urllib.parse.urlencode({"cc": "BR", "l": "brazilian", **params})
    return online.requisitar_json(f"{LOJA}{caminho}?{q}")


def _preco(final, inicial=None, desconto=0, moeda="BRL", gratis=False) -> dict | None:
    if gratis:
        return {"gratis": True, "final": 0, "inicial": 0, "desconto_pct": 0, "moeda": moeda}
    try:
        final = int(final)
    except (TypeError, ValueError):
        return None
    try:
        inicial = int(inicial) if inicial is not None else final
    except (TypeError, ValueError):
        inicial = final
    return {"gratis": False, "final": final, "inicial": inicial,
            "desconto_pct": int(desconto or 0), "moeda": str(moeda or "BRL")}


def _cartao(appid, nome, imagem, preco=None) -> dict | None:
    appid = str(appid or "")
    if not appid.isdigit() or not str(nome or "").strip():
        return None
    imagem = str(imagem or "")
    if not online.url_https(imagem):
        imagem = f"{CDN}/{appid}/header.jpg"
    return {"appid": appid, "nome": str(nome).strip(), "imagem": imagem, "preco": preco}


def destaques() -> list[dict]:
    """Seções da vitrine: [{chave, titulo, itens:[cartão]}] (cache de 6 h)."""
    dados = obter("loja-destaques", "br", 6 * 3600, lambda: _get("/api/featuredcategories"))
    saida = []
    for chave, titulo in SECOES:
        bloco = dados.get(chave) if isinstance(dados, dict) else None
        itens, vistos = [], set()
        for i in (bloco or {}).get("items") or []:
            if not isinstance(i, dict) or str(i.get("id")) in vistos:
                continue
            preco = None
            if i.get("final_price") is not None:
                preco = _preco(i.get("final_price"), i.get("original_price"), i.get("discount_percent"),
                               i.get("currency") or "BRL", gratis=i.get("final_price") == 0 and not i.get("original_price"))
            c = _cartao(i.get("id"), i.get("name"), i.get("large_capsule_image") or i.get("header_image"), preco)
            if c:
                vistos.add(c["appid"])
                itens.append(c)
        if itens:
            saida.append({"chave": chave, "titulo": titulo, "itens": itens[:12]})
    return saida


def buscar(termo: str) -> list[dict]:
    termo = " ".join(str(termo or "").split())
    if len(termo) < 2:
        raise ValueError("Digite pelo menos dois caracteres.")
    dados = obter("loja-busca", termo.casefold(), 86400, lambda: _get("/api/storesearch/", term=termo))
    saida = []
    for i in (dados.get("items") or []) if isinstance(dados, dict) else []:
        if not isinstance(i, dict) or i.get("type", "app") != "app":
            continue
        p = i.get("price") if isinstance(i.get("price"), dict) else None
        preco = _preco(p.get("final"), p.get("initial"), 0, p.get("currency")) if p else None
        appid = str(i.get("id") or "")
        c = _cartao(appid, i.get("name"), f"{CDN}/{appid}/header.jpg", preco)
        if c:
            saida.append(c)
    return saida[:24]


def pagina(appid: str) -> dict:
    """Página da loja de um app (descrição, arte, screenshots, preço)."""
    appid = str(appid or "").strip()
    if not appid.isdigit():
        raise ValueError("appid inválido.")
    info = appdetails(appid)
    if not info:
        raise ValueError("A Steam não tem página para este jogo.")
    po = info.get("price_overview") if isinstance(info.get("price_overview"), dict) else None
    preco = _preco(po.get("final"), po.get("initial"), po.get("discount_percent"), po.get("currency")) if po \
        else _preco(0, gratis=True) if info.get("is_free") else None
    site = str(info.get("website") or "")
    return {
        "appid": appid,
        "nome": str(info.get("name") or appid),
        "tipo": str(info.get("type") or "game"),
        "resumo": html_para_texto(info.get("short_description") or "", 600),
        "descricao": html_para_texto(info.get("about_the_game") or ""),
        "generos": [str(g.get("description")) for g in info.get("genres") or [] if isinstance(g, dict)][:8],
        "desenvolvedora": ", ".join(str(d) for d in (info.get("developers") or [])[:3]),
        "publicadora": ", ".join(str(d) for d in (info.get("publishers") or [])[:3]),
        "lancamento": str((info.get("release_date") or {}).get("date") or ""),
        "site": site if online.url_https(site) else "",
        "hero_url": f"{CDN}/{appid}/library_hero.jpg",
        "logo_url": f"{CDN}/{appid}/logo.png",
        "capa_url": f"{CDN}/{appid}/library_600x900_2x.jpg",
        "screenshots": [s["path_thumbnail"] for s in info.get("screenshots") or []
                        if isinstance(s, dict) and online.url_https(s.get("path_thumbnail") or "")][:8],
        "preco": preco,
        "url_loja": f"{LOJA}/app/{appid}/",
    }


__all__ = ["SECOES", "destaques", "buscar", "pagina"]
