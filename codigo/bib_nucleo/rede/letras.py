"""Letras de músicas via LRCLIB (https://lrclib.net) — sob ação do usuário.

API pública e sem chave. O app se identifica no User-Agent, como o serviço pede.
Respostas definitivas (letra achada ou não cadastrada) ficam em cache local, em
`dados/cache/letras`, para não repetir consultas. Erros de rede não são cacheados.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request

from bib_nucleo.rede import exigir_rede, online

ENDPOINT = "https://lrclib.net/api/get"
USER_AGENT = "TucoTeca/1.0 (uso pessoal; https://github.com/Artur-Lucena/Projeto-Launcher)"
_TEMPO_LRC = re.compile(r"\[(\d{1,3}):(\d{2}(?:\.\d{1,3})?)\]")
_PEDIDOS = threading.Lock()


def linhas_lrc(texto: str) -> list[dict]:
    """'[mm:ss.xx] letra' -> [{'t': segundos, 'texto': ...}], ordenado pelo tempo."""
    saida = []
    for bruta in (texto or "").splitlines():
        bruta = bruta.strip()
        tempos = list(_TEMPO_LRC.finditer(bruta))
        if not tempos or tempos[0].start() != 0:
            continue
        letra = bruta[tempos[-1].end():].lstrip()
        for m in tempos:
            minutos, segundos = int(m.group(1)), float(m.group(2))
            if segundos < 60:
                saida.append({"t": round(minutos * 60 + segundos, 3), "texto": letra})
    return sorted(saida, key=lambda linha: linha["t"])


def _vazio(erro: str) -> dict:
    return {"ok": False, "sincronizadas": False, "linhas": [], "texto": "", "erro": erro}


def _url(artista: str, titulo: str, album: str, duracao_s: int) -> str:
    params = {"artist_name": artista, "track_name": titulo}
    if album:
        params["album_name"] = album
    if duracao_s:
        params["duration"] = int(duracao_s)
    return ENDPOINT + "?" + urllib.parse.urlencode(params)


def buscar_letras(artista: str, titulo: str, album: str = "", duracao_s: int = 0,
                  timeout: int = 15) -> dict:
    """{'ok', 'sincronizadas', 'linhas', 'texto', 'erro', 'cache'}.

    Levanta ValueError se a rede estiver desligada (BIBLIOTECA_REDE=0).
    """
    artista, titulo = (artista or "").strip(), (titulo or "").strip()
    album = str(album or "").strip()
    duracao_s = max(0, int(duracao_s or 0))
    if not artista or not titulo:
        return dict(_vazio("Informe artista e título."), cache=False)
    chave = hashlib.sha256(json.dumps(
        [artista.casefold(), titulo.casefold(), album.casefold(), duracao_s]).encode()).hexdigest()
    alvo = online.cache_path("letras", chave)
    cache = online.ler_json(alvo, None)
    if isinstance(cache, dict) and "ok" in cache:
        return dict(cache, cache=True)
    with _PEDIDOS:
        cache = online.ler_json(alvo, None)
        if isinstance(cache, dict) and "ok" in cache:
            return dict(cache, cache=True)
        return _consultar(artista, titulo, album, duracao_s, timeout, alvo)


def _consultar(artista, titulo, album, duracao_s, timeout, alvo):
    exigir_rede("Buscar letras")
    req = urllib.request.Request(_url(artista, titulo, album, duracao_s),
                                 headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("resposta grande demais")
            dados = json.loads(raw.decode("utf-8"))
            if not isinstance(dados, dict):
                raise ValueError("esperado um objeto JSON")
            for campo in ("syncedLyrics", "plainLyrics"):
                if dados.get(campo) is not None and not isinstance(dados[campo], str):
                    raise ValueError("letra inválida")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            return dict(_vazio(f"LRCLIB respondeu {e.code}; tente de novo mais tarde."), cache=False)
        resultado = _vazio("Esta faixa não tem letra cadastrada.")
    except (OSError, ValueError) as e:
        return dict(_vazio(f"Falha de rede ou resposta inválida: {e}"), cache=False)
    else:
        sincronizado = dados.get("syncedLyrics") or ""
        plano = dados.get("plainLyrics") or ""
        linhas = linhas_lrc(sincronizado)
        tem = bool(linhas or plano)
        resultado = {"ok": tem, "sincronizadas": bool(linhas), "linhas": linhas,
                     "texto": plano or "\n".join(linha["texto"] for linha in linhas),
                     "erro": "" if tem else "Esta faixa não tem letra cadastrada."}
    online.gravar_json(alvo, resultado)
    return dict(resultado, cache=False)
