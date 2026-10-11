"""FTS5 em jogos: busca sem acento, prefixo, sincronia e fallback."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from executar import afirmar


def _con():
    from bib_nucleo import banco as B
    tmp = Path(tempfile.mkdtemp(prefix="suite-fts-"))
    db = tmp / "biblioteca.db"
    con = B.get_db(db)
    return con, B, db


def teste_fts5_busca_sem_acento_e_prefixo():
    con, B, _db = _con()
    try:
        B.criar_jogo(con, {"titulo": "Pokémon X"})
        B.criar_jogo(con, {"titulo": "Zelda: Ocarina of Time"})
        B.criar_jogo(con, {"titulo": "Chrono Trigger"})
        con.commit()

        # sem acento acha o que tem acento (remove_diacritics 2)
        r = B.listar_jogos(con, q="pokemon")
        afirmar([j["titulo"] for j in r] == ["Pokémon X"], r)

        # prefixo
        r = B.listar_jogos(con, q="ocar")
        afirmar([j["titulo"] for j in r] == ["Zelda: Ocarina of Time"], r)

        # nada encontrado
        r = B.listar_jogos(con, q="final fantasy xyz")
        afirmar(r == [], r)

        # etiquetas entram no índice
        B.atualizar_jogo(con, 3, {"etiquetas": "rpg, snk"})
        con.commit()
        r = B.listar_jogos(con, q="snk")
        afirmar([j["titulo"] for j in r] == ["Chrono Trigger"], r)
    finally:
        con.close()


def teste_fts5_sincroniza_insert_update_delete():
    con, B, _db = _con()
    try:
        a = B.criar_jogo(con, {"titulo": "Hollow Knight"})["id"]
        b = B.criar_jogo(con, {"titulo": "Silksong"})["id"]
        con.commit()
        afirmar([j["titulo"] for j in B.listar_jogos(con, q="silksong")] == ["Silksong"])

        B.atualizar_jogo(con, a, {"titulo": "Hollow Knight: Silksong"})
        con.commit()
        r = {j["titulo"] for j in B.listar_jogos(con, q="silksong")}
        afirmar(r == {"Hollow Knight: Silksong", "Silksong"}, r)

        B.excluir_jogo(con, b)
        con.commit()
        afirmar([j["titulo"] for j in B.listar_jogos(con, q="silksong")] == ["Hollow Knight: Silksong"])
    finally:
        con.close()


def teste_fts5_indisponivel_cai_no_like():
    """Sem FTS5 a busca continua funcionando pelo caminho antigo."""
    con, B, db = _con()
    try:
        B.criar_jogo(con, {"titulo": "Metroid Prime"})
        con.commit()
        # remove o índice: qualquer consulta MATCH passa a falhar
        con.execute("DROP TABLE jogos_fts")
        con.commit()
        r = B.listar_jogos(con, q="Metroid")
        afirmar([j["titulo"] for j in r] == ["Metroid Prime"], r)
    finally:
        con.close()


def teste_fts5_termo_estranho_nao_quebra():
    con, B, _db = _con()
    try:
        B.criar_jogo(con, {"titulo": 'Jogo "estranho" (2024)'})
        con.commit()
        for termo in ('"', '(', ')', '*', 'NEAR', 'and or', 'a"b'):
            r = B.listar_jogos(con, q=termo)
            afirmar(isinstance(r, list), (termo, r))
        r = B.listar_jogos(con, q="estranho")
        afirmar([j["titulo"] for j in r] == ['Jogo "estranho" (2024)'], r)
    finally:
        con.close()


def teste_fts5_abertura_nao_reconstroi_e_recupera_trigger_ausente():
    con, B, db = _con()
    try:
        B.criar_jogo(con, {"titulo": "Pokémon Azul"})
        trace = []
        con.set_trace_callback(trace.append)
        afirmar(B.garantir_fts(con))
        afirmar(not any("rebuild" in s.lower() for s in trace), trace)
        con.execute("DROP TRIGGER jogos_fts_ai")
        con.execute("INSERT INTO jogos(titulo,etiquetas) VALUES('Título atrasado','aventura')")
        con.commit()
        trace.clear()
        afirmar(B.garantir_fts(con))
        afirmar(any("rebuild" in s.lower() for s in trace), trace)
        afirmar(len(B.listar_jogos(con, q="aventura atras")) == 1)
        con.execute("DROP TABLE jogos_fts")
        con.commit()
        afirmar([j["titulo"] for j in B.listar_jogos(con, q="azul pokemon")] == ["Pokémon Azul"])
    finally:
        con.close()
