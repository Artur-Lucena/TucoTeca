#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite: schema, migrações, validação, CRUD, capas e horas."""
from __future__ import annotations

import base64
import datetime
import math
import shutil
import sqlite3
import uuid as uuid_mod
from pathlib import Path

from bib_nucleo.base import (BACKUP_DIR, CAPAS_DIR, _desaspas, _txt,
                                agora_iso, resolver_exe, slugify)



# --------------------------------------------------------------------------
# Banco + validação + CRUD
# --------------------------------------------------------------------------

STATUS_VALIDOS = ("backlog", "jogando", "zerado", "pausado", "abandonado")


SCHEMA = """
CREATE TABLE IF NOT EXISTS jogos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    executable_path TEXT DEFAULT '',
    wine_prefix TEXT DEFAULT '',
    launch_options TEXT DEFAULT '',
    status TEXT DEFAULT 'backlog',
    nota INTEGER,
    favorito INTEGER DEFAULT 0,
    horas REAL DEFAULT 0,
    ultima_execucao TEXT,
    observacoes TEXT DEFAULT '',
    origem TEXT DEFAULT 'manual',
    shop TEXT DEFAULT '',
    object_id TEXT DEFAULT '',
    capa TEXT DEFAULT '',
    confianca REAL DEFAULT 0,
    exe_win TEXT DEFAULT '',
    exe_linux TEXT DEFAULT '',
    game_code TEXT DEFAULT '',
    regiao TEXT DEFAULT '',
    azahar_preset TEXT DEFAULT '',
    uuid TEXT DEFAULT '',
    criado_em TEXT,
    atualizado_em TEXT,
    UNIQUE(titulo, executable_path, launch_options)
);
"""


# Migração de bancos antigos: v1 (sem capa/confianca), v2 (sem exe por SO),
# v3 (sem game_code/regiao), v4 (sem azahar_preset), v5 (sem uuid).
MIGRACOES = (
    "ALTER TABLE jogos ADD COLUMN capa TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN confianca REAL DEFAULT 0",
    "ALTER TABLE jogos ADD COLUMN exe_win TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN exe_linux TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN game_code TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN regiao TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN azahar_preset TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN uuid TEXT DEFAULT ''",
)


CAMPOS_EDITAVEIS = ("titulo", "executable_path", "exe_win", "exe_linux",
                    "wine_prefix", "launch_options", "status", "nota", "favorito",
                    "horas", "observacoes", "shop", "object_id", "origem",
                    "game_code", "regiao", "azahar_preset")



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
    cols = ["id", "titulo", "executable_path", "exe_win", "exe_linux", "wine_prefix",
            "launch_options", "status", "nota", "favorito", "horas", "ultima_execucao",
            "observacoes", "origem", "shop", "object_id", "game_code", "regiao",
            "azahar_preset", "uuid", "capa", "confianca", "criado_em", "atualizado_em"]
    todos = ", ".join(cols)
    con.executescript(f"""
        CREATE TABLE jogos_nova (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            executable_path TEXT DEFAULT '',
            exe_win TEXT DEFAULT '',
            exe_linux TEXT DEFAULT '',
            wine_prefix TEXT DEFAULT '',
            launch_options TEXT DEFAULT '',
            status TEXT DEFAULT 'backlog',
            nota INTEGER,
            favorito INTEGER DEFAULT 0,
            horas REAL DEFAULT 0,
            ultima_execucao TEXT,
            observacoes TEXT DEFAULT '',
            origem TEXT DEFAULT 'manual',
            shop TEXT DEFAULT '',
            object_id TEXT DEFAULT '',
            game_code TEXT DEFAULT '',
            regiao TEXT DEFAULT '',
            azahar_preset TEXT DEFAULT '',
            uuid TEXT DEFAULT '',
            capa TEXT DEFAULT '',
            confianca REAL DEFAULT 0,
            criado_em TEXT,
            atualizado_em TEXT,
            UNIQUE(titulo, executable_path, launch_options)
        );
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
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_jogos_uuid ON jogos(uuid)")
    if vazios:
        con.commit()



def get_db(db_path: Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    if str(db_path.parent) and not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    # DELETE (não WAL): sem sidecars -wal/-shm, portátil no NTFS compartilhado.
    con.execute("PRAGMA journal_mode=DELETE;")
    existe = con.execute("SELECT 1 FROM sqlite_master WHERE name='jogos'").fetchone()
    colunas = {r['name'] for r in con.execute('PRAGMA table_info(jogos)')} if existe else set()
    faltantes = [sql for sql in MIGRACOES if sql.split()[5] not in colunas]
    if existe and faltantes:
        backup_dir = db_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        with sqlite3.connect(str(backup_dir / f"pre-migracao-{stamp}.db")) as dst:
            con.backup(dst)
    con.executescript(SCHEMA)
    if existe:
        for sql in faltantes:
            con.execute(sql)
    _garantir_unique_triplo(con, db_path)
    _garantir_uuid(con)
    con.commit()
    return con



def row_to_dict(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["favorito"] = bool(d.get("favorito"))
    exe, _origem = resolver_exe(d)
    if not exe:
        from bib_nucleo.emuladores import provedor_por_origem
        prov = provedor_por_origem(d.get("origem") or "")
        if prov:
            exe = prov["exe"]()
    try:
        existe = bool(exe) and Path(exe).exists()
    except (ValueError, OSError):
        existe = False  # caminho malformado vindo de importação antiga
    d["exe_existe"] = existe
    d["exe_traduzido"] = exe
    return d



def validar_dados(dados: dict, parcial: bool = False) -> dict:
    """Limpa e valida campos de jogo. Retorna dict limpo ou levanta ValueError."""
    limpo: dict = {}
    if "titulo" in dados or not parcial:
        titulo = _txt(dados.get("titulo"))
        if not titulo:
            raise ValueError("titulo é obrigatório")
        limpo["titulo"] = titulo
    if "executable_path" in dados or not parcial:
        limpo["executable_path"] = _desaspas(_txt(dados.get("executable_path")))
    for campo in ("exe_win", "exe_linux", "game_code", "regiao", "azahar_preset"):
        if campo in dados or not parcial:
            v = _txt(dados.get(campo))
            limpo[campo] = _desaspas(v) if campo.startswith("exe_") else v
    for campo in ("wine_prefix", "launch_options", "observacoes", "shop", "object_id"):
        if campo in dados or not parcial:
            limpo[campo] = _txt(dados.get(campo))
    if "status" in dados or not parcial:
        status = dados.get("status") or "backlog"
        if status not in STATUS_VALIDOS:
            raise ValueError(f"status inválido. Use: {STATUS_VALIDOS}")
        limpo["status"] = status
    if "nota" in dados or not parcial:
        nota = dados.get("nota")
        if nota == "":
            nota = None
        if nota is not None:
            try:
                nota = int(nota)
            except (TypeError, ValueError):
                raise ValueError("nota deve ser inteiro 0-10 ou vazio")
            if not 0 <= nota <= 10:
                raise ValueError("nota deve ser inteiro 0-10 ou vazio")
        limpo["nota"] = nota
    if "favorito" in dados or not parcial:
        limpo["favorito"] = 1 if dados.get("favorito") else 0
    if "horas" in dados or not parcial:
        try:
            horas = float(dados.get("horas") or 0)
        except (TypeError, ValueError):
            raise ValueError("horas deve ser número >= 0")
        if not math.isfinite(horas) or horas < 0:
            raise ValueError("horas deve ser número >= 0")
        limpo["horas"] = horas
    if "origem" in dados or not parcial:
        limpo["origem"] = _txt(dados.get("origem")) or "manual"
    return limpo



def _like_esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")



def listar_jogos(con: sqlite3.Connection, q: str = "", status: str = "",
                 favorito: bool = False) -> list[dict]:
    sql = "SELECT * FROM jogos WHERE 1=1"
    params: list = []
    if q:
        sql += " AND (titulo LIKE ? ESCAPE '\\' OR executable_path LIKE ? ESCAPE '\\')"
        like = f"%{_like_esc(q)}%"
        params += [like, like]
    if status:
        sql += " AND status = ?"
        params.append(status)
    if favorito:
        sql += " AND favorito = 1"
    sql += " ORDER BY favorito DESC, titulo COLLATE NOCASE"
    return [row_to_dict(r) for r in con.execute(sql, params).fetchall()]



def criar_jogo(con: sqlite3.Connection, dados: dict) -> dict:
    limpo = validar_dados(dados)
    limpo["uuid"] = _txt(dados.get("uuid")) or uuid_mod.uuid4().hex
    agora = agora_iso()
    try:
        cur = con.execute(
            """INSERT INTO jogos (titulo, executable_path, exe_win, exe_linux, wine_prefix,
               launch_options, status, nota, favorito, horas, observacoes, origem, shop,
               object_id, game_code, regiao, azahar_preset, uuid, criado_em, atualizado_em)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
             (limpo["titulo"], limpo["executable_path"], limpo["exe_win"],
             limpo["exe_linux"], limpo["wine_prefix"],
             limpo["launch_options"], limpo["status"], limpo["nota"],
             limpo["favorito"], limpo["horas"], limpo["observacoes"],
             limpo["origem"], limpo["shop"], limpo["object_id"],
             limpo["game_code"], limpo["regiao"], limpo["azahar_preset"],
             limpo["uuid"], agora, agora),
        )
        con.commit()
    except sqlite3.IntegrityError:
        raise ValueError("jogo já cadastrado (mesmo título + executável)")
    return row_to_dict(con.execute("SELECT * FROM jogos WHERE id=?", (cur.lastrowid,)).fetchone())



def atualizar_jogo(con: sqlite3.Connection, gid: int, dados: dict) -> dict:
    row = con.execute("SELECT * FROM jogos WHERE id=?", (gid,)).fetchone()
    if not row:
        raise LookupError("jogo não encontrado")
    atual = dict(row)
    limpo = validar_dados({**{c: atual.get(c) for c in CAMPOS_EDITAVEIS}, **dados})
    con.execute(
        """UPDATE jogos SET titulo=?, executable_path=?, exe_win=?, exe_linux=?,
           wine_prefix=?, launch_options=?, status=?, nota=?, favorito=?, horas=?,
           observacoes=?, shop=?, object_id=?, origem=?, game_code=?, regiao=?,
           azahar_preset=?, atualizado_em=? WHERE id=?""",
        (limpo["titulo"], limpo["executable_path"], limpo["exe_win"],
         limpo["exe_linux"], limpo["wine_prefix"], limpo["launch_options"],
         limpo["status"], limpo["nota"], limpo["favorito"],
         limpo["horas"], limpo["observacoes"], limpo["shop"], limpo["object_id"],
         limpo["origem"], limpo["game_code"], limpo["regiao"],
         limpo["azahar_preset"], agora_iso(), gid),
    )
    con.commit()
    return row_to_dict(con.execute("SELECT * FROM jogos WHERE id=?", (gid,)).fetchone())



def excluir_jogo(con: sqlite3.Connection, gid: int) -> None:
    row = con.execute("SELECT capa FROM jogos WHERE id=?", (gid,)).fetchone()
    if not row:
        raise LookupError("jogo não encontrado")
    con.execute("DELETE FROM jogos WHERE id=?", (gid,))
    con.commit()
    if row["capa"]:
        try:
            (CAPAS_DIR / Path(row["capa"]).name).unlink()
        except OSError:
            pass



CAPA_EXTS = {".png": "image/png", ".jpg": "image/jpeg",
             ".jpeg": "image/jpeg", ".webp": "image/webp"}



def salvar_capa(con: sqlite3.Connection, gid: int, filename: str, data_b64: str) -> dict:
    ext = Path(filename or "").suffix.lower()
    if ext not in CAPA_EXTS:
        return {"ok": False, "erro": f"extensão inválida. Use: {sorted(CAPA_EXTS)}"}
    try:
        raw = base64.b64decode(data_b64, validate=True)
    except Exception:
        return {"ok": False, "erro": "base64 inválido"}
    return salvar_capa_bytes(con, gid, filename, raw)



def salvar_capa_bytes(con: sqlite3.Connection, gid: int, filename: str, raw: bytes) -> dict:
    ext = Path(filename or "").suffix.lower()
    if ext not in CAPA_EXTS:
        return {"ok": False, "erro": f"extensão inválida. Use: {sorted(CAPA_EXTS)}"}
    if len(raw) > 2_000_000:
        return {"ok": False, "erro": "capa maior que 2 MB"}
    row = con.execute("SELECT * FROM jogos WHERE id=?", (gid,)).fetchone()
    if not row:
        return {"ok": False, "erro": "jogo não encontrado"}
    CAPAS_DIR.mkdir(parents=True, exist_ok=True)
    nome = f"{gid}-{slugify(Path(filename).stem)}{ext}"
    (CAPAS_DIR / nome).write_bytes(raw)
    antiga = row["capa"] or ""
    if antiga and antiga != nome:
        try:
            (CAPAS_DIR / Path(antiga).name).unlink()
        except OSError:
            pass
    con.execute("UPDATE jogos SET capa=?, atualizado_em=? WHERE id=?",
                (nome, agora_iso(), gid))
    con.commit()
    return {"ok": True, "capa": nome}



def caminho_capa(nome: str) -> Path | None:
    """Resolve um nome de capa dentro de CAPAS_DIR (anti path-traversal)."""
    alvo = (CAPAS_DIR / Path(nome or "").name).resolve()
    try:
        base = CAPAS_DIR.resolve()
    except OSError:
        return None
    if base not in alvo.parents or not alvo.is_file():
        return None
    return alvo



def marcar_execucao(con: sqlite3.Connection, gid: int) -> None:
    agora = agora_iso()
    con.execute("UPDATE jogos SET ultima_execucao=?, atualizado_em=? WHERE id=?",
                (agora, agora, gid))
    con.commit()



def adicionar_horas(con: sqlite3.Connection, gid: int, delta_h: float) -> dict:
    """Soma horas ao jogo (atômico). Retorna total novo."""
    try:
        delta = float(delta_h or 0)
    except (TypeError, ValueError):
        return {"ok": False, "erro": "delta inválido"}
    if not math.isfinite(delta) or delta <= 0:
        return {"ok": False, "erro": "nada a somar"}
    cur = con.execute("SELECT horas FROM jogos WHERE id=?", (gid,)).fetchone()
    if cur is None:
        return {"ok": False, "erro": "jogo inexistente"}
    con.execute("UPDATE jogos SET horas=COALESCE(horas, 0)+?, atualizado_em=? WHERE id=?",
                (delta, agora_iso(), gid))
    con.commit()
    total = con.execute("SELECT horas FROM jogos WHERE id=?", (gid,)).fetchone()["horas"]
    return {"ok": True, "somado": round(delta, 2), "total": total}



def contar_por_origem(con: sqlite3.Connection) -> dict:
    rows = con.execute("SELECT origem, COUNT(*) AS n FROM jogos GROUP BY origem").fetchall()
    return {(r["origem"] or ""): r["n"] for r in rows}

__all__ = ['STATUS_VALIDOS', 'SCHEMA', 'MIGRACOES', 'CAMPOS_EDITAVEIS', '_garantir_unique_triplo', '_garantir_uuid', 'get_db', 'row_to_dict', 'validar_dados', '_like_esc', 'listar_jogos', 'criar_jogo', 'atualizar_jogo', 'excluir_jogo', 'CAPA_EXTS', 'salvar_capa', 'salvar_capa_bytes', 'caminho_capa', 'marcar_execucao', 'adicionar_horas', 'contar_por_origem']
