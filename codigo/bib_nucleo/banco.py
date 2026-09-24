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
import uuid as uuid_mod
from pathlib import Path

from bib_nucleo.base import (BACKUP_DIR, CAPAS_DIR, _desaspas, _txt,
                                agora_iso, existe_aqui_ou_traduzido,
                                resolver_exe, slugify)


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
    citron_preset TEXT DEFAULT '',
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
# v9 (sem azahar_mods), v10 (sem azahar_mods_off), v11 (sem citron_preset).
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
    "ALTER TABLE jogos ADD COLUMN citron_preset TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN uuid TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN etiquetas TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN save_path TEXT DEFAULT ''",
)


CAMPOS_EDITAVEIS = ("titulo", "executable_path", "exe_win", "exe_linux",
                    "exe_mac",
                    "wine_prefix", "launch_options", "status", "nota", "favorito",
                    "horas", "observacoes", "shop", "object_id", "origem",
                    "game_code", "regiao", "azahar_preset", "citron_preset", "etiquetas",
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
    """PC/3DS/NDS/Switch a partir da origem (sem consultar o registro)."""
    o = (origem or "").strip().lower()
    if o == "rom-3ds":
        return "3DS"
    if o == "rom-nds":
        return "NDS"
    if o == "rom-switch":
        return "Switch"
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
            if re.search(r"Switch", sist):
                return "Switch"
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
            "azahar_preset", "citron_preset", "uuid", "etiquetas", "save_path", "azahar_mods", "azahar_mods_off",
            "capa", "confianca", "criado_em", "atualizado_em"]
    todos = ", ".join(cols)
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
            citron_preset TEXT DEFAULT '',
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
    for campo in ("exe_win", "exe_linux", "exe_mac", "game_code", "regiao", "azahar_preset",
                    "citron_preset"):
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
    """Chave anti-duplicata: barra e caixa normalizadas.

    Sem isso, o mesmo exe gravado como D:/... e D:\\... vira duas linhas
    a cada re-scan (UNIQUE do banco é literal e não pega).
    """
    def _n(c):
        return (c or "").strip().replace("/", "\\").casefold()
    return (_n(titulo), _n(exe), _n(launch))


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
               object_id, game_code, regiao, azahar_preset, citron_preset, uuid, etiquetas, save_path, azahar_mods,
               azahar_mods_off, criado_em, atualizado_em)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
             (limpo["titulo"], limpo["executable_path"], limpo["exe_win"],
              limpo["exe_linux"], limpo["exe_mac"], limpo["wine_prefix"],
               limpo["launch_options"], limpo["status"], limpo["nota"],
               limpo["favorito"], limpo["horas"], limpo["observacoes"],
               limpo["origem"], limpo["shop"], limpo["object_id"],
               limpo["game_code"], limpo["regiao"], limpo["azahar_preset"],
               limpo["citron_preset"],
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
    con.execute(
        """UPDATE jogos SET titulo=?, executable_path=?, exe_win=?, exe_linux=?, exe_mac=?,
           wine_prefix=?, launch_options=?, status=?, nota=?, favorito=?, horas=?,
           observacoes=?, shop=?, object_id=?, origem=?, game_code=?, regiao=?,
           azahar_preset=?, citron_preset=?, etiquetas=?, save_path=?, azahar_mods=?, azahar_mods_off=?,
           atualizado_em=? WHERE id=?""",
        (limpo["titulo"], limpo["executable_path"], limpo["exe_win"],
         limpo["exe_linux"], limpo["exe_mac"], limpo["wine_prefix"], limpo["launch_options"],
         limpo["status"], limpo["nota"], limpo["favorito"],
         limpo["horas"], limpo["observacoes"], limpo["shop"], limpo["object_id"],
         limpo["origem"], limpo["game_code"], limpo["regiao"],
         limpo["azahar_preset"], limpo["citron_preset"], limpo["etiquetas"], limpo["save_path"], limpo["azahar_mods"],
         limpo["azahar_mods_off"], agora_iso(), gid),
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


def _normalizar_capa(raw: bytes, ext: str) -> tuple[bytes, str]:
    """Se Pillow existir: jpg/webp/gif → PNG 600x800 padronizado.

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
        img = _enquadrar_capa(img)
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


def selo_confianca(j: dict) -> str:
    """' · ◎0.85' se o jogo tem confiança de importação, senão ''."""
    try:
        conf = float((j or {}).get("confianca") or 0)
    except (TypeError, ValueError):
        return ""
    return f" · ◎{conf:.2f}" if conf > 0 else ""

__all__ = ['STATUS_VALIDOS', 'SCHEMA', 'MIGRACOES', 'CAMPOS_EDITAVEIS', 'ETIQUETA_MAX', 'ETIQUETAS_MAX', 'normalizar_etiquetas', 'etiquetas_de', 'MODS_MAX_NOME', 'MODS_MAX_QTD', 'normalizar_mods', 'mods_de', 'plataforma_de_origem', 'plataforma_jogo', 'get_db', 'row_to_dict', 'validar_dados', 'chave_dedup', 'listar_jogos', 'listar_etiquetas', 'criar_jogo', 'atualizar_jogo', 'excluir_jogo', 'CAPA_EXTS', 'CAPA_LARG', 'CAPA_ALT', 'salvar_capa', 'salvar_capa_bytes', 'caminho_capa', 'marcar_execucao', 'adicionar_horas', 'contar_por_origem', 'selo_confianca']
