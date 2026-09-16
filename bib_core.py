#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bib_core — núcleo compartilhado da Biblioteca de Jogos (zero dependências).

Usado pelos dois frontends, todos nesta mesma pasta:
    app_win.py  aplicativo GUI com tkinter (Windows)
    app_tui.py  aplicativo de terminal com curses (Linux)

Tudo que é regra de negócio mora aqui: caminhos canônicos e tradução
Win<->Linux, SQLite (+migrações), validação, CRUD, pontuação de
confiança, varredura do Hydra, scanner de disco, importação, backup
versionado, capas locais, execução com horas automáticas, presets do
Azahar, pacote portátil (.zip) e execução de jogos.
"""
from __future__ import annotations

import base64
import configparser
import datetime
import hashlib
import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
import unicodedata
import urllib.request
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Casa canônica + tradução determinística de caminhos (Win <-> Linux)
# --------------------------------------------------------------------------

WIN_ROOT = os.environ.get("BIBLIOTECA_WIN_ROOT", "D:\\")
LINUX_ROOT = os.environ.get("BIBLIOTECA_LINUX_ROOT", "/run/media/tuco/Games")
REL_HOME = Path("Tuco-Compartilhado") / "Jogos" / "biblioteca"


def resolve_home() -> Path:
    env = os.environ.get("BIBLIOTECA_HOME")
    if env:
        return Path(env)
    if os.name == "nt":
        cand = Path(WIN_ROOT) / REL_HOME
        if cand.is_dir():
            return cand
    else:
        cand = Path(LINUX_ROOT) / REL_HOME
        if cand.is_dir():
            return cand
    return BASE_DIR


HOME_DIR = resolve_home()
DEFAULT_DB = HOME_DIR / "biblioteca.db"
BACKUP_DIR = HOME_DIR / "backups"
CAPAS_DIR = HOME_DIR / "capas"
PRESETS_DIR = HOME_DIR / "presets"


def garantir_dirs() -> None:
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    CAPAS_DIR.mkdir(parents=True, exist_ok=True)
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)


def _com_barra(p: str) -> str:
    return p.replace("\\", "/")


def win_para_linux(p: str) -> str:
    """D:\\Games\\X -> /run/media/tuco/Games/Games/X. Fora de D:\\, devolve igual."""
    n = _com_barra(p)
    w = _com_barra(WIN_ROOT).rstrip("/") + "/"
    if n[: len(w)].lower() == w.lower():
        return LINUX_ROOT.rstrip("/") + "/" + n[len(w):]
    return p


def linux_para_win(p: str) -> str:
    n = _com_barra(p)
    lx = LINUX_ROOT.rstrip("/") + "/"
    if n[: len(lx)].lower() == lx.lower():
        resto = n[len(lx):].replace("/", "\\")
        return WIN_ROOT.rstrip("\\") + "\\" + resto
    return p


def traduzir_para_atual(p: str) -> str:
    """Converte um caminho gravado para o equivalente neste SO (ou igual)."""
    if not p:
        return p
    return linux_para_win(p) if os.name == "nt" else win_para_linux(p)


def existe_aqui_ou_traduzido(p: str) -> tuple[bool, str]:
    """(existe, caminho_que_existe_ou_traduzido). Para exibir e executar."""
    if not p:
        return False, ""
    if Path(p).exists():
        return True, p
    t = traduzir_para_atual(p)
    if t != p and Path(t).exists():
        return True, t
    return False, t


def resolver_exe(d: dict) -> tuple[str, str]:
    """(executável final neste SO, origem). exe_win/exe_linux vencem o legado."""
    if os.name == "nt":
        esp = (d.get("exe_win") or "").strip()
        if esp:
            return esp, "exe_win"
    else:
        esp = (d.get("exe_linux") or "").strip()
        if esp:
            return esp, "exe_linux"
    return traduzir_para_atual((d.get("executable_path") or "").strip()), "executavel"


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
    criado_em TEXT,
    atualizado_em TEXT,
    UNIQUE(titulo, executable_path, launch_options)
);
"""

# Migração de bancos antigos: v1 (sem capa/confianca), v2 (sem exe por SO),
# v3 (sem game_code/regiao), v4 (sem azahar_preset).
MIGRACOES = (
    "ALTER TABLE jogos ADD COLUMN capa TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN confianca REAL DEFAULT 0",
    "ALTER TABLE jogos ADD COLUMN exe_win TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN exe_linux TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN game_code TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN regiao TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN azahar_preset TEXT DEFAULT ''",
)

CAMPOS_EDITAVEIS = ("titulo", "executable_path", "exe_win", "exe_linux",
                    "wine_prefix", "launch_options", "status", "nota", "favorito",
                    "horas", "observacoes", "shop", "object_id", "origem",
                    "game_code", "regiao", "azahar_preset")


def agora_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _txt(v) -> str:
    """Texto limpo: sem NUL (quebra Path/SQLite) e sem espaços nas bordas."""
    if v is None:
        return ""
    return (v if isinstance(v, str) else str(v)).replace("\x00", "").strip()


def _desaspas(s: str) -> str:
    """Remove um par de aspas duplas coladas (colo de 'copiar como caminho')."""
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s


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
            "azahar_preset", "capa", "confianca", "criado_em", "atualizado_em"]
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


def get_db(db_path: Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    if str(db_path.parent) and not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    # DELETE (não WAL): sem sidecars -wal/-shm, portátil no NTFS compartilhado.
    con.execute("PRAGMA journal_mode=DELETE;")
    con.executescript(SCHEMA)
    for sql in MIGRACOES:
        try:
            con.execute(sql)
        except sqlite3.OperationalError:
            pass  # coluna já existe
    _garantir_unique_triplo(con, db_path)
    return con


def row_to_dict(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["favorito"] = bool(d.get("favorito"))
    exe, _origem = resolver_exe(d)
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
        if horas < 0:
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
    agora = agora_iso()
    try:
        cur = con.execute(
            """INSERT INTO jogos (titulo, executable_path, exe_win, exe_linux, wine_prefix,
               launch_options, status, nota, favorito, horas, observacoes, origem, shop,
               object_id, game_code, regiao, azahar_preset, criado_em, atualizado_em)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
             (limpo["titulo"], limpo["executable_path"], limpo["exe_win"],
             limpo["exe_linux"], limpo["wine_prefix"],
             limpo["launch_options"], limpo["status"], limpo["nota"],
             limpo["favorito"], limpo["horas"], limpo["observacoes"],
             limpo["origem"], limpo["shop"], limpo["object_id"],
             limpo["game_code"], limpo["regiao"], limpo["azahar_preset"], agora, agora),
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


# --------------------------------------------------------------------------
# Confiança (preview de importação)
# --------------------------------------------------------------------------

SHOPS_CONHECIDAS = {
    "steam", "gog", "epic", "fitgirl", "steamrip",
    "dodi", "online-fix", "onlinefix", "xbox", "riot",
}


def pontuar(item: dict) -> dict:
    """Enriquece um achado com score 0..1, motivos e existência do exe."""
    score = 0.0
    motivos: list[str] = []
    exe = (item.get("executable_path") or "").strip()
    existe, traduzido = existe_aqui_ou_traduzido(exe)
    if exe and Path(exe).exists():
        score += 0.5
        motivos.append("executável existe neste SO")
    elif existe:
        score += 0.3
        motivos.append("executável existe no outro SO (traduzido)")
    elif exe:
        motivos.append("executável não encontrado em nenhum SO")
    shop = (item.get("shop") or "").strip().lower()
    if shop in SHOPS_CONHECIDAS:
        score += 0.15
        motivos.append(f"loja conhecida ({shop})")
    elif shop:
        score += 0.05
        motivos.append(f"loja: {shop}")
    if (item.get("object_id") or "").strip():
        score += 0.1
        motivos.append("tem objectId")
    try:
        horas = float(item.get("horas") or 0)
    except (TypeError, ValueError):
        horas = 0.0
    if horas > 0:
        score += 0.15
        motivos.append(f"{horas}h jogadas")
    if (item.get("origem") or "") in ("steam-manifest", "epic", "gog", "riot"):
        score += 0.1
        motivos.append("manifesto da loja")
    if (item.get("origem") or "") == "rom-3ds" and (item.get("rom_path") or "").strip():
        rp = item["rom_path"].strip()
        if Path(rp).exists():
            score += 0.5
            motivos.append("ROM existe neste SO")
        else:
            tr = traduzir_para_atual(rp)
            if tr != rp and Path(tr).exists():
                score += 0.3
                motivos.append("ROM existe no outro SO (traduzida)")
    if item.get("tem_metadados"):
        score += 0.1
        motivos.append("metadados internos lidos")
    out = dict(item)
    out["score"] = round(min(1.0, score), 2)
    out["motivos"] = motivos
    out["exe_existe"] = existe
    out["exe_traduzido"] = traduzido
    return out


def selecionar_prev(corpo: dict) -> list[dict] | None:
    """Extrai itens {indices, prev} vindos de um preview. None = varrer tudo."""
    if not isinstance(corpo, dict):
        return None
    prev = corpo.get("prev")
    idx = corpo.get("indices")
    if isinstance(idx, int):  # tolera cliente que manda escalar
        idx = [idx]
    if not isinstance(prev, list) or not isinstance(idx, list):
        return None
    sel = []
    for i in idx:
        if isinstance(i, int) and 0 <= i < len(prev) and isinstance(prev[i], dict):
            sel.append(prev[i])
    return sel


# --------------------------------------------------------------------------
# Hydra: localização + varredura sem dependências
# --------------------------------------------------------------------------

def hydra_db_candidates() -> list[Path]:
    cands: list[Path] = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        cands.append(Path(appdata) / "hydralauncher" / "hydra-db")
        cands.append(Path(appdata) / "hydra" / "hydra-db")
    home = Path.home()
    cands.append(home / ".config" / "hydralauncher" / "hydra-db")
    cands.append(home / ".config" / "hydra" / "hydra-db")
    cands.append(home / ".var" / "app" / "io.github.hydralauncher.hydra" / "config" / "hydralauncher" / "hydra-db")
    cands.append(home / ".var" / "app" / "io.github.hydralauncher.hydra" / "config" / "hydra" / "hydra-db")
    if appdata:
        cands.append(Path(appdata) / "hydralauncher" / "hydra-db-staging")
        cands.append(Path(appdata) / "hydra" / "hydra-db-staging")
    cands.append(home / ".config" / "hydralauncher" / "hydra-db-staging")
    cands.append(home / ".config" / "hydra" / "hydra-db-staging")
    env = os.environ.get("HYDRA_DB_PATH")
    if env:
        cands.insert(0, Path(env))
    return cands


def find_hydra_db() -> Path | None:
    for p in hydra_db_candidates():
        try:
            if p.is_dir() and any(p.iterdir()):
                return p
        except OSError:
            continue
    return None


TITLE_RE = re.compile(r'"title"\s*:\s*"((?:[^"\\]|\\.)+)"')
EXEC_RE = re.compile(r'"executablePath"\s*:\s*(null|"((?:[^"\\]|\\.)*)")')
SHOP_RE = re.compile(r'"shop"\s*:\s*"((?:[^"\\]|\\.)+)"')
OBJID_RE = re.compile(r'"objectId"\s*:\s*"((?:[^"\\]|\\.)+)"')
PLAYTIME_RE = re.compile(r'"playTimeInMilliseconds"\s*:\s*(\d+)')


def _unescape(s: str) -> str:
    try:
        return json.loads(f'"{s}"')
    except Exception:
        return s


def scan_hydra_db(db_dir: Path, limite_bytes_por_arquivo: int = 20_000_000) -> list[dict]:
    """Varredura bruta dos arquivos do LevelDB. Retorna [{'titulo', ...}]."""
    achados: dict[str, dict] = {}
    arquivos = [p for p in db_dir.rglob("*") if p.is_file() and p.suffix.lower() in (".log", ".ldb", ".sst", ".db", "")]
    for arq in arquivos:
        try:
            if arq.stat().st_size > limite_bytes_por_arquivo:
                continue
            data = arq.read_bytes()
        except OSError:
            continue
        texto = data.decode("utf-8", errors="ignore")
        matches = list(TITLE_RE.finditer(texto))
        for i, m in enumerate(matches):
            fim_janela = m.start() + 8000
            if i + 1 < len(matches):
                fim_janela = min(fim_janela, matches[i + 1].start())
            janela = texto[m.start():fim_janela]
            if "objectId" not in janela and "executablePath" not in janela and "shop" not in janela:
                continue
            titulo = _unescape(m.group(1)).strip()
            if not titulo or len(titulo) > 200:
                continue
            me = EXEC_RE.search(janela)
            exe = ""
            if me:
                exe = "" if me.group(1) == "null" else _unescape(me.group(2) or "")
            ms = SHOP_RE.search(janela)
            shop = _unescape(ms.group(1)) if ms else ""
            mo = OBJID_RE.search(janela)
            objid = _unescape(mo.group(1)) if mo else ""
            mp = PLAYTIME_RE.search(janela)
            horas = round(int(mp.group(1)) / 3_600_000, 2) if mp else 0.0
            chave = f"{titulo}\x00{exe}"
            if chave not in achados:
                achados[chave] = {
                    "titulo": titulo,
                    "executable_path": exe or "",
                    "shop": shop,
                    "object_id": objid,
                    "horas": horas,
                    "origem": "hydra",
                }
            elif horas > achados[chave].get("horas", 0):
                achados[chave]["horas"] = horas
    return sorted(achados.values(), key=lambda j: j["titulo"].lower())


def preview_hydra() -> tuple[Path | None, list[dict]]:
    """(pasta_encontrada, itens pontuados). Pasta None = Hydra ausente."""
    db = find_hydra_db()
    if not db:
        return None, []
    return db, [pontuar(j) for j in scan_hydra_db(db)]


# --------------------------------------------------------------------------
# Scanner de disco (D:\\Games, SteamLibrary, Riot...) + manifests Steam
# --------------------------------------------------------------------------

SKIP_DIRS = {
    "windowsapps", "system volume information", "$recycle.bin",
    ".pnpm-store", "msdownld.tmp", "found.000", "wpsystem",
    "backups", "capas",
}
SKIP_EXE_RE = re.compile(
    r"(?i)^(unins|uninstall|setup|dotnet|dxweb|quicksfv|visualcpp|"
    r"vc_?redist|dxsetup|oalinst|crash|crashhandler|bugreport|"
    r"unitycrashhandler|qt|python|hydra|redist|vcredist|eac|easyanticheat)"
)
RIOT_EXE = {
    "leagueclient.exe": "League of Legends",
    "league of legends.exe": "League of Legends",
    "riotclientservices.exe": "Riot Client",
}
ACF_NAME_RE = re.compile(r'"name"\s+"([^"]+)"')
ACF_DIR_RE = re.compile(r'"installdir"\s+"([^"]+)"')


def default_scan_roots() -> list[str]:
    env = os.environ.get("BIBLIOTECA_SCAN_ROOTS")
    if env:
        return [r for r in re.split(r"[;\n]+", env) if r.strip()]
    if os.name == "nt":
        base = WIN_ROOT.rstrip("\\")
        return [f"{base}\\Games", f"{base}\\SteamLibrary", f"{base}\\Riot Games"]
    base = LINUX_ROOT.rstrip("/")
    roots = [f"{base}/Games", f"{base}/SteamLibrary"]
    # Steam nativo do Linux (fora da partilha): só entra se existir
    for cand in (Path.home() / ".steam/steam/steamapps",
                 Path.home() / ".local/share/Steam/steamapps"):
        if cand.is_dir():
            roots.append(str(cand))
    return roots


def _titulo_de_exe(p: Path) -> str:
    baixo = p.name.lower()
    if baixo in RIOT_EXE:
        return RIOT_EXE[baixo]
    stem = p.stem
    stem = re.sub(r"(?i)[-_ ]?(win64|win32|x64|shipping|game)$", "", stem)
    return stem.replace("_", " ").replace(".", " ").strip() or p.stem


def scan_discos(roots: list[str], max_arquivos: int = 60_000, prof_max: int = 5,
                retornar_info: bool = False) -> list[dict] | tuple[list[dict], dict]:
    """Procura .exe e manifests Steam. Leitura apenas, com teto de arquivos.

    Se retornar_info, devolve (lista, {"vistos", "truncado", "raizes"}).
    "truncado" True = o teto estourou; a lista é parcial.
    """
    achados: dict[str, dict] = {}
    vistos = 0
    truncado = False

    def _final():
        res = sorted(achados.values(), key=lambda j: j["titulo"].lower())
        if retornar_info:
            return res, {"vistos": vistos, "truncado": truncado,
                         "raizes": [str(r) for r in roots if Path(r).is_dir()]}
        return res

    def registrar(item: dict):
        chave = f"{item['titulo'].lower()}\x00{item['executable_path'].lower()}"
        if chave not in achados:
            achados[chave] = item

    for raiz in roots:
        rp = Path(raiz)
        if not rp.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(rp):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            try:
                prof = len(Path(dirpath).relative_to(rp).parts)
            except ValueError:
                dirnames[:] = []
                continue
            if prof > prof_max:
                dirnames[:] = []
                continue
            for fn in filenames:
                if vistos >= max_arquivos:
                    truncado = True
                    return _final()
                baixo = fn.lower()
                full = str(Path(dirpath) / fn)
                if baixo.startswith("appmanifest_") and baixo.endswith(".acf"):
                    vistos += 1
                    try:
                        txt = Path(full).read_text(encoding="utf-8", errors="ignore")
                    except OSError:
                        continue
                    it = _item_steam_manifest(txt, dirpath)
                    if it is not None:
                        registrar(it)
                elif baixo.endswith(".exe"):
                    vistos += 1
                    if SKIP_EXE_RE.search(fn):
                        continue
                    p = Path(full)
                    registrar({
                        "titulo": _titulo_de_exe(p), "executable_path": full,
                        "shop": "", "object_id": "",
                        "horas": 0.0, "origem": "scan-disco",
                    })
    return _final()


def preview_scan(roots: list[str] | None = None) -> tuple[list[str], list[dict], dict]:
    """(raízes_usadas, itens pontuados, info{vistos, truncado, raizes})."""
    roots = roots or default_scan_roots()
    achados, info = scan_discos(roots, retornar_info=True)
    return roots, [pontuar(j) for j in achados], info


# --------------------------------------------------------------------------
# Ler do disco: todas as fontes de jogos instalados (não só o Hydra)
# --------------------------------------------------------------------------

JUNK_PROG_RE = re.compile(
    r"(?i)(redistributable|\bredist\b|\bsdk\b|driver|update for |security update|"
    r"hotfix|\bkb\d{6,}|\blanguage pack\b|help viewer|visual studio|\bdotnet\b|"
    r"directx|vulkan|physx|anticheat|easyanticheat|\beac\b|prerequisites)"
)


def _detector_hydra() -> tuple[str, list[dict], str]:
    db = find_hydra_db()
    if db is None:
        return "Hydra", [], "ausente neste PC"
    try:
        itens = scan_hydra_db(db)
    except Exception as e:
        return "Hydra", [], f"falha ao ler: {e}"
    for it in itens:
        it["fonte"] = "Hydra"
    return "Hydra", itens, f"{len(itens)} em {db}"


def _steamapps_dirs() -> list[Path]:
    cands: list[Path] = []
    if os.name == "nt":
        pf86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        pf = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        cands += [pf86 / "Steam/steamapps", pf / "Steam/steamapps"]
    else:
        h = Path.home()
        cands += [h / ".local/share/Steam/steamapps", h / ".steam/steam/steamapps"]
    for r in default_scan_roots():
        cands.append(Path(r) / "steamapps")
        cands.append(Path(r))  # a raiz pode SER o steamapps
    vistas: list[Path] = []
    for c in cands:
        try:
            if c.is_dir() and c not in vistas:
                vistas.append(c)
        except OSError:
            pass
    # libraryfolders.vdf revela bibliotecas fora do padrão
    extras: list[Path] = []
    for c in vistas:
        vdf = c / "libraryfolders.vdf"
        try:
            txt = vdf.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in re.finditer(r'"path"\s+"((?:[^"\\]|\\.)+)"', txt):
            p = Path(_unescape(m.group(1)))
            cand = p / "steamapps" if (p / "steamapps").is_dir() else p
            try:
                if cand.is_dir() and cand not in vistas and cand not in extras:
                    extras.append(cand)
            except OSError:
                pass
    return vistas + extras


def _item_steam_manifest(txt: str, dirpath: str) -> dict | None:
    mn = ACF_NAME_RE.search(txt)
    md = ACF_DIR_RE.search(txt)
    nome = mn.group(1).strip() if mn else None
    if not nome or ("Steam" in nome and "Runtime" in nome):
        return None
    if "redistributable" in nome.lower():
        return None  # Steamworks Common Redistributables etc.: só suporte
    exe = ""
    if md:
        cand_dir = Path(dirpath) / "common" / md.group(1).strip()
        if cand_dir.is_dir():
            try:
                exes = sorted(
                    x for x in cand_dir.iterdir()
                    if x.is_file() and x.suffix.lower() == ".exe"
                    and not SKIP_EXE_RE.search(x.name)
                )
                if exes:
                    exe = str(exes[0])
            except OSError:
                pass
    return {"titulo": nome, "executable_path": exe, "shop": "steam",
            "object_id": "", "horas": 0.0, "origem": "steam-manifest",
            "fonte": "Steam"}


def _detector_steam(steamapps: list[Path] | None = None) -> tuple[str, list[dict], str]:
    alvos = steamapps if steamapps is not None else _steamapps_dirs()
    # fora o que o scan de disco já cobre (evita duplicar no preview)
    cobertas = [Path(r) for r in default_scan_roots()]
    noveis = [c for c in alvos
              if not any(c == b or b in c.parents for b in cobertas)]
    achados: dict[str, dict] = {}
    olhadas = 0
    for c in noveis:
        try:
            acfs = sorted(c.glob("appmanifest_*.acf"))
        except OSError:
            continue
        if not acfs:
            continue
        olhadas += 1
        for arq in acfs:
            try:
                txt = arq.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            it = _item_steam_manifest(txt, str(c))
            if it:
                achados.setdefault(f"{it['titulo'].lower()}\x00{it['executable_path'].lower()}", it)
    det = f"{len(achados)} em {olhadas} biblioteca(s)" if olhadas else "Steam ausente"
    return "Steam", list(achados.values()), det


def _detector_epic(manifests: Path | None = None) -> tuple[str, list[dict], str]:
    if manifests is None:
        if os.name == "nt":
            pd = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
            manifests = pd / "Epic/EpicGamesLauncher/Data/Manifests"
        else:
            return "Epic", [], "só no Windows"
    achados: dict[str, dict] = {}
    try:
        arquivos = sorted(manifests.glob("*.item")) if manifests.is_dir() else []
    except OSError:
        arquivos = []
    if not arquivos:
        return "Epic", [], "sem manifestos"
    for arq in arquivos:
        try:
            d = json.loads(arq.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict):
            continue
        nome = (d.get("DisplayName") or "").strip()
        if not nome:
            continue
        inst = (d.get("InstallLocation") or "").strip()
        exe = ""
        lan = (d.get("LaunchExecutable") or "").strip().replace("/", os.sep)
        if inst and lan:
            cand = str(Path(inst) / lan)
            exe = cand
        achados.setdefault(nome.lower(), {
            "titulo": nome, "executable_path": exe, "shop": "epic",
            "object_id": (d.get("AppName") or "").strip(),
            "horas": 0.0, "origem": "epic", "fonte": "Epic",
        })
    return "Epic", list(achados.values()), f"{len(achados)} manifesto(s)"


def _detector_gog(roots: list[str] | None = None) -> tuple[str, list[dict], str]:
    alvos = roots if roots is not None else default_scan_roots()
    achados: dict[str, dict] = {}
    vistos = 0
    for raiz in alvos:
        rp = Path(raiz)
        if not rp.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(rp):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            try:
                if len(Path(dirpath).relative_to(rp).parts) > 4:
                    dirnames[:] = []
                    continue
            except ValueError:
                dirnames[:] = []
                continue
            for fn in filenames:
                if vistos >= 20_000:
                    break
                if not fn.lower().startswith("goggame-") or not fn.lower().endswith(".info"):
                    continue
                vistos += 1
                full = Path(dirpath) / fn
                try:
                    d = json.loads(full.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if not isinstance(d, dict):
                    continue
                nome = (d.get("name") or "").strip() or full.parent.name
                exe = ""
                try:
                    tasks = d.get("playTasks") or []
                    rel = (tasks[0].get("path") or "").strip().replace("/", os.sep).lstrip("\\/")
                    if rel:
                        exe = str(full.parent / rel)
                except (IndexError, AttributeError, TypeError):
                    pass
                achados.setdefault(nome.lower(), {
                    "titulo": nome, "executable_path": exe, "shop": "gog",
                    "object_id": str(d.get("gameId") or ""), "horas": 0.0,
                    "origem": "gog", "fonte": "GOG",
                })
    det = f"{len(achados)} jogo(s)" if achados else "sem goggame-*.info nas raízes"
    return "GOG", list(achados.values()), det


def _detector_riot(arqs: list[Path] | None = None) -> tuple[str, list[dict], str]:
    if arqs is None:
        arqs = []
        if os.name == "nt":
            pd = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
            arqs.append(pd / "Riot Games/RiotClientInstalls.json")
    achados: dict[str, dict] = {}
    achou_arq = False
    for arq in arqs:
        try:
            d = json.loads(arq.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict):
            continue
        achou_arq = True
        dirs: dict[str, str] = {}
        assoc = d.get("associated_client")
        if isinstance(assoc, dict):
            dirs.update({str(k): str(v) for k, v in assoc.items()})
        for k in ("rc_default", "rc_live"):
            if d.get(k):
                dirs.setdefault(k, str(d[k]))
        for _nome, inst in dirs.items():
            inst = (inst or "").strip()
            if not inst:
                continue
            exe = inst if inst.lower().endswith(".exe") else str(
                Path(inst) / "RiotClientServices.exe")
            if os.name == "nt":
                exe = exe.replace("/", "\\")  # json vem com /; dedupe + exibe igual
            achados.setdefault(exe.lower(), {
                "titulo": "Riot Client", "executable_path": exe,
                "shop": "riot", "object_id": "", "horas": 0.0,
                "origem": "riot", "fonte": "Riot",
            })
    det = f"{len(achados)} instalação(ões)" if achou_arq else "Riot ausente"
    return "Riot", list(achados.values()), det


def _detector_windows() -> tuple[str, list[dict], str]:
    if os.name != "nt":
        return "Windows", [], "só no Windows"
    import winreg
    chaves = [
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    achados: dict[str, dict] = {}
    for raiz, sub in chaves:
        try:
            h = winreg.OpenKey(raiz, sub)
        except OSError:
            continue
        try:
            n = winreg.QueryInfoKey(h)[0]
            for i in range(min(n, 5000)):
                try:
                    nome_sub = winreg.EnumKey(h, i)
                except OSError:
                    continue
                try:
                    with winreg.OpenKey(h, nome_sub) as k:
                        def _sv(campo):
                            try:
                                v, _t = winreg.QueryValueEx(k, campo)
                                return v
                            except OSError:
                                return None
                        if _sv("SystemComponent"):
                            continue
                        titulo = (_sv("DisplayName") or "").strip()
                        if not titulo or JUNK_PROG_RE.search(titulo):
                            continue
                        exe = ""
                        icon = (_sv("DisplayIcon") or "").strip()
                        if icon:
                            cand = icon.split(",")[0].strip().strip('"')
                            base = cand.lower()
                            if base.endswith(".exe") and not re.match(
                                    r"(?i)^(unins|uninstall|setup)",
                                    Path(base).name):
                                exe = cand  # desinstalador não é jogo
                        achados.setdefault(titulo.lower(), {
                            "titulo": titulo, "executable_path": exe,
                            "shop": "", "object_id": "",
                            "horas": 0.0, "origem": "win",
                            "fonte": "Windows",
                        })
                except OSError:
                    continue
        finally:
            try:
                winreg.CloseKey(h)
            except OSError:
                pass
    return "Windows", list(achados.values()), f"{len(achados)} programa(s)"


def ler_do_disco() -> tuple[list[dict], dict]:
    """Todas as fontes de jogos instalados, de uma vez (só leitura).

    (itens pontuados ordenados, info{fontes:[{fonte, ok, n, detalhe}], total}).
    Nunca levanta: fonte que falha entra como ok=False.
    """
    detectores = (("Hydra", _detector_hydra), ("Steam", _detector_steam),
                  ("Epic", _detector_epic), ("GOG", _detector_gog),
                  ("Riot", _detector_riot), ("Windows", _detector_windows))
    itens: list[dict] = []
    fontes: list[dict] = []
    for nome, det in detectores:
        try:
            fonte, achados, detalhe = det()
            fontes.append({"fonte": fonte, "ok": True, "n": len(achados),
                           "detalhe": detalhe})
            itens.extend(achados)
        except Exception as e:
            fontes.append({"fonte": nome, "ok": False, "n": 0,
                           "detalhe": f"falha: {e}"})
    pont = fundir_duplicados(itens)
    pont.sort(key=lambda j: j["titulo"].lower())
    return pont, {"fontes": fontes, "total": len(pont)}


# --------------------------------------------------------------------------
# ROMs (ex.: 3DS no Azahar) — scanner + raízes + emulador padrão
# --------------------------------------------------------------------------

ROM_EXTS_3DS = {".cci", ".cxi", ".3ds", ".3dsx", ".elf", ".app", ".axf"}


def default_roms_roots() -> list[str]:
    env = os.environ.get("BIBLIOTECA_ROMS_ROOTS")
    if env:
        return [r for r in re.split(r"[;\n]+", env) if r.strip()]
    if os.name == "nt":
        base = WIN_ROOT.rstrip("\\")
        return [f"{base}\\Games\\Roms", f"{base}\\Games\\Roms\\3DS"]
    base = LINUX_ROOT.rstrip("/")
    return [f"{base}/Games/Roms", f"{base}/Games/Roms/3DS"]


def default_emu_3ds() -> str:
    """Caminho do Azahar neste SO (env BIBLIOTECA_EMULADOR_3DS vence). "" se ausente."""
    env = os.environ.get("BIBLIOTECA_EMULADOR_3DS")
    if env:
        return env
    if os.name == "nt":
        cand = Path(WIN_ROOT) / "Games/Emuladores/Azahar/azahar.exe"
        return str(cand) if cand.is_file() else ""
    pasta = Path(LINUX_ROOT) / "Games/Emuladores/Azahar"
    if pasta.is_dir():
        imgs = sorted(pasta.glob("azahar*.AppImage"))
        if imgs:
            return str(imgs[-1])
    return ""


def azahar_user_dir(exe: str = "") -> str:
    """Pasta user do Azahar (portátil ao lado do exe vence os padrões do SO)."""
    exe = exe or default_emu_3ds()
    if exe:
        port = Path(exe).parent / "user"
        if port.is_dir():
            return str(port)
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", "")) / "Azahar"
    else:
        base = Path.home() / ".local/share/azahar-emu"
    return str(base) if base.is_dir() else ""


def azahar_status() -> dict:
    """Saúde do Azahar sem abrir nada: instalado, user dir, configurado, chaves."""
    exe = default_emu_3ds()
    st = {"instalado": bool(exe), "exe": exe, "user_dir": "",
          "configurado": False, "chaves": False,
          "versao_local": azahar_versao_local()}
    if not exe:
        return st
    ud = azahar_user_dir(exe)
    st["user_dir"] = ud
    if ud:
        st["configurado"] = (Path(ud) / "config" / "qt-config.ini").is_file()
        st["chaves"] = (Path(ud) / "sysdata" / "aes_keys.txt").is_file()
    return st


# --------------------------------------------------------------------------
# Gerenciador do Azahar: verifica, baixa, confere sha256 e instala sozinho
# --------------------------------------------------------------------------

AZAHAR_API_LATEST = "https://api.github.com/repos/azahar-emu/azahar/releases/latest"
AZAHAR_VERSAO_ARQ = "versao-azahar.txt"


def _emu_dir() -> Path:
    if os.name == "nt":
        return Path(WIN_ROOT) / "Games/Emuladores/Azahar"
    return Path(LINUX_ROOT) / "Games/Emuladores/Azahar"


def azahar_versao_local() -> str:
    arq = _emu_dir() / AZAHAR_VERSAO_ARQ
    try:
        if arq.is_file():
            return arq.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return ""


def azahar_release_info(timeout: int = 25) -> dict:
    """{'tag','nome','size','sha256','url'} do asset deste SO, ou {'erro':...}."""
    try:
        with urllib.request.urlopen(AZAHAR_API_LATEST, timeout=timeout) as r:
            rel = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"erro": f"falha de rede: {type(e).__name__}: {e}"}
    tag = (rel.get("tag_name") or "").strip()
    if os.name == "nt":
        casa = lambda n: n.startswith("azahar-windows-msys2-") and n.endswith(".zip")  # noqa: E731
    else:
        casa = lambda n: n == "azahar.AppImage"  # noqa: E731
    for a in rel.get("assets", []):
        nome = a.get("name") or ""
        if casa(nome):
            digest = a.get("digest") or ""
            sha = digest.split(":", 1)[1].strip() if ":" in digest else ""
            return {"tag": tag, "nome": nome, "size": a.get("size") or 0,
                    "sha256": sha, "url": a.get("browser_download_url") or ""}
    return {"erro": "asset deste SO não encontrado no release"}


def _fundir(orig: Path, dst: Path) -> None:
    """Move orig p/ dentro de dst mesclando pastas (nunca apaga o que já há)."""
    for item in orig.iterdir():
        alvo = dst / item.name
        if item.is_dir():
            alvo.mkdir(exist_ok=True)
            _fundir(item, alvo)
        else:
            try:
                if alvo.exists():
                    alvo.unlink()
                shutil.move(str(item), str(alvo))
            except OSError:
                pass


def azahar_instalar(info: dict, progresso=None) -> dict:
    """Baixa o asset, confere tamanho+sha256 e instala preservando user/.

    progresso(feitos_bytes, total_bytes) é chamado durante o download.
    Roda em thread na GUI; aqui é bloqueante.
    """
    url, tag = (info.get("url") or ""), (info.get("tag") or "").strip()
    if not url or not tag:
        return {"ok": False, "erro": "release inválido (sem URL/tag)"}
    dest = _emu_dir()
    tmpzip = Path(tempfile.gettempdir()) / f"azahar-{tag}.baixando"
    h = hashlib.sha256()
    feito = 0
    try:
        with urllib.request.urlopen(url, timeout=60) as r, open(tmpzip, "wb") as f:
            total = int(r.headers.get("Content-Length") or info.get("size") or 0)
            while True:
                blk = r.read(1024 * 256)
                if not blk:
                    break
                f.write(blk)
                h.update(blk)
                feito += len(blk)
                if progresso:
                    try:
                        progresso(feito, total)
                    except Exception:
                        pass
    except Exception as e:
        try:
            tmpzip.unlink()
        except OSError:
            pass
        return {"ok": False, "erro": f"download falhou: {type(e).__name__}: {e}"}
    if info.get("size") and feito != info["size"]:
        try:
            tmpzip.unlink()
        except OSError:
            pass
        return {"ok": False, "erro": f"tamanho divergente ({feito} != {info['size']})"}
    if info.get("sha256") and h.hexdigest() != info["sha256"].lower():
        try:
            tmpzip.unlink()
        except OSError:
            pass
        return {"ok": False, "erro": "sha256 divergente (arquivo descartado)"}
    stage = None
    try:
        dest.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            stage = Path(tempfile.mkdtemp(prefix="azahar-"))
            with zipfile.ZipFile(tmpzip) as z:
                z.extractall(stage)
            raiz = None
            for cand in [stage] + [d for d in stage.iterdir() if d.is_dir()]:
                if (cand / "azahar.exe").is_file():
                    raiz = cand
                    break
            if raiz is None:
                return {"ok": False, "erro": "azahar.exe não encontrado no pacote"}
            _fundir(raiz, dest)
        else:
            alvo = dest / "azahar.AppImage"
            try:
                if alvo.exists():
                    alvo.unlink()
                shutil.move(str(tmpzip), str(alvo))
                tmpzip = None  # virou o AppImage final
                os.chmod(alvo, 0o755)
            except OSError as e:
                return {"ok": False, "erro": f"falha ao instalar AppImage: {e}"}
        (dest / AZAHAR_VERSAO_ARQ).write_text(tag, encoding="utf-8")
    except Exception as e:
        return {"ok": False, "erro": f"instalação falhou: {type(e).__name__}: {e}"}
    finally:
        try:
            if tmpzip is not None and tmpzip.exists():
                tmpzip.unlink()
        except OSError:
            pass
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
    exe = default_emu_3ds()
    return {"ok": True, "tag": tag, "exe": exe,
            "exe_existe": bool(exe) and Path(exe).is_file()}


ROM_TAGS_LIXO_RE = re.compile(
    r"\s*\((USA|EUR|JPN|JAP|KOR|CHN|TWN|AUS|BRA|World|"
    r"En(?:,[A-Za-z]{2})+|Rev\s*\d+|v\d+[\.\d]*|Decrypted|Trimmed)\)", re.IGNORECASE)


def _titulo_de_rom(p: Path) -> str:
    nome = p.stem.replace("_", " ").replace(".", " ").replace("-", " ").strip()
    nome = ROM_TAGS_LIXO_RE.sub("", nome)  # "Pokemon X (USA) (En,Ja…)" -> "Pokemon X"
    return re.sub(r"\s+", " ", nome).strip() or p.stem


def _item_rom(full: str, emu_exe: str = "") -> dict:
    """Um achado de ROM (título/código/região lidos de dentro do arquivo)."""
    item = {
        "titulo": _titulo_de_rom(Path(full)),
        "executable_path": emu_exe,
        "launch_options": full,
        "shop": "", "object_id": "",
        "horas": 0.0, "origem": "rom-3ds",
        "rom_path": full,
        "game_code": "", "regiao": "",
        "tem_metadados": False,
    }
    try:
        m = ler_metadados_3ds(full)
    except Exception:
        m = {}
    if m.get("titulo"):
        item["titulo"] = m["titulo"]
        item["tem_metadados"] = True
    if m.get("game_code"):
        item["game_code"] = m["game_code"]
    if m.get("regiao"):
        item["regiao"] = m["regiao"]
    return item


def scan_roms(roots: list[str], emu_exe: str = "", prof_max: int = 4,
              retornar_info: bool = False) -> list[dict] | tuple[list[dict], dict]:
    """Procura ROMs 3DS. Leitura apenas. Itens já vêm com o emu em executable_path."""
    achados: dict[str, dict] = {}
    vistos = 0
    truncado = False

    def _final():
        res = sorted(achados.values(), key=lambda j: j["titulo"].lower())
        if retornar_info:
            return res, {"vistos": vistos, "truncado": truncado,
                         "raizes": [str(r) for r in roots if Path(r).is_dir()]}
        return res

    for raiz in roots:
        rp = Path(raiz)
        if not rp.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(rp):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            try:
                prof = len(Path(dirpath).relative_to(rp).parts)
            except ValueError:
                dirnames[:] = []
                continue
            if prof > prof_max:
                dirnames[:] = []
                continue
            for fn in filenames:
                if vistos >= 60_000:
                    truncado = True
                    return _final()
                if Path(fn).suffix.lower() not in ROM_EXTS_3DS:
                    continue
                vistos += 1
                full = str(Path(dirpath) / fn)
                chave = full.lower()
                if chave not in achados:
                    achados[chave] = _item_rom(full, emu_exe)
    return _final()


def preview_roms(roots: list[str] | None = None,
                 emu_exe: str | None = None) -> tuple[list[str], list[dict], dict, str]:
    """(raízes, itens pontuados, info, emu_usado)."""
    roots = roots or default_roms_roots()
    emu = emu_exe if emu_exe is not None else default_emu_3ds()
    achados, info = scan_roms(roots, emu_exe=emu, retornar_info=True)
    return roots, [pontuar(j) for j in achados], info, emu


EXE_IMPORTAVEIS = {".exe", ".lnk", ".bat", ".cmd", ".sh", ".AppImage"}


def analisar_arquivo(caminho: str) -> dict:
    """Classifica UM caminho p/ a importação unificada. Só leitura.

    Retorna {"tipo", "item", "provedor", "detalhe", "aviso"} onde tipo é
    'pasta' | 'rom' | 'jogo' | 'json' | 'pacote' | 'desconhecido'.
    Emulador ausente NÃO bloqueia: a ROM importa e o aviso orienta (⬇).
    """
    vazio = {"tipo": "desconhecido", "item": None, "provedor": None,
             "detalhe": "", "aviso": None}
    p = Path((caminho or "").strip())
    if not p.exists():
        return {**vazio, "detalhe": "caminho não existe."}
    if p.is_dir():
        return {**vazio, "tipo": "pasta",
                "detalhe": f"pasta: varre jogos de PC + ROMs ({p})."}
    ext = p.suffix.lower()
    if ext == ".json":
        return {**vazio, "tipo": "json", "detalhe": "lista de jogos (JSON)."}
    if ext == ".zip":
        return {**vazio, "tipo": "pacote",
                "detalhe": "pacote portátil (.zip) — tenta restaurar."}
    prov = provedor_por_extensao(ext)
    if prov is not None:
        emu = prov["exe"]() or ""
        item = pontuar(_item_rom(str(p), emu))
        aviso = None
        if not emu:
            aviso = (f"{prov['nome']} não instalado — a ROM importa mesmo assim; "
                     f"depois instale com 'Atualizar {prov['nome']}'.")
        return {"tipo": "rom", "item": item, "provedor": prov["chave"],
                "detalhe": (f"ROM { '/'.join(prov['sistemas'])} → {prov['nome']} "
                            f"· '{item['titulo']}'"),
                "aviso": aviso}
    if ext in EXE_IMPORTAVEIS or not ext:
        item = pontuar({
            "titulo": _titulo_de_exe(p), "executable_path": str(p),
            "shop": "", "object_id": "",
            "horas": 0.0, "origem": "scan-disco",
        })
        aviso = None
        if SKIP_EXE_RE.search(p.name):
            aviso = "parece instalador/suporte (setup, redist…) — confira antes."
        return {"tipo": "jogo", "item": item, "provedor": None,
                "detalhe": f"jogo de PC (roda direto, sem emulador) · '{item['titulo']}'",
                "aviso": aviso}
    return {**vazio, "detalhe": (f"extensão '{ext or '?'}' não suportada "
                                 "(exe, ROM 3DS, .json, .zip ou pasta).")}


def preview_pasta(roots: list[str] | None = None) -> tuple[list[str], list[dict], dict]:
    """Uma varredura só: jogos de PC + ROMs nas mesmas raízes.

    (raízes_usadas, itens pontuados mistos e sem duplicatas,
    info{vistos, truncado, raizes, emu}).
    ROMs sem emulador vêm com exe vazio (importam; o play orienta).
    """
    if not roots:
        vistas: list[str] = []
        for r in default_scan_roots() + default_roms_roots():
            if r not in vistas:
                vistas.append(r)
        roots = vistas
    roots_u, itens_disco, info_d = preview_scan(roots)
    _r, itens_rom, info_r, emu = preview_roms(roots, None)
    itens = sorted(fundir_duplicados(itens_disco + itens_rom),
                   key=lambda j: j["titulo"].lower())
    info = {"vistos": info_d["vistos"] + info_r["vistos"],
            "truncado": info_d["truncado"] or info_r["truncado"],
            "raizes": info_d["raizes"], "emu": emu}
    return roots_u, itens, info


def _norm_titulo(t) -> str:
    return " ".join((t or "").casefold().split())


def _norm_caminho(c) -> str:
    """Mesmo arquivo em SOs distintos compara igual (D:\… == /run/media/…)."""
    c = (c or "").strip()
    if not c:
        return ""
    return win_para_linux(c).lower()


def _dobrar_fundido(atual: dict, novo: dict) -> None:
    """Funde `novo` dentro de `atual` (mesmo jogo, outra fonte)."""
    exe_a, exe_n = (atual.get("executable_path") or ""), (novo.get("executable_path") or "")
    # o exe que existe neste ou no outro SO vence; senão, o não-vazio
    troca = False
    for cand in (exe_n, exe_a):
        if cand and existe_aqui_ou_traduzido(cand)[0]:
            if cand != exe_a:
                atual["executable_path"] = cand
                atual["launch_options"] = novo.get("launch_options") or atual.get("launch_options")
                troca = True
            break
    else:
        if exe_n and not exe_a:
            atual["executable_path"] = exe_n
            atual["launch_options"] = novo.get("launch_options") or atual.get("launch_options")
            troca = True
    if (novo.get("horas") or 0) > (atual.get("horas") or 0):
        atual["horas"] = novo["horas"]
    for campo in ("shop", "object_id", "game_code", "regiao", "rom_path"):
        if not (atual.get(campo) or "") and (novo.get(campo) or ""):
            atual[campo] = novo[campo]
    if novo.get("tem_metadados"):
        atual["tem_metadados"] = True
    for f in novo.get("fontes", [novo.get("fonte") or novo.get("origem") or "?"]):
        if f and f not in atual["fontes"]:
            atual["fontes"].append(f)
    atual["fonte"] = "+".join(atual["fontes"])


def _compativel(atual: dict, novo: dict) -> bool:
    """Podem ser o mesmo jogo? ROMs: mesma rom. PC: exe igual ou ausente."""
    if (atual.get("origem") or "") == "rom-3ds":
        return _norm_caminho(atual.get("rom_path")) == _norm_caminho(novo.get("rom_path"))
    ea, en = _norm_caminho(atual.get("executable_path")), _norm_caminho(novo.get("executable_path"))
    return (not ea) or (not en) or (ea == en)


def fundir_duplicados(itens: list[dict]) -> list[dict]:
    """Junta achados repetidos do preview (mesmo jogo em N fontes).

    Grupo = mesmo título normalizado + mesmo kind (rom/pc). Dentro do grupo,
    exes diferentes e não-vazios = instalações distintas (separa); resto funde:
    herda o melhor exe, soma fontes/horas e re-pontua. Itens já pontuados são
    re-pontuados (idempotente).
    """
    grupos: dict[tuple, list[dict]] = {}
    ordem: list[tuple] = []
    for it in itens:
        t = _norm_titulo(it.get("titulo"))
        kind = "rom" if (it.get("origem") or "") == "rom-3ds" else "pc"
        chave = (kind, t) if t else ("unico", id(it))
        if chave not in grupos:
            grupos[chave] = []
            ordem.append(chave)
        grupos[chave].append(dict(it))
    saidas: list[dict] = []
    for chave in ordem:
        fundidos: list[dict] = []
        for it in grupos[chave]:
            it["fontes"] = [it.get("fonte") or it.get("origem") or "?"]
            for f in fundidos:
                if _compativel(f, it):
                    _dobrar_fundido(f, it)
                    break
            else:
                fundidos.append(it)
        for f in fundidos:
            f["fonte"] = "+".join(f["fontes"])
            saida = pontuar(f)
            if len(f["fontes"]) > 1:
                saida["motivos"] = [*saida.get("motivos", []),
                                    f"achado também em: {', '.join(f['fontes'][1:])}"]
            saidas.append(saida)
    return saidas


# --------------------------------------------------------------------------
# Metadados internos de ROMs 3DS (NCSD/CCI, NCCH/CXI, 3DSX + SMDH)
# --------------------------------------------------------------------------

SMDH_IDIOMAS = ("Japonês", "Inglês", "Francês", "Alemão", "Italiano", "Espanhol",
                "Chinês Simplificado", "Coreano", "Holandês", "Português",
                "Russo", "Chinês Tradicional")
SMDH_REGIOES = ("Japão", "América do Norte", "Europa", "Austrália", "China",
                "Coreia", "Taiwan")


def _u32(buf: bytes, off: int) -> int:
    return int.from_bytes(buf[off:off + 4], "little")


def _parse_smdh(smdh: bytes) -> dict:
    if len(smdh) < 0x201C or smdh[:4] != b"SMDH":
        return {}
    nomes: list[str] = []
    for i in range(12):
        # Campo UTF-16LE de tamanho fixo: decodifica TUDO e corta no 1º NUL.
        # (Separar os BYTES por b"\x00\x00" quebra no meio do último char.)
        raw = smdh[0x8 + i * 0x200:0x8 + i * 0x200 + 0x80]
        try:
            nomes.append(raw.decode("utf-16-le").split("\x00")[0].strip())
        except Exception:
            nomes.append("")
    titulo, idioma = "", ""
    for i in (1, 0):
        if nomes[i]:
            titulo, idioma = nomes[i], SMDH_IDIOMAS[i]
            break
    if not titulo:
        for i, t in enumerate(nomes):
            if t:
                titulo, idioma = t, SMDH_IDIOMAS[i]
                break
    regs = [SMDH_REGIOES[b] for b in range(7) if _u32(smdh, 0x2018) & (1 << b)]
    out: dict = {}
    if titulo:
        out["titulo"] = titulo
        out["idioma_titulo"] = idioma
    if regs:
        out["regiao"] = "Livre" if len(regs) == 7 else ", ".join(regs)
    return out


def _ler_icon_bin(caminho: str) -> bytes:
    """Extrai o icon.bin (SMDH) bruto da ROM, ou b"" se não der."""
    p = Path(caminho)
    if not p.is_file():
        return b""
    with p.open("rb") as f:
        head = f.read(0x400)
        if len(head) < 0x204:
            return b""
        if head[:4] == b"3DSX":  # homebrew: SMDH ao final do cabeçalho
            if len(head) < 0x28:
                return b""
            off, size = _u32(head, 0x20), _u32(head, 0x24)
            if not off or not size or off > 64 * 1024 * 1024:
                return b""
            f.seek(off)
            return f.read(min(size, 0x4000))
        if head[0x100:0x104] == b"NCSD":  # .cci/.3ds
            if len(head) < 0x128:
                return b""
            base = _u32(head, 0x120) * 0x200
        elif head[0x100:0x104] == b"NCCH":  # .cxi
            base = 0
        else:
            return b""
        f.seek(base)
        ncch = f.read(0x300)
        if len(ncch) < 0x300 or ncch[0x100:0x104] != b"NCCH":
            return b""
        ex_off = base + _u32(ncch, 0x1A0) * 0x200
        if ex_off > 16 * 1024 ** 3:
            return b""
        f.seek(ex_off)
        exeh = f.read(0x200)
        if len(exeh) < 0x200:
            return b""
        for i in range(10):
            e = exeh[i * 16:(i + 1) * 16]
            if e[:8].rstrip(b"\x00") in (b"icon", b"icon.bin"):
                fo, fs = _u32(e, 8), _u32(e, 12)
                if not fs or fs > 0x4000:
                    return b""
                f.seek(ex_off + 0x200 + fo)
                return f.read(min(fs, 0x4000))
    return b""


def ler_metadados_3ds(caminho: str) -> dict:
    """Lê título/código/região de dentro da ROM. {} se não der (usa nome do arquivo)."""
    try:
        p = Path(caminho)
        if not p.is_file():
            return {}
        meta: dict = {}
        with p.open("rb") as f:
            head = f.read(0x400)
            if len(head) < 0x204:
                return {}
            if head[:4] == b"3DSX":
                pass  # sem product code; só SMDH abaixo
            elif head[0x100:0x104] == b"NCSD":
                if len(head) < 0x128:
                    return {}
                base = _u32(head, 0x120) * 0x200
                f.seek(base)
                ncch = f.read(0x300)
                if len(ncch) < 0x300 or ncch[0x100:0x104] != b"NCCH":
                    return {}
                code = ncch[0x150:0x160].split(b"\x00")[0].decode("ascii", "ignore").strip()
                if code:
                    meta["game_code"] = code
            elif head[0x100:0x104] == b"NCCH":
                f.seek(0)
                ncch = f.read(0x300)
                if len(ncch) >= 0x300 and ncch[0x100:0x104] == b"NCCH":
                    code = ncch[0x150:0x160].split(b"\x00")[0].decode("ascii", "ignore").strip()
                    if code:
                        meta["game_code"] = code
            else:
                return {}
        meta.update(_parse_smdh(_ler_icon_bin(caminho)))
        return meta
    except (OSError, ValueError, OverflowError):
        return {}


def _morton(x: int, y: int) -> int:
    z = 0
    for i in range(4):
        z |= ((x >> i) & 1) << (2 * i)
        z |= ((y >> i) & 1) << (2 * i + 1)
    return z


def _desembaralha_rgb565(dados: bytes, lado: int) -> bytes:
    """SMDH guarda o ícone em tiles 8x8 (ordem Morton). Devolve RGB888 linear."""
    n = lado * lado
    if len(dados) < n * 2:
        raise ValueError("ícone curto")
    rgb = bytearray(n * 3)
    tiles = lado // 8
    for ty in range(tiles):
        for tx in range(tiles):
            base_t = (ty * tiles + tx) * 64
            for y in range(8):
                for x in range(8):
                    src = (base_t + _morton(x, y)) * 2
                    v = dados[src] | (dados[src + 1] << 8)
                    r = ((v >> 11) & 31) * 255 // 31
                    g = ((v >> 5) & 63) * 255 // 63
                    b = (v & 31) * 255 // 31
                    dst = ((ty * 8 + y) * lado + (tx * 8 + x)) * 3
                    rgb[dst:dst + 3] = bytes((r, g, b))
    return bytes(rgb)


def _png_rgb(larg: int, alt: int, rgb: bytes) -> bytes:
    import struct
    import zlib

    def bloco(tipo: bytes, dado: bytes) -> bytes:
        c = tipo + dado
        return struct.pack(">I", len(dado)) + c + struct.pack(
            ">I", zlib.crc32(c) & 0xFFFFFFFF)

    cab = struct.pack(">IIBBBBB", larg, alt, 8, 2, 0, 0, 0)
    corpo = b"".join(b"\x00" + rgb[y * larg * 3:(y + 1) * larg * 3]
                     for y in range(alt))
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", cab)
            + bloco(b"IDAT", zlib.compress(corpo)) + bloco(b"IEND", b""))


def icone_rom_para_png(caminho: str, alvo_px: int = 144) -> bytes | None:
    """Decodifica o ícone SMDH da ROM e devolve PNG RGB (None se não der).

    Ordem de tiles documentada (Morton 8x8); conferir visualmente na 1ª ROM real.
    """
    try:
        icon = _ler_icon_bin(caminho)
        if len(icon) >= 0x1680:
            rgb, lado = _desembaralha_rgb565(icon[:0x1200], 48), 48
        elif len(icon) >= 0x480:
            rgb, lado = _desembaralha_rgb565(icon[0x1200:0x1200 + 0x480], 24), 24
        else:
            return None
        fator = max(1, alvo_px // lado)
        if fator > 1:  # amplia por vizinho mais próximo (pixel nítido)
            amp = bytearray(lado * fator * lado * fator * 3)
            W = lado * fator
            for y in range(lado):
                for x in range(lado):
                    px = rgb[(y * lado + x) * 3:(y * lado + x) * 3 + 3]
                    for dy in range(fator):
                        base = ((y * fator + dy) * W + x * fator) * 3
                        amp[base:base + fator * 3] = px * fator
            rgb, lado = bytes(amp), W
        return _png_rgb(lado, lado, rgb)
    except Exception:
        return None


# --------------------------------------------------------------------------
# Importação / backup / capas
# --------------------------------------------------------------------------

def importar_lista(con: sqlite3.Connection, itens: list[dict]) -> dict:
    antes = con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()["n"]
    agora = agora_iso()
    novos = 0
    for j in itens:
        if not isinstance(j, dict):
            continue
        j = {k: (v.replace("\x00", "") if isinstance(v, str) else v)
             for k, v in j.items()}
        titulo = (j.get("titulo") or "").strip()
        if not titulo:
            continue
        try:
            nota = j.get("nota")
            nota = None if nota in (None, "") else int(nota)
            if nota is not None and not 0 <= nota <= 10:
                nota = None
            horas = float(j.get("horas") or 0)
            if horas < 0:
                horas = 0.0
            confianca = float(j.get("score") or j.get("confianca") or 0)
        except (TypeError, ValueError):
            continue
        try:
            cur = con.execute(
                """INSERT OR IGNORE INTO jogos
                   (titulo, executable_path, exe_win, exe_linux, wine_prefix, launch_options,
                    status, nota, favorito, horas, observacoes, origem, shop, object_id,
                    game_code, regiao, azahar_preset, confianca, criado_em, atualizado_em)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (titulo, (j.get("executable_path") or "").strip(),
                 (j.get("exe_win") or "").strip(), (j.get("exe_linux") or "").strip(),
                 (j.get("wine_prefix") or ""), (j.get("launch_options") or ""),
                 j.get("status") if j.get("status") in STATUS_VALIDOS else "backlog",
                 nota, 1 if j.get("favorito") else 0,
                 horas, (j.get("observacoes") or ""),
                 j.get("origem") or "manual", (j.get("shop") or ""),
                 (j.get("object_id") or ""), (j.get("game_code") or "").strip(),
                 (j.get("regiao") or "").strip(), (j.get("azahar_preset") or "").strip(),
                 confianca, agora, agora),
            )
            novos += cur.rowcount
            if cur.rowcount and (j.get("origem") or "") == "rom-3ds":
                try:  # capa automática: ícone de dentro da própria ROM
                    rom = (j.get("rom_path") or "").strip()
                    png = icone_rom_para_png(rom) if rom else None
                    if png:
                        salvar_capa_bytes(con, cur.lastrowid,
                                          slugify(titulo) + ".png", png)
                except Exception:
                    pass
        except Exception:
            continue
    con.commit()
    depois = con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()["n"]
    return {"novos": novos, "total_no_banco": depois, "antes": antes}


def importar_com_min_score(con: sqlite3.Connection, itens: list[dict], min_score: float) -> dict:
    return importar_lista(con, [j for j in itens if float(j.get("score") or 0) >= min_score])


def fazer_backup(db_path: Path, manter: int = 10) -> dict:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest_db = BACKUP_DIR / f"biblioteca-{ts}.db"
    dest_json = BACKUP_DIR / f"biblioteca-{ts}.json"
    con = get_db(db_path)
    try:
        dados = _dados_exportacao(con)
        dst = sqlite3.connect(str(dest_db))
        try:
            con.backup(dst)
        finally:
            dst.close()
    finally:
        con.close()
    dest_json.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    # poda: mantém os `manter` mais recentes de cada tipo
    for padrao in ("biblioteca-*.db", "biblioteca-*.json"):
        arqs = sorted(BACKUP_DIR.glob(padrao), key=lambda p: p.name, reverse=True)
        for velho in arqs[manter:]:
            try:
                velho.unlink()
            except OSError:
                pass
    return {"db": str(dest_db), "json": str(dest_json),
            "jogos": len(dados["jogos"]), "mantidos": manter}


def listar_backups() -> list[dict]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    arqs = sorted(BACKUP_DIR.glob("biblioteca-*.json"),
                  key=lambda p: p.name, reverse=True)
    return [{"arquivo": str(p), "nome": p.name, "bytes": p.stat().st_size} for p in arqs]


def slugify(s: str) -> str:
    n = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    n = re.sub(r"[^a-zA-Z0-9]+", "-", n.lower()).strip("-")
    return n or "capa"


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


def backup_saves_azahar(manter: int = 10) -> dict:
    """Zipa sdmc/ + states/ do Azahar em backups/. Retorna dict (sempre)."""
    return backup_saves_emu("azahar", manter)


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


# --------------------------------------------------------------------------
# Execução de jogos (Windows + Linux)
# --------------------------------------------------------------------------

def _eh_elevacao_necessaria(e: Exception) -> bool:
    return isinstance(e, OSError) and getattr(e, "winerror", None) == 740


def executar_elevado(executable_path: str, launch_options: str = "") -> dict:
    """Relança via UAC (ShellExecute 'runas'). Só Windows. Abre o prompt do UAC."""
    if os.name == "nt":
        import ctypes
        exe = traduzir_para_atual((executable_path or "").strip())
        p = Path(exe)
        if not p.exists():
            return {"ok": False, "erro": f"Executável não encontrado: {exe}"}
        cwd = str(p.parent) if p.parent.exists() else None
        extra = shlex.split(launch_options.strip(), posix=False) if launch_options.strip() else []
        params = subprocess.list2cmdline(extra) or None
        try:
            rc = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", str(p), params, cwd, 1)
            if int(rc) <= 32:
                return {"ok": False, "erro": f"UAC recusou/falhou (código {int(rc)})"}
            return {"ok": True, "modo": "runas-uac"}
        except Exception as e:
            return {"ok": False, "erro": f"{type(e).__name__}: {e}"}
    return {"ok": False, "erro": "elevação só existe no Windows"}


def _lancar(executable_path: str, wine_prefix: str = "", launch_options: str = "",
            elevar: bool = False) -> tuple[dict, object | None]:
    """Núcleo do lançamento. Retorna (resultado, Popen|None).

    Processo None = sem handle rastreável (startfile, UAC, erro, sem exe).
    """
    exe = (executable_path or "").strip()
    if not exe:
        return {"ok": False, "erro": "Jogo sem caminho de executável cadastrado."}, None
    if elevar:
        return executar_elevado(exe, launch_options), None
    exe = traduzir_para_atual(exe)  # gravado num SO, executando no outro
    p = Path(exe)
    if not p.exists():
        return {"ok": False, "erro": f"Executável não encontrado: {exe}"}, None

    env = os.environ.copy()
    if wine_prefix.strip():
        env["WINEPREFIX"] = wine_prefix.strip()

    # Aspas são só agrupamento p/ o split (Popen recebe lista e cita sozinho):
    # "C:\com espaco\jogo.cci" vira um arg limpo, sem aspas literais.
    extra = shlex.split(launch_options, posix=(os.name != "nt")) if launch_options.strip() else []
    if os.name == "nt":
        extra = [(a[1:-1] if len(a) >= 2 and a[0] == a[-1] and a[0] in "\"'" else a)
                 for a in extra]

    try:
        cwd = str(p.parent) if p.parent.exists() else None
        if os.name == "nt":
            ext = p.suffix.lower()
            if ext in (".lnk", ".url") or p.is_dir():
                os.startfile(str(p))  # type: ignore[attr-defined]
                return {"ok": True, "modo": "startfile"}, None
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            proc = subprocess.Popen([str(p), *extra], cwd=cwd, env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL, creationflags=creationflags,
                                    close_fds=True)
            return {"ok": True, "modo": "popen-windows"}, proc
        else:
            if not os.access(str(p), os.X_OK):
                return {"ok": False,
                        "erro": f"Sem permissão de execução: {exe} (rode chmod +x?)"}, None
            cmd = [str(p), *extra]
            proc = subprocess.Popen(cmd, cwd=cwd, env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL, start_new_session=True,
                                    close_fds=True)
            return {"ok": True, "modo": "popen-linux"}, proc
    except Exception as e:
        if _eh_elevacao_necessaria(e):
            return {"ok": False, "requer_elevacao": True,
                    "erro": f"{type(e).__name__}: {e} — o executável exige administrador."}, None
        return {"ok": False, "erro": f"{type(e).__name__}: {e}"}, None


def executar_jogo(executable_path: str, wine_prefix: str = "", launch_options: str = "",
                  elevar: bool = False) -> dict:
    res, _proc = _lancar(executable_path, wine_prefix, launch_options, elevar)
    return res


def _lancar_jogo_dict(jogo: dict, elevar: bool = False) -> tuple[dict, object | None]:
    """Resolve o exe do SO atual (exe_win/exe_linux vencem) e lança.

    Origens com provider (ex.: rom-3ds) usam o exe e as flags do provider.
    """
    origem = (jogo.get("origem") or "")
    prov = provedor_por_origem(origem)
    exe, _origem = resolver_exe(jogo)
    if not exe and prov is not None:
        exe = prov["exe"]() or ""  # linha sem emu (ou apagado): o instalado vale
    if not exe and prov is not None:
        return {"ok": False, "erro": prov["dica_instalacao"]}, None
    launch = (jogo.get("launch_options") or "")
    if prov is not None and launch.strip():
        launch = montar_launch_rom(prov, launch)
    return _lancar(exe, (jogo.get("wine_prefix") or ""), launch, elevar=elevar)


def executar_jogo_dict(jogo: dict, elevar: bool = False) -> dict:
    """Resolve o exe do SO atual (exe_win/exe_linux vencem) e executa."""
    res, _proc = _lancar_jogo_dict(jogo, elevar)
    return res


def azahar_flags() -> list[str]:
    """Flags extras ao bootar ROM (padrão -f fullscreen; vazio desliga)."""
    return shlex.split(os.environ.get("BIBLIOTECA_AZAHAR_FLAGS", "-f"),
                       posix=(os.name != "nt"))


def marcar_execucao(con: sqlite3.Connection, gid: int) -> None:
    agora = agora_iso()
    con.execute("UPDATE jogos SET ultima_execucao=?, atualizado_em=? WHERE id=?",
                (agora, agora, gid))
    con.commit()


# --------------------------------------------------------------------------
# Provedores de emulação (HUB): um registro, N emuladores
#
# Cada provider descreve UM emulador: que origens de jogo ele atende, onde
# está o exe, onde ficam config/saves, como montar a linha de lançamento e
# como aplicar preset. Azahar é o provider nº 1; o próximo (ex.: NDS, GBA)
# entra aqui sem tocar em lançamento, pacote ou frontends.
# --------------------------------------------------------------------------

def _prov_azahar() -> dict:
    return {
        "chave": "azahar",
        "nome": "Azahar",
        "sistemas": ("Nintendo 3DS",),
        "origens": ("rom-3ds",),
        "exe": default_emu_3ds,          # () -> str
        "user_dir": azahar_user_dir,     # (exe="") -> str
        "saves_subs": ("sdmc", "states"),
        "pacote_subs": ("sdmc",),        # states travam à versão: fora do pacote
        "rom_exts": ROM_EXTS_3DS,
        "flags": azahar_flags,           # () -> list[str]
        "aplicar_preset": aplicar_preset,  # (nome) -> dict
        "dica_instalacao": ("Azahar não encontrado — instale em "
                            "Games/Emuladores/Azahar ou defina BIBLIOTECA_EMULADOR_3DS."),
    }


def provedores() -> dict:
    """chave -> spec. Construído sob demanda (as funções existem no import)."""
    return {"azahar": _prov_azahar()}


def provedor_por_origem(origem: str) -> dict | None:
    for prov in provedores().values():
        if (origem or "") in prov["origens"]:
            return prov
    return None


def provedor_por_extensao(ext: str) -> dict | None:
    """Provider que abre essa extensão de ROM ('.3ds' -> Azahar). None = PC."""
    ext = (ext or "").strip().lower()
    if not ext.startswith("."):
        ext = "." + ext
    for prov in provedores().values():
        if ext in prov.get("rom_exts", ()):
            return prov
    return None


def provedor_nome(jogo_ou_origem) -> str:
    """'Azahar · Nintendo 3DS' p/ ROMs; origem crua p/ jogos de PC."""
    origem = jogo_ou_origem.get("origem") if isinstance(jogo_ou_origem, dict) \
        else jogo_ou_origem
    prov = provedor_por_origem(origem or "")
    if prov is None:
        return origem or ""
    return f"{prov['nome']} · {'/'.join(prov['sistemas'])}"


def montar_launch_rom(prov: dict, rom_path: str) -> str:
    """flags do provider + ROM entre aspas quando tem espaço."""
    rom = (rom_path or "").strip()
    if " " in rom and not (rom.startswith('"') and rom.endswith('"')):
        rom = f'"{rom}"'
    flags = " ".join(prov["flags"]())
    return (flags + " " if flags else "") + rom


def backup_saves_emu(chave: str, manter: int = 10) -> dict:
    """Zipa as pastas de save do provider em backups/. Retorna dict (sempre)."""
    prov = provedores().get(chave)
    if prov is None:
        return {"ok": False, "erro": f"emulador '{chave}' desconhecido"}
    ud = prov["user_dir"]() or ""
    if not ud:
        return {"ok": False, "erro": f"{prov['nome']} não instalado"}
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"{chave}-saves-{ts}.zip"
    n = 0
    try:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for sub in prov["saves_subs"]:
                d = Path(ud) / sub
                if not d.is_dir():
                    continue
                for f in sorted(d.rglob("*")):
                    if f.is_file():
                        try:
                            z.write(f, f.relative_to(ud))
                            n += 1
                        except OSError:
                            pass
    except OSError as e:
        return {"ok": False, "erro": f"falha ao zipar: {e}"}
    if n == 0:
        try:
            dest.unlink()
        except OSError:
            pass
        return {"ok": False, "erro": "sem saves ainda (saves vazios ou ausentes)"}
    for padrao in (f"{chave}-saves-*.zip", "azahar-saves-*.zip"):
        arqs = sorted(BACKUP_DIR.glob(padrao), key=lambda p: p.name, reverse=True)
        for velho in arqs[manter:]:
            try:
                velho.unlink()
            except OSError:
                pass
    return {"ok": True, "arquivo": str(dest), "arquivos": n}


# --------------------------------------------------------------------------
# Sessões rastreadas: horas automáticas (mede o processo lançado)
# --------------------------------------------------------------------------

LIMIAR_SESSAO_S = 30  # sessões mais curtas não contam (clique de teste)


def adicionar_horas(con: sqlite3.Connection, gid: int, delta_h: float) -> dict:
    """Soma horas ao jogo (atômico). Retorna total novo."""
    try:
        delta = float(delta_h or 0)
    except (TypeError, ValueError):
        return {"ok": False, "erro": "delta inválido"}
    if delta <= 0:
        return {"ok": False, "erro": "nada a somar"}
    cur = con.execute("SELECT horas FROM jogos WHERE id=?", (gid,)).fetchone()
    if cur is None:
        return {"ok": False, "erro": "jogo inexistente"}
    total = round((cur["horas"] or 0) + delta, 2)
    con.execute("UPDATE jogos SET horas=?, atualizado_em=? WHERE id=?",
                (total, agora_iso(), gid))
    con.commit()
    return {"ok": True, "somado": round(delta, 2), "total": total}


def _vigiar_processo(proc, limiar_s: float, ao_fim) -> None:
    t0 = time.monotonic()
    try:
        proc.wait()
    except Exception:
        pass  # processo já morreu ou handle inválido: conta o decorrido
    decorrido = time.monotonic() - t0
    sessao = round(decorrido / 3600.0, 2) if decorrido >= limiar_s else 0.0
    try:
        ao_fim(sessao, True)
    except Exception:
        pass


def executar_monitorado(jogo: dict, ao_fim=None,
                        limiar_s: float = LIMIAR_SESSAO_S) -> dict:
    """Lança e, havendo handle (Popen), vigia o fim em thread daemon.

    ao_fim(sessao_horas, rastreado) roda na thread vigia — o frontend deve
    despachar para a thread de UI. Sem handle (startfile/UAC) e com ok:
    chama ao_fim(0.0, False) direto. Limite honesto: fechar o launcher
    antes do jogo mata a vigia e perde a sessão.
    """
    res, proc = _lancar_jogo_dict(jogo)
    rastreavel = bool(res.get("ok")) and proc is not None
    res["rastreado"] = rastreavel
    if ao_fim is None:
        return res
    if rastreavel:
        threading.Thread(target=_vigiar_processo, args=(proc, limiar_s, ao_fim),
                         daemon=True).start()
    elif res.get("ok"):
        ao_fim(0.0, False)
    return res


# --------------------------------------------------------------------------
# Presets por jogo do Azahar (mescla no qt-config.ini antes de lançar)
# --------------------------------------------------------------------------

def presets_dir() -> Path:
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    return PRESETS_DIR


def listar_presets() -> list[str]:
    try:
        return sorted(p.stem for p in presets_dir().glob("*.ini") if p.is_file())
    except OSError:
        return []


def azahar_config_atual() -> Path | None:
    ud = azahar_user_dir()
    if ud:
        cfgdir = Path(ud) / "config"
        cfg = cfgdir / "qt-config.ini"
        if cfg.is_file():
            return cfg
        try:
            alts = sorted(p for p in cfgdir.glob("*.ini") if p.is_file())
        except OSError:
            alts = []
        if alts:
            return alts[0]
    return None


def salvar_preset_de_atual(nome: str) -> dict:
    """Fotografa o qt-config.ini atual como presets/<nome>.ini."""
    cfg = azahar_config_atual()
    if cfg is None:
        return {"ok": False,
                "erro": "config do Azahar não encontrada (abra o Azahar uma vez)."}
    slug = slugify(nome or "")
    if not slug:
        return {"ok": False, "erro": "nome de preset vazio."}
    dest = presets_dir() / f"{slug}.ini"
    try:
        shutil.copy2(str(cfg), str(dest))
    except OSError as e:
        return {"ok": False, "erro": f"falha ao copiar: {e}"}
    return {"ok": True, "preset": slug, "arquivo": str(dest)}


def aplicar_preset(nome: str) -> dict:
    """Mescla presets/<nome>.ini sobre o qt-config.ini (backup .bak uma vez)."""
    nome = (nome or "").strip()
    if not nome:
        return {"ok": False, "erro": "sem preset"}
    base = presets_dir()
    alvo = base / Path(nome).name
    if not alvo.suffix:
        alvo = alvo.with_name(alvo.name + ".ini")  # aceita stem ("up-2x") ou "up-2x.ini"
    try:
        dentro = alvo.resolve().parent == base.resolve()
    except OSError:
        dentro = False
    if not dentro or alvo.suffix.lower() != ".ini" or not alvo.is_file():
        return {"ok": False, "erro": f"preset '{nome}' não existe em presets/."}
    cfg = azahar_config_atual()
    if cfg is None:
        return {"ok": False, "erro": "config do Azahar não encontrada."}
    try:
        bak = cfg.with_name(cfg.name + ".bak")
        if not bak.is_file():
            shutil.copy2(str(cfg), str(bak))  # estado pré-preset, uma única vez
        atual, novo = configparser.ConfigParser(), configparser.ConfigParser()
        atual.optionxform = str  # type: ignore[assignment]  # Qt usa camelCase
        novo.optionxform = str  # type: ignore[assignment]
        atual.read(cfg, encoding="utf-8")
        novo.read(alvo, encoding="utf-8")
        for sec in novo.sections():
            if not atual.has_section(sec):
                atual.add_section(sec)
            for chave, valor in novo.items(sec):
                atual.set(sec, chave, valor)
        with cfg.open("w", encoding="utf-8") as fh:
            atual.write(fh)
    except (OSError, configparser.Error) as e:
        return {"ok": False, "erro": f"falha ao mesclar: {e}"}
    return {"ok": True, "preset": alvo.stem, "config": str(cfg)}


def restaurar_config_azahar() -> dict:
    """Volta o qt-config.ini ao estado pré-preset (.bak)."""
    cfg = azahar_config_atual()
    if cfg is None:
        return {"ok": False, "erro": "config do Azahar não encontrada."}
    bak = cfg.with_name(cfg.name + ".bak")
    if not bak.is_file():
        return {"ok": False, "erro": "sem backup pré-preset (.bak ausente)."}
    try:
        shutil.copy2(str(bak), str(cfg))
    except OSError as e:
        return {"ok": False, "erro": f"falha ao restaurar: {e}"}
    return {"ok": True, "config": str(cfg)}


def preparar_lancamento(jogo: dict) -> dict:
    """Aplica o preset do provider do jogo. Nunca bloqueia o play."""
    origem = (jogo.get("origem") or "")
    prov = provedor_por_origem(origem)
    if prov is None:
        return {"preset_aplicado": None, "aviso": None}
    avisos: list[str] = []
    aplicado = None
    nome = (jogo.get("azahar_preset") or "").strip()
    if nome:
        r = prov["aplicar_preset"](nome)
        if r.get("ok"):
            aplicado = r["preset"]
        else:
            avisos.append(f"Preset '{nome}' falhou ({r['erro']}); abrindo com config atual.")
    launch = (jogo.get("launch_options") or "").strip()
    if launch and provedor_por_extensao(Path(launch).suffix) is not None:
        if rom_parece_criptografada(launch) and not azahar_tem_chaves():
            avisos.append("ROM parece criptografada e o Azahar está sem aes_keys.txt "
                          "— o jogo não vai abrir. Faça o dump das chaves do seu 3DS "
                          "(GodMode9) para user/sysdata/aes_keys.txt.")
    return {"preset_aplicado": aplicado, "aviso": " ".join(avisos) or None}


def rom_parece_criptografada(rom_path: str) -> bool:
    """ExeFS sem ícone extraível = quase sempre ROM criptografada."""
    rom = (rom_path or "").strip()
    if not rom or not Path(rom).is_file():
        return False  # ausente é outro erro (o play já reporta)
    try:
        return not _ler_icon_bin(rom)
    except Exception:
        return False


def azahar_tem_chaves() -> bool:
    ud = azahar_user_dir()
    return bool(ud) and (Path(ud) / "sysdata" / "aes_keys.txt").is_file()


# --------------------------------------------------------------------------
# Pacote portátil (.zip): banco + capas + presets + saves 3DS
# --------------------------------------------------------------------------

PACOTE_ESQUEMA = 1
PACOTE_INFO = "pacote-info.json"
PACOTE_JSON = "biblioteca.json"
PACOTE_MANIFESTO = "capas-manifesto.json"


def _dados_exportacao(con: sqlite3.Connection) -> dict:
    rows = con.execute("SELECT * FROM jogos ORDER BY id").fetchall()
    return {"exportado_em": agora_iso(), "jogos": [row_to_dict(r) for r in rows]}


def _saves_para_pacote() -> list[tuple[str, Path]]:
    """[(membro_no_zip, caminho)] dos saves de todos os providers instalados.

    Nomes estáveis por provider: 'azahar-user/sdmc/...' (compat com pacotes
    já exportados).
    """
    pares: list[tuple[str, Path]] = []
    for prov in provedores().values():
        try:
            ud = prov["user_dir"]() or ""
        except Exception:
            continue
        if not ud:
            continue
        for sub in prov["pacote_subs"]:
            base = Path(ud) / sub
            if not base.is_dir():
                continue
            try:
                arquivos = sorted(p for p in base.rglob("*") if p.is_file())
            except OSError:
                continue
            for arq in arquivos:
                try:
                    rel = arq.relative_to(base).as_posix()
                except ValueError:
                    continue
                pares.append((f"{prov['chave']}-user/{sub}/{rel}", arq))
    return pares


def exportar_pacote(destino, db_path=None, incluir_saves: bool = True) -> dict:
    """Empacota tudo para levar a outra máquina (ou guardar)."""
    destino = Path(destino)
    if destino.suffix.lower() != ".zip":
        destino = destino.with_suffix(".zip")
    if str(destino.parent):
        destino.parent.mkdir(parents=True, exist_ok=True)
    garantir_dirs()
    con = get_db(Path(db_path) if db_path else DEFAULT_DB)
    try:
        dados = _dados_exportacao(con)
    finally:
        con.close()
    ud = azahar_user_dir()
    sdmc = Path(ud) / "sdmc" if ud else None
    pares_saves = _saves_para_pacote() if incluir_saves else []
    com_saves = bool(pares_saves)
    info = {"app": "biblioteca-jogos", "esquema": PACOTE_ESQUEMA,
            "exportado_em": dados["exportado_em"], "jogos": len(dados["jogos"]),
            "inclui_saves": com_saves, "azahar_versao": azahar_versao_local(),
            "provedores": sorted(provedores())}
    manifesto = {}
    for j in dados["jogos"]:
        if j.get("capa"):
            manifesto[Path(j["capa"]).name] = j["titulo"]
    n = 0
    try:
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(PACOTE_INFO, json.dumps(info, ensure_ascii=False, indent=2))
            z.writestr(PACOTE_JSON, json.dumps(dados, ensure_ascii=False, indent=2))
            z.writestr(PACOTE_MANIFESTO,
                       json.dumps(manifesto, ensure_ascii=False, indent=2))
            n += 3
            for arq in sorted(CAPAS_DIR.glob("*")):
                if arq.is_file() and arq.suffix.lower() in CAPA_EXTS:
                    z.write(arq, f"capas/{arq.name}")
                    n += 1
            for arq in sorted(presets_dir().glob("*.ini")):
                if arq.is_file():
                    z.write(arq, f"presets/{arq.name}")
                    n += 1
            if com_saves:
                for membro, arq in pares_saves:
                    z.write(arq, membro)
                    n += 1
    except OSError as e:
        return {"ok": False, "erro": f"falha ao gravar pacote: {e}"}
    return {"ok": True, "destino": str(destino), "arquivos": n,
            "bytes": destino.stat().st_size, "jogos": len(dados["jogos"]),
            "inclui_saves": com_saves}


def _membro_pacote_ok(nome: str) -> str | None:
    """Categoria do membro ('json','info','manifesto','capa','preset','save')
    ou None se proibido (traversal, absoluto, fora da allowlist)."""
    if not nome:
        return None
    n = nome.replace("\\", "/")
    if ".." in n.split("/") or n.startswith("/") or (len(n) > 1 and n[1] == ":"):
        return None
    if n == PACOTE_JSON:
        return "json"
    if n == PACOTE_INFO:
        return "info"
    if n == PACOTE_MANIFESTO:
        return "manifesto"
    if n.startswith("capas/") and "/" not in n[6:] \
            and Path(n).suffix.lower() in CAPA_EXTS:
        return "capa"
    if n.startswith("presets/") and "/" not in n[8:] and n.lower().endswith(".ini"):
        return "preset"
    partes = n.split("/")
    if len(partes) >= 3 and partes[0].endswith("-user") and not n.endswith("/"):
        prov = provedores().get(partes[0][:-5])
        if prov is not None and partes[1] in prov["pacote_subs"]:
            return "save"
    return None


def importar_pacote(origem, db_path=None, restaurar_saves: bool = False) -> dict:
    """Restaura um pacote: valida TODOS os nomes antes de aplicar qualquer
    coisa (nada parcial em pacote hostil). Capas voltam remapeadas para os
    ids novos via manifesto {arquivo: titulo}."""
    origem = Path(origem)
    try:
        zf = zipfile.ZipFile(origem)
    except (OSError, zipfile.BadZipFile) as e:
        return {"ok": False, "erro": f"pacote inválido: {e}"}
    with zf:
        nomes = [i.filename for i in zf.infolist() if not i.is_dir()]
        cats: dict[str, str] = {}
        for nm in nomes:
            cat = _membro_pacote_ok(nm)
            if cat is None:
                return {"ok": False,
                        "erro": f"membro proibido no pacote: {nm!r} (nada foi aplicado)"}
            cats[nm] = cat
        if PACOTE_JSON not in cats:
            return {"ok": False, "erro": "pacote sem biblioteca.json"}
        try:
            dados = json.loads(zf.read(PACOTE_JSON).decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            return {"ok": False, "erro": f"biblioteca.json inválida: {e}"}
        lista = dados if isinstance(dados, list) else dados.get("jogos", [])
        if not isinstance(lista, list):
            return {"ok": False, "erro": "biblioteca.json deve ser lista ou {jogos:[...]}"}
        try:
            manifesto = json.loads(zf.read(PACOTE_MANIFESTO).decode("utf-8")) \
                if PACOTE_MANIFESTO in cats else {}
        except (ValueError, UnicodeDecodeError):
            manifesto = {}
        if not isinstance(manifesto, dict):
            manifesto = {}
        con = get_db(Path(db_path) if db_path else DEFAULT_DB)
        try:
            res = importar_lista(con, lista)
            capas = 0
            for arq, titulo in manifesto.items():
                cat = cats.get(f"capas/{Path(arq).name}")
                if cat != "capa" or not isinstance(titulo, str) or not titulo.strip():
                    continue
                try:
                    raw = zf.read(f"capas/{Path(arq).name}")
                except KeyError:
                    continue
                alvo = con.execute(
                    "SELECT id FROM jogos WHERE titulo=? ORDER BY id LIMIT 1",
                    (titulo.strip(),)).fetchone()
                if alvo is None:
                    continue
                r = salvar_capa_bytes(con, alvo["id"], Path(arq).name, raw)
                if r.get("ok"):
                    capas += 1
            presets = 0
            garantir_dirs()
            for nm, cat in cats.items():
                if cat != "preset":
                    continue
                try:
                    (presets_dir() / Path(nm).name).write_bytes(zf.read(nm))
                    presets += 1
                except OSError:
                    pass
            saves, saves_ignorados = 0, 0
            tem_saves = any(c == "save" for c in cats.values())
            if tem_saves and restaurar_saves:
                for nm, cat in cats.items():
                    if cat != "save":
                        continue
                    partes = nm.split("/")
                    prov = provedores().get(partes[0][:-5])
                    ud = (prov["user_dir"]() or "") if prov is not None else ""
                    if not ud:
                        saves_ignorados += 1
                        continue
                    try:
                        dest = Path(ud) / partes[1] / Path(*partes[2:])
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(zf.read(nm))
                        saves += 1
                    except (OSError, ValueError):
                        saves_ignorados += 1
        finally:
            con.close()
    return {"ok": True, "novos": res["novos"], "total_no_banco": res["total_no_banco"],
            "capas": capas, "presets": presets, "saves": saves,
            "saves_ignorados": saves_ignorados}
