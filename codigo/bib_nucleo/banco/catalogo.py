#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Catálogos de áudio, fila de downloads e videoteca (fatia de banco)."""
from __future__ import annotations

import sqlite3
import uuid as uuid_mod
from pathlib import Path

from bib_nucleo.base import CAPAS_DIR, _txt, agora_iso


def musica_to_dict(r: sqlite3.Row) -> dict:
    return dict(r)


def criar_musica(con: sqlite3.Connection, dados: dict) -> dict:
    titulo = _txt(dados.get("titulo"))
    if not titulo:
        raise ValueError("música sem título")
    sha = _txt(dados.get("musica_sha"))
    if not sha:
        raise ValueError("música sem sha")
    if con.execute("SELECT id FROM musicas WHERE musica_sha=?",
                   (sha,)).fetchone():
        raise ValueError("música já cadastrada (mesmo arquivo)")
    agora = agora_iso()
    try:
        cur = con.execute(
            """INSERT INTO musicas (titulo, artista, album, musica_path,
               musica_sha, origem, criado_em, atualizado_em)
               VALUES (?,?,?,?,?,?,?,?)""",
            (titulo, _txt(dados.get("artista")), _txt(dados.get("album")),
             _txt(dados.get("musica_path")), sha,
             _txt(dados.get("origem")) or "harmoni", agora, agora))
        con.commit()
    except sqlite3.IntegrityError:
        raise ValueError("música já cadastrada (mesmo arquivo)")
    return musica_to_dict(con.execute(
        "SELECT * FROM musicas WHERE id=?", (cur.lastrowid,)).fetchone())


def listar_musicas(con: sqlite3.Connection, q: str = "") -> list[dict]:
    q = (q or "").strip().lower()
    rows = con.execute("SELECT * FROM musicas ORDER BY artista, titulo").fetchall()
    out = [musica_to_dict(r) for r in rows]
    if q:
        out = [m for m in out
               if q in (m.get("titulo") or "").lower()
               or q in (m.get("artista") or "").lower()
               or q in (m.get("album") or "").lower()]
    return out


def excluir_musica(con: sqlite3.Connection, mid: int) -> None:
    row = con.execute("SELECT musica_path, musica_capa FROM musicas WHERE id=?",
                      (mid,)).fetchone()
    if not row:
        raise LookupError("música não encontrada")
    con.execute("DELETE FROM musicas WHERE id=?", (mid,))
    con.commit()
    if row["musica_path"]:
        try:
            from bib_nucleo.base import MUSICAS_DIR
            alvo = Path(row["musica_path"])
            raiz = MUSICAS_DIR.resolve()
            if alvo.resolve() == raiz or raiz in alvo.resolve().parents:
                alvo.unlink()
        except OSError:
            pass
    if row["musica_capa"]:
        try:
            (CAPAS_DIR / Path(row["musica_capa"]).name).unlink()
        except OSError:
            pass

ESTADOS_DOWNLOAD = ("pendente", "baixando", "baixado", "pronta", "falha")

def download_to_dict(r: sqlite3.Row) -> dict:
    return dict(r)


def enfileirar_downloads(con: sqlite3.Connection, itens: list[dict]) -> dict:
    """Põe faixas do CSV na fila com dedup (uri, par, catálogo).

    Ignora sem travar o lote: sem título, uri/par repetido ou faixa que o
    Hub já tem. Retorna {'novos', 'ignorados', 'erros'}.
    """
    novos = ignorados = 0
    erros: list[str] = []
    vistos_uri = {r["uri"] for r in
                  con.execute("SELECT uri FROM downloads").fetchall()}
    vistos_par = {(r["artista"] or "").strip().lower()
                  + "\x00" + (r["titulo"] or "").strip().lower()
                  for r in con.execute(
                      "SELECT artista, titulo FROM downloads").fetchall()}
    agora = agora_iso()
    catalogo = {(str(r["artista"] or "").strip().casefold(),
                 str(r["titulo"] or "").strip().casefold())
                for r in con.execute("SELECT titulo, artista FROM musicas")}
    for item in itens or []:
        if not isinstance(item, dict):
            ignorados += 1
            continue
        tit = _txt((item or {}).get("titulo"))
        if not tit:
            ignorados += 1
            continue
        art = _txt((item or {}).get("artista"))
        uri = _txt((item or {}).get("uri"))
        par = art.strip().lower() + "\x00" + tit.strip().lower()
        if (uri and uri in vistos_uri) or par in vistos_par:
            ignorados += 1
            continue
        if (art.casefold(), tit.casefold()) in catalogo:
            ignorados += 1
            continue
        try:
            con.execute(
                """INSERT INTO downloads (titulo, artista, album, uri, estado,
                   criado_em, atualizado_em) VALUES (?,?,?,?,?,?,?)""",
                (tit, art, _txt((item or {}).get("album")), uri,
                 "pendente", agora, agora))
        except sqlite3.IntegrityError:
            ignorados += 1
            continue
        if uri:
            vistos_uri.add(uri)
        vistos_par.add(par)
        novos += 1
    con.commit()
    return {"novos": novos, "ignorados": ignorados, "erros": erros}


def listar_downloads(con: sqlite3.Connection, estado: str = "") -> list[dict]:
    if estado:
        if estado not in ESTADOS_DOWNLOAD:
            raise ValueError(f"estado inválido: {estado}")
        rows = con.execute("SELECT * FROM downloads WHERE estado=? ORDER BY id",
                           (estado,)).fetchall()
    else:
        rows = con.execute("SELECT * FROM downloads ORDER BY id").fetchall()
    return [download_to_dict(r) for r in rows]


def marcar_download(con: sqlite3.Connection, did: int, estado: str,
                    video_id: str | None = None, erro: str = "",
                    musica_sha: str | None = None, musica_path: str | None = None) -> dict:
    """Avança a faixa; campos omitidos preservam arquivo/identidade para retry."""
    if estado not in ESTADOS_DOWNLOAD:
        raise ValueError(f"estado inválido: {estado}")
    row = con.execute("SELECT * FROM downloads WHERE id=?", (did,)).fetchone()
    if not row:
        raise LookupError("download não encontrado")
    con.execute("UPDATE downloads SET estado=?, video_id=?, erro=?,"
                " musica_sha=?, musica_path=?, atualizado_em=? WHERE id=?",
                (estado, _txt(video_id) if video_id is not None else row["video_id"],
                 _txt(erro), _txt(musica_sha) if musica_sha is not None else row["musica_sha"],
                 _txt(musica_path) if musica_path is not None else row["musica_path"],
                 agora_iso(), did))
    con.commit()
    return download_to_dict(
        con.execute("SELECT * FROM downloads WHERE id=?", (did,)).fetchone())


def limpar_downloads(con: sqlite3.Connection,
                     estados: tuple = ("pronta", "falha")) -> int:
    """Apaga faixas terminadas da fila (Clear Done do Harmoni)."""
    ruins = [e for e in estados if e not in ESTADOS_DOWNLOAD]
    if ruins:
        raise ValueError(f"estado inválido: {ruins}")
    cur = con.execute(
        "DELETE FROM downloads WHERE estado IN (%s)" % ",".join("?" * len(estados)),
        tuple(estados))
    con.commit()
    return cur.rowcount

def video_to_dict(r: sqlite3.Row) -> dict:
    return dict(r)


def criar_video(con: sqlite3.Connection, dados: dict) -> dict:
    titulo = _txt((dados or {}).get("titulo"))
    if not titulo:
        raise ValueError("título do vídeo é obrigatório")
    vid = _txt((dados or {}).get("video_id"))
    if not vid:
        vid = "local:" + uuid_mod.uuid4().hex
    agora = agora_iso()
    try:
        cur = con.execute(
            """INSERT INTO videos (titulo, canal, video_id, video_path, video_sha,
               thumb, origem, duracao_s, criado_em, atualizado_em)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (titulo, _txt((dados or {}).get("canal")), vid,
             _txt((dados or {}).get("video_path")), _txt((dados or {}).get("video_sha")),
             _txt((dados or {}).get("thumb")), _txt((dados or {}).get("origem")) or "local",
             int((dados or {}).get("duracao_s") or 0), agora, agora))
    except sqlite3.IntegrityError:
        raise ValueError("este vídeo já está na videoteca") from None
    con.commit()
    return video_to_dict(con.execute("SELECT * FROM videos WHERE id=?", (cur.lastrowid,)).fetchone())


def listar_videos(con: sqlite3.Connection, q: str = "") -> list[dict]:
    rows = con.execute("SELECT * FROM videos ORDER BY titulo").fetchall()
    out = [video_to_dict(r) for r in rows]
    if (q or "").strip():
        ql = q.strip().lower()
        out = [v for v in out if ql in (v.get("titulo") or "").lower()
               or ql in (v.get("canal") or "").lower()]
    return out


def excluir_video(con: sqlite3.Connection, vid: int) -> None:
    row = con.execute("SELECT id FROM videos WHERE id=?", (vid,)).fetchone()
    if not row:
        raise LookupError("vídeo não encontrado")
    con.execute("DELETE FROM videos WHERE id=?", (vid,))
    con.commit()
