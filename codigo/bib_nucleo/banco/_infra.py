#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Schema, migrações incrementais, FTS e abridor de banco (fatia de banco)."""
from __future__ import annotations

import datetime
import re
import shutil
import sqlite3
import threading
import uuid as uuid_mod
from contextlib import closing
from pathlib import Path

from bib_nucleo.banco_desejos import _garantir_tabela_desejos
from bib_nucleo.base import BACKUP_DIR

# Fonte única das colunas de `jogos`: gera o SCHEMA e a reconstrução da
# migração de UNIQUE (antes a lista de colunas era escrita duas vezes à mão).
COLUNAS_JOGOS: tuple[tuple[str, str], ...] = (
    ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
    ("titulo", "TEXT NOT NULL"),
    ("executable_path", "TEXT DEFAULT ''"),
    ("wine_prefix", "TEXT DEFAULT ''"),
    ("launch_options", "TEXT DEFAULT ''"),
    ("status", "TEXT DEFAULT 'backlog'"),
    ("nota", "INTEGER"),
    ("favorito", "INTEGER DEFAULT 0"),
    ("horas", "REAL DEFAULT 0"),
    ("ultima_execucao", "TEXT"),
    ("observacoes", "TEXT DEFAULT ''"),
    ("origem", "TEXT DEFAULT 'manual'"),
    ("shop", "TEXT DEFAULT ''"),
    ("object_id", "TEXT DEFAULT ''"),
    ("capa", "TEXT DEFAULT ''"),
    ("confianca", "REAL DEFAULT 0"),
    ("exe_win", "TEXT DEFAULT ''"),
    ("exe_linux", "TEXT DEFAULT ''"),
    ("exe_mac", "TEXT DEFAULT ''"),
    ("game_code", "TEXT DEFAULT ''"),
    ("regiao", "TEXT DEFAULT ''"),
    ("azahar_preset", "TEXT DEFAULT ''"),
    ("uuid", "TEXT DEFAULT ''"),
    ("etiquetas", "TEXT DEFAULT ''"),
    ("save_path", "TEXT DEFAULT ''"),
    ("azahar_mods", "TEXT DEFAULT ''"),
    ("azahar_mods_off", "INTEGER DEFAULT 0"),
    ("criado_em", "TEXT"),
    ("atualizado_em", "TEXT"),
)


def _ddl_jogos(tabela: str, se_nao_existe: bool = True) -> str:
    colunas = ",\n".join(f"    {nome} {tipo}" for nome, tipo in COLUNAS_JOGOS)
    criar = "CREATE TABLE IF NOT EXISTS" if se_nao_existe else "CREATE TABLE"
    return (f"\n{criar} {tabela} (\n{colunas},\n"
            "    UNIQUE(titulo, executable_path, launch_options)\n);\n")


SCHEMA = _ddl_jogos("jogos")

# Migração de bancos antigos: v1 (sem capa/confianca), v2 (sem exe por SO),
# v3 (sem game_code/regiao), v4 (sem azahar_preset), v5 (sem uuid),
# v6 (sem etiquetas), v7 (sem save_path), v8 (sem exe_mac),
# v9 (sem azahar_mods), v10 (sem azahar_mods_off), v11 (REMOVIDA: era citron_preset),
# v12 (sem tabela musicas — catálogo de áudio do selfhost).
MIGRACOES = (
    "ALTER TABLE jogos ADD COLUMN capa TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN confianca REAL DEFAULT 0",
    "ALTER TABLE jogos ADD COLUMN exe_win TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN exe_linux TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN exe_mac TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN azahar_mods TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN azahar_mods_off INTEGER DEFAULT 0",
    "ALTER TABLE jogos ADD COLUMN game_code TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN regiao TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN azahar_preset TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN uuid TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN etiquetas TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN save_path TEXT DEFAULT ''",
)

def _garantir_unique_triplo(con: sqlite3.Connection, db_path: Path) -> None:
    """Migra UNIQUE(titulo, executable_path) -> (+ launch_options), uma única vez.

    Sem isso, duas ROMs com mesmo título interno e mesmo emulador colapsam
    numa linha só na importação (perda silenciosa). Preserva ids (capas usam
    o id no nome do arquivo) e faz cópia de segurança do arquivo antes.
    """
    alvo = {"titulo", "executable_path", "launch_options"}
    for ix in con.execute("PRAGMA index_list(jogos)").fetchall():
        if not ix["unique"]:
            continue
        cols = {r["name"] for r in con.execute(
            f'PRAGMA index_info("{ix["name"]}")').fetchall()}
        if cols == alvo:
            return  # já migrado
    try:
        if db_path.is_file() and db_path.stat().st_size > 0:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            shutil.copy2(str(db_path),
                         str(BACKUP_DIR / f"pre-migracao-unique-{ts}.db"))
    except OSError:
        pass
    cols = [nome for nome, _ in COLUNAS_JOGOS]
    todos = ", ".join(cols)
    # banco legado sem UNIQUE: funde triplos repetidos (soma horas, preserva
    # texto) em vez de abortar a migração no meio e órfã jogos_nova
    try:
        dups = con.execute(
            "SELECT titulo, executable_path, launch_options FROM jogos"
            " GROUP BY titulo, executable_path, launch_options"
            " HAVING COUNT(*) > 1").fetchall()
    except sqlite3.OperationalError:
        dups = []
    for _t, _e, _l in [tuple(r) for r in dups]:
        ids = [r["id"] for r in con.execute(
            "SELECT id FROM jogos WHERE titulo IS ? AND executable_path IS ?"
            " AND launch_options IS ? ORDER BY id", (_t, _e, _l)).fetchall()]
        if len(ids) < 2:
            continue
        fica, sai = ids[0], ids[1:]
        agg = con.execute(
            "SELECT COALESCE(SUM(horas), 0), MAX(ultima_execucao),"
            " MAX(nota), MAX(favorito) FROM jogos WHERE id IN (%s)"
            % ",".join("?" * len(ids)), ids).fetchone()
        obs = con.execute(
            "SELECT observacoes FROM jogos WHERE id IN (%s)"
            " AND observacoes IS NOT NULL AND observacoes <> ''"
            " ORDER BY id LIMIT 1" % ",".join("?" * len(ids)),
            ids).fetchone()
        con.execute("UPDATE jogos SET horas=?, ultima_execucao=?, nota=?,"
                    " favorito=?, observacoes=COALESCE(observacoes, '') WHERE id=?",
                    (agg[0], agg[1], agg[2], agg[3] or 0, fica))
        if obs and obs[0]:
            con.execute("UPDATE jogos SET observacoes=? WHERE id=?",
                        (obs[0], fica))
        con.execute("DELETE FROM jogos WHERE id IN (%s)"
                    % ",".join("?" * len(sai)), sai)
    if dups:
        con.commit()
    con.executescript(_ddl_jogos("jogos_nova", se_nao_existe=False) + f"""
        INSERT INTO jogos_nova ({todos}) SELECT {todos} FROM jogos ORDER BY id;
        DROP TABLE jogos;
        ALTER TABLE jogos_nova RENAME TO jogos;
    """)
    con.commit()


def _garantir_uuid(con: sqlite3.Connection) -> None:
    """v5: toda linha tem uuid único (identidade estável p/ pacotes).

    Preenche vazios e cria índice único. Roda em todo get_db (barato quando ok).
    """
    try:
        vazios = [r["id"] for r in con.execute(
            "SELECT id FROM jogos WHERE uuid IS NULL OR uuid=''").fetchall()]
    except sqlite3.OperationalError:
        return  # coluna ainda não existe (banco legado estranho): MIGRACOES cuidam
    vistos = {r["uuid"] for r in con.execute(
        "SELECT uuid FROM jogos WHERE uuid IS NOT NULL AND uuid<>''").fetchall()}
    for gid in vazios:
        novo = uuid_mod.uuid4().hex
        while novo in vistos:
            novo = uuid_mod.uuid4().hex
        vistos.add(novo)
        con.execute("UPDATE jogos SET uuid=? WHERE id=?", (novo, gid))
    # uuid duplicado herdado quebraria o índice único: preserva o menor id
    mexeu = bool(vazios)
    for (dup,) in con.execute(
            "SELECT uuid FROM jogos WHERE uuid IS NOT NULL AND uuid<>''"
            " GROUP BY uuid HAVING COUNT(*) > 1").fetchall():
        ids = [r["id"] for r in con.execute(
            "SELECT id FROM jogos WHERE uuid=? ORDER BY id", (dup,)).fetchall()]
        for gid in ids[1:]:
            novo = uuid_mod.uuid4().hex
            while novo in vistos:
                novo = uuid_mod.uuid4().hex
            vistos.add(novo)
            con.execute("UPDATE jogos SET uuid=? WHERE id=?", (novo, gid))
            mexeu = True
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_jogos_uuid ON jogos(uuid)")
    if mexeu:
        con.commit()

SCHEMA_MUSICAS = """
CREATE TABLE IF NOT EXISTS musicas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    artista TEXT DEFAULT '',
    album TEXT DEFAULT '',
    musica_path TEXT DEFAULT '',
    musica_sha TEXT DEFAULT '',
    musica_capa TEXT DEFAULT '',
    origem TEXT DEFAULT 'harmoni',
    criado_em TEXT,
    atualizado_em TEXT,
    UNIQUE(musica_sha)
);
"""


def _garantir_tabela_musicas(con: sqlite3.Connection) -> None:
    """v12: catálogo de áudio. Idempotente; preserva linhas (sem backup:
    só cria tabela vazia quando ausente)."""
    con.execute(SCHEMA_MUSICAS)
    _garantir_coluna_musica_capa(con)


def _garantir_coluna_musica_capa(con: sqlite3.Connection) -> None:
    """v15: `musica_capa` em bancos pré-capa (aditivo, sem backup)."""
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(musicas)")}
    except sqlite3.Error:
        return
    if cols and "musica_capa" not in cols:
        con.execute("ALTER TABLE musicas ADD COLUMN musica_capa TEXT DEFAULT ''")


def _garantir_sem_citron(con: sqlite3.Connection) -> None:
    """v13: remove a coluna citron_preset (fim do Switch). Idempotente."""
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(jogos)")}
    except sqlite3.OperationalError:
        return
    if "citron_preset" in cols:
        con.execute("ALTER TABLE jogos DROP COLUMN citron_preset")
        con.commit()

SCHEMA_DOWNLOADS = """
CREATE TABLE IF NOT EXISTS downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    artista TEXT DEFAULT '',
    album TEXT DEFAULT '',
    uri TEXT DEFAULT '',
    estado TEXT DEFAULT 'pendente',
    video_id TEXT DEFAULT '',
    musica_sha TEXT DEFAULT '',
    musica_path TEXT DEFAULT '',
    erro TEXT DEFAULT '',
    criado_em TEXT,
    atualizado_em TEXT
);
"""


def _garantir_tabela_downloads(con: sqlite3.Connection) -> None:
    """v14: fila de downloads. Idempotente; preserva linhas."""
    con.execute(SCHEMA_DOWNLOADS)

_DB_INICIALIZADOS: dict[str, tuple] = {}
_DB_INIT_LOCK = threading.RLock()


def get_db(db_path: Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    if str(db_path.parent) and not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        with _DB_INIT_LOCK:
            try:
                st = db_path.stat()
                chave = str(db_path.resolve())
                versao = con.execute("PRAGMA schema_version").fetchone()[0]
                identidade = (st.st_dev, st.st_ino, st.st_mtime_ns, versao)
            except OSError:  # :memory: não possui identidade de arquivo
                chave, identidade = "", None
            pronto = chave and _DB_INICIALIZADOS.get(chave) == identidade
            # Edição manual/legada de linhas continua recebendo backfill de UUID.
            if pronto and con.execute("SELECT 1 FROM jogos WHERE uuid IS NULL OR uuid='' LIMIT 1").fetchone():
                pronto = False
            if not pronto:
                # via fachada: mantém patch.object(banco, '_inicializar_db')
                # efetivo nos testes (o alvo do monkeypatch é o pacote).
                from bib_nucleo import banco as _fachada
                _fachada._inicializar_db(con, db_path)
                if chave:
                    st = db_path.stat()
                    _DB_INICIALIZADOS[chave] = (st.st_dev, st.st_ino, st.st_mtime_ns,
                        con.execute("PRAGMA schema_version").fetchone()[0])
                    if len(_DB_INICIALIZADOS) > 128:
                        _DB_INICIALIZADOS.pop(next(iter(_DB_INICIALIZADOS)))
    except BaseException:
        con.close()
        raise
    return con


FTS_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS jogos_fts USING fts5(
    titulo, etiquetas, executable_path,
    content='jogos', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS jogos_fts_ai AFTER INSERT ON jogos BEGIN
    INSERT INTO jogos_fts(rowid, titulo, etiquetas, executable_path)
    VALUES (new.id, new.titulo, COALESCE(new.etiquetas, ''), new.executable_path);
END;
CREATE TRIGGER IF NOT EXISTS jogos_fts_ad AFTER DELETE ON jogos BEGIN
    INSERT INTO jogos_fts(jogos_fts, rowid, titulo, etiquetas, executable_path)
    VALUES ('delete', old.id, old.titulo, COALESCE(old.etiquetas, ''), old.executable_path);
END;
CREATE TRIGGER IF NOT EXISTS jogos_fts_au AFTER UPDATE ON jogos BEGIN
    INSERT INTO jogos_fts(jogos_fts, rowid, titulo, etiquetas, executable_path)
    VALUES ('delete', old.id, old.titulo, COALESCE(old.etiquetas, ''), old.executable_path);
    INSERT INTO jogos_fts(rowid, titulo, etiquetas, executable_path)
    VALUES (new.id, new.titulo, COALESCE(new.etiquetas, ''), new.executable_path);
END;
"""


def _fts_disponivel(con: sqlite3.Connection) -> bool:
    """FTS5 compilado neste SQLite? ( builds antigos podem não ter)."""
    try:
        con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts5_probe USING fts5(t)")
        con.execute("DROP TABLE _fts5_probe")
        return True
    except sqlite3.Error:
        return False


def garantir_fts(con: sqlite3.Connection) -> bool:
    """Cria/popula uma vez; as triggers mantêm o índice nas aberturas seguintes.

    Índice de conteúdo externo (content='jogos'): ocupa espaço pequeno e
    reflete a tabela via triggers; `rebuild` reindexa a coleção inteira.
    """
    existentes = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE name IN ('jogos_fts','jogos_fts_ai','jogos_fts_ad','jogos_fts_au')")}
    if len(existentes) == 4:
        return True
    if not _fts_disponivel(con):
        return False
    con.executescript(FTS_DDL)
    con.execute("INSERT INTO jogos_fts(jogos_fts) VALUES('rebuild')")
    con.commit()
    return True

def _termo_fts(termo: str) -> str:
    """Termo do usuário → consulta FTS5 segura (prefixo, sem sintaxe do usuário)."""
    palavras = re.findall(r"\w+", str(termo or ""), flags=re.UNICODE)
    return " AND ".join('"' + p + '"*' for p in palavras)

def _inicializar_db(con: sqlite3.Connection, db_path: Path) -> None:
    con.row_factory = sqlite3.Row
    # DELETE (não WAL): sem sidecars -wal/-shm, portátil no NTFS compartilhado.
    con.execute("PRAGMA journal_mode=DELETE;")
    existe = con.execute("SELECT 1 FROM sqlite_master WHERE name='jogos'").fetchone()
    colunas = {r['name'] for r in con.execute('PRAGMA table_info(jogos)')} if existe else set()
    faltantes = [sql for sql in MIGRACOES if sql.split()[5] not in colunas]
    if existe and faltantes:
        try:
            backup_dir = db_path.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            with closing(sqlite3.connect(str(backup_dir / f"pre-migracao-{stamp}.db"))) as dst:
                con.backup(dst)
        except (OSError, sqlite3.Error):
            pass  # best-effort: disco cheio não pode impedir abrir o banco
    con.executescript(SCHEMA)
    if existe:
        for sql in faltantes:
            con.execute(sql)
    _garantir_unique_triplo(con, db_path)
    _garantir_uuid(con)
    _garantir_sem_citron(con)
    _garantir_tabela_musicas(con)
    _garantir_tabela_downloads(con)
    _garantir_tabela_desejos(con)
    _garantir_tabela_videos(con)
    garantir_fts(con)
    con.commit()

SCHEMA_VIDEOS = """
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    canal TEXT DEFAULT '',
    video_id TEXT DEFAULT '',
    video_path TEXT DEFAULT '',
    video_sha TEXT DEFAULT '',
    thumb TEXT DEFAULT '',
    origem TEXT DEFAULT 'local',
    duracao_s INTEGER DEFAULT 0,
    criado_em TEXT,
    atualizado_em TEXT,
    UNIQUE(video_id)
);
"""


def _garantir_tabela_videos(con: sqlite3.Connection) -> None:
    """v18: videoteca. Idempotente; preserva linhas (só cria quando ausente)."""
    con.execute(SCHEMA_VIDEOS)
