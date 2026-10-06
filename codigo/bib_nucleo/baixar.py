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
           'erro_sem_ytdlp', 'consulta_busca', 'casar_video', 'baixar_faixa',
           'localizar_ffmpeg', 'erro_sem_ffmpeg', 'converter_faixa',
           'importar_fila_pronta']


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


# --------------------------------------------------------------------------
# Fase C: mp3 via ffmpeg BYOB (sem ffmpeg: guarda nativo + avisa) + import
# --------------------------------------------------------------------------

def localizar_ffmpeg() -> str:
    """Binário ffmpeg: env `BIBLIOTECA_FFMPEG` → PATH → `''` (ausente)."""
    env = (os.environ.get(FFMPEG_ENV) or "").strip()
    if env and Path(env).is_file():
        return env
    achado = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    return achado or ""


def erro_sem_ffmpeg() -> str:
    return ("ffmpeg não encontrado. mp3 exige ffmpeg"
            " (https://ffmpeg.org) ou aponte BIBLIOTECA_FFMPEG p/ o binário;"
            " sem ele, o Hub guarda o áudio nativo (.m4a).")


def _destino_musica(artista: str, titulo: str, ext: str):
    """Caminho livre em `MUSICAS_DIR` (`slug` + `-n`, molde importar_musicas)."""
    from bib_nucleo.base import MUSICAS_DIR, slugify
    MUSICAS_DIR.mkdir(parents=True, exist_ok=True)
    base = slugify(f"{artista}-{titulo}") or "faixa"
    dest = MUSICAS_DIR / f"{base}{ext}"
    n = 1
    while dest.exists():
        n += 1
        dest = MUSICAS_DIR / f"{base}-{n}{ext}"
    return dest


def converter_faixa(con, did: int, ffmpeg: str = "") -> dict:
    """Converte 1 `baixado` p/ `musicas/` e marca pronta. Nunca levanta.

    Com ffmpeg: mp3 (ID3v2.3 com artista/título/álbum da fila). Sem ffmpeg:
    copia o nativo se tocável (`MUSICA_EXTS`) + aviso; senão falha honesta.
    """
    from bib_nucleo import banco as B
    from bib_nucleo.base import MUSICA_EXTS
    row = con.execute("SELECT * FROM downloads WHERE id=?", (did,)).fetchone()
    if not row:
        return {"ok": False, "erro": "download não encontrado"}
    d = dict(row)
    if d.get("estado") != "baixado":
        return {"ok": False, "erro": f"estado {d.get('estado')} não converte"}
    src = Path(d.get("musica_path") or "")
    if not src.is_file():
        B.marcar_download(con, did, "falha", video_id=d.get("video_id") or "",
                          erro="staging sumiu")
        return {"ok": False, "erro": "staging sumiu"}
    art, tit, alb = (d.get("artista") or "", d.get("titulo") or "",
                     d.get("album") or "")
    binario = (ffmpeg or "").strip() or localizar_ffmpeg()
    if binario:
        dest = _destino_musica(art, tit, ".mp3")
        cmd = [binario, "-y", "-i", str(src), "-codec:a", "libmp3lame",
               "-q:a", "2", "-id3v2_version", "3", "-metadata",
               f"title={tit}", "-metadata", f"artist={art}", "-metadata",
               f"album={alb}", str(dest)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=900)
        except (OSError, subprocess.SubprocessError) as e:
            B.marcar_download(con, did, "falha", video_id=d.get("video_id") or "",
                              erro=f"ffmpeg: {e}")
            return {"ok": False, "erro": f"ffmpeg: {e}"}
        if r.returncode != 0 or not dest.is_file():
            detalhe = (r.stderr or "").strip().splitlines()
            msg = detalhe[-1][:200] if detalhe else f"ffmpeg rc={r.returncode}"
            try:
                dest.unlink()
            except OSError:
                pass
            B.marcar_download(con, did, "falha", video_id=d.get("video_id") or "",
                              erro=msg)
            return {"ok": False, "erro": msg}
        aviso = ""
    else:
        if src.suffix.lower() not in MUSICA_EXTS:
            msg = f"{src.suffix or 'sem ext'} sem ffmpeg: {erro_sem_ffmpeg()}"
            B.marcar_download(con, did, "falha", video_id=d.get("video_id") or "",
                              erro=msg[:300])
            return {"ok": False, "erro": msg}
        dest = _destino_musica(art, tit, src.suffix.lower())
        try:
            import shutil as _sh
            _sh.copy2(str(src), str(dest))
        except OSError as e:
            B.marcar_download(con, did, "falha", video_id=d.get("video_id") or "",
                              erro=f"cópia: {e}")
            return {"ok": False, "erro": f"cópia: {e}"}
        aviso = (f"nativo {dest.suffix} (sem ffmpeg; mp3 quando houver): "
                 f"{erro_sem_ffmpeg()}")
    from bib_nucleo.musicas import sha_arquivo
    try:
        sha = sha_arquivo(dest)
        B.criar_musica(con, {"titulo": tit, "artista": art, "album": alb,
                             "musica_path": str(dest), "musica_sha": sha,
                             "origem": "csv"})
    except ValueError as e:
        try:
            dest.unlink()
        except OSError:
            pass
        B.marcar_download(con, did, "falha", video_id=d.get("video_id") or "",
                          erro=str(e))
        return {"ok": False, "erro": str(e)}
    try:
        src.unlink()
    except OSError:
        pass
    B.marcar_download(con, did, "pronta", video_id=d.get("video_id") or "",
                      musica_sha=sha, musica_path=str(dest))
    out = {"ok": True, "path": str(dest), "sha": sha}
    if aviso:
        out["aviso"] = aviso
    return out


def importar_fila_pronta(con, ffmpeg: str = "") -> dict:
    """Converte todas as `baixado` (Fase C em lote). Nunca levanta."""
    from bib_nucleo import banco as B
    novas = ignoradas = 0
    erros: list[str] = []
    avisos: list[str] = []
    try:
        alvos = [d["id"] for d in B.listar_downloads(con, estado="baixado")]
    except Exception as e:
        return {"novas": 0, "ignoradas": 0, "erros": [str(e)], "avisos": []}
    for did in alvos:
        try:
            r = converter_faixa(con, did, ffmpeg=ffmpeg)
        except Exception as e:
            r = {"ok": False, "erro": str(e)}
        if r.get("ok"):
            novas += 1
            if r.get("aviso") and len(avisos) < 5:
                avisos.append(r["aviso"][:160])
        else:
            ignoradas += 1
            if len(erros) < 20:
                erros.append(f"#{did}: {r.get('erro')}")
    return {"novas": novas, "ignoradas": ignoradas, "erros": erros,
            "avisos": avisos}
