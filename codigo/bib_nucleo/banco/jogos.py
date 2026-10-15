#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Catálogo de jogos: validação, CRUD, etiquetas, mods, capas e horas."""
from __future__ import annotations

import base64
import math
import re
import sqlite3
import uuid as uuid_mod
from pathlib import Path

from bib_nucleo.banco._infra import _termo_fts
from bib_nucleo.base import (
    CAPAS_DIR,
    _desaspas,
    _txt,
    agora_iso,
    existe_aqui_ou_traduzido,
    mac_para_linux,
    resolver_exe,
    slugify,
    win_para_linux,
)

STATUS_VALIDOS = ("backlog", "jogando", "zerado", "pausado", "abandonado")

CAMPOS_EDITAVEIS = ("titulo", "executable_path", "exe_win", "exe_linux",
                    "exe_mac",
                    "wine_prefix", "launch_options", "status", "nota", "favorito",
                    "horas", "observacoes", "shop", "object_id", "origem",
                    "game_code", "regiao", "azahar_preset", "etiquetas",
                    "save_path", "azahar_mods", "azahar_mods_off")

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
    fallback = False
    if q:
        termo = _termo_fts(q)
        ids = None
        if termo:
            try:
                ids = [r[0] for r in con.execute(
                    "SELECT rowid FROM jogos_fts WHERE jogos_fts MATCH ?",
                    (termo,)).fetchall()]
            except sqlite3.Error:
                ids = None  # FTS5 ausente/consult falhou: cai no LIKE abaixo
        if ids is not None:
            if not ids:
                return []
            sql += f" AND id IN ({','.join('?' * len(ids))})"
            params += ids
        else:
            fallback = True  # substring sem acento; não interpreta sintaxe SQL
    if status:
        sql += " AND status = ?"
        params.append(status)
    if favorito:
        sql += " AND favorito = 1"
    sql += " ORDER BY favorito DESC, titulo COLLATE NOCASE"
    jogos = [row_to_dict(r) for r in con.execute(sql, params).fetchall()]
    if fallback:
        import unicodedata
        def sem_acento(texto):
            return "".join(c for c in unicodedata.normalize("NFD", str(texto).casefold())
                           if unicodedata.category(c) != "Mn")
        termos = sem_acento(q).split()
        jogos = [j for j in jogos if all(t in sem_acento(" ".join(
            str(j.get(k) or "") for k in ("titulo", "etiquetas", "executable_path"))) for t in termos)]
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
    from PIL import ImageFilter
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

def selo_confianca(j: dict) -> str:
    """' · ◎0.85' se o jogo tem confiança de importação, senão ''."""
    try:
        conf = float((j or {}).get("confianca") or 0)
    except (TypeError, ValueError):
        return ""
    return f" · ◎{conf:.2f}" if conf > 0 else ""
