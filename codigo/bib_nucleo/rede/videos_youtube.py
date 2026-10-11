#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Busca/metadados com yt-dlp e download MP4 até 720p para dados/videos/.

A rede só é usada por chamada explícita. Sem FFmpeg, baixa formato MP4
progressivo (áudio+vídeo); com FFmpeg, também pode mesclar fluxos separados.
Não usa fallback acima de 720p nem salva WebM com extensão MP4. O arquivo
final só é publicado depois de confirmar sucesso do downloader.
"""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from bib_nucleo import online
from bib_nucleo.processos import executar_com_progresso

VIDEO_ID_RE = re.compile(r"[A-Za-z0-9_-]{11}")
_YT_HOSTS = ("www.youtube.com", "youtube.com", "youtu.be", "m.youtube.com")


def identificar_youtube(texto: str):
    """(video_id) de URL `watch?v=` / `youtu.be/` / `shorts/` ou ID puro."""
    texto = str(texto or "").strip()
    if VIDEO_ID_RE.fullmatch(texto):
        return texto
    try:
        import urllib.parse
        p = urllib.parse.urlsplit(texto)
        if (p.scheme != "https" or (p.hostname or "").lower() not in _YT_HOSTS
                or p.username or p.password or p.port not in (None, 443)):
            return None
        if (p.hostname or "").lower() == "youtu.be":
            cand = p.path.strip("/").split("/")[0] if p.path.strip("/") else ""
            return cand if VIDEO_ID_RE.fullmatch(cand) else None
        q = urllib.parse.parse_qs(p.query)
        if q.get("v", [""])[0] and VIDEO_ID_RE.fullmatch(q["v"][0]):
            return q["v"][0]
        partes = p.path.strip("/").split("/")
        if len(partes) >= 2 and partes[0] in ("shorts", "embed", "live"):
            return partes[1] if VIDEO_ID_RE.fullmatch(partes[1]) else None
    except (ValueError, AttributeError, IndexError):
        return None
    return None


def _ytdlp() -> str:
    from bib_nucleo.baixar import localizar_ytdlp
    return localizar_ytdlp()


def erro_sem_ytdlp_video() -> str:
    from bib_nucleo.baixar import erro_sem_ytdlp
    return erro_sem_ytdlp() + " (a aba Vídeos usa o mesmo yt-dlp das músicas)."


def _args_js() -> list[str]:
    try:
        from bib_nucleo.baixar import _args_js as _js
        return _js()
    except (ImportError, AttributeError):
        return []


def buscar_youtube(termo: str, limite: int = 10, atualizar: bool = False) -> dict:
    """Pesquisa `ytsearchN:` via yt-dlp. Retorna {itens, erros, cache}."""
    termo = (termo or "").strip()
    if len(termo) < 2:
        raise ValueError("Digite o nome do vídeo/canal para buscar.")
    vid = identificar_youtube(termo)
    if vid:
        try:
            return {"itens": [info_video_youtube(vid)], "erros": [], "cache": False}
        except ValueError as e:
            return {"itens": [], "erros": [str(e)], "cache": False}
    limite = max(1, min(25, int(limite or 10)))
    alvo = online.cache_path("videos-youtube", termo.lower())
    cache = online.ler_json(alvo)
    if isinstance(cache, dict) and cache.get("itens") and not atualizar:
        return {"itens": cache["itens"], "erros": [], "cache": True}
    from bib_nucleo.rede import exigir_rede
    exigir_rede("Pesquisar no YouTube")
    binario = _ytdlp()
    if not binario:
        if isinstance(cache, dict) and cache.get("itens"):
            return {"itens": cache["itens"], "erros": [erro_sem_ytdlp_video()], "cache": True}
        raise ValueError(erro_sem_ytdlp_video())
    from bib_nucleo.ferramentas import comando_externo
    cmd = [*comando_externo(binario), f"ytsearch{limite}:{termo}",
            "--ignore-config", "--flat-playlist", "--no-playlist", "--quiet",
           "--socket-timeout", "20", "--print", "%(id)s\t%(title)s\t%(channel)s\t%(duration)s",
           *_args_js()]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        if isinstance(cache, dict) and cache.get("itens"):
            return {"itens": cache["itens"], "erros": [f"busca falhou: {e}"], "cache": True}
        raise ValueError(f"busca falhou: {e}") from None
    if r.returncode != 0:
        detalhe = (r.stderr or "").strip().splitlines()
        msg = detalhe[-1][:200] if detalhe else f"yt-dlp rc={r.returncode}"
        if isinstance(cache, dict) and cache.get("itens"):
            return {"itens": cache["itens"], "erros": [msg], "cache": True}
        raise ValueError(msg)
    itens = []
    for linha in (r.stdout or "").strip().splitlines():
        partes = linha.split("\t")
        if len(partes) < 2 or not VIDEO_ID_RE.fullmatch((partes[0] or "").strip()):
            continue
        v_id, titulo = partes[0].strip(), partes[1].strip()
        canal = partes[2].strip() if len(partes) > 2 else ""
        try:
            dur = int(float(partes[3])) if len(partes) > 3 and partes[3].strip() not in ("", "NA", "None") else 0
        except (TypeError, ValueError):
            dur = 0
        if titulo:
            itens.append({"video_id": v_id, "titulo": titulo, "canal": canal,
                          "duracao_s": dur,
                          "url": f"https://www.youtube.com/watch?v={v_id}",
                          "thumb": f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg",
                          "origem": "youtube"})
    resultado = {"itens": itens[:25], "erros": [], "cache": False}
    if itens:
        online.gravar_json(alvo, resultado)
    return resultado


def info_video_youtube(video_id: str) -> dict:
    """Metadados de 1 vídeo (`yt-dlp --dump-json`). Levanta ValueError."""
    from bib_nucleo.rede import exigir_rede
    exigir_rede("Consultar vídeo no YouTube")
    video_id = identificar_youtube(video_id) or ""
    if not video_id:
        raise ValueError("Link ou ID do YouTube inválido.")
    binario = _ytdlp()
    if not binario:
        raise ValueError(erro_sem_ytdlp_video())
    from bib_nucleo.ferramentas import comando_externo
    cmd = [*comando_externo(binario), f"https://www.youtube.com/watch?v={video_id}",
            "--ignore-config", "--dump-json", "--no-playlist", "--quiet", "--socket-timeout", "20",
           *_args_js()]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        raise ValueError(f"info falhou: {e}") from None
    if r.returncode != 0:
        detalhe = (r.stderr or "").strip().splitlines()
        raise ValueError(detalhe[-1][:200] if detalhe else f"yt-dlp rc={r.returncode}")
    try:
        dados = json.loads((r.stdout or "").strip().splitlines()[0])
    except (ValueError, IndexError) as e:
        raise ValueError("resposta do YouTube inválida") from e
    if not isinstance(dados, dict):
        raise ValueError("resposta do YouTube inválida")
    try:
        dur = int(dados.get("duration") or 0)
    except (TypeError, ValueError):
        dur = 0
    return {"video_id": video_id, "titulo": str(dados.get("title") or "Vídeo").strip(),
            "canal": str(dados.get("channel") or dados.get("uploader") or "").strip(),
            "duracao_s": dur,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "thumb": str(dados.get("thumbnail") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"),
            "origem": "youtube"}


def _destino_video(video_id: str):
    from bib_nucleo.base import VIDEOS_DIR
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    dest = VIDEOS_DIR / f"{video_id}.mp4"
    n = 1
    while dest.exists():
        n += 1
        dest = VIDEOS_DIR / f"{video_id}-{n}.mp4"
    return dest


def baixar_video_youtube(con, video_id: str, progresso=None) -> dict:
    """Baixa o melhor mp4 ≤720p p/ `videos/` e registra no banco. Nunca levanta."""
    from bib_nucleo import banco as B
    from bib_nucleo.arquivos import destino_temporario
    from bib_nucleo.baixar import localizar_ffmpeg
    from bib_nucleo.videos import sha_arquivo_video
    vid = identificar_youtube(video_id) or ""
    if not vid:
        return {"ok": False, "erro": "Link ou ID do YouTube inválido."}
    try:
        existente = con.execute("SELECT * FROM videos WHERE video_id=?", (vid,)).fetchone()
    except sqlite3.Error as e:
        return {"ok": False, "erro": f"Videoteca indisponível: {e}"}
    if existente:
        from bib_nucleo.reprodutores_video import resolver_video
        caminho = resolver_video(existente["video_path"])
        if caminho:
            return {"ok": True, "video_id": vid, "path": caminho,
                     "titulo": existente["titulo"], "sha": existente["video_sha"], "cache": True}
    from bib_nucleo.rede import exigir_rede
    try:
        exigir_rede("Baixar vídeo do YouTube")
    except ValueError as e:
        return {"ok": False, "erro": str(e)}
    binario = _ytdlp()
    if not binario:
        return {"ok": False, "erro": erro_sem_ytdlp_video()}
    try:
        meta = info_video_youtube(vid)
    except ValueError as e:
        return {"ok": False, "erro": str(e)}
    try:
        dest = _destino_video(vid)
    except OSError as e:
        return {"ok": False, "erro": f"Pasta de vídeos indisponível: {e}"}
    from bib_nucleo.ferramentas import comando_externo
    ffmpeg = localizar_ffmpeg()
    formato = "bv[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]" if ffmpeg else "b[height<=720][ext=mp4]"
    diagnostico = []
    try:
        # A pasta temporária recolhe .part/fragmentos/mesclas após qualquer falha.
        with tempfile.TemporaryDirectory(prefix=".youtube-", dir=dest.parent) as stage, destino_temporario(dest) as tmp:
            saida = Path(stage) / (vid + ".mp4")
            cmd = [*comando_externo(binario), f"https://www.youtube.com/watch?v={vid}",
                   "-o", str(saida), "--ignore-config", "--no-playlist", "--quiet", "--progress", "--newline",
                   "--socket-timeout", "20", "-f", formato, "--merge-output-format", "mp4", *_args_js()]
            if ffmpeg:
                cmd.extend(["--ffmpeg-location", ffmpeg])
            def linha_recebida(linha):
                if "ERROR:" in linha:
                    diagnostico.append(linha.strip()[:300])
                    del diagnostico[:-8]
                m = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", linha or "")
                if m and progresso:
                    progresso(vid, float(m.group(1)))
            rc = executar_com_progresso(cmd, linha_recebida, timeout=1800)
            if rc != 0 or not saida.is_file() or saida.stat().st_size == 0:
                raise ValueError(diagnostico[-1] if diagnostico else f"yt-dlp rc={rc} ou arquivo vazio")
            saida.replace(tmp)
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        return {"ok": False, "erro": f"download: {e}"}
    if progresso:
        try:
            progresso(vid, 100.0)
        except Exception:
            pass
    try:
        sha = sha_arquivo_video(dest)
        dados = {"titulo": meta["titulo"], "canal": meta["canal"],
                             "video_id": vid, "video_path": str(dest),
                             "video_sha": sha, "thumb": meta.get("thumb", ""),
                             "origem": "youtube",
                             "duracao_s": meta.get("duracao_s", 0)}
        if existente:
            con.execute("UPDATE videos SET video_path=?,video_sha=?,atualizado_em=? WHERE id=?",
                        (str(dest), sha, B.agora_iso(), existente["id"]))
            con.commit()
        else:
            B.criar_video(con, dados)
    except (ValueError, OSError, sqlite3.Error) as e:
        try:
            dest.unlink(missing_ok=True)
        except OSError:
            pass
        return {"ok": False, "erro": str(e)}
    return {"ok": True, "video_id": vid, "path": str(dest),
            "titulo": meta["titulo"], "sha": sha}


def baixar_audio_youtube(con, video, progresso=None):
    """MP3 por URL/ID validado; sem busca aproximada nem configuração externa do yt-dlp."""
    from bib_nucleo.arquivos import destino_temporario
    from bib_nucleo.baixar import localizar_ffmpeg
    from bib_nucleo.banco import criar_musica
    from bib_nucleo.base import MUSICAS_DIR
    from bib_nucleo.ferramentas import comando_externo
    from bib_nucleo.musicas import sha_arquivo
    from bib_nucleo.rede import exigir_rede
    vid = identificar_youtube(video)
    if not vid:
        return {"ok": False, "erro": "Link/ID do YouTube inválido."}
    try:
        exigir_rede("Baixar MP3 do YouTube")
        binario, ffmpeg = _ytdlp(), localizar_ffmpeg()
        if not binario or not ffmpeg:
            raise ValueError("MP3 exige yt-dlp e FFmpeg. Instale as dependências de áudio.")
        meta = info_video_youtube(vid)
        MUSICAS_DIR.mkdir(parents=True, exist_ok=True)
        destino = MUSICAS_DIR / (vid + ".mp3")
        n = 1
        while destino.exists():
            n += 1
            destino = MUSICAS_DIR / f"{vid}-{n}.mp3"
        with tempfile.TemporaryDirectory(prefix=".youtube-audio-", dir=MUSICAS_DIR) as tmp, \
             destino_temporario(destino) as parcial:
            stage = Path(tmp)
            cmd = [*comando_externo(binario), f"https://www.youtube.com/watch?v={vid}",
                   "--ignore-config", "--no-playlist", "--socket-timeout", "20", "--quiet",
                   "--newline", "--progress", "-f", "bestaudio/best", "--extract-audio",
                   "--audio-format", "mp3", "--audio-quality", "2", "--ffmpeg-location", ffmpeg,
                   "-o", str(stage / "%(id)s.%(ext)s"), *_args_js()]
            def receber(linha):
                m = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", linha or "")
                if m and progresso:
                    progresso(vid, float(m.group(1)))
            rc = executar_com_progresso(cmd, receber, timeout=1800)
            mp3 = stage / (vid + ".mp3")
            if rc or not mp3.is_file() or not mp3.stat().st_size:
                raise ValueError("Download/conversão MP3 não concluído.")
            mp3.replace(parcial)
        sha = sha_arquivo(destino)
        try:
            criar_musica(con, {"titulo": meta["titulo"], "artista": meta["canal"],
                         "musica_path": str(destino), "musica_sha": sha, "origem": "youtube"})
        except Exception:
            destino.unlink(missing_ok=True)
            raise
        return {"ok": True, "path": str(destino), "titulo": meta["titulo"], "sha": sha}
    except (OSError, ValueError, sqlite3.Error, subprocess.SubprocessError) as e:
        return {"ok": False, "erro": str(e)}


__all__ = ["VIDEO_ID_RE", "identificar_youtube", "erro_sem_ytdlp_video",
           "buscar_youtube", "info_video_youtube", "baixar_video_youtube", "baixar_audio_youtube"]
