"""Filmes e Séries (1.4.4): índice, Cinemeta, progresso, calendário e ponte — sem rede real."""
import datetime as dt
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from bib_nucleo import banco as nucleo_banco
from bib_nucleo.midia import banco as mb
from bib_nucleo.midia import indexar
from bib_nucleo.rede import cinemeta
from executar import afirmar

HOJE = dt.date.today()
META_SERIE = {"id": "tt0903747", "imdb_id": "tt0903747", "type": "series", "name": "Breaking Bad",
              "releaseInfo": "2008–2013", "poster": "https://img.example/bb.jpg", "genres": ["Drama"],
              "videos": [{"id": f"tt0903747:1:{e}", "season": 1, "episode": e, "name": f"Ep {e}",
                          "released": "2008-01-20T00:00:00.000Z"} for e in (1, 2, 3)] +
              [{"id": "tt0903747:2:1", "season": 2, "episode": 1, "name": "Novo",
                "released": f"{HOJE + dt.timedelta(days=3)}T00:00:00.000Z"}]}
META_FILME = {"id": "tt0133093", "imdb_id": "tt0133093", "type": "movie", "name": "The Matrix",
              "releaseInfo": "1999", "poster": "https://img.example/m.jpg", "description": "Neo."}


def _buscar(tipo, termo):
    if "matrix" in termo.lower():
        return [{"id": "tt9999999", "name": "The Matrix Resurrections", "releaseInfo": "2021"},
                {"id": "tt0133093", "name": "The Matrix", "releaseInfo": "1999"}]
    if "breaking" in termo.lower():
        return [{"id": "tt0903747", "name": "Breaking Bad", "releaseInfo": "2008–2013"}]
    return [{"id": "tt0000001", "name": "Algo Bem Diferente", "releaseInfo": "1990"}]


def _meta(tipo, imdb, validade_s=None):
    return META_SERIE if imdb == "tt0903747" else META_FILME


def _pasta():
    raiz = Path(tempfile.mkdtemp(prefix="suite-midia-"))
    arqs = ["Filmes/The.Matrix.1999.1080p.mkv", "Filmes/The.Matrix.1999.1080p.srt",
            "Filmes/The.Matrix.1999.1080p.pt-BR.srt", "Filmes/Filme.Esquisito.2003.mkv",
            "Séries/Breaking Bad/Season 1/Breaking.Bad.S01E01.mkv",
            "Séries/Breaking Bad/Season 1/Breaking.Bad.S01E02.mkv",
            "Séries/Breaking Bad/Season 1/sample-Breaking.Bad.S01E02.mkv",
            ".escondida/oculto.mkv", "Filmes/notas.txt"]
    for i, rel in enumerate(arqs):
        p = raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".srt"):
            p.write_text("1\n00:00:01,000 --> 00:00:02,500\nOlá\n", encoding="utf-8")
        else:
            p.write_bytes(bytes([i]) * 4096)
    return raiz


def _banco():
    db = Path(tempfile.mkdtemp(prefix="suite-midia-db-")) / "hub.db"
    nucleo_banco.get_db(db).close()
    return db


def teste_indexar_casar_e_reindexar():
    from bib_nucleo.midia.casar import casar_pendentes
    raiz = _pasta()
    con = nucleo_banco.get_db(_banco())
    try:
        for ruim in ("relativa/x", str(Path(raiz.anchor)), str(raiz / "nao-existe")):
            try:
                mb.adicionar_pasta(con, ruim)
            except ValueError:
                continue
            afirmar(False, f"aceitou pasta {ruim!r}")
        p = mb.adicionar_pasta(con, str(raiz))
        try:
            mb.adicionar_pasta(con, str(raiz / "Filmes"))
            afirmar(False, "subpasta já coberta")
        except ValueError:
            pass
        with patch.object(indexar, "MIN_BYTES", 1024):
            r = indexar.indexar_pasta(con, p["id"], str(raiz))
        afirmar(r["novos"] == 4 and r["ausentes"] == 0, r)  # sem sample, oculta e .txt
        matrix = con.execute("SELECT * FROM midia_arquivos WHERE caminho LIKE '%Matrix%'").fetchone()
        afirmar(len(json.loads(matrix["legendas"])) == 2 and matrix["ano_lido"] == 1999, dict(matrix))
        c = casar_pendentes(con, _buscar, _meta)
        afirmar(c["casados"] == 3 and c["revisar"] == 1, c)
        afirmar(mb.ler_titulo(con, "tt0133093")["nome"] == "The Matrix", "filme gravado")
        esquisito = con.execute("SELECT * FROM midia_arquivos WHERE caminho LIKE '%Esquisito%'").fetchone()
        afirmar(esquisito["imdb_id"] is None and esquisito["sugestao"] == "tt0000001", dict(esquisito))
        # sem mudança: não re-hasheia; apagado: ausente
        (raiz / "Filmes/Filme.Esquisito.2003.mkv").unlink()
        with patch.object(indexar, "MIN_BYTES", 1024), \
             patch.object(indexar, "hash_rapido", side_effect=AssertionError("não devia re-hashear")):
            r = indexar.indexar_pasta(con, p["id"], str(raiz))
        afirmar(r["iguais"] == 3 and r["ausentes"] == 1 and r["novos"] == 0, r)
    finally:
        con.close()


def teste_progresso_limiar_e_marcar():
    con = nucleo_banco.get_db(_banco())
    try:
        afirmar(mb.salvar_progresso(con, "tt0133093", 600, 7200)["assistido"] is False)
        afirmar(mb.salvar_progresso(con, "tt0133093", 6700, 7200)["assistido"] is True, "≥ 92 % é assistido")
        p = mb.progresso(con)["tt0133093"]
        afirmar(p["assistido"] and p["posicao"] == 0, p)
        mb.salvar_progresso(con, "tt0133093", 2, 7200)
        afirmar(mb.progresso(con)["tt0133093"]["assistido"], "reabrir do início não desmarca")
        mb.marcar_assistido(con, ["tt0903747:1:1", "tt0903747:1:2"], True)
        mb.marcar_assistido(con, ["tt0903747:1:2"], False)
        afirmar([k for k, v in mb.progresso(con).items() if v["assistido"]] == ["tt0133093", "tt0903747:1:1"])
    finally:
        con.close()


def teste_legenda_srt_para_vtt():
    from bib_nucleo.midia.legendas import srt_para_vtt
    vtt = srt_para_vtt("﻿1\r\n00:00:01,000 --> 00:00:02,500\r\nOlá\r\n\r\n2\r\n00:01:00,100 --> 00:01:02,000\r\nTchau\r\n")
    afirmar(vtt == "WEBVTT\n\n00:00:01.000 --> 00:00:02.500\nOlá\n\n00:01:00.100 --> 00:01:02.000\nTchau\n", vtt)
    afirmar(srt_para_vtt("WEBVTT\n\nx") == "WEBVTT\n\nx")


def teste_calendario_das_seguidas():
    from bib_nucleo.midia.calendario import calendario
    con = nucleo_banco.get_db(_banco())
    try:
        mb.gravar_titulo(con, META_SERIE, seguindo=True)
        cal = calendario(con)
        afirmar([e["chave"] for e in cal] == ["tt0903747:2:1"] and cal[0]["lancado"] is False, cal)
        afirmar(calendario(con, hoje=dt.date(2008, 1, 25))[0]["lancado"] is True)
    finally:
        con.close()


def _ponte(db):
    from ponte import Ponte, Trabalhos
    from servicos_ui import ServicoBiblioteca
    eventos = []
    ponte = Ponte(ServicoBiblioteca(db), trabalhos=Trabalhos(eventos.append))

    def chamar(metodo, **params):
        return json.loads(ponte.executar_linha(json.dumps({"id": 1, "metodo": metodo, "params": params})))

    def esperar(ident):
        for _ in range(200):
            fim = next((e["dados"] for e in eventos if e["dados"].get("id") == ident
                        and e["dados"].get("motivo") == "fim"), None)
            if fim:
                return fim
            time.sleep(0.05)
        raise AssertionError("trabalho não terminou")
    return chamar, esperar


def teste_ponte_fluxo_completo():
    raiz = _pasta()
    db = _banco()
    chamar, esperar = _ponte(db)
    afirmar(chamar("midia.pasta_adicionar", caminho=str(raiz))["ok"])
    from bib_nucleo.rede import online
    png = (b"\x89PNG\r\n\x1a\n" + b"0" * 64, ".png", "")
    with patch.object(indexar, "MIN_BYTES", 1024), patch.object(cinemeta, "buscar", side_effect=_buscar), \
         patch.object(cinemeta, "meta", side_effect=_meta), \
         patch.object(online, "baixar_imagem", return_value=png) as baixar:
        t = chamar("midia.varrer")["resultado"]["trabalho"]
        fim = esperar(t["id"])
    afirmar(fim["estado"] == "ok" and "3 identificado" in fim["detalhe"]["aviso"], fim)
    afirmar(baixar.call_count == 2, "um pôster por título identificado")
    bib = chamar("midia.biblioteca")["resultado"]
    afirmar([t["nome"] for t in bib["titulos"]] == ["Breaking Bad", "The Matrix"] and len(bib["revisar"]) == 1, bib)
    afirmar(all(t["poster"].startswith("file:") for t in bib["titulos"]), "pôster salvo no disco")

    serie = chamar("midia.titulo", imdb="tt0903747")["resultado"]
    eps = serie["temporadas"][0]["episodios"]
    afirmar([e["arquivo"] is not None for e in eps] == [True, True, False], eps)
    afirmar(serie["temporadas"][1]["numero"] == 2, serie["temporadas"])

    rep = chamar("midia.reproduzir", arquivo=eps[0]["arquivo"])["resultado"]
    afirmar(rep["chave"] == "tt0903747:1:1" and rep["titulo"] == "Breaking Bad · T1E1" and rep["legendas"] == [], rep)
    afirmar(chamar("midia.salvar_posicao", chave=rep["chave"], posicao=3000, duracao=3100)["resultado"]["assistido"])
    cont = chamar("midia.continuar")["resultado"]
    afirmar(cont and cont[0]["chave"] == "tt0903747:1:2" and cont[0]["motivo"] == "próximo episódio", cont)
    chamar("midia.salvar_posicao", chave="tt0903747:1:2", posicao=600, duracao=3100)
    cont = chamar("midia.continuar")["resultado"]
    afirmar(cont[0]["motivo"] == "em andamento" and 0.19 < cont[0]["fracao"] < 0.2, cont)

    filme = chamar("midia.titulo", imdb="tt0133093")["resultado"]
    leg = chamar("midia.reproduzir", arquivo=filme["arquivos"][0]["id"])["resultado"]["legendas"]
    afirmar(len(leg) == 2, leg)
    vtt = chamar("midia.legenda", arquivo=filme["arquivos"][0]["id"], indice=0)["resultado"]["vtt"]
    afirmar(vtt.startswith("WEBVTT") and "00:00:01.000" in vtt, vtt)

    esquisito = bib["revisar"][0]["id"]
    with patch.object(cinemeta, "meta", side_effect=_meta), patch.object(online, "baixar_imagem", return_value=png):
        r = chamar("midia.corrigir", arquivo=esquisito, imdb="tt0133093", tipo="movie")
    afirmar(r["ok"] and chamar("midia.biblioteca")["resultado"]["revisar"] == [], r)

    with patch.object(cinemeta, "meta", side_effect=_meta), patch.object(online, "baixar_imagem", return_value=png):
        afirmar(chamar("midia.lista_alternar", imdb="tt0903747", tipo="series")["resultado"]["na_lista"] is True)
        afirmar(chamar("midia.seguir", imdb="tt0903747", seguir=True)["ok"])
    afirmar([t["imdb_id"] for t in chamar("midia.lista")["resultado"]] == ["tt0903747"])
    afirmar(chamar("midia.calendario")["resultado"][0]["chave"] == "tt0903747:2:1")

    for metodo, params in (("midia.titulo", {"imdb": "123"}), ("midia.salvar_posicao", {"chave": "../x", "posicao": 1, "duracao": 2}),
                           ("midia.salvar_posicao", {"chave": "tt0133093", "posicao": -1, "duracao": 2}),
                           ("midia.marcar", {"chaves": ["tt1"], "assistido": True}),
                           ("midia.reproduzir", {"arquivo": 9999})):
        afirmar(chamar(metodo, **params)["ok"] is False, metodo)


def teste_seguidas_so_a_cada_12h_e_sem_rede():
    db = _banco()
    chamar, esperar = _ponte(db)
    con = nucleo_banco.get_db(db)
    mb.gravar_titulo(con, META_SERIE, seguindo=True)
    con.close()
    with patch.object(cinemeta, "meta", side_effect=_meta) as m:
        r1 = esperar(chamar("midia.atualizar_seguidas")["resultado"]["trabalho"]["id"])
        r2 = esperar(chamar("midia.atualizar_seguidas")["resultado"]["trabalho"]["id"])
    afirmar(r1["detalhe"]["atualizado"] is True and r2["detalhe"]["motivo"] == "recente" and m.call_count == 1,
            (r1, r2))
    os.environ["BIBLIOTECA_REDE"] = "0"
    try:
        r3 = esperar(chamar("midia.atualizar_seguidas", forcar=True)["resultado"]["trabalho"]["id"])
        afirmar(r3["detalhe"]["motivo"] == "sem rede", r3)
        afirmar(chamar("midia.descobrir", tipo="movie")["ok"] is False, "descobrir exige rede")
    finally:
        os.environ.pop("BIBLIOTECA_REDE", None)


def teste_cinemeta_urls_e_cache():
    from bib_nucleo.rede import online
    resp = {"metas": [{"id": "tt0133093", "name": "The Matrix", "type": "movie", "poster": "http://inseguro"},
                      {"id": "x", "name": "sem id"}]}
    with patch.object(online, "requisitar_json", return_value=resp) as req:
        r = cinemeta.catalogo("movie", "Sci-Fi", 100)
        cinemeta.catalogo("movie", "Sci-Fi", 100)
        cinemeta.buscar("series", "dark matter")
    afirmar(req.call_count == 2, "catálogo repetido vem do cache")
    afirmar(req.call_args_list[0].args[0] == "https://v3-cinemeta.strem.io/catalog/movie/top/genre=Sci-Fi&skip=100.json",
            req.call_args_list[0])
    afirmar("search=dark%20matter" in req.call_args_list[1].args[0], req.call_args_list[1])
    afirmar(len(r) == 1 and cinemeta.resumo(r[0])["poster"] == "", r)
    for ruim in (lambda: cinemeta.catalogo("anime"), lambda: cinemeta.catalogo("movie", "Nada"),
                 lambda: cinemeta.meta("movie", "123"), lambda: cinemeta.buscar("movie", "a")):
        try:
            ruim()
        except ValueError:
            continue
        afirmar(False, "aceitou entrada ruim")
