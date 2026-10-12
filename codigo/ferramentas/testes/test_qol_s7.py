"""QoL pessoal (S7): notas por jogo, exportação da coleção e modo simples (Isa)."""
from __future__ import annotations

import os
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from executar import afirmar, fundo_segundo_plano


def _app():
    fundo_segundo_plano()
    try:
        from PySide6.QtGui import QGuiApplication
    except ImportError:
        print("[pula] PySide6 opcional não instalado")
        return None
    return QGuiApplication.instance() or QGuiApplication([])


def _bridge():
    sys.path.insert(0, str(Path(__file__).parents[3] / "frontends"))
    from qt_bridge import HubBridge
    return HubBridge(":memory:")


def teste_notas_do_jogo_persistem_no_campo_observacoes():
    from bib_nucleo import banco as B
    tmp = Path(tempfile.mkdtemp(prefix="suite-notas-"))
    con = B.get_db(tmp / "biblioteca.db")
    try:
        jogo = B.criar_jogo(con, {"titulo": "Hollow Knight"})
        con.commit()
        B.atualizar_jogo(con, jogo["id"], {"observacoes": "Parei na Cidade das Lágrimas"})
        con.commit()
        lido = B.listar_jogos(con, q="Hollow")[0]
        afirmar(lido["observacoes"] == "Parei na Cidade das Lágrimas", lido)
    finally:
        con.close()


def _bridge_arquivo():
    """Bridge com banco em arquivo temporário (':memory:' não é compartilhado entre conexões)."""
    sys.path.insert(0, str(Path(__file__).parents[3] / "frontends"))
    from qt_bridge import HubBridge
    tmp = Path(tempfile.mkdtemp(prefix="suite-bridge-"))
    return HubBridge(str(tmp / "biblioteca.db"))


def teste_notas_salvar_pelo_servico_trunca_e_nao_quebra():
    app = _app()
    if app is None:
        return
    bridge = _bridge_arquivo()
    try:
        # texto gigante é cortado para 4000 caracteres, sem exceção
        from bib_nucleo import banco as B
        con = B.get_db(bridge.servico.db_path)
        try:
            jogo = B.criar_jogo(con, {"titulo": "Teste notas"})
            con.commit()
        finally:
            con.close()
        bridge.servico.salvar_observacoes(jogo["id"], "x" * 9000)
        con = B.get_db(bridge.servico.db_path)
        try:
            lido = B.listar_jogos(con, q="Teste notas")[0]
            afirmar(len(lido["observacoes"]) == 4000, len(lido["observacoes"]))
        finally:
            con.close()
    finally:
        bridge.fechar()


def teste_exportar_colecao_para_pasta_gera_zip_valido():
    app = _app()
    if app is None:
        return
    bridge = _bridge_arquivo()
    destino = Path(tempfile.mkdtemp(prefix="suite-export-"))  # simula pendrive
    try:
        r = bridge.servico.exportar_colecao_para(str(destino))
        zips = list(destino.glob("tucoteca-*.zip"))
        afirmar(len(zips) == 1, (zips, r))
        with zipfile.ZipFile(zips[0]) as z:
            afirmar(z.testzip() is None, "ZIP corrompido")
            afirmar(any("json" in n for n in z.namelist()), z.namelist())
    finally:
        bridge.fechar()


def teste_modo_simples_persistido_e_filtra_navegacao():
    from bib_nucleo import aparencia_usuario as A
    with patch.dict(os.environ):
        os.environ.pop("BIBLIOTECA_JOGOS_DIR", None)
        afirmar(A.ler_aparencia()["modo_simples"] is False, "padrão é o modo completo")
        r = A.salvar_aparencia("", "", None, True)
        afirmar(r["modo_simples"] is True, r)
        # outras preferências não são apagadas ao mudar só o modo
        afirmar(r["tema"] in ("escuro", "claro") and r["densidade"] in ("compacto", "conforto", "bigpicture"), r)
        afirmar(A.ler_aparencia()["modo_simples"] is True, "modo precisa persistir")
        A.salvar_aparencia("", "", None, False)
        afirmar(A.ler_aparencia()["modo_simples"] is False)
