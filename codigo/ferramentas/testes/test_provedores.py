"""Metadados de jogo (1.4.2): banco, provedores e página do jogo — sem rede real."""
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from bib_nucleo import banco
from executar import afirmar

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64

APPDETAILS = {"620": {"success": True, "data": {
    "name": "Portal 2",
    "short_description": "Jogo de <b>quebra-cabeça</b>.",
    "about_the_game": "<p>Primeiro parágrafo &amp; mais.</p><ul><li>Item</li></ul><script>x()</script>",
    "genres": [{"description": "Ação"}, {"description": "Aventura"}],
    "developers": ["Valve"], "publishers": ["Valve"],
    "release_date": {"date": "18 abr. 2011"}, "website": "http://inseguro.example",
    "screenshots": [{"path_thumbnail": f"https://cdn.example/s{i}.jpg"} for i in range(8)],
}}}


def _banco(titulo="Portal 2", **extra):
    db = Path(tempfile.mkdtemp(prefix="suite-meta-")) / "hub.db"
    con = banco.get_db(db)
    jogo = banco.criar_jogo(con, {"titulo": titulo, "executable_path": "", **extra})
    con.commit()
    uuid = con.execute("SELECT uuid FROM jogos WHERE id=?", (jogo["id"],)).fetchone()[0]
    return db, con, jogo["id"], uuid


def teste_meta_mescla_trava_e_lista_pendentes():
    from bib_nucleo.banco import meta
    _, con, _, uuid = _banco()
    try:
        afirmar([u for _, u in meta.uuids_sem_meta(con)] == [uuid])
        m = meta.gravar_meta(con, uuid, {"descricao": "da loja", "steam_appid": "620",
                                         "generos": ["Ação"], "lixo": 1, "fontes": {"steam": "x"}})
        afirmar(m["descricao"] == "da loja" and m["steam_appid"] == "620" and "lixo" not in m, m)
        afirmar(meta.uuids_sem_meta(con) == [], "com fonte não é mais pendente")
        m = meta.salvar_edicao(con, uuid, {"descricao": "minha", "generos": "RPG, Ação"})
        afirmar(m["generos"] == ["RPG", "Ação"] and "descricao" in m["travado"], m)
        m = meta.gravar_meta(con, uuid, {"descricao": "outra da loja", "desenvolvedora": "Valve"})
        afirmar(m["descricao"] == "minha" and m["desenvolvedora"] == "Valve", "trava ignorada")
        m = meta.gravar_meta(con, uuid, {"desenvolvedora": ""})
        afirmar(m["desenvolvedora"] == "Valve", "vazio de provedor não apaga")
        m = meta.salvar_edicao(con, uuid, {"descricao": ""})
        afirmar(m["descricao"] == "" and "descricao" not in m["travado"], m)
        for ruim in ({"titulo": "x"}, {"steam_appid": "abc"}, {"generos": 3}):
            try:
                meta.salvar_edicao(con, uuid, ruim)
            except ValueError:
                continue
            afirmar(False, f"aceitou {ruim}")
    finally:
        con.close()


def teste_html_para_texto_tira_marcacao():
    from bib_nucleo.rede.provedores._apoio import html_para_texto, normalizar_titulo
    texto = html_para_texto("<p>Olá &amp; <b>mundo</b></p><ul><li>um</li></ul><script>mal()</script>")
    afirmar("<" not in texto and "mal()" not in texto and "Olá & mundo" in texto and "• um" in texto, texto)
    afirmar(html_para_texto("x " * 5000, limite=50).endswith("…"))
    afirmar(normalizar_titulo("Pokémon™: Edição (USA)") == normalizar_titulo("pokémon edição"))


def teste_steam_traz_campos_e_reusa_cache():
    from bib_nucleo.rede import online
    from bib_nucleo.rede.provedores import steam
    with patch.object(online, "requisitar_json", return_value=APPDETAILS) as req:
        r = steam.buscar({"titulo": "Portal 2", "shop": "steam", "object_id": "620"}, {})
        steam.buscar({"titulo": "Portal 2", "shop": "steam", "object_id": "620"}, {})
    afirmar(req.call_count == 1, "segunda leitura deveria vir do cache")
    afirmar("l=brazilian" in req.call_args.args[0], req.call_args)
    afirmar(r["steam_appid"] == "620" and r["generos"] == ["Ação", "Aventura"], r)
    afirmar(r["resumo"] == "Jogo de quebra-cabeça." and "<" not in r["descricao"], r)
    afirmar(r["site"] == "", "site sem https não passa")
    afirmar(len(r["screenshots_urls"]) == 6 and r["hero_url"].endswith("/620/library_hero.jpg"), r)


def teste_enriquecer_junta_provedores_e_pula_sem_credencial():
    from bib_nucleo.rede import provedores
    from bib_nucleo.rede.provedores import retro, sgdb, steam
    with patch.object(steam, "buscar", return_value={"steam_appid": "1", "descricao": "d",
                                                     "hero_url": "https://a/h.jpg"}), \
         patch.object(sgdb, "buscar", side_effect=AssertionError("sem chave não roda")), \
         patch.object(retro, "buscar", side_effect=AssertionError("sem chave não roda")):
        campos, artes, erros = provedores.enriquecer({"titulo": "X"}, {})
    afirmar(campos["descricao"] == "d" and set(campos["fontes"]) == {"steam"}, campos)
    afirmar(artes["hero"] == ["https://a/h.jpg"] and erros == [], (artes, erros))
    _, _, erros = provedores.enriquecer({"titulo": "X"}, {}, chaves=["sgdb"])
    afirmar(erros and "SteamGridDB" in erros[0], erros)
    afirmar(provedores.ligados()["sgdb"] is True, "SteamGridDB nasce ligado")
    provedores.definir_ligados({"sgdb": False})
    afirmar(provedores.ligados()["sgdb"] is False)
    provedores.definir_ligados({"sgdb": True})
    # config antiga ainda cita o HowLongToBeat removido: é ignorada
    from bib_nucleo.arquivos import gravar_json
    gravar_json(provedores._arquivo_config(), {"hltb": True, "steam": True})
    afirmar("hltb" not in provedores.ligados() and provedores.ligados()["steam"] is True)
    os.environ["BIBLIOTECA_REDE"] = "0"
    try:
        provedores.enriquecer({"titulo": "X"}, {})
        afirmar(False, "modo avião deveria recusar")
    except ValueError as e:
        afirmar("BIBLIOTECA_REDE" in str(e), e)
    finally:
        os.environ.pop("BIBLIOTECA_REDE", None)


def teste_retro_casa_nds_por_nome_e_le_progresso():
    from bib_nucleo.rede import online
    from bib_nucleo.rede.provedores import retro
    os.environ.update({"BIBLIOTECA_RETRO_USER": "tuco", "BIBLIOTECA_RETRO_KEY": "k" * 32})
    lista = [{"ID": 5, "Title": "Outro"}, {"ID": 1234, "Title": "Pokémon: Platinum Version"}]
    progresso = {"ID": 1234, "Title": "Pokémon Platinum", "ConsoleName": "Nintendo DS", "Achievements": {
        "1": {"ID": 1, "Title": "A", "Description": "a", "Points": 5, "DisplayOrder": 2, "DateEarned": "2026-01-01"},
        "2": {"ID": 2, "Title": "B", "Description": "b", "Points": 10, "DisplayOrder": 1},
    }}
    try:
        def responder(url, **_):
            return lista if "API_GetGameList" in url else progresso
        jogo = {"titulo": "Pokemon Platinum Version", "origem": "nds"}
        with patch.object(online, "requisitar_json", side_effect=responder) as req, \
             patch("bib_nucleo.banco.plataforma_jogo", return_value="NDS"):
            r = retro.buscar(jogo, {})
        afirmar(r["retro_id"] == "1234", r)
        dados = r["retro"]
        afirmar(dados["total"] == 2 and dados["ganhas"] == 1 and dados["pontos_ganhos"] == 5, dados)
        afirmar([c["titulo"] for c in dados["conquistas"]] == ["B", "A"], "ordem de exibição")
        afirmar("y=" + "k" * 32 in req.call_args.args[0] and "u=tuco" in req.call_args.args[0])
        with patch.object(online, "requisitar_json", side_effect=AssertionError("3DS não consulta")), \
             patch("bib_nucleo.banco.plataforma_jogo", return_value="3DS"):
            afirmar(retro.buscar({"titulo": "Zelda"}, {}) == {})
    finally:
        os.environ.pop("BIBLIOTECA_RETRO_USER", None)
        os.environ.pop("BIBLIOTECA_RETRO_KEY", None)


def _esperar_trabalho(eventos, ident, limite=30):
    fim = time.time() + limite
    while time.time() < fim:
        for e in list(eventos):
            d = e.get("dados") or {}
            if e.get("evento") == "trabalho" and d.get("id") == ident and d.get("motivo") == "fim":
                return d
        time.sleep(0.05)
    raise AssertionError("trabalho não terminou")


def teste_ponte_pagina_enriquecer_e_editar():
    from bib_nucleo.rede import online
    from ponte import Ponte, Trabalhos
    from servicos_ui import ServicoBiblioteca
    db, con, gid, uuid = _banco(shop="steam", object_id="620")
    con.close()
    eventos = []
    ponte = Ponte(ServicoBiblioteca(db), trabalhos=Trabalhos(eventos.append))

    def chamar(metodo, **params):
        r = json.loads(ponte.executar_linha(json.dumps({"id": 1, "metodo": metodo, "params": params})))
        return r

    r = chamar("jogo.pagina", id=gid)
    afirmar(r["ok"] and r["resultado"]["enriquecido"] is False and r["resultado"]["meta"]["hero_url"] == "", r)
    afirmar({p["chave"] for p in r["resultado"]["provedores"]} == {"steam", "sgdb", "retro"}, r)

    def imagem(url, timeout=15, limite=2_000_000):
        return PNG, ".png", ""
    with patch.object(online, "requisitar_json", return_value=APPDETAILS), \
         patch.object(online, "baixar_imagem", side_effect=imagem):
        t = chamar("jogo.enriquecer", id=gid)
        afirmar(t["ok"] and t["resultado"]["trabalho"]["cancelavel"] is True, t)
        fim = _esperar_trabalho(eventos, t["resultado"]["trabalho"]["id"])
    afirmar(fim["estado"] == "ok" and "Steam" in fim["detalhe"]["aviso"], fim)
    pagina = chamar("jogo.pagina", id=gid)["resultado"]
    meta = pagina["meta"]
    afirmar(pagina["enriquecido"] and meta["desenvolvedora"] == "Valve", meta)
    afirmar(meta["hero_url"].startswith("file:") and len(meta["screenshots_urls"]) == 6, meta)
    afirmar("artes" in meta["hero_url"] and uuid in meta["hero_url"], meta["hero_url"])

    r = chamar("jogo.meta_salvar", id=gid, campos={"desenvolvedora": "Eu"})
    afirmar(r["ok"] and r["resultado"]["desenvolvedora"] == "Eu" and "desenvolvedora" in r["resultado"]["travado"], r)
    r = chamar("jogo.meta_salvar", id=gid, campos={"titulo": "x"})
    afirmar(not r["ok"] and "não editável" in r["erro"], r)

    with patch.object(online, "baixar_imagem", side_effect=imagem):
        r = chamar("jogo.arte_aplicar", id=gid, tipo="logo", url="https://a/logo.png")
    afirmar(r["ok"] and r["resultado"]["logo_url"].startswith("file:") and "logo" in r["resultado"]["travado"], r)
    r = chamar("jogo.arte_aplicar", id=gid, tipo="capa_errada", url="https://a")
    afirmar(not r["ok"], r)

    r = chamar("metadados.configurar", ligados={"sgdb": False}, retro_user="tuco", retro_key="k" * 32)
    afirmar(r["ok"] and r["resultado"]["retro_user"] == "tuco" and r["resultado"]["retro_key"] is True, r)
    afirmar(any(p["chave"] == "sgdb" and not p["ligado"] for p in r["resultado"]["provedores"]), r)
    r = chamar("metadados.configurar", ligados={"nada": True})
    afirmar(not r["ok"], r)

    with patch.object(online, "requisitar_json", return_value=APPDETAILS), \
         patch.object(online, "baixar_imagem", side_effect=imagem):
        t = chamar("jogos.enriquecer_lote")
        fim = _esperar_trabalho(eventos, t["resultado"]["trabalho"]["id"])
    afirmar(fim["estado"] == "ok" and "já têm dados" in fim["detalhe"]["aviso"], fim)
