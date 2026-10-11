"""SponsorBlock opt-in: consulta somente o ID, sem enviar cookies ou perfil."""
from __future__ import annotations

import math
import urllib.parse

from bib_nucleo.rede import exigir_rede, online
from bib_nucleo.rede.videos_youtube import identificar_youtube


def buscar_segmentos(video):
    vid = identificar_youtube(video)
    if not vid:
        raise ValueError("Vídeo inválido.")
    alvo = online.cache_path("sponsorblock", vid)
    cache = online.ler_json(alvo, None)
    if isinstance(cache, list):
        return cache
    exigir_rede("Consultar SponsorBlock")
    url = "https://sponsor.ajay.app/api/skipSegments?" + urllib.parse.urlencode(
        {"videoID": vid, "categories": '["sponsor"]'})
    try:
        dados = online.requisitar_json(url)
    except ValueError as e:
        if "404" in str(e):
            dados = []
        else:
            raise
    if not isinstance(dados, list):
        raise ValueError("Resposta SponsorBlock inválida.")
    segmentos = []
    for d in dados[:1000]:
        if not isinstance(d, dict) or d.get("category") != "sponsor":
            continue
        par = d.get("segment")
        if not isinstance(par, list) or len(par) != 2:
            continue
        try:
            inicio, fim = float(par[0]), float(par[1])
        except (TypeError, ValueError):
            continue
        if math.isfinite(inicio) and math.isfinite(fim) and 0 <= inicio < fim <= 86400:
            segmentos.append([inicio, fim])
    segmentos.sort()
    online.gravar_json(alvo, segmentos)
    return segmentos
