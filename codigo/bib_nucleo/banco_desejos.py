"""Persistência da wishlist local; contrato público reexportado por banco.py."""
from __future__ import annotations

import sqlite3
from bib_nucleo.base import _txt, agora_iso

SCHEMA_DESEJOS = """
CREATE TABLE IF NOT EXISTS desejos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appid TEXT NOT NULL,
    titulo TEXT NOT NULL,
    ordem INTEGER DEFAULT 0,
    manual INTEGER DEFAULT 0,
    obtido_em TEXT,
    criado_em TEXT,
    atualizado_em TEXT,
    UNIQUE(appid)
);
"""


def _garantir_coluna_desejo_manual(con):
    cols = {r["name"] for r in con.execute("PRAGMA table_info(desejos)")}
    if cols and "manual" not in cols:
        con.execute("ALTER TABLE desejos ADD COLUMN manual INTEGER DEFAULT 0")


def _garantir_tabela_desejos(con):
    con.execute(SCHEMA_DESEJOS)
    _garantir_coluna_desejo_manual(con)
    cols = {r["name"] for r in con.execute("PRAGMA table_info(desejos)")}
    if "obtido_em" not in cols:
        con.execute("ALTER TABLE desejos ADD COLUMN obtido_em TEXT")


def desejo_to_dict(r):
    return dict(r)


def listar_desejos(con, q="", incluir_obtidos=False):
    q = (q or "").strip().lower()
    out = [desejo_to_dict(r) for r in con.execute("SELECT * FROM desejos ORDER BY ordem, titulo")]
    if not incluir_obtidos:
        out = [d for d in out if not d.get("obtido_em")]
    if q:
        out = [d for d in out if q in d["titulo"].lower()]
    return out


def sincronizar_desejos(con, itens):
    """Espelha sem apagar desejos manuais ou ressuscitar os já obtidos."""
    novos = atualizados = removidos = 0
    agora, vistos = agora_iso(), set()
    for pos, item in enumerate(itens or []):
        if not isinstance(item, dict):
            continue
        appid, titulo = str(item.get("appid") or "").strip(), _txt(item.get("titulo"))
        if not appid.isdigit() or not titulo or appid in vistos:
            continue
        vistos.add(appid)
        row = con.execute("SELECT * FROM desejos WHERE appid=?", (appid,)).fetchone()
        if row is None:
            con.execute("INSERT INTO desejos(appid,titulo,ordem,manual,criado_em,atualizado_em) VALUES(?,?,?,?,?,?)",
                        (appid, titulo, pos, 0, agora, agora))
            novos += 1
        elif row["titulo"] != titulo or row["ordem"] != pos:
            con.execute("UPDATE desejos SET titulo=?,ordem=?,atualizado_em=? WHERE appid=?",
                        (titulo, pos, agora, appid))
            atualizados += 1
    for r in con.execute("SELECT appid,manual FROM desejos").fetchall():
        if r["appid"] not in vistos and not r["manual"]:
            removidos += con.execute("DELETE FROM desejos WHERE appid=? AND obtido_em IS NULL",
                                     (r["appid"],)).rowcount
    con.commit()
    return {"novos": novos, "atualizados": atualizados, "removidos": removidos}


def adicionar_desejo(con, appid, titulo):
    """Retorna resultado da operação, não uma linha; ID vem de listar_desejos."""
    appid, titulo = str(appid or "").strip(), _txt(titulo)
    if not appid.isdigit() or not titulo:
        raise ValueError("appid e título são obrigatórios")
    agora = agora_iso()
    row = con.execute("SELECT * FROM desejos WHERE appid=?", (appid,)).fetchone()
    if row is None:
        try:
            pos = con.execute("SELECT COALESCE(MAX(ordem),-1)+1 AS p FROM desejos").fetchone()["p"]
        except (sqlite3.Error, TypeError, KeyError):
            pos = 0
        con.execute("INSERT INTO desejos(appid,titulo,ordem,manual,criado_em,atualizado_em) VALUES(?,?,?,?,?,?)",
                    (appid, titulo, pos, 1, agora, agora))
    else:
        con.execute("UPDATE desejos SET titulo=?,manual=1,atualizado_em=? WHERE appid=?",
                    (titulo, agora, appid))
    con.commit()
    return {"ok": True, "novo": row is None}


def marcar_desejo_obtido(con, did):
    con.execute("UPDATE desejos SET obtido_em=?,atualizado_em=? WHERE id=?",
                (agora_iso(), agora_iso(), int(did)))
    con.commit()


def remover_desejo(con, did):
    if not con.execute("SELECT id FROM desejos WHERE id=?", (did,)).fetchone():
        raise LookupError("desejo não encontrado")
    con.execute("DELETE FROM desejos WHERE id=?", (did,))
    con.commit()
