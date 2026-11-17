"""Nome de arquivo de vídeo → título, ano, temporada e episódio (sem rede).

Cobre os formatos comuns de release: `S01E02`, `s1e2`, `1x02`, pastas
"Season 1"/"Temporada 1" com `E02`/"Episódio 2", ano entre parênteses ou
pontos, e remove o "lixo" (resolução, codec, fonte, grupo, idioma).
"""
from __future__ import annotations

import re
from pathlib import PurePath

EXTENSOES_VIDEO = (".mkv", ".mp4", ".avi", ".m4v", ".webm", ".mov", ".wmv", ".ts", ".mpg", ".mpeg")
EXTENSOES_LEGENDA = (".srt", ".vtt")

_LIXO = re.compile(
    r"\b(2160p|1080p|1080i|720p|576p|480p|4k|uhd|hdr10?\+?|hdr|dv|dolby ?vision|10bit|8bit|"
    r"x26[45]|h\.?26[45]|hevc|avc|xvid|divx|av1|"
    r"web[ .-]?dl|web[ .-]?rip|webrip|web|bluray|blu[ .-]?ray|brrip|bdrip|bdremux|remux|dvdrip|dvdscr|hdtv|hdrip|"
    r"hdcam|cam|ts|tc|amzn|nf|dsnp|hmax|atvp|pcok|hulu|"
    r"aac(2\.0)?|ac3|eac3|ddp?\d?\.?\d?|dts(-hd)?|truehd|atmos|flac|mp3|opus|"
    r"5\.1|7\.1|2\.0|"
    r"dual[ .-]?audio|dual|dublado|legendado|nacional|multi|multisub|subs?|pt-?br|ptbr|eng?|"
    r"proper|repack|extended|unrated|uncut|directors[ .]cut|imax|internal|limited|complete|"
    r"rarbg|yts|yify|eztv|ettv|psa|tgx|galaxyrg|qxr|ion10)\b",
    re.I)
_EPISODIO = (
    re.compile(r"\bs(\d{1,2})[ ._-]?e(\d{1,3})(?:[-e]+\d{1,3})?\b", re.I),
    re.compile(r"\b(\d{1,2})x(\d{2,3})\b", re.I),
    re.compile(r"\btemporada[ ._-]?(\d{1,2})[ ._-]+epis[oó]dio[ ._-]?(\d{1,3})\b", re.I),
    re.compile(r"\bseason[ ._-]?(\d{1,2})[ ._-]+episode[ ._-]?(\d{1,3})\b", re.I),
)
_SO_EPISODIO = re.compile(r"(?:^|[ ._-])(?:e|ep|episode|epis[oó]dio)[ ._-]?(\d{1,3})\b", re.I)
_PASTA_TEMPORADA = re.compile(r"^(?:season|temporada|s)[ ._-]?(\d{1,2})$", re.I)
_ANO = re.compile(r"(?:^|[ ._(\[-])((?:19[2-9]|20[0-4])\d)(?=$|[ ._)\]-])")


def _limpar(texto: str) -> str:
    t = re.sub(r"\[[^\]]*\]|\{[^}]*\}", " ", texto)          # [grupo], {tags}
    t = re.sub(r"(?<=\w)\.(?=\w)", " ", t)                    # pontos como separador
    t = re.sub(r"[_]+", " ", t)
    t = _LIXO.sub(" ", t)
    t = re.sub(r"\(\s*\)", " ", t)
    t = re.sub(r"\s[-–]\s*$|^\s*[-–]\s", " ", t)
    t = re.sub(r"[\s\-–.]+$", "", t)
    return re.sub(r"\s{2,}", " ", t).strip(" -–.")


def ler_nome(caminho: str) -> dict:
    """{titulo, ano, temporada, episodio, tipo} a partir do caminho do arquivo.

    `tipo` é "series" quando há temporada/episódio, senão "movie". O título de
    série cai para a pasta (ou a pasta-mãe de "Season 1") quando o arquivo só
    tem o número do episódio."""
    p = PurePath(str(caminho).replace("\\", "/"))
    nome = p.stem
    pastas = [x for x in p.parent.parts if x not in ("/", "")]
    temporada = episodio = None
    titulo_cru = nome
    for padrao in _EPISODIO:
        m = padrao.search(nome)
        if m:
            temporada, episodio = int(m.group(1)), int(m.group(2))
            titulo_cru = nome[:m.start()]
            break
    pasta_temp = None
    if pastas:
        mt = _PASTA_TEMPORADA.match(pastas[-1].strip())
        if mt:
            pasta_temp = int(mt.group(1))
    if episodio is None and pasta_temp is not None:
        me = _SO_EPISODIO.search(nome)
        if me:
            temporada, episodio = pasta_temp, int(me.group(1))
            titulo_cru = nome[:me.start()]
    ano = None
    ma = None
    for ma in _ANO.finditer(titulo_cru if episodio is not None else nome):
        pass
    if ma is not None:
        ano = int(ma.group(1))
        if episodio is None:
            titulo_cru = nome[:ma.start()] or nome
    titulo = _limpar(titulo_cru)
    if episodio is not None and len(titulo) < 2:
        # "S01E02.mkv" dentro de "Série/Season 1" ou "Série"
        candidatas = pastas[:-1] if pasta_temp is not None else pastas
        if candidatas:
            titulo = _limpar(candidatas[-1])
            if ano is None:
                m2 = _ANO.search(candidatas[-1])
                if m2:
                    ano = int(m2.group(1))
                    titulo = _limpar(candidatas[-1][:m2.start()])
    if ano is not None and titulo.endswith(str(ano)):
        titulo = titulo[: -len(str(ano))].strip(" -(")
    return {"titulo": titulo or _limpar(nome) or nome, "ano": ano,
            "temporada": temporada, "episodio": episodio,
            "tipo": "series" if episodio is not None else "movie"}


def eh_video(nome: str) -> bool:
    return str(nome).lower().endswith(EXTENSOES_VIDEO)


def legendas_vizinhas(caminho_video: str, irmaos: list[str]) -> list[dict]:
    """Legendas com o mesmo nome do vídeo (`filme.srt`, `filme.pt-BR.srt`, `filme.eng.vtt`)."""
    base = PurePath(caminho_video).stem.casefold()
    saida = []
    for nome in sorted(irmaos):
        p = PurePath(nome)
        if p.suffix.lower() not in EXTENSOES_LEGENDA:
            continue
        stem = p.stem.casefold()
        if stem == base:
            saida.append({"arquivo": nome, "idioma": ""})
        elif stem.startswith(base + "."):
            saida.append({"arquivo": nome, "idioma": p.stem[len(base) + 1:][:12]})
    return saida


__all__ = ["EXTENSOES_VIDEO", "EXTENSOES_LEGENDA", "ler_nome", "eh_video", "legendas_vizinhas"]
