"""Catálogo Steam e capas iTunes; fachadas locais preservam os contratos antigos."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

from bib_nucleo.rede import abrir_rede, rede_ativa
from bib_nucleo.versao import user_agent


def _capa_steam(appid: str, timeout: int = 15):
    from bib_nucleo.rede.online import url_https
    if not str(appid).isdigit():
        return None
    req = urllib.request.Request(f"https://store.steampowered.com/api/appdetails?appids={appid}",
                                 headers={"User-Agent": user_agent()})
    with abrir_rede(req, timeout=timeout) as r:
        data = json.loads(r.read(2_000_001).decode("utf-8"))
    info = data.get(str(appid)) or {}
    if not info.get("success"):
        return None
    url = ((info.get("data") or {}).get("header_image") or "").split("?")[0]
    if not url_https(url):
        return None
    req = urllib.request.Request(url, headers={"User-Agent": user_agent()})
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
                                         headers={"User-Agent": user_agent()})
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
                                         headers={"User-Agent": user_agent()})
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


# --------------------------------------------------------------------------
# Preços da loja Steam (consulta sob demanda + cache local)
# --------------------------------------------------------------------------

def _precos_lote(appids: list[str], regiao: str, timeout: int = 15) -> dict:
    """Consulta crua de appids numa requisição; {appid: dados|None}.

    `price_overview` ausente (gratuito/fora de venda) vira {"gratis": True}.
    Falha de rede devolve {} — nada é cacheado como sucesso.
    """
    if not appids or not rede_ativa():
        return {}
    try:
        q = urllib.parse.urlencode({"appids": ",".join(appids), "cc": regiao,
                                    "l": "portuguese", "filters": "price_overview"})
        req = urllib.request.Request(f"https://store.steampowered.com/api/appdetails?{q}",
                                     headers={"User-Agent": user_agent()})
        with abrir_rede(req, timeout=timeout) as r:
            dados = json.loads(r.read(1_500_001).decode("utf-8"))
    except (ValueError, OSError, AttributeError, TypeError):
        return {}
    saida = {}
    for appid in appids:
        info = (dados or {}).get(str(appid)) or {}
        if not isinstance(info, dict) or not info.get("success"):
            continue
        po = ((info.get("data") or {}).get("price_overview")) or {}
        if not po:
            saida[appid] = {"appid": appid, "gratis": True, "moeda": "",
                            "final": 0, "inicial": 0, "desconto_pct": 0}
        else:
            saida[appid] = {"appid": appid, "gratis": False,
                            "moeda": str(po.get("currency") or ""),
                            "final": int(po.get("final") or 0),
                            "inicial": int(po.get("initial") or 0),
                            "desconto_pct": int(po.get("discount_percent") or 0)}
    return saida


def _cache_precos_path():
    from bib_nucleo import base
    return base.DADOS_DIR / "precos-steam.json"


def precos_steam(appids, regiao: str = "br", validade_h: float = 24) -> dict:
    """Preços de vários appids com cache local de 24h (padrão).

    Consulta só o que está ausente/vencido, em lotes; falha não é cacheada.
    Rede desligada devolve apenas o que já existe no cache, sem consultar.
    """
    import time

    from bib_nucleo.arquivos import gravar_json, ler_json
    regiao = (regiao or "br").lower()[:8]
    agora = time.time()
    valida = max(0.0, float(validade_h or 0)) * 3600
    alvo = [str(a).strip() for a in (appids or []) if str(a).strip().isdigit()]
    alvo = list(dict.fromkeys(alvo))[:500]
    cache = ler_json(_cache_precos_path(), {})
    cache = cache if isinstance(cache, dict) else {}
    por_regiao = cache.get(regiao)
    por_regiao = dict(por_regiao) if isinstance(por_regiao, dict) else {}
    saida: dict = {}
    faltando: list[str] = []
    for appid in alvo:
        item = por_regiao.get(appid)
        if (isinstance(item, dict) and isinstance(item.get("dados"), dict)
                and (agora - float(item.get("em") or 0)) < valida):
            saida[appid] = item["dados"]
        else:
            faltando.append(appid)
    if faltando and rede_ativa():
        mudou = False
        for i in range(0, len(faltando), 20):
            lote = faltando[i:i + 20]
            obtidos = _precos_lote(lote, regiao)
            for appid in lote:
                dados = obtidos.get(appid)
                if dados is None:
                    continue  # falha não vira cache; próxima consulta tenta de novo
                por_regiao[appid] = {"em": agora, "dados": dados}
                saida[appid] = dados
                mudou = True
        if mudou:
            cache[regiao] = por_regiao
            gravar_json(_cache_precos_path(), cache)
    return saida
