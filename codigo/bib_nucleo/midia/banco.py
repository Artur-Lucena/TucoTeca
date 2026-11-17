"""Tabelas de Filmes e Séries: pastas escolhidas, títulos (Cinemeta), arquivos e progresso.

O progresso é por "vídeo" no formato do Stremio: `tt0133093` (filme) ou
`tt0903747:1:2` (episódio); arquivo sem correspondência usa `arq:<hash>`.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from bib_nucleo.base import agora_iso

SCHEMA_MIDIA = """
CREATE TABLE IF NOT EXISTS midia_pastas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caminho TEXT NOT NULL UNIQUE,
    adicionada_em TEXT
);
CREATE TABLE IF NOT EXISTS midia_titulos (
    imdb_id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    nome TEXT NOT NULL,
    ano TEXT DEFAULT '',
    poster TEXT DEFAULT '',
    fundo TEXT DEFAULT '',
    logo TEXT DEFAULT '',
    descricao TEXT DEFAULT '',
    generos TEXT DEFAULT '[]',
    meta_json TEXT DEFAULT '{}',
    na_lista INTEGER DEFAULT 0,
    seguindo INTEGER DEFAULT 0,
    atualizado_em TEXT
);
CREATE TABLE IF NOT EXISTS midia_arquivos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caminho TEXT NOT NULL UNIQUE,
    pasta_id INTEGER,
    tamanho INTEGER DEFAULT 0,
    mtime REAL DEFAULT 0,
    hash TEXT DEFAULT '',
    nome_lido TEXT DEFAULT '',
    ano_lido INTEGER,
    tipo_lido TEXT DEFAULT 'movie',
    imdb_id TEXT,
    temporada INTEGER,
    episodio INTEGER,
    confianca REAL DEFAULT 0,
    sugestao TEXT DEFAULT '',
    manual INTEGER DEFAULT 0,
    legendas TEXT DEFAULT '[]',
    ausente INTEGER DEFAULT 0,
    indexado_em TEXT
);
CREATE INDEX IF NOT EXISTS midia_arquivos_imdb ON midia_arquivos(imdb_id);
CREATE TABLE IF NOT EXISTS midia_progresso (
    chave TEXT PRIMARY KEY,
    posicao REAL DEFAULT 0,
    duracao REAL DEFAULT 0,
    assistido INTEGER DEFAULT 0,
    atualizado_em TEXT
);
"""

LIMIAR_ASSISTIDO = 0.92


def garantir_tabelas_midia(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA_MIDIA)


# ---------------------------------------------------------------- pastas

def raiz_valida(caminho: str) -> Path:
    """Pasta existente, absoluta e que não seja a raiz de um disco."""
    p = Path(str(caminho or "")).expanduser()
    if not p.is_absolute():
        raise ValueError("Escolha uma pasta (caminho completo).")
    p = p.resolve()
    if p.parent == p:
        raise ValueError("Escolha uma pasta, não o disco inteiro.")
    if not p.is_dir():
        raise ValueError("Pasta não encontrada.")
    return p


def listar_pastas(con) -> list[dict]:
    garantir_tabelas_midia(con)
    return [{"id": int(r[0]), "caminho": str(r[1]),
             "arquivos": int(con.execute("SELECT COUNT(*) FROM midia_arquivos WHERE pasta_id=? AND ausente=0",
                                         (r[0],)).fetchone()[0])}
            for r in con.execute("SELECT id, caminho FROM midia_pastas ORDER BY id")]


def adicionar_pasta(con, caminho: str) -> dict:
    garantir_tabelas_midia(con)
    p = raiz_valida(caminho)
    for outra in listar_pastas(con):
        o = Path(outra["caminho"])
        if o == p or o in p.parents or p in o.parents:
            raise ValueError(f"Já está coberta pela pasta {outra['caminho']}.")
    cur = con.execute("INSERT INTO midia_pastas(caminho, adicionada_em) VALUES (?, ?)", (str(p), agora_iso()))
    con.commit()
    return {"id": int(cur.lastrowid), "caminho": str(p), "arquivos": 0}


def remover_pasta(con, pid: int) -> None:
    """Tira a pasta do índice (os arquivos no disco não são tocados)."""
    garantir_tabelas_midia(con)
    con.execute("DELETE FROM midia_arquivos WHERE pasta_id=?", (int(pid),))
    con.execute("DELETE FROM midia_pastas WHERE id=?", (int(pid),))
    con.commit()


# ---------------------------------------------------------------- títulos

def gravar_titulo(con, meta: dict, **marcas) -> None:
    """Upsert do título a partir de um `meta` do Cinemeta (mantém lista/seguindo)."""
    garantir_tabelas_midia(con)
    imdb = str(meta.get("imdb_id") or meta.get("id") or "")
    if not imdb.startswith("tt"):
        raise ValueError("Título sem id IMDb.")
    tipo = "series" if meta.get("type") == "series" else "movie"
    campos = {
        "tipo": tipo, "nome": str(meta.get("name") or imdb),
        "ano": str(meta.get("releaseInfo") or meta.get("year") or ""),
        "poster": str(meta.get("poster") or ""), "fundo": str(meta.get("background") or ""),
        "logo": str(meta.get("logo") or ""), "descricao": str(meta.get("description") or ""),
        "generos": json.dumps([str(g) for g in meta.get("genres") or []][:8], ensure_ascii=False),
        "meta_json": json.dumps({k: meta[k] for k in ("videos", "runtime", "imdbRating", "director", "cast")
                                 if k in meta}, ensure_ascii=False),
    }
    existe = con.execute("SELECT 1 FROM midia_titulos WHERE imdb_id=?", (imdb,)).fetchone()
    if existe:
        sets = ", ".join(f"{k}=?" for k in campos)
        con.execute(f"UPDATE midia_titulos SET {sets}, atualizado_em=? WHERE imdb_id=?",
                    (*campos.values(), agora_iso(), imdb))
    else:
        con.execute(f"INSERT INTO midia_titulos(imdb_id, {', '.join(campos)}, atualizado_em) "
                    f"VALUES (?, {', '.join('?' * len(campos))}, ?)", (imdb, *campos.values(), agora_iso()))
    for marca in ("na_lista", "seguindo"):
        if marca in marcas:
            con.execute(f"UPDATE midia_titulos SET {marca}=? WHERE imdb_id=?", (int(bool(marcas[marca])), imdb))
    con.commit()


def ler_titulo(con, imdb: str) -> dict | None:
    garantir_tabelas_midia(con)
    r = con.execute("SELECT * FROM midia_titulos WHERE imdb_id=?", (str(imdb),)).fetchone()
    if r is None:
        return None
    d = dict(r)
    d["generos"] = json.loads(d.get("generos") or "[]")
    d["meta"] = json.loads(d.pop("meta_json") or "{}")
    d["na_lista"], d["seguindo"] = bool(d["na_lista"]), bool(d["seguindo"])
    return d


def marcar_titulo(con, imdb: str, **marcas) -> None:
    for marca, valor in marcas.items():
        if marca not in ("na_lista", "seguindo"):
            raise ValueError(f"marca desconhecida: {marca}")
        con.execute(f"UPDATE midia_titulos SET {marca}=? WHERE imdb_id=?", (int(bool(valor)), str(imdb)))
    con.commit()


# ---------------------------------------------------------------- progresso

def chave_do_arquivo(arq: dict) -> str:
    imdb = arq.get("imdb_id") or ""
    if imdb and arq.get("temporada") is not None and arq.get("episodio") is not None:
        return f"{imdb}:{int(arq['temporada'])}:{int(arq['episodio'])}"
    if imdb:
        return imdb
    return f"arq:{arq.get('hash') or arq.get('id')}"


def salvar_progresso(con, chave: str, posicao: float, duracao: float) -> dict:
    garantir_tabelas_midia(con)
    posicao, duracao = max(0.0, float(posicao)), max(0.0, float(duracao))
    assistido = duracao > 0 and posicao / duracao >= LIMIAR_ASSISTIDO
    antes = con.execute("SELECT assistido FROM midia_progresso WHERE chave=?", (chave,)).fetchone()
    assistido = assistido or bool(antes and antes[0] and posicao < 5)  # reabrir do início não "desassiste"
    con.execute("INSERT INTO midia_progresso(chave, posicao, duracao, assistido, atualizado_em) VALUES (?,?,?,?,?) "
                "ON CONFLICT(chave) DO UPDATE SET posicao=excluded.posicao, duracao=excluded.duracao, "
                "assistido=excluded.assistido, atualizado_em=excluded.atualizado_em",
                (chave, 0.0 if assistido else posicao, duracao, int(assistido), agora_iso()))
    con.commit()
    return {"chave": chave, "assistido": assistido}


def marcar_assistido(con, chaves: list[str], assistido: bool) -> None:
    garantir_tabelas_midia(con)
    for chave in chaves:
        con.execute("INSERT INTO midia_progresso(chave, posicao, duracao, assistido, atualizado_em) VALUES (?,0,0,?,?) "
                    "ON CONFLICT(chave) DO UPDATE SET posicao=0, assistido=excluded.assistido, "
                    "atualizado_em=excluded.atualizado_em", (str(chave), int(bool(assistido)), agora_iso()))
    con.commit()


def progresso(con, chaves=None) -> dict[str, dict]:
    garantir_tabelas_midia(con)
    if chaves is None:
        rows = con.execute("SELECT * FROM midia_progresso").fetchall()
    else:
        chaves = list(chaves)
        rows = []
        for i in range(0, len(chaves), 500):
            lote = chaves[i:i + 500]
            rows += con.execute(f"SELECT * FROM midia_progresso WHERE chave IN ({','.join('?' * len(lote))})",
                                lote).fetchall()
    return {r["chave"]: {"posicao": float(r["posicao"]), "duracao": float(r["duracao"]),
                         "assistido": bool(r["assistido"]), "atualizado_em": r["atualizado_em"]} for r in rows}


__all__ = ["SCHEMA_MIDIA", "LIMIAR_ASSISTIDO", "garantir_tabelas_midia", "raiz_valida", "listar_pastas",
           "adicionar_pasta", "remover_pasta", "gravar_titulo", "ler_titulo", "marcar_titulo",
           "chave_do_arquivo", "salvar_progresso", "marcar_assistido", "progresso"]
