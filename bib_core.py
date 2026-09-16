#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bib_core — núcleo compartilhado da Biblioteca de Jogos (zero dependências).

Usado pelos dois frontends, todos nesta mesma pasta:
    app_win.py  aplicativo GUI com tkinter (Windows)
    app_tui.py  aplicativo de terminal com curses (Linux)

Tudo que é regra de negócio mora aqui: caminhos canônicos e tradução
Win<->Linux, SQLite (+migração v1->v2), validação, CRUD, pontuação de
confiança, varredura do Hydra, scanner de disco, importação, backup
versionado, capas locais e execução de jogos.
"""
from __future__ import annotations

import base64
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


def garantir_dirs() -> None:
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    CAPAS_DIR.mkdir(parents=True, exist_ok=True)


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
    criado_em TEXT,
    atualizado_em TEXT,
    UNIQUE(titulo, executable_path, launch_options)
);
"""

# Migração de bancos criados pela v1 (sem capa/confianca) e v2 (sem exe por SO).
MIGRACOES = (
    "ALTER TABLE jogos ADD COLUMN capa TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN confianca REAL DEFAULT 0",
    "ALTER TABLE jogos ADD COLUMN exe_win TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN exe_linux TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN game_code TEXT DEFAULT ''",
    "ALTER TABLE jogos ADD COLUMN regiao TEXT DEFAULT ''",
)

CAMPOS_EDITAVEIS = ("titulo", "executable_path", "exe_win", "exe_linux",
                    "wine_prefix", "launch_options", "status", "nota", "favorito",
                    "horas", "observacoes", "shop", "object_id", "origem",
                    "game_code", "regiao")


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
            "capa", "confianca", "criado_em", "atualizado_em"]
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
    for campo in ("exe_win", "exe_linux", "game_code", "regiao"):
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
               object_id, game_code, regiao, criado_em, atualizado_em)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
             (limpo["titulo"], limpo["executable_path"], limpo["exe_win"],
             limpo["exe_linux"], limpo["wine_prefix"],
             limpo["launch_options"], limpo["status"], limpo["nota"],
             limpo["favorito"], limpo["horas"], limpo["observacoes"],
             limpo["origem"], limpo["shop"], limpo["object_id"],
             limpo["game_code"], limpo["regiao"], agora, agora),
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
           atualizado_em=? WHERE id=?""",
        (limpo["titulo"], limpo["executable_path"], limpo["exe_win"],
         limpo["exe_linux"], limpo["wine_prefix"], limpo["launch_options"],
         limpo["status"], limpo["nota"], limpo["favorito"],
         limpo["horas"], limpo["observacoes"], limpo["shop"], limpo["object_id"],
         limpo["origem"], limpo["game_code"], limpo["regiao"], agora_iso(), gid),
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
    if (item.get("origem") or "") == "steam-manifest":
        score += 0.1
        motivos.append("manifesto Steam")
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
                    mn = ACF_NAME_RE.search(txt)
                    md = ACF_DIR_RE.search(txt)
                    nome = mn.group(1).strip() if mn else None
                    if not nome or "Steam" in nome and "Runtime" in nome:
                        continue
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
                    registrar({
                        "titulo": nome, "executable_path": exe,
                        "shop": "steam", "object_id": "",
                        "horas": 0.0, "origem": "steam-manifest",
                    })
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


def _titulo_de_rom(p: Path) -> str:
    nome = p.stem.replace("_", " ").replace(".", " ").replace("-", " ").strip()
    return re.sub(r"\s+", " ", nome) or p.stem


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
                    achados[chave] = item
    return _final()


def preview_roms(roots: list[str] | None = None,
                 emu_exe: str | None = None) -> tuple[list[str], list[dict], dict, str]:
    """(raízes, itens pontuados, info, emu_usado)."""
    roots = roots or default_roms_roots()
    emu = emu_exe if emu_exe is not None else default_emu_3ds()
    achados, info = scan_roms(roots, emu_exe=emu, retornar_info=True)
    return roots, [pontuar(j) for j in achados], info, emu


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
            if e[:8].rstrip(b"\x00") == b"icon.bin":
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
                    game_code, regiao, confianca, criado_em, atualizado_em)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (titulo, (j.get("executable_path") or "").strip(),
                 (j.get("exe_win") or "").strip(), (j.get("exe_linux") or "").strip(),
                 (j.get("wine_prefix") or ""), (j.get("launch_options") or ""),
                 j.get("status") if j.get("status") in STATUS_VALIDOS else "backlog",
                 nota, 1 if j.get("favorito") else 0,
                 horas, (j.get("observacoes") or ""),
                 j.get("origem") or "manual", (j.get("shop") or ""),
                 (j.get("object_id") or ""), (j.get("game_code") or "").strip(),
                 (j.get("regiao") or "").strip(), confianca,
                 agora, agora),
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
        rows = con.execute("SELECT * FROM jogos ORDER BY id").fetchall()
        dados = {"exportado_em": agora_iso(), "jogos": [row_to_dict(r) for r in rows]}
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
    st = azahar_status()
    ud = st.get("user_dir") or ""
    if not ud:
        return {"ok": False, "erro": "Azahar não instalado"}
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"azahar-saves-{ts}.zip"
    n = 0
    try:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for sub in ("sdmc", "states"):
                d = Path(ud) / sub
                if not d.is_dir():
                    continue
                for f in sorted(d.rglob("*")):
                    if f.is_file():
                        try:
                            z.write(f, f.relative_to(ud))
                            n += 1
                        except OSError:
                            continue
    except Exception as e:
        try:
            dest.unlink()
        except OSError:
            pass
        return {"ok": False, "erro": f"backup de saves falhou: {e}"}
    if n == 0:
        try:
            dest.unlink()
        except OSError:
            pass
        return {"ok": False, "erro": "sem saves ainda (sdmc/ vazio ou ausente)"}
    for padrao in ("azahar-saves-*.zip",):
        arqs = sorted(BACKUP_DIR.glob(padrao), key=lambda p: p.name, reverse=True)
        for velho in arqs[manter:]:
            try:
                velho.unlink()
            except OSError:
                pass
    return {"ok": True, "arquivo": str(dest), "arquivos": n}


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


def executar_jogo(executable_path: str, wine_prefix: str = "", launch_options: str = "",
                  elevar: bool = False) -> dict:
    exe = (executable_path or "").strip()
    if not exe:
        return {"ok": False, "erro": "Jogo sem caminho de executável cadastrado."}
    if elevar:
        return executar_elevado(exe, launch_options)
    exe = traduzir_para_atual(exe)  # gravado num SO, executando no outro
    p = Path(exe)
    if not p.exists():
        return {"ok": False, "erro": f"Executável não encontrado: {exe}"}

    env = os.environ.copy()
    if wine_prefix.strip():
        env["WINEPREFIX"] = wine_prefix.strip()

    extra = shlex.split(launch_options, posix=(os.name != "nt")) if launch_options.strip() else []

    try:
        cwd = str(p.parent) if p.parent.exists() else None
        if os.name == "nt":
            ext = p.suffix.lower()
            if ext in (".lnk", ".url") or p.is_dir():
                os.startfile(str(p))  # type: ignore[attr-defined]
                return {"ok": True, "modo": "startfile"}
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            subprocess.Popen([str(p), *extra], cwd=cwd, env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, creationflags=creationflags,
                             close_fds=True)
            return {"ok": True, "modo": "popen-windows"}
        else:
            if not os.access(str(p), os.X_OK):
                return {"ok": False,
                        "erro": f"Sem permissão de execução: {exe} (rode chmod +x?)"}
            cmd = [str(p), *extra]
            subprocess.Popen(cmd, cwd=cwd, env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, start_new_session=True,
                             close_fds=True)
            return {"ok": True, "modo": "popen-linux"}
    except Exception as e:
        if _eh_elevacao_necessaria(e):
            return {"ok": False, "requer_elevacao": True,
                    "erro": f"{type(e).__name__}: {e} — o executável exige administrador."}
        return {"ok": False, "erro": f"{type(e).__name__}: {e}"}


def executar_jogo_dict(jogo: dict, elevar: bool = False) -> dict:
    """Resolve o exe do SO atual (exe_win/exe_linux vencem) e executa."""
    exe, _origem = resolver_exe(jogo)
    if not exe and (jogo.get("origem") or "") == "rom-3ds":
        return {"ok": False, "erro": ("Azahar não encontrado — instale em "
                                      "Games/Emuladores/Azahar ou defina BIBLIOTECA_EMULADOR_3DS.")}
    launch = (jogo.get("launch_options") or "")
    if (jogo.get("origem") or "") == "rom-3ds" and launch.strip():
        rom = launch.strip()
        if " " in rom and not (rom.startswith('"') and rom.endswith('"')):
            rom = f'"{rom}"'
        flags = " ".join(azahar_flags())
        launch = (flags + " " if flags else "") + rom
    return executar_jogo(exe, (jogo.get("wine_prefix") or ""), launch, elevar=elevar)


def azahar_flags() -> list[str]:
    """Flags extras ao bootar ROM (padrão -f fullscreen; vazio desliga)."""
    return shlex.split(os.environ.get("BIBLIOTECA_AZAHAR_FLAGS", "-f"),
                       posix=(os.name != "nt"))


def marcar_execucao(con: sqlite3.Connection, gid: int) -> None:
    agora = agora_iso()
    con.execute("UPDATE jogos SET ultima_execucao=?, atualizado_em=? WHERE id=?",
                (agora, agora, gid))
    con.commit()
