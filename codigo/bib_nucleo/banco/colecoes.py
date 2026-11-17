"""Coleções de jogos (à la Hydra): listas com nome, ligadas aos jogos pelo `uuid`.

Pelo `uuid` (e não pelo `id`) a coleção sobrevive a exportar/importar e à
reconstrução da tabela de jogos. Um jogo pode estar em várias coleções.
"""
from __future__ import annotations

import sqlite3

from bib_nucleo.base import agora_iso

SCHEMA_COLECOES = """
CREATE TABLE IF NOT EXISTS colecoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE COLLATE NOCASE,
    ordem INTEGER DEFAULT 0,
    criada_em TEXT
);
CREATE TABLE IF NOT EXISTS colecao_jogos (
    colecao_id INTEGER NOT NULL,
    uuid TEXT NOT NULL,
    adicionado_em TEXT,
    PRIMARY KEY (colecao_id, uuid)
);
"""

LIMITE_NOME = 60


def garantir_tabelas_colecoes(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA_COLECOES)


def _nome(nome) -> str:
    nome = " ".join(str(nome or "").split())
    if not nome:
        raise ValueError("Dê um nome à coleção.")
    if len(nome) > LIMITE_NOME:
        raise ValueError(f"Nome de coleção com até {LIMITE_NOME} caracteres.")
    return nome


def _existe(con, cid: int) -> None:
    if con.execute("SELECT 1 FROM colecoes WHERE id=?", (int(cid),)).fetchone() is None:
        raise LookupError("A coleção não existe mais.")


def listar_colecoes(con: sqlite3.Connection) -> list[dict]:
    """[{id, nome, uuids}] em ordem de criação (uuids só de jogos que ainda existem)."""
    garantir_tabelas_colecoes(con)
    vivos = {r[0] for r in con.execute("SELECT uuid FROM jogos WHERE uuid <> ''")}
    saida = []
    for r in con.execute("SELECT id, nome FROM colecoes ORDER BY ordem, id"):
        uuids = [u[0] for u in con.execute(
            "SELECT uuid FROM colecao_jogos WHERE colecao_id=? ORDER BY adicionado_em, uuid", (r[0],))
            if u[0] in vivos]
        saida.append({"id": int(r[0]), "nome": str(r[1]), "uuids": uuids})
    return saida


def criar_colecao(con: sqlite3.Connection, nome) -> dict:
    garantir_tabelas_colecoes(con)
    nome = _nome(nome)
    try:
        cur = con.execute("INSERT INTO colecoes(nome, ordem, criada_em) VALUES (?, "
                          "(SELECT COALESCE(MAX(ordem), 0) + 1 FROM colecoes), ?)", (nome, agora_iso()))
    except sqlite3.IntegrityError:
        raise ValueError(f"Já existe uma coleção chamada {nome}.") from None
    con.commit()
    return {"id": int(cur.lastrowid), "nome": nome, "uuids": []}


def renomear_colecao(con: sqlite3.Connection, cid: int, nome) -> None:
    garantir_tabelas_colecoes(con)
    _existe(con, cid)
    nome = _nome(nome)
    try:
        con.execute("UPDATE colecoes SET nome=? WHERE id=?", (nome, int(cid)))
    except sqlite3.IntegrityError:
        raise ValueError(f"Já existe uma coleção chamada {nome}.") from None
    con.commit()


def apagar_colecao(con: sqlite3.Connection, cid: int) -> None:
    """Apaga a lista; os jogos continuam na biblioteca."""
    garantir_tabelas_colecoes(con)
    _existe(con, cid)
    con.execute("DELETE FROM colecao_jogos WHERE colecao_id=?", (int(cid),))
    con.execute("DELETE FROM colecoes WHERE id=?", (int(cid),))
    con.commit()


def definir_membro(con: sqlite3.Connection, cid: int, uuid: str, dentro: bool) -> None:
    garantir_tabelas_colecoes(con)
    _existe(con, cid)
    if not uuid:
        raise ValueError("Jogo sem identidade (uuid).")
    if dentro:
        con.execute("INSERT OR IGNORE INTO colecao_jogos(colecao_id, uuid, adicionado_em) VALUES (?,?,?)",
                    (int(cid), str(uuid), agora_iso()))
    else:
        con.execute("DELETE FROM colecao_jogos WHERE colecao_id=? AND uuid=?", (int(cid), str(uuid)))
    con.commit()


def colecoes_do_jogo(con: sqlite3.Connection, uuid: str) -> list[dict]:
    """Todas as coleções com `tem` = o jogo está nela."""
    garantir_tabelas_colecoes(con)
    dentro = {r[0] for r in con.execute("SELECT colecao_id FROM colecao_jogos WHERE uuid=?", (str(uuid),))}
    return [{"id": int(r[0]), "nome": str(r[1]), "tem": int(r[0]) in dentro}
            for r in con.execute("SELECT id, nome FROM colecoes ORDER BY ordem, id")]


def exportar_colecoes(con: sqlite3.Connection) -> list[dict]:
    """Formato do pacote: [{nome, uuids}] (ids locais não viajam)."""
    return [{"nome": c["nome"], "uuids": c["uuids"]} for c in listar_colecoes(con)]


def importar_colecoes(con: sqlite3.Connection, lista) -> int:
    """Junta coleções do pacote (por nome) às existentes. Devolve quantos vínculos novos."""
    garantir_tabelas_colecoes(con)
    novos = 0
    for item in lista if isinstance(lista, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            nome = _nome(item.get("nome"))
        except ValueError:
            continue
        row = con.execute("SELECT id FROM colecoes WHERE nome=?", (nome,)).fetchone()
        cid = int(row[0]) if row else criar_colecao(con, nome)["id"]
        for uuid in item.get("uuids") or []:
            if isinstance(uuid, str) and uuid.strip():
                cur = con.execute("INSERT OR IGNORE INTO colecao_jogos(colecao_id, uuid, adicionado_em) "
                                  "VALUES (?,?,?)", (cid, uuid.strip(), agora_iso()))
                novos += cur.rowcount
    con.commit()
    return novos


__all__ = ["SCHEMA_COLECOES", "garantir_tabelas_colecoes", "listar_colecoes", "criar_colecao",
           "renomear_colecao", "apagar_colecao", "definir_membro", "colecoes_do_jogo",
           "exportar_colecoes", "importar_colecoes"]
