"""Coleções, catálogo da loja Steam e lojas instaladas (1.4.3) — sem rede real."""
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from bib_nucleo import banco, pacotes, scans
from bib_nucleo.rede import online
from executar import afirmar
from ponte import Ponte, Trabalhos
from servicos_ui import ServicoBiblioteca


def _banco(*titulos):
    db = Path(tempfile.mkdtemp(prefix="suite-col-")) / "hub.db"
    con = banco.get_db(db)
    ids = [banco.criar_jogo(con, {"titulo": t, "executable_path": f"C:/jogos/{t}.exe"})["id"] for t in titulos]
    con.commit()
    return db, con, ids


def _ponte(db):
    eventos = []
    ponte = Ponte(ServicoBiblioteca(db), trabalhos=Trabalhos(eventos.append))

    def chamar(metodo, **params):
        return json.loads(ponte.executar_linha(json.dumps({"id": 1, "metodo": metodo, "params": params})))
    return chamar, eventos


def teste_colecoes_crud_membros_e_revisao():
    from bib_nucleo.banco import colecoes as C
    from bib_nucleo.banco._infra import ler_revisoes
    db, con, ids = _banco("Hades", "Celeste")
    try:
        antes = ler_revisoes(con)["colecoes"]
        c = C.criar_colecao(con, "  Zerar   em 2026 ")
        afirmar(c["nome"] == "Zerar em 2026", c)
        for ruim in ("", "x" * 61, "zerar EM 2026"):
            try:
                C.criar_colecao(con, ruim)
            except ValueError:
                continue
            afirmar(False, f"aceitou {ruim!r}")
        uuid = con.execute("SELECT uuid FROM jogos WHERE id=?", (ids[0],)).fetchone()[0]
        C.definir_membro(con, c["id"], uuid, True)
        C.definir_membro(con, c["id"], uuid, True)  # repetir não duplica
        afirmar(C.listar_colecoes(con)[0]["uuids"] == [uuid])
        afirmar([x["tem"] for x in C.colecoes_do_jogo(con, uuid)] == [True])
        afirmar(ler_revisoes(con)["colecoes"] > antes, "coleção deveria subir o contador")
        con.execute("DELETE FROM jogos WHERE id=?", (ids[0],))
        con.commit()
        afirmar(C.listar_colecoes(con)[0]["uuids"] == [], "jogo apagado some da coleção")
        C.renomear_colecao(con, c["id"], "Favoritos da Isa")
        C.apagar_colecao(con, c["id"])
        afirmar(C.listar_colecoes(con) == [])
        try:
            C.apagar_colecao(con, c["id"])
            afirmar(False, "apagar duas vezes")
        except LookupError:
            pass
    finally:
        con.close()


def teste_ponte_colecoes_e_snapshot():
    db, con, ids = _banco("Hades", "Celeste")
    con.close()
    chamar, _ = _ponte(db)
    c = chamar("colecoes.criar", nome="Roguelikes")["resultado"]
    r = chamar("colecoes.definir", colecao=c["id"], jogo=ids[0], dentro=True)
    afirmar(r["ok"] and r["resultado"] == [{"id": c["id"], "nome": "Roguelikes", "tem": True}], r)
    snap = chamar("nucleo.snapshot", partes=["colecoes"])["resultado"]
    afirmar(set(snap) == {"colecoes", "sistema"} and len(snap["colecoes"][0]["uuids"]) == 1, snap)
    afirmar(chamar("colecoes.criar", nome="roguelikes")["ok"] is False, "nome repetido")
    afirmar(chamar("colecoes.definir", colecao=c["id"], jogo=ids[0], dentro="sim")["ok"] is False)
    afirmar(chamar("colecoes.apagar", id=999)["ok"] is False)


def teste_pacote_leva_colecoes_e_metadados():
    from bib_nucleo.banco import colecoes as C
    from bib_nucleo.banco import meta
    db, con, ids = _banco("Hades")
    uuid = con.execute("SELECT uuid FROM jogos").fetchone()[0]
    c = C.criar_colecao(con, "Zerados")
    C.definir_membro(con, c["id"], uuid, True)
    meta.gravar_meta(con, uuid, {"descricao": "da loja", "hero": "C:/local/hero.jpg"}, fonte="steam")
    meta.salvar_edicao(con, uuid, {"desenvolvedora": "Supergiant"})
    con.close()
    pacote = db.parent / "colecao.zip"
    r = pacotes.exportar_pacote(pacote, db, incluir_saves=False)
    afirmar(r.get("ok"), r)
    novo = db.parent / "novo" / "hub.db"
    novo.parent.mkdir()
    r = pacotes.importar_pacote(pacote, novo)
    afirmar(r.get("ok") and r.get("colecoes") == 1 and r.get("jogos_meta") == 1, r)
    con = banco.get_db(novo)
    try:
        afirmar(C.listar_colecoes(con) == [{"id": 1, "nome": "Zerados", "uuids": [uuid]}], C.listar_colecoes(con))
        m = meta.ler_meta(con, uuid)
        afirmar(m["descricao"] == "da loja" and m["desenvolvedora"] == "Supergiant", m)
        afirmar("desenvolvedora" in m["travado"] and "hero" not in m, "caminho local de arte não viaja")
    finally:
        con.close()


APPS = {"367520": {"success": True, "data": {
    "name": "Hollow Knight", "type": "game", "short_description": "Insetos.", "about_the_game": "<p>Texto</p>",
    "genres": [{"description": "Ação"}], "developers": ["Team Cherry"], "publishers": ["Team Cherry"],
    "release_date": {"date": "24 fev. 2017"}, "screenshots": [{"path_thumbnail": "https://cdn.example/1.jpg"}],
    "price_overview": {"currency": "BRL", "initial": 4699, "final": 2349, "discount_percent": 50}}}}
DESTAQUES = {"specials": {"items": [
    {"id": 367520, "name": "Hollow Knight", "final_price": 2349, "original_price": 4699, "discount_percent": 50,
     "currency": "BRL", "large_capsule_image": "https://cdn.example/hk.jpg"},
    {"id": 367520, "name": "Hollow Knight"}, {"id": "x", "name": "inválido"}]},
    "top_sellers": {"items": [{"id": 620, "name": "Portal 2", "final_price": 0, "currency": "BRL"}]}}
BUSCA = {"items": [{"type": "app", "id": 367520, "name": "Hollow Knight", "price": {"currency": "BRL", "initial": 4699, "final": 4699}},
                   {"type": "sub", "id": 1, "name": "Pacote"}]}


def _responder(url, **_):
    if "featuredcategories" in url:
        return DESTAQUES
    if "storesearch" in url:
        return BUSCA
    return APPS


def teste_loja_destaques_busca_pagina_e_desejo():
    db, con, ids = _banco("Hollow Knight")
    con.execute("UPDATE jogos SET shop='steam', object_id='367520' WHERE id=?", (ids[0],))
    con.commit()
    con.close()
    chamar, _ = _ponte(db)
    with patch.object(online, "requisitar_json", side_effect=_responder) as req:
        d = chamar("loja.destaques")["resultado"]
        b = chamar("loja.buscar", termo="hollow")["resultado"]
        p = chamar("loja.pagina", appid="367520")["resultado"]
    afirmar(all("cc=BR" in c.args[0] and "l=brazilian" in c.args[0] for c in req.call_args_list
                if "appdetails" not in c.args[0]), req.call_args_list)
    especial = d[0]
    afirmar(especial["titulo"] == "Em promoção" and len(especial["itens"]) == 1, d)
    afirmar(especial["itens"][0]["preco"]["desconto_pct"] == 50 and especial["itens"][0]["na_biblioteca"] == ids[0], d)
    afirmar(d[1]["itens"][0]["preco"]["gratis"] is True, d[1])
    afirmar(len(b) == 1 and b[0]["imagem"].endswith("/367520/header.jpg"), b)
    afirmar(p["nome"] == "Hollow Knight" and p["preco"]["final"] == 2349 and p["descricao"] == "Texto", p)
    afirmar(p["na_biblioteca"] == ids[0] and p["nos_desejos"] is False, p)
    r = chamar("loja.desejar", appid="367520", titulo="Hollow Knight")
    afirmar(r["ok"], r)
    with patch.object(online, "requisitar_json", side_effect=_responder):
        afirmar(chamar("loja.pagina", appid="367520")["resultado"]["nos_desejos"] is True)
    afirmar(chamar("loja.pagina", appid="abc")["ok"] is False)
    afirmar(chamar("loja.buscar", termo="a")["ok"] is False)


def teste_lojas_instaladas_so_mostra_novos():
    db, con, ids = _banco("Hades")
    con.close()
    chamar, eventos = _ponte(db)
    achados = [{"titulo": "Hades", "executable_path": "C:\\jogos\\Hades.exe", "launch_options": ""},
               {"titulo": "Celeste", "executable_path": "D:/Epic/Celeste/Celeste.exe", "launch_options": ""}]
    info = {"fontes": [{"fonte": "Epic", "ok": True, "n": 2, "detalhe": ""}]}
    with patch.object(scans, "ler_do_disco", return_value=(achados, info)):
        t = chamar("jogos.lojas_prever")["resultado"]["trabalho"]
        fim = None
        for _ in range(200):
            fim = next((e["dados"] for e in eventos if e["dados"].get("id") == t["id"]
                        and e["dados"].get("motivo") == "fim"), None)
            if fim:
                break
            time.sleep(0.05)
    afirmar(fim and fim["estado"] == "ok", fim)
    det = fim["detalhe"]
    afirmar([i["titulo"] for i in det["itens"]] == ["Celeste"] and det["ja_na_biblioteca"] == 1, det)
    afirmar("Epic: 2" in det["aviso"], det["aviso"])
