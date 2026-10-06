"""Fila CSV → mp3: parser Exportify, dedup da fila, estados v14 (sem rede)."""
import tempfile
from pathlib import Path

import bib_core as core
from executar import afirmar

CAB = ("Track URI,ISRC,Track Name,Album Name,Artist Name(s),Release Date,"
       "Duration (ms),Popularity\n")


def _csv(tmp, linhas, nome="pl.csv"):
    p = Path(tmp) / nome
    p.write_text(CAB + "".join(linhas), encoding="utf-8")
    return p


def teste_baixar_parser_e_primeiro_artista():
    from bib_nucleo import baixar as BX
    afirmar(BX.primeiro_artista("Chico Buarque;MPB4") == "Chico Buarque")
    afirmar(BX.primeiro_artista("Solo") == "Solo")
    afirmar(BX.primeiro_artista("") == "")
    tmp = Path(tempfile.mkdtemp(prefix="suite-bx-"))
    p = _csv(tmp, [
        'spotify:track:1,x,"Cotidiano","Construção","Chico Buarque",1971,1,1\n',
        'spotify:track:2,x,"Apesar De Você","Chico Buarque","Chico Buarque;MPB4",1978,1,1\n',
        'spotify:track:3,x,"","Sem Titulo","Anon",2000,1,1\n',
        'spotify:track:4,x,"A, Vida","Album X","Y",2001,1,1\n',
    ])
    r = BX.ler_csv_exportify(p)
    afirmar(r["erros"] == [], r)
    afirmar(r["ignorados"] == 1, r)
    afirmar(len(r["itens"]) == 3, r)
    afirmar(r["itens"][1]["artista"] == "Chico Buarque", r)
    afirmar(r["itens"][2]["titulo"] == "A, Vida", r)
    ruim = tmp / "nada.csv"
    ruim.write_text("a,b\n1,2\n", encoding="utf-8")
    r = BX.ler_csv_exportify(ruim)
    afirmar(r["itens"] == [] and r["erros"], r)
    r = BX.ler_csv_exportify(tmp / "sumiu.csv")
    afirmar(r["itens"] == [] and r["erros"], r)


def teste_baixar_fila_dedup_e_estados():
    from bib_nucleo import baixar as BX
    tmp = Path(tempfile.mkdtemp(prefix="suite-bx-"))
    con = core.get_db(tmp / "b.db")
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(downloads)").fetchall()}
        afirmar({"titulo", "uri", "estado", "video_id"} <= cols, sorted(cols))
        p = _csv(tmp, [
            'spotify:track:1,x,"Cotidiano","Construção","Chico Buarque",1971,1,1\n',
            'spotify:track:1,x,"Cotidiano","Construção","Chico Buarque",1971,1,1\n',
            'spotify:track:9,x,"COTIDIANO","Outro","CHICO BUARQUE",1971,1,1\n',
        ])
        r = BX.ler_csv_exportify(p)
        q = core.enfileirar_downloads(con, r["itens"])
        afirmar(q == {"novos": 1, "ignorados": 2, "erros": []}, (r, q))
        q = core.enfileirar_downloads(con, [{"titulo": "", "artista": "X"}])
        afirmar(q["novos"] == 0 and q["ignorados"] == 1, q)
        # faixa que o Hub já tem não entra na fila
        core.criar_musica(con, {"titulo": "Cotidiano", "artista": "Chico Buarque",
                                "musica_sha": "s" * 64})
        q = core.enfileirar_downloads(
            con, [{"titulo": "Cotidiano", "artista": "Chico Buarque",
                   "uri": "spotify:track:7"}])
        afirmar(q["novos"] == 0 and q["ignorados"] == 1, q)
        pand = core.listar_downloads(con, estado="pendente")
        afirmar(len(pand) == 1, pand)
        did = pand[0]["id"]
        d = core.marcar_download(con, did, "baixando", video_id="abc123")
        afirmar(d["estado"] == "baixando" and d["video_id"] == "abc123", d)
        d = core.marcar_download(con, did, "pronta", musica_sha="s" * 63 + "0")
        afirmar(d["estado"] == "pronta", d)
        afirmar(core.listar_downloads(con, estado="pronta")[0]["id"] == did)
        try:
            core.marcar_download(con, did, "voando")
            afirmar(False, "devia levantar")
        except ValueError:
            pass
        try:
            core.listar_downloads(con, estado="voando")
            afirmar(False, "devia levantar")
        except ValueError:
            pass
        try:
            core.marcar_download(con, 9999, "falha")
            afirmar(False, "devia levantar")
        except LookupError:
            pass
        afirmar(core.limpar_downloads(con) == 1)
        afirmar(core.listar_downloads(con) == [])
        try:
            core.limpar_downloads(con, estados=("pendente", "voando"))
            afirmar(False, "devia levantar")
        except ValueError:
            pass
    finally:
        con.close()


def teste_baixar_v14_idempotente():
    tmp = Path(tempfile.mkdtemp(prefix="suite-bx-"))
    con = core.get_db(tmp / "b.db")
    con.close()
    con = core.get_db(tmp / "b.db")  # reabre: migração não duplica nem perde
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(downloads)").fetchall()}
        afirmar("video_id" in cols, sorted(cols))
        afirmar(core.listar_downloads(con) == [])
    finally:
        con.close()
