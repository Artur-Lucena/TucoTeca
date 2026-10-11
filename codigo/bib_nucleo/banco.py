#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite: schema, migrações, validação, CRUD, capas, horas e etiquetas."""
from __future__ import annotations

import base64
import datetime
import math
import re
import shutil
import sqlite3
import threading
import uuid as uuid_mod
from contextlib import closing
from pathlib import Path

from bib_nucleo.base import (BACKUP_DIR, CAPAS_DIR, _desaspas, _txt,
                                 agora_iso, existe_aqui_ou_traduzido,
                                 mac_para_linux, resolver_exe, slugify, win_para_linux)


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
    exe_mac TEXT DEFAULT '',
    game_code TEXT DEFAULT '',
    regiao TEXT DEFAULT '',
    azahar_preset TEXT DEFAULT '',
    uuid TEXT DEFAULT '',
    etiquetas TEXT DEFAULT '',
    save_path TEXT DEFAULT '',
    azahar_mods TEXT DEFAULT '',
    azahar_mods_off INTEGER DEFAULT 0,
    criado_em TEXT,
    atualizado_em TEXT,
    UNIQUE(titulo, executable_path, launch_options)
);
"""


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


CAMPOS_EDITAVEIS = ("titulo", "executable_path", "exe_win", "exe_linux",
                    "exe_mac",
                    "wine_prefix", "launch_options", "status", "nota", "favorito",
                    "horas", "observacoes", "shop", "object_id", "origem",
                    "game_code", "regiao", "azahar_preset", "etiquetas",
                    "save_path", "azahar_mods", "azahar_mods_off")


# --------------------------------------------------------------------------
# Etiquetas (tags livres) + plataforma derivada (PC/3DS/NDS)
# --------------------------------------------------------------------------

ETIQUETA_MAX = 30
ETIQUETAS_MAX = 20


def normalizar_etiquetas(v) -> str:
    """Normaliza etiquetas livres para ", ".join ordenado e dedupado.

    Aceita str (separada por vírgula/ponto-vírgula) ou lista. Remove vazias,
    limita a ETIQUETAS_MAX tags de até ETIQUETA_MAX chars. Tag não pode conter
    vírgula, ponto-vírgula ou NUL (são separadores). Retorna "" se vazio.
    """
    if v is None:
        return ""
    if isinstance(v, str):
        partes = re.split(r"[;,]+", v)
    elif isinstance(v, (list, tuple)):
        partes = []
        for item in v:
            if isinstance(item, str):
                partes.extend(re.split(r"[;,]+", item))
            elif item is not None:
                partes.extend(re.split(r"[;,]+", str(item)))
    else:
        partes = re.split(r"[;,]+", str(v))
    vistas: dict[str, str] = {}
    for p in partes:
        t = (p or "").replace("\x00", "").strip()
        if not t:
            continue
        t = re.sub(r"\s+", " ", t)[:ETIQUETA_MAX].strip()
        if not t:
            continue
        chave = t.casefold()
        if chave not in vistas:
            vistas[chave] = t
        if len(vistas) >= ETIQUETAS_MAX:
            break
    return ", ".join(sorted(vistas.values(), key=str.casefold))


def etiquetas_de(j: dict | None) -> list[str]:
    """Lista de etiquetas do jogo (a partir do campo gravado)."""
    if not j:
        return []
    norm = normalizar_etiquetas(j.get("etiquetas") or "")
    return norm.split(", ") if norm else []


def plataforma_de_origem(origem: str) -> str:
    """PC/3DS/NDS a partir da origem (sem consultar o registro)."""
    o = (origem or "").strip().lower()
    if o == "rom-3ds":
        return "3DS"
    if o == "rom-nds":
        return "NDS"
    return "PC"


def plataforma_jogo(j: dict | None) -> str:
    """Plataforma de exibição do jogo (provider quando conhecido)."""
    if not j:
        return "PC"
    origem = (j.get("origem") or "")
    try:
        from bib_nucleo.emuladores import provedor_por_origem
        prov = provedor_por_origem(origem)
        if prov is not None:
            sist = " ".join(prov.get("sistemas") or ())
            if "3DS" in sist:
                return "3DS"
            if re.search(r"\bNDS\b|Nintendo DS", sist):
                return "NDS"
    except Exception:
        pass
    return plataforma_de_origem(origem)


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
    cols = ["id", "titulo", "executable_path", "exe_win", "exe_linux", "exe_mac", "wine_prefix",
            "launch_options", "status", "nota", "favorito", "horas", "ultima_execucao",
            "observacoes", "origem", "shop", "object_id", "game_code", "regiao",
            "azahar_preset", "uuid", "etiquetas", "save_path", "azahar_mods", "azahar_mods_off",
            "capa", "confianca", "criado_em", "atualizado_em"]
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
    con.executescript(f"""
        CREATE TABLE jogos_nova (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            executable_path TEXT DEFAULT '',
            exe_win TEXT DEFAULT '',
            exe_linux TEXT DEFAULT '',
            exe_mac TEXT DEFAULT '',
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
            etiquetas TEXT DEFAULT '',
            save_path TEXT DEFAULT '',
            azahar_mods TEXT DEFAULT '',
            azahar_mods_off INTEGER DEFAULT 0,
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
                _inicializar_db(con, db_path)
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
    con.commit()


def row_to_dict(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["favorito"] = bool(d.get("favorito"))
    d["etiquetas"] = normalizar_etiquetas(d.get("etiquetas") or "")
    d["etiquetas_lista"] = etiquetas_de(d)
    try:
        d["azahar_mods"] = normalizar_mods(d.get("azahar_mods"))
    except ValueError:
        d["azahar_mods"] = "[]"  # JSON antigo corrompido: lista vazia, sem quebrar
    d["mods_lista"] = mods_de(d)
    try:
        d["azahar_mods_off"] = 1 if d.get("azahar_mods_off") else 0
    except (TypeError, ValueError):
        d["azahar_mods_off"] = 0
    d["mods_off"] = bool(d["azahar_mods_off"])
    d["plataforma"] = plataforma_jogo(d)
    exe, _origem = resolver_exe(d)
    if not exe:
        from bib_nucleo.emuladores import provedor_por_origem
        prov = provedor_por_origem(d.get("origem") or "")
        if prov:
            exe = prov["exe"]()
    try:
        existe, exe_ok = existe_aqui_ou_traduzido(exe)
        if existe:
            exe = exe_ok
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
    for campo in ("exe_win", "exe_linux", "exe_mac", "game_code", "regiao", "azahar_preset"):
        if campo in dados or not parcial:
            v = _txt(dados.get(campo))
            limpo[campo] = _desaspas(v) if campo.startswith("exe_") else v
    for campo in ("wine_prefix", "launch_options", "observacoes", "shop", "object_id",
                    "save_path"):
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
    if "etiquetas" in dados or not parcial:
        limpo["etiquetas"] = normalizar_etiquetas(dados.get("etiquetas") or "")
    if "azahar_mods" in dados or not parcial:
        limpo["azahar_mods"] = normalizar_mods(dados.get("azahar_mods"))
    if "azahar_mods_off" in dados or not parcial:
        limpo["azahar_mods_off"] = 1 if dados.get("azahar_mods_off") else 0
    return limpo


MODS_MAX_NOME = 60

MODS_MAX_QTD = 20


def normalizar_mods(v) -> str:
    """Lista JSON de mods ativos do jogo (nomes da biblioteca, ordem mantida).

    Aceita JSON (gravado), lista/tupla ou str única. Remove vazios e
    duplicados (sem caixa), limita a MODS_MAX_QTD nomes de até
    MODS_MAX_NOME chars. Nome não pode conter separador de caminho ou
    NUL. Retorna '"[]"' se vazio.
    """
    import json as _json
    if v is None or v == "":
        return "[]"
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("["):
            try:
                v = _json.loads(s)
            except ValueError:
                raise ValueError("azahar_mods inválido (JSON esperado)")
        else:
            v = [s]
    if not isinstance(v, (list, tuple)):
        raise ValueError("azahar_mods inválido (lista esperada)")
    vistos: dict[str, str] = {}
    for item in v:
        t = (item if isinstance(item, str) else str(item or "")).replace(
            "\x00", "").strip().strip("/\\")
        if not t or "/" in t or "\\" in t:
            continue
        t = t[:MODS_MAX_NOME].strip()
        if not t:
            continue
        if t.casefold() not in vistos:
            vistos[t.casefold()] = t
        if len(vistos) >= MODS_MAX_QTD:
            break
    return _json.dumps(list(vistos.values()), ensure_ascii=False)


def mods_de(j: dict | None) -> list[str]:
    """Nomes dos mods ativos do jogo (a partir do campo gravado)."""
    import json as _json
    if not j:
        return []
    v = j.get("azahar_mods")
    if isinstance(v, (list, tuple)):
        return [t.strip() for t in v if isinstance(t, str) and t.strip()]
    try:
        v = _json.loads(v or "[]")
    except (ValueError, TypeError):
        return []
    return [t for t in v if isinstance(t, str) and t] if isinstance(v, list) else []


def _like_esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def chave_dedup(titulo: str, exe: str, launch: str) -> tuple:
    """Chave anti-duplicata: SO canônico + barra e caixa normalizadas.

    Sem isso, o mesmo exe gravado como D:/... e D:\\... vira duas linhas
    a cada re-scan (UNIQUE do banco é literal e não pega) — e o mesmo vale
    para o mesmo jogo visto como D:\\... no Windows e /run/... no Linux.
    """
    def _n(c, caminho=True):
        c = (c or "").strip()
        if caminho:
            c = mac_para_linux(win_para_linux(c))
        return c.replace("/", "\\").casefold()
    return (_n(titulo, False), _n(exe), _n(launch))


def listar_jogos(con: sqlite3.Connection, q: str = "", status: str = "",
                 favorito: bool = False, etiquetas: list[str] | None = None,
                 plataformas: list[str] | None = None) -> list[dict]:
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
    jogos = [row_to_dict(r) for r in con.execute(sql, params).fetchall()]
    if etiquetas:
        alvos = [e.casefold() for e in etiquetas if (e or "").strip()]
        if alvos:
            jogos = [j for j in jogos
                     if all(a in {t.casefold() for t in j.get("etiquetas_lista") or []}
                            for a in alvos)]
    if plataformas:
        plats = {(p or "").strip().upper() for p in plataformas if (p or "").strip()}
        if plats:
            jogos = [j for j in jogos if (j.get("plataforma") or "PC").upper() in plats]
    return jogos


def listar_etiquetas(con: sqlite3.Connection) -> list[dict]:
    """[{nome, n}] de etiquetas livres usadas, ordenadas por uso e nome."""
    cont: dict[str, dict] = {}
    for r in con.execute("SELECT etiquetas FROM jogos").fetchall():
        for t in etiquetas_de({"etiquetas": r["etiquetas"] or ""}):
            chave = t.casefold()
            if chave not in cont:
                cont[chave] = {"nome": t, "n": 0}
            cont[chave]["n"] += 1
    return sorted(cont.values(), key=lambda d: (-d["n"], d["nome"].casefold()))


def criar_jogo(con: sqlite3.Connection, dados: dict) -> dict:
    limpo = validar_dados(dados)
    limpo["uuid"] = _txt(dados.get("uuid")) or uuid_mod.uuid4().hex
    agora = agora_iso()
    chave = chave_dedup(limpo["titulo"], limpo["executable_path"],
                        limpo["launch_options"])
    for r in con.execute(
            "SELECT titulo, executable_path, launch_options FROM jogos").fetchall():
        if chave_dedup(r["titulo"], r["executable_path"], r["launch_options"]) == chave:
            raise ValueError("jogo já cadastrado (mesmo título + executável)")
    try:
        cur = con.execute(
            """INSERT INTO jogos (titulo, executable_path, exe_win, exe_linux, exe_mac, wine_prefix,
               launch_options, status, nota, favorito, horas, observacoes, origem, shop,
               object_id, game_code, regiao, azahar_preset, uuid, etiquetas, save_path, azahar_mods,
               azahar_mods_off, criado_em, atualizado_em)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
             (limpo["titulo"], limpo["executable_path"], limpo["exe_win"],
              limpo["exe_linux"], limpo["exe_mac"], limpo["wine_prefix"],
               limpo["launch_options"], limpo["status"], limpo["nota"],
               limpo["favorito"], limpo["horas"], limpo["observacoes"],
               limpo["origem"], limpo["shop"], limpo["object_id"],
               limpo["game_code"], limpo["regiao"], limpo["azahar_preset"],
               limpo["uuid"], limpo["etiquetas"], limpo["save_path"], limpo["azahar_mods"],
               limpo["azahar_mods_off"], agora, agora),
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
    try:
        con.execute(
            """UPDATE jogos SET titulo=?, executable_path=?, exe_win=?, exe_linux=?, exe_mac=?,
               wine_prefix=?, launch_options=?, status=?, nota=?, favorito=?, horas=?,
               observacoes=?, shop=?, object_id=?, origem=?, game_code=?, regiao=?,
               azahar_preset=?, etiquetas=?, save_path=?, azahar_mods=?, azahar_mods_off=?,
               atualizado_em=? WHERE id=?""",
            (limpo["titulo"], limpo["executable_path"], limpo["exe_win"],
             limpo["exe_linux"], limpo["exe_mac"], limpo["wine_prefix"], limpo["launch_options"],
             limpo["status"], limpo["nota"], limpo["favorito"],
             limpo["horas"], limpo["observacoes"], limpo["shop"], limpo["object_id"],
             limpo["origem"], limpo["game_code"], limpo["regiao"],
             limpo["azahar_preset"], limpo["etiquetas"], limpo["save_path"], limpo["azahar_mods"],
             limpo["azahar_mods_off"], agora_iso(), gid),
        )
        con.commit()
    except sqlite3.IntegrityError:
        raise ValueError("jogo já cadastrado (mesmo título + executável)")
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


# --------------------------------------------------------------------------
# Músicas (selfhost de áudio): catálogo próprio, fora da tabela de jogos
# --------------------------------------------------------------------------

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


# Downloads CSV → mp3 (fila tal qual o Harmoni): catálogo próprio v14
# --------------------------------------------------------------------------

ESTADOS_DOWNLOAD = ("pendente", "baixando", "baixado", "pronta", "falha")

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


SCHEMA_DESEJOS = """
CREATE TABLE IF NOT EXISTS desejos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appid TEXT NOT NULL,
    titulo TEXT NOT NULL,
    ordem INTEGER DEFAULT 0,
    manual INTEGER DEFAULT 0,
    criado_em TEXT,
    atualizado_em TEXT,
    UNIQUE(appid)
);
"""


def _garantir_coluna_desejo_manual(con: sqlite3.Connection) -> None:
    """v17: `manual` em desejos pré-Adicionar (aditivo, sem backup)."""
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(desejos)")}
    except sqlite3.Error:
        return
    if cols and "manual" not in cols:
        con.execute("ALTER TABLE desejos ADD COLUMN manual INTEGER DEFAULT 0")


def _garantir_tabela_desejos(con: sqlite3.Connection) -> None:
    """v16: wishlist Steam espelhada. Idempotente; preserva linhas."""
    con.execute(SCHEMA_DESEJOS)
    _garantir_coluna_desejo_manual(con)


def desejo_to_dict(r: sqlite3.Row) -> dict:
    return dict(r)


def listar_desejos(con: sqlite3.Connection, q: str = "") -> list[dict]:
    q = (q or "").strip().lower()
    rows = con.execute("SELECT * FROM desejos ORDER BY ordem, titulo").fetchall()
    out = [desejo_to_dict(r) for r in rows]
    if q:
        out = [d for d in out if q in (d.get("titulo") or "").lower()]
    return out


def sincronizar_desejos(con: sqlite3.Connection, itens: list[dict]) -> dict:
    """Espelha a wishlist: insere novos, atualiza títulos, apaga saídos.

    A wishlist é a fonte da verdade (igual restore por uuid), mas linhas
    `manual=1` (➕ Adicionar) nunca são apagadas pelo espelho.
    """
    novos = atualizados = removidos = 0
    agora = agora_iso()
    vistos: set[str] = set()
    for pos, item in enumerate(itens or []):
        if not isinstance(item, dict):
            continue
        appid = str(item.get("appid") or "").strip()
        titulo = _txt(item.get("titulo"))
        if not appid.isdigit() or not titulo or appid in vistos:
            continue
        vistos.add(appid)
        row = con.execute("SELECT * FROM desejos WHERE appid=?",
                          (appid,)).fetchone()
        if row is None:
            con.execute("INSERT INTO desejos (appid, titulo, ordem, manual,"
                        " criado_em, atualizado_em) VALUES (?,?,?,?,?,?)",
                        (appid, titulo, pos, 0, agora, agora))
            novos += 1
        elif dict(row).get("titulo") != titulo or dict(row).get("ordem") != pos:
            con.execute("UPDATE desejos SET titulo=?, ordem=?,"
                        " atualizado_em=? WHERE appid=?",
                        (titulo, pos, agora, appid))
            atualizados += 1
    for r in con.execute("SELECT appid, manual FROM desejos").fetchall():
        if r["appid"] not in vistos and not r["manual"]:
            con.execute("DELETE FROM desejos WHERE appid=?", (r["appid"],))
            removidos += 1
    con.commit()
    return {"novos": novos, "atualizados": atualizados,
            "removidos": removidos}


def adicionar_desejo(con: sqlite3.Connection, appid: str, titulo: str) -> dict:
    """➕ Adicionar manual: insere (ou protege) sem apagar nada.

    Linha nasce `manual=1`: o espelho da wishlist nunca a remove.
    """
    appid = str(appid or "").strip()
    titulo = _txt(titulo)
    if not appid.isdigit() or not titulo:
        raise ValueError("appid e título são obrigatórios")
    agora = agora_iso()
    row = con.execute("SELECT * FROM desejos WHERE appid=?",
                      (appid,)).fetchone()
    if row is None:
        try:
            pos = con.execute("SELECT COALESCE(MAX(ordem), -1) + 1 AS p"
                              " FROM desejos").fetchone()["p"]
        except (sqlite3.Error, TypeError, KeyError):
            pos = 0
        con.execute("INSERT INTO desejos (appid, titulo, ordem, manual,"
                    " criado_em, atualizado_em) VALUES (?,?,?,?,?,?)",
                    (appid, titulo, pos, 1, agora, agora))
        con.commit()
        return {"ok": True, "novo": True}
    con.execute("UPDATE desejos SET titulo=?, manual=1, atualizado_em=?"
                " WHERE appid=?", (titulo, agora, appid))
    con.commit()
    return {"ok": True, "novo": False}


def remover_desejo(con: sqlite3.Connection, did: int) -> None:
    row = con.execute("SELECT id FROM desejos WHERE id=?", (did,)).fetchone()
    if not row:
        raise LookupError("desejo não encontrado")
    con.execute("DELETE FROM desejos WHERE id=?", (did,))
    con.commit()


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


CAPA_LARG, CAPA_ALT = 600, 800  # retrato padrão de todas as capas

CAPA_ICON_MAX = 200  # até aqui é ícone extraído de ROM: preserva intacto


def _enquadrar_capa(img):
    """Arte em retrato 600x800: contém a arte + fundo blur da própria arte.

    Ícones pequenos (≤200px nos dois lados) voltam intactos.
    """
    from PIL import Image, ImageFilter
    if img.width <= CAPA_ICON_MAX and img.height <= CAPA_ICON_MAX:
        return img
    base = img.convert("RGB")
    fundo = base.resize((CAPA_LARG, CAPA_ALT))
    fundo = fundo.filter(ImageFilter.GaussianBlur(24))
    fator = min(CAPA_LARG / base.width, CAPA_ALT / base.height)
    arte = base.resize((max(1, round(base.width * fator)),
                        max(1, round(base.height * fator))))
    tela = fundo.copy()
    tela.paste(arte, ((CAPA_LARG - arte.width) // 2,
                       (CAPA_ALT - arte.height) // 2))
    return tela


def _normalizar_capa(raw: bytes, ext: str, enquadrar=True) -> tuple[bytes, str]:
    """Se Pillow existir: jogos → PNG 600x800; álbuns preservam proporção.

    Sem Pillow, devolve bytes/ext originais (GUI mostra tile p/ não-png/gif).
    Nunca levanta: falha de conversão = original.
    """
    try:
        from io import BytesIO
        from PIL import Image  # opcional, não é dependência
        img = Image.open(BytesIO(raw))
        img.load()
        if img.mode in ("RGBA", "LA"):
            fundo = Image.new("RGB", img.size, (16, 18, 24))
            fundo.paste(img, mask=img.split()[-1])
            img = fundo
        else:
            img = img.convert("RGB")
        if ext == ".gif":
            buf = BytesIO()
            img.save(buf, format="PNG")
            out = buf.getvalue()
            return (out, ".png") if len(out) <= 2_000_000 else (raw, ext)
        if enquadrar:
            img = _enquadrar_capa(img)
        else:
            img.thumbnail((1200, 1200))
        for _tent in (1, 2):
            buf = BytesIO()
            img.save(buf, format="PNG", optimize=True)
            out = buf.getvalue()
            if len(out) <= 2_000_000:
                return out, ".png"
            img = img.resize((img.width // 2, img.height // 2))
    except Exception:
        pass
    return raw, ext


def salvar_capa_bytes(con: sqlite3.Connection, gid: int, filename: str, raw: bytes) -> dict:
    ext = Path(filename or "").suffix.lower()
    if ext not in CAPA_EXTS:
        return {"ok": False, "erro": f"extensão inválida. Use: {sorted(CAPA_EXTS)}"}
    row = con.execute("SELECT * FROM jogos WHERE id=?", (gid,)).fetchone()
    if not row:
        return {"ok": False, "erro": "jogo não encontrado"}
    raw, ext = _normalizar_capa(raw, ext)  # encolhe/padroniza antes do teto
    if len(raw) > 2_000_000:
        return {"ok": False, "erro": "capa maior que 2 MB"}
    CAPAS_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(filename).stem
    while stem.startswith(f"{gid}-"):  # re-salvar não empilha o id
        stem = stem[len(str(gid)) + 1:] or "capa"
    nome = f"{gid}-{slugify(stem)}{ext}"
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


def salvar_capa_musica_bytes(con: sqlite3.Connection, mid: int,
                             filename: str, raw: bytes) -> dict:
    """Guarda arte do álbum (`mus-<id>-<slug>.jpg`) e grava `musica_capa`."""
    ext = Path(filename or "").suffix.lower()
    if ext not in CAPA_EXTS:
        return {"ok": False, "erro": f"extensão inválida. Use: {sorted(CAPA_EXTS)}"}
    row = con.execute("SELECT * FROM musicas WHERE id=?", (mid,)).fetchone()
    if not row:
        return {"ok": False, "erro": "música não encontrada"}
    raw, ext = _normalizar_capa(raw, ext, enquadrar=False)
    if len(raw) > 2_000_000:
        return {"ok": False, "erro": "capa maior que 2 MB"}
    CAPAS_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(filename).stem
    while stem.startswith(f"mus-{mid}-"):
        stem = stem[len(f"mus-{mid}-"):] or "capa"
    nome = f"mus-{mid}-{slugify(stem)}{ext}"
    try:
        (CAPAS_DIR / nome).write_bytes(raw)
    except OSError as e:
        return {"ok": False, "erro": f"falha ao gravar: {e}"}
    antiga = (row["musica_capa"] if "musica_capa" in row.keys() else "") or ""
    if antiga and antiga != nome:
        try:
            (CAPAS_DIR / Path(antiga).name).unlink()
        except OSError:
            pass
    con.execute("UPDATE musicas SET musica_capa=?, atualizado_em=? WHERE id=?",
                (nome, agora_iso(), mid))
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
    con.execute("UPDATE jogos SET horas=ROUND(COALESCE(horas, 0)+?, 2), atualizado_em=? WHERE id=?",
                (delta, agora_iso(), gid))
    con.commit()
    total = con.execute("SELECT horas FROM jogos WHERE id=?", (gid,)).fetchone()["horas"]
    try:
        total = round(float(total or 0), 2)
    except (TypeError, ValueError):
        pass
    return {"ok": True, "somado": round(delta, 2), "total": total}


def contar_por_origem(con: sqlite3.Connection) -> dict:
    rows = con.execute("SELECT origem, COUNT(*) AS n FROM jogos GROUP BY origem").fetchall()
    return {(r["origem"] or ""): r["n"] for r in rows}


# Videoteca 2.0 (v18): filmes/vídeos locais + downloads do YouTube.
# --------------------------------------------------------------------------

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


def selo_confianca(j: dict) -> str:
    """' · ◎0.85' se o jogo tem confiança de importação, senão ''."""
    try:
        conf = float((j or {}).get("confianca") or 0)
    except (TypeError, ValueError):
        return ""
    return f" · ◎{conf:.2f}" if conf > 0 else ""

__all__ = ['STATUS_VALIDOS', 'SCHEMA', 'MIGRACOES', 'CAMPOS_EDITAVEIS', 'ETIQUETA_MAX', 'ETIQUETAS_MAX', 'normalizar_etiquetas', 'etiquetas_de', 'MODS_MAX_NOME', 'MODS_MAX_QTD', 'normalizar_mods', 'mods_de', 'plataforma_de_origem', 'plataforma_jogo', 'get_db', 'row_to_dict', 'validar_dados', 'chave_dedup', 'listar_jogos', 'listar_etiquetas', 'criar_jogo', 'atualizar_jogo', 'excluir_jogo', 'SCHEMA_MUSICAS', 'musica_to_dict', 'criar_musica', 'listar_musicas', 'excluir_musica', 'salvar_capa_musica_bytes', 'ESTADOS_DOWNLOAD', 'SCHEMA_DOWNLOADS', 'download_to_dict', 'enfileirar_downloads', 'listar_downloads', 'marcar_download', 'limpar_downloads', 'SCHEMA_DESEJOS', 'desejo_to_dict', 'listar_desejos',
 'sincronizar_desejos', 'adicionar_desejo', 'remover_desejo', 'CAPA_EXTS', 'CAPA_LARG', 'CAPA_ALT', 'salvar_capa', 'salvar_capa_bytes', 'caminho_capa', 'marcar_execucao', 'adicionar_horas', 'contar_por_origem', 'selo_confianca', 'SCHEMA_VIDEOS', 'video_to_dict', 'criar_video', 'listar_videos', 'excluir_video']
