"""Metadados de jogo vindos dos provedores (descrição, arte, HLTB, RetroAchievements).

Uma linha por `uuid` do jogo em `jogos_meta`: ids externos em colunas e o resto
em JSON (`dados`). Campos editados à mão entram em `travado` e nenhum provedor
os sobrescreve depois. Só leitura/escrita local — rede fica em `rede.provedores`.
"""
from __future__ import annotations

import json
import sqlite3

from bib_nucleo.base import agora_iso

SCHEMA_META = """
CREATE TABLE IF NOT EXISTS jogos_meta (
    uuid TEXT PRIMARY KEY,
    steam_appid TEXT DEFAULT '',
    sgdb_id TEXT DEFAULT '',
    retro_id TEXT DEFAULT '',
    dados TEXT NOT NULL DEFAULT '{}',
    atualizado_em TEXT
);
"""

IDS = ("steam_appid", "sgdb_id", "retro_id")

# Campos de `dados` e o tipo esperado (o resto é descartado ao gravar).
CAMPOS: dict[str, type | tuple[type, ...]] = {
    "descricao": str,
    "resumo": str,
    "generos": list,
    "desenvolvedora": str,
    "publicadora": str,
    "lancamento": str,
    "site": str,
    "hero": str,
    "logo": str,
    "icone": str,
    "screenshots": list,
    "hltb": dict,
    "retro": dict,
    "fontes": dict,
    "travado": list,
}

EDITAVEIS = ("descricao", "generos", "desenvolvedora", "publicadora", "lancamento",
             "site", "steam_appid", "sgdb_id", "retro_id")


def garantir_tabela_meta(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA_META)


def _vazio(uuid: str) -> dict:
    return {"uuid": uuid, **{k: "" for k in IDS}, "fontes": {}, "travado": [],
            "atualizado_em": None}


def ler_meta(con: sqlite3.Connection, uuid: str) -> dict:
    """Metadados do jogo (dicionário plano); vazio quando ainda não há nada."""
    garantir_tabela_meta(con)
    row = con.execute("SELECT * FROM jogos_meta WHERE uuid=?", (str(uuid),)).fetchone()
    if row is None:
        return _vazio(str(uuid))
    try:
        dados = json.loads(row["dados"] or "{}")
    except (TypeError, ValueError):
        dados = {}
    saida = _vazio(str(uuid))
    saida.update({k: v for k, v in dados.items() if k in CAMPOS and isinstance(v, CAMPOS[k])})
    saida.update({k: str(row[k] or "") for k in IDS})
    saida["atualizado_em"] = row["atualizado_em"]
    return saida


def _escrever(con: sqlite3.Connection, uuid: str, atual: dict) -> dict:
    dados = {k: atual[k] for k in CAMPOS if k in atual}
    con.execute(
        "INSERT INTO jogos_meta(uuid, steam_appid, sgdb_id, retro_id, dados, atualizado_em) "
        "VALUES (?,?,?,?,?,?) ON CONFLICT(uuid) DO UPDATE SET steam_appid=excluded.steam_appid, "
        "sgdb_id=excluded.sgdb_id, retro_id=excluded.retro_id, dados=excluded.dados, "
        "atualizado_em=excluded.atualizado_em",
        (str(uuid), atual["steam_appid"], atual["sgdb_id"], atual["retro_id"],
         json.dumps(dados, ensure_ascii=False), agora_iso()))
    con.commit()
    return ler_meta(con, uuid)


def gravar_meta(con: sqlite3.Connection, uuid: str, novos: dict, *, respeitar_trava=True,
                fonte: str = "", travar=()) -> dict:
    """Mescla `novos` no que já existe. Campos travados não mudam (salvo
    `respeitar_trava=False`, usado pela edição manual). Valores vazios não
    apagam o que um provedor já trouxe."""
    if not uuid:
        raise ValueError("Jogo sem identidade (uuid); abra a biblioteca de novo.")
    atual = ler_meta(con, uuid)
    travados = set(atual.get("travado") or [])
    for chave, valor in (novos or {}).items():
        if chave in ("uuid", "atualizado_em", "travado"):
            continue
        if respeitar_trava and chave in travados:
            continue
        if chave in IDS:
            valor = str(valor or "").strip()
            if valor:
                atual[chave] = valor
            continue
        tipo = CAMPOS.get(chave)
        if tipo is None or not isinstance(valor, tipo):
            continue
        if chave == "fontes":
            atual["fontes"] = {**(atual.get("fontes") or {}), **valor}
            continue
        if valor in ("", [], {}) and respeitar_trava:
            continue
        atual[chave] = valor
    if travar:
        atual["travado"] = sorted(travados | set(travar))
    if fonte:
        atual["fontes"] = {**(atual.get("fontes") or {}), fonte: agora_iso()}
    return _escrever(con, uuid, atual)


def salvar_edicao(con: sqlite3.Connection, uuid: str, campos: dict) -> dict:
    """Edição manual: grava e trava cada campo informado (vazio destrava e limpa)."""
    atual = ler_meta(con, uuid)
    travado = set(atual.get("travado") or [])
    limpos = {}
    for chave, valor in (campos or {}).items():
        if chave not in EDITAVEIS:
            raise ValueError(f"Campo não editável: {chave}")
        if chave == "generos":
            if isinstance(valor, str):
                valor = [g.strip() for g in valor.split(",") if g.strip()]
            if not isinstance(valor, list) or not all(isinstance(g, str) for g in valor):
                raise ValueError("generos deve ser uma lista de textos")
            valor = [g[:40] for g in valor][:12]
        elif not isinstance(valor, str):
            raise ValueError(f"{chave} deve ser um texto")
        else:
            valor = valor.strip()[:4000 if chave == "descricao" else 200]
        if chave in ("steam_appid", "retro_id", "sgdb_id") and valor and not valor.isdigit():
            raise ValueError(f"{chave} deve conter só dígitos")
        vazio = valor in ("", [])
        if vazio:
            travado.discard(chave)
        else:
            travado.add(chave)
        limpos[chave] = valor
    atual.update(limpos)  # aqui vazio limpa de propósito (inclusive ids)
    atual["travado"] = sorted(travado)
    return _escrever(con, uuid, atual)


def uuids_sem_meta(con: sqlite3.Connection) -> list[tuple[int, str]]:
    """(id, uuid) dos jogos que nunca passaram por um provedor."""
    garantir_tabela_meta(con)
    return [(r[0], r[1]) for r in con.execute(
        "SELECT j.id, j.uuid FROM jogos j LEFT JOIN jogos_meta m ON m.uuid = j.uuid "
        "WHERE j.uuid <> '' AND (m.uuid IS NULL OR json_extract(m.dados, '$.fontes') IS NULL "
        "OR json_extract(m.dados, '$.fontes') = '{}') "
        "ORDER BY j.titulo COLLATE NOCASE")]


ARTE_LOCAL = ("hero", "logo", "icone", "screenshots")


def exportar_meta(con: sqlite3.Connection) -> list[dict]:
    """Para o pacote: tudo menos os caminhos de arte (são locais desta máquina)."""
    garantir_tabela_meta(con)
    saida = []
    for (uuid,) in con.execute("SELECT uuid FROM jogos_meta ORDER BY uuid").fetchall():
        m = ler_meta(con, uuid)
        saida.append({k: v for k, v in m.items() if k not in ARTE_LOCAL and k != "atualizado_em"})
    return saida


def importar_meta(con: sqlite3.Connection, lista) -> int:
    """Aplica metadados do pacote aos jogos que existem (por uuid); campos
    travados no pacote continuam travados. Devolve quantos jogos receberam."""
    vivos = {r[0] for r in con.execute("SELECT uuid FROM jogos WHERE uuid <> ''")}
    n = 0
    for item in lista if isinstance(lista, list) else []:
        if not isinstance(item, dict) or item.get("uuid") not in vivos:
            continue
        campos = {k: v for k, v in item.items() if k not in ARTE_LOCAL and k not in ("uuid", "travado")}
        travado = [t for t in item.get("travado") or [] if isinstance(t, str) and t not in ARTE_LOCAL]
        gravar_meta(con, item["uuid"], campos, travar=travado)
        n += 1
    return n


__all__ = ["exportar_meta", "importar_meta", "SCHEMA_META", "CAMPOS", "EDITAVEIS", "garantir_tabela_meta", "ler_meta",
           "gravar_meta", "salvar_edicao", "uuids_sem_meta"]
