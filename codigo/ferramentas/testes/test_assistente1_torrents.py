"""A1-04: importar torrents concluídos pelo Qt.

Sucesso = só 100% aparece na lista; importar pasta pronta grava o jogo e
preserva a origem do download.
Cancelamento = lista vazia/sem 100% não importa nada.
Falha = caminho sumido, formato não suportado e seleção vazia falham explícito.
Nenhum download real, nenhum cliente real: listar_torrents é simulado e as
pastas são fixtures sintéticas em diretório descartável.
Parte Qt usa _qt() e pula sem PySide6.
"""
import tempfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import bib_core as core
from executar import afirmar
from servicos_ui import ServicoBiblioteca


def _servico_tmp():
    tmp = Path(tempfile.mkdtemp(prefix="a1-tor-"))
    db = tmp / "colecao.db"
    svc = ServicoBiblioteca(str(db))
    with closing(core.get_db(str(db))):  # garante o schema antes de contar
        pass
    return svc, tmp, db


def _contar(db):
    with closing(core.get_db(str(db))) as con:
        return con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()["n"]


def _falsa_lista(itens):
    return {"torrents": itens, "erros": []}


def teste_prontos_listam_so_concluidos():
    svc, tmp, _db = _servico_tmp()
    pasta = tmp / "dl-pronta"
    pasta.mkdir(parents=True)
    (pasta / "Aventura.exe").write_bytes(b"MZ-falso")
    incompleta = tmp / "dl-metade"
    incompleta.mkdir(parents=True)
    falsa = _falsa_lista([
        {"hash": "a1", "nome": "Pronta Pasta", "completo": True,
         "save_path": str(pasta), "progresso": 1.0},
        {"hash": "b2", "nome": "Pela Metade", "completo": False,
         "save_path": str(incompleta), "progresso": 0.5},
        {"hash": "c3", "nome": "Sumiu", "completo": True,
         "save_path": str(tmp / "nao-baixado"), "progresso": 1.0},
    ])
    with patch.object(core, "listar_torrents", lambda: falsa):
        r = svc.torrents_prontos()
    nomes = [t["nome"] for t in r["itens"]]
    afirmar("Pronta Pasta" in nomes, nomes)
    afirmar("Sumiu" in nomes, nomes)
    afirmar("Pela Metade" not in nomes, nomes)
    estados = {t["nome"]: t["estado"] for t in r["itens"]}
    afirmar(estados["Pronta Pasta"] == "pasta", estados)
    afirmar(estados["Sumiu"] == "sumiu", estados)


def teste_importar_torrent_pasta_preserva_origem():
    svc, tmp, db = _servico_tmp()
    pasta = tmp / "dl-jogo"
    pasta.mkdir(parents=True)
    (pasta / "Aventura.exe").write_bytes(b"MZ-falso")
    antes = _contar(db)
    with patch.object(core, "dentro_do_destino", lambda _c: True):
        r = svc.importar_torrent(str(pasta))
    afirmar(bool(r), r)
    afirmar(_contar(db) == antes + 1, r)
    afirmar(pasta.is_dir() and (pasta / "Aventura.exe").is_file(),
            "origem do download foi movida/apagada")


def teste_importar_torrent_caminho_ausente_falha():
    svc, tmp, db = _servico_tmp()
    antes = _contar(db)
    try:
        svc.importar_torrent(str(tmp / "sumiu-do-disco"))
    except ValueError as e:
        afirmar("disco" in str(e).lower(), str(e))
    else:
        raise AssertionError("aceitou caminho ausente")
    afirmar(_contar(db) == antes, "falha mutou a coleção")
    try:
        svc.importar_torrent("   ")
    except ValueError as e:
        afirmar("caminho" in str(e).lower() or "informe" in str(e).lower(), str(e))
    else:
        raise AssertionError("aceitou caminho vazio")


def teste_importar_torrent_formato_nao_suportado_falha():
    svc, tmp, db = _servico_tmp()
    txt = tmp / "leia-me.txt"
    txt.write_text("só um texto", encoding="utf-8")
    antes = _contar(db)
    with patch.object(core, "dentro_do_destino", lambda _c: True):
        try:
            svc.importar_torrent(str(txt))
        except ValueError as e:
            afirmar("formato" in str(e).lower(), str(e))
        else:
            raise AssertionError("aceitou formato não suportado")
    afirmar(_contar(db) == antes, "falha mutou a coleção")


def _sincrono(bridge):
    def executar(rotulo, trabalho, pronto=None, falha=None):
        try:
            r = trabalho()
        except Exception as exc:
            if falha:
                falha(str(exc))
            else:
                bridge.aviso.emit(str(exc), True)
            return
        if pronto:
            pronto(r)
    return patch.object(bridge, "executar", side_effect=executar)


def teste_qt_consultar_prontos_popula_sem_importar():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    tmp = Path(tempfile.mkdtemp(prefix="a1-tor-qt-"))
    pasta = tmp / "dl-qt"
    pasta.mkdir(parents=True)
    (pasta / "Aventura.exe").write_bytes(b"MZ-falso")
    falsa = _falsa_lista([{"hash": "q1", "nome": "Qt Pronta", "completo": True,
                           "save_path": str(pasta), "progresso": 1.0}])
    import sqlite3
    db = Path(bridge.servico.db_path)
    con = sqlite3.connect(str(db))
    try:
        antes = con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()[0]
    finally:
        con.close()
    try:
        with _sincrono(bridge), patch.object(core, "listar_torrents", lambda: falsa):
            bridge.consultarTorrentsProntos()
            itens = list(bridge.torrentsProntos.get("itens") or [])
            afirmar(len(itens) == 1 and itens[0]["nome"] == "Qt Pronta",
                    bridge.torrentsProntos)
        con = sqlite3.connect(str(db))
        try:
            depois = con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()[0]
        finally:
            con.close()
        afirmar(depois == antes, f"consulta mutou a coleção ({antes} → {depois})")
    finally:
        bridge.fechar()


def teste_qt_importar_concluido_e_atualiza_lista():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    tmp = Path(tempfile.mkdtemp(prefix="a1-tor-qti-"))
    pasta = tmp / "dl-qt2"
    pasta.mkdir(parents=True)
    (pasta / "Beta.exe").write_bytes(b"MZ-falso")
    try:
        with _sincrono(bridge), \
                patch.object(core, "dentro_do_destino", lambda _c: True), \
                patch.object(core, "listar_torrents",
                             lambda: _falsa_lista([])):
            bridge.importarTorrent(str(pasta))
            afirmar(bridge.torrentsProntos.get("itens") == [], bridge.torrentsProntos)
            titulos = [j.get("titulo", "") for j in bridge.servico.snapshot()["jogos"]]
            afirmar(any("Beta" in t for t in titulos), titulos)
    finally:
        bridge.fechar()


def teste_qt_importar_vazio_avisa_sem_mutar():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    avisos = []
    bridge.aviso.connect(lambda texto, erro: avisos.append((texto, erro)))
    import sqlite3
    db = Path(bridge.servico.db_path)
    con = sqlite3.connect(str(db))
    try:
        antes = con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()[0]
    finally:
        con.close()
    try:
        with _sincrono(bridge):
            bridge.importarTorrent("   ")
            afirmar(any("caminho" in t.lower() or "informe" in t.lower()
                        for t, _ in avisos), avisos)
    finally:
        bridge.fechar()
    con = sqlite3.connect(str(db))
    try:
        depois = con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()[0]
    finally:
        con.close()
    afirmar(depois == antes, (antes, depois))
