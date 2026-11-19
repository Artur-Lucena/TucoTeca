"""Liga um vídeo do YouTube à mesma música no Spotify (a versão sem o clipe).

Do título do vídeo saem artista e faixa (sem "(Official Video)", "[MV]",
"| Letra"…); a busca no catálogo do Spotify usa o cliente já configurado e
o melhor candidato precisa bater título e artista. Com ele, o MP3 baixado do
YouTube entra na coleção com título, artista, álbum e capa do Spotify. Só
roda quando o usuário pede para baixar; sem Spotify configurado devolve o
motivo, sem falhar.
"""
from __future__ import annotations

import re
import unicodedata

# trechos entre parênteses/colchetes que são do vídeo, não da música
_RUIDO = re.compile(
    r"[\(\[][^\)\]]*\b(official|oficial|video|vídeo|videoclipe|clipe|clip|lyric|lyrics|letra|"
    r"audio|áudio|visualizer|mv|m/v|hd|hq|4k|remaster(?:ed)?|live|ao vivo|legendado|tradução)\b[^\)\]]*[\)\]]",
    re.IGNORECASE)
_SEPARADORES = (" - ", " – ", " — ", " ~ ")
_CANAL_RUIDO = re.compile(r"\s*(-\s*topic|vevo|official|oficial|tv|music|records?)\s*$", re.IGNORECASE)
MINIMO = 0.6


def normalizar(texto: str) -> str:
    """Comparável: sem acento, minúsculo, só letras/números separados por espaço."""
    sem_acento = unicodedata.normalize("NFKD", str(texto or ""))
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^0-9a-z]+", " ", sem_acento.casefold()).split())


def termos_do_video(titulo: str, canal: str = "") -> tuple[str, str]:
    """(artista, faixa) a partir do título do vídeo; sem separador, o canal é o artista."""
    t = _RUIDO.sub(" ", str(titulo or ""))
    t = re.split(r"\s[|•]\s", t)[0]
    t = re.sub(r"\s+", " ", t).strip(" -–—")
    for sep in _SEPARADORES:
        if sep in t:
            artista, faixa = t.split(sep, 1)
            return artista.strip(), faixa.strip(" \"'“”")
    canal = _CANAL_RUIDO.sub("", str(canal or "")).strip()
    return canal, t.strip(" \"'“”")


def _sem_feat(texto: str) -> str:
    return re.split(r"\b(feat|ft|featuring)\b", normalizar(texto))[0].strip()


def pontuar(candidato: dict, artista: str, faixa: str, duracao_s: float | int | None = None) -> float:
    """0..1: título (0,6), artista (0,3) e duração parecida (0,1)."""
    alvo = _sem_feat(faixa)
    titulo = _sem_feat(re.split(r"\s-\s", str(candidato.get("titulo") or ""))[0])
    nota = 0.0
    if alvo and titulo:
        if alvo == titulo:
            nota += 0.6
        elif alvo in titulo or titulo in alvo:
            nota += 0.45
        else:
            a, b = set(alvo.split()), set(titulo.split())
            nota += 0.4 * len(a & b) / max(len(a | b), 1)
    artistas = [normalizar(x) for x in re.split(r";|,|&", str(candidato.get("artista") or "")) if x.strip()]
    quem = normalizar(artista)
    if quem and any(x and (x in quem or quem in x) for x in artistas):
        nota += 0.3
    try:
        dur = float(duracao_s or 0)
        ms = float(candidato.get("duracao_ms") or 0)
    except (TypeError, ValueError):
        dur = ms = 0.0
    if dur > 0 and ms > 0:
        # clipe costuma ter intro/final a mais; até 1 min ainda conta um pouco
        diferenca = abs(dur - ms / 1000)
        nota += 0.1 if diferenca <= 10 else 0.05 if diferenca <= 60 else 0.0
    return round(nota, 3)


def melhor_faixa(candidatos: list[dict], artista: str, faixa: str,
                 duracao_s: float | int | None = None, minimo: float = MINIMO) -> dict | None:
    """O candidato de maior nota, se passar do mínimo (título e artista batendo)."""
    escolhido, maior = None, 0.0
    for c in candidatos or []:
        if not isinstance(c, dict):
            continue
        nota = pontuar(c, artista, faixa, duracao_s)
        if nota > maior:
            escolhido, maior = c, nota
    return dict(escolhido, nota=maior) if escolhido is not None and maior >= minimo else None


def versao_spotify(cliente, video: dict) -> dict:
    """{faixa: dict|None, artista, musica, aviso} para o vídeo `{titulo, canal, duracao_s}`."""
    artista, faixa = termos_do_video(video.get("titulo") or "", video.get("canal") or "")
    saida = {"faixa": None, "artista": artista, "musica": faixa, "aviso": ""}
    if len(faixa) < 2:
        saida["aviso"] = "Não deu para tirar o nome da música do título do vídeo."
        return saida
    try:
        resultado = cliente.catalogo("busca", f"{faixa} {artista}".strip())
    except ValueError as erro:
        saida["aviso"] = str(erro)
        return saida
    saida["faixa"] = melhor_faixa(resultado.get("itens") or [], artista, faixa, video.get("duracao_s"))
    if saida["faixa"] is None:
        saida["aviso"] = "Essa música não apareceu no Spotify."
    return saida


__all__ = ["normalizar", "termos_do_video", "pontuar", "melhor_faixa", "versao_spotify"]
