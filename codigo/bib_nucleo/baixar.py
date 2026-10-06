#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fila CSV → mp3 tal qual o Harmoni: lê Exportify e enfileira p/ baixar.

Fase A (sem rede): parse + fila no banco (`downloads`, v14).
Fase B: download via yt-dlp BYOB p/ staging (`baixados/`).
Fase C (depois): mp3/ffmpeg + import p/ `musicas/`.
"""
from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
from pathlib import Path

YTDLP_ENV = "BIBLIOTECA_YTDLP"
FFMPEG_ENV = "BIBLIOTECA_FFMPEG"  # Fase C usa; nome centralizado aqui

_PCT_RE = re.compile(r"\[download\]\s+(\d+(?:\.\d+)?)%")

_COL_TRACK = "Track Name"
_COL_ALBUM = "Album Name"
_COL_ARTIST = "Artist Name(s)"
_COL_URI = "Track URI"


__all__ = ['primeiro_artista', 'ler_csv_exportify', 'localizar_ytdlp',
           'erro_sem_ytdlp', 'consulta_busca', 'casar_video', 'baixar_faixa']


def primeiro_artista(campo: str) -> str:
    """`A;B;C` (Exportify) → `A` (o 1º, como a busca do Harmoni usa)."""
    return (campo or "").split(";")[0].strip()


def ler_csv_exportify(caminho: str | os.PathLike) -> dict:
    """{'itens': [{titulo, artista, album, uri}], 'ignorados': n, 'erros': []}.

    Só leitura, nunca levanta por arquivo estranho (vira `erros`).
    """
    p = Path(caminho)
    try:
        fh = p.open("r", encoding="utf-8-sig", newline="")
    except OSError as e:
        return {"itens": [], "ignorados": 0, "erros": [f"não abri: {e}"]}
    itens: list[dict] = []
    ignorados = 0
    erros: list[str] = []
    num = 1
    try:
        try:
            leitor = csv.DictReader(fh)
        except (csv.Error, UnicodeDecodeError) as e:
            return {"itens": [], "ignorados": 0, "erros": [f"csv inválido: {e}"]}
        if not leitor.fieldnames or _COL_TRACK not in leitor.fieldnames:
            return {"itens": [], "ignorados": 0,
                    "erros": ["não é um CSV Exportify (sem 'Track Name')"]}
        for num, lin in enumerate(leitor, start=2):
            tit = ((lin.get(_COL_TRACK) if isinstance(lin, dict) else "") or "")
            tit = tit.strip()
            if not tit:
                ignorados += 1
                continue
            art = lin.get(_COL_ARTIST) if isinstance(lin, dict) else ""
            alb = lin.get(_COL_ALBUM) if isinstance(lin, dict) else ""
            uri = lin.get(_COL_URI) if isinstance(lin, dict) else ""
            itens.append({"titulo": tit,
                          "artista": primeiro_artista(art or ""),
                          "album": (alb or "").strip(),
                          "uri": (uri or "").strip()})
    except (csv.Error, UnicodeDecodeError) as e:
        if len(erros) < 20:
            erros.append(f"linha {num}: {e}")
    finally:
        try:
            fh.close()
        except OSError:
            pass
    return {"itens": itens, "ignorados": ignorados, "erros": erros}


# --------------------------------------------------------------------------
# Fase B: download via yt-dlp BYOB (molde 7z/emuladores: detecta, nunca bundle)
# --------------------------------------------------------------------------

def localizar_ytdlp() -> str:
    """Binário yt-dlp: env `BIBLIOTECA_YTDLP` → PATH → `''` (ausente)."""
    env = (os.environ.get(YTDLP_ENV) or "").strip()
    if env and Path(env).is_file():
        return env
    achado = shutil.which("yt-dlp") or shutil.which("yt-dlp.exe")
    return achado or ""


def erro_sem_ytdlp() -> str:
    return ("yt-dlp não encontrado. Instale"
            " (https://github.com/yt-dlp/yt-dlp) ou aponte"
            " BIBLIOTECA_YTDLP p/ o binário.")


def consulta_busca(artista: str, titulo: str) -> str:
    """`ytsearch1:Artista - Título` (vazio se sem título)."""
    q = " - ".join(x for x in ((artista or "").strip(),
                               (titulo or "").strip()) if x)
    return f"ytsearch1:{q}" if q else ""


def casar_video(ytdlp: str, artista: str, titulo: str) -> dict:
    """1º resultado da busca (automático, tal qual o Harmoni). Levanta ValueError."""
    q = consulta_busca(artista, titulo)
    if not q:
        raise ValueError("faixa sem título")
    try:
        r = subprocess.run(
            [ytdlp, q, "--print", "%(id)s\t%(title)s", "--no-playlist",
             "--quiet", "--socket-timeout", "20"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        raise ValueError(f"busca falhou: {e}")
    if r.returncode != 0:
        detalhe = (r.stderr or "").strip().splitlines()
        raise ValueError(f"busca falhou ({detalhe[-1][:160] if detalhe else 'rc'})")
    linhas = (r.stdout or "").strip().splitlines()
    if not linhas or "\t" not in linhas[0]:
        raise ValueError("busca sem resultado")
    vid, vtit = linhas[0].split("\t", 1)
    if not vid.strip():
        raise ValueError("busca sem resultado")
    return {"video_id": vid.strip(), "video_titulo": vtit.strip()}


def baixar_faixa(con, did: int, ytdlp: str = "", destino=None,
                 progresso=None) -> dict:
    """Baixa 1 faixa p/ staging (`baixados/`). Marca baixando→baixado|falha.

    `progresso(did, pct)` opcional (UI). Nunca levanta: falha vira estado.
    """
    from bib_nucleo import banco as B
    from bib_nucleo.base import BAIXAR_DIR
    row = con.execute("SELECT * FROM downloads WHERE id=?", (did,)).fetchone()
    if not row:
        return {"ok": False, "erro": "download não encontrado"}
    d = dict(row)
    if d.get("estado") not in ("pendente", "falha", "baixando"):
        return {"ok": False, "erro": f"estado {d.get('estado')} não baixa"}
    binario = (ytdlp or "").strip() or localizar_ytdlp()
    if not binario:
        return {"ok": False, "erro": erro_sem_ytdlp()}
    try:
        B.marcar_download(con, did, "baixando")
    except (LookupError, ValueError) as e:
        return {"ok": False, "erro": str(e)}
    try:
        casa = casar_video(binario, d.get("artista") or "",
                           d.get("titulo") or "")
    except ValueError as e:
        B.marcar_download(con, did, "falha", erro=str(e))
        return {"ok": False, "erro": str(e)}
    base = Path(destino) if destino else BAIXAR_DIR
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        B.marcar_download(con, did, "falha", video_id=casa["video_id"],
                          erro=f"staging: {e}")
        return {"ok": False, "erro": f"staging: {e}"}
    cmd = [binario, f"https://www.youtube.com/watch?v={casa['video_id']}",
           "-o", str(base / "%(id)s.%(ext)s"), "--no-playlist", "--quiet",
           "--progress", "--newline", "--socket-timeout", "20",
           "-f", "bestaudio/best"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError) as e:
        B.marcar_download(con, did, "falha", video_id=casa["video_id"],
                          erro=f"download: {e}")
        return {"ok": False, "erro": f"download: {e}"}
    try:
        for linha in (proc.stdout or []):
            m = _PCT_RE.search(linha or "")
            if m and progresso:
                try:
                    progresso(did, float(m.group(1)))
                except Exception:
                    pass
        rc = proc.wait(timeout=1800)
    except (OSError, subprocess.SubprocessError) as e:
        B.marcar_download(con, did, "falha", video_id=casa["video_id"],
                          erro=f"download: {e}")
        return {"ok": False, "erro": f"download: {e}"}
    if rc != 0:
        B.marcar_download(con, did, "falha", video_id=casa["video_id"],
                          erro=f"yt-dlp rc={rc}")
        return {"ok": False, "erro": f"yt-dlp rc={rc}"}
    achados = sorted(base.glob(f"{casa['video_id']}.*"))
    if not achados:
        B.marcar_download(con, did, "falha", video_id=casa["video_id"],
                          erro="arquivo sumiu")
        return {"ok": False, "erro": "arquivo sumiu"}
    arq = achados[0]
    if progresso:
        try:
            progresso(did, 100.0)
        except Exception:
            pass
    B.marcar_download(con, did, "baixado", video_id=casa["video_id"],
                      musica_path=str(arq))
    return {"ok": True, "video_id": casa["video_id"], "path": str(arq)}
