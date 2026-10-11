"""Regressões da integração entre as duas frentes: Qt, bibliotecas e videoteca."""
import tempfile
from pathlib import Path
from unittest.mock import patch

import bib_core as core
from executar import afirmar
from test_qt import _aguardar, _encontrar, _qt


def teste_qt_video_importa_pesquisa_e_ferramentas_sem_executar_programa():
    app, bridge = _qt()
    if app is None:
        return
    from PySide6.QtCore import QMetaObject, QObject, QUrl, qInstallMessageHandler
    from PySide6.QtTest import QTest
    from shiboken6 import delete
    from app_qt import criar_engine
    avisos = []
    anterior = qInstallMessageHandler(lambda _t, _c, m: avisos.append(m))
    engine = criar_engine(bridge)
    try:
        afirmar(engine.rootObjects(), avisos)
        window = engine.rootObjects()[0]
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        pasta = Path(tempfile.mkdtemp())
        (pasta / "Filme.mp4").write_bytes(b"video-de-teste" * 100)
        bridge.importarVideos(QUrl.fromLocalFile(str(pasta)))
        _aguardar(app, lambda: not bridge.ocupado)
        bridge.navegar("videos")
        afirmar(bridge.quantidade == 1 and bridge.selecionado["titulo"] == "Filme")
        for largura, altura in ((960, 640), (1200, 800), (1440, 920)):
            window.setWidth(largura); window.setHeight(altura)
            QTest.qWait(60)
            for nome in ("nav_videos", "settingsButton"):
                item = _encontrar(window.contentItem(), nome)
                afirmar(item is not None and item.mapToItem(window.contentItem(), item.width(), 0).x() <= largura, nome)
        mid = bridge.selecionado["id"]
        with patch.object(bridge.servico, "reproduzir_video", return_value={"ok": True}) as play:
            bridge.reproduzirVideo(mid, "mpv")
            _aguardar(app, lambda: not bridge.ocupado)
            afirmar(play.call_args.args == (mid, "mpv"))
        resultado = {"itens": [{"video_id": "dQw4w9WgXcQ", "titulo": "Clipe", "canal": "Canal",
                                "thumb": "", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "duracao_s": 212}], "erros": []}
        with patch.object(bridge.servico, "buscar_videos_online", return_value=resultado):
            bridge.buscarVideos("clipe", False)
            _aguardar(app, lambda: not bridge.ocupado)
        afirmar(len(bridge.video_resultados.itens) == 1)
        dialogo = window.findChild(QObject, "youtubeDialog")
        QMetaObject.invokeMethod(dialogo, "open"); QTest.qWait(50)
        QMetaObject.invokeMethod(dialogo, "close")
        with patch.object(bridge.servico, "midias_status", return_value={
                "imagens": {"krita": {"nome": "Krita", "instalado": True, "site": "https://krita.org", "suportado": True}},
                "equalizadores": {}, "videos": {}, "eq_presets": ["bass"]}):
            dialogo = window.findChild(QObject, "mediaToolsDialog")
            QMetaObject.invokeMethod(dialogo, "open")
            _aguardar(app, lambda: not bridge.ocupado)
            QTest.qWait(50)
            afirmar(bridge.midiasStatus["imagens"]["krita"]["instalado"])
            QMetaObject.invokeMethod(dialogo, "close")
        erros = [m for m in avisos if any(s in m for s in
                 ("ReferenceError", "TypeError", "Unable to assign", "Binding loop", "is not defined"))]
        afirmar(not erros, "\n".join(erros))
    finally:
        bridge.fechar(); delete(engine); qInstallMessageHandler(anterior)


def teste_qt_spotify_aparece_e_erros_de_busca_ficam_inline():
    app, bridge = _qt()
    if app is None:
        return
    try:
        faixa = {"id": "a" * 22, "uri": "spotify:track:" + "a" * 22,
                 "titulo": "Faixa Spotify", "artista": "Autor", "album": "Álbum", "capa_url": ""}
        with patch.object(bridge.servico.spotify, "consultar", return_value={"itens": [faixa], "next": ""}):
            bridge.consultarSpotify("salvas", "", False)
            _aguardar(app, lambda: not bridge.ocupado)
        afirmar(bridge.musica_online_resultados.itens[0]["titulo"] == "Faixa Spotify")
        with patch.object(bridge.servico, "buscar_musicas_online", side_effect=ValueError("Configuração Spotify ausente")):
            bridge.pesquisarMusicas("Autor", "spotify", False)
            _aguardar(app, lambda: not bridge.ocupado)
        afirmar(bridge.musicaOnlineMensagem == "Configuração Spotify ausente")
        afirmar("Buscando" not in bridge.musicaOnlineMensagem)
    finally:
        bridge.fechar()


def teste_eq_gera_copia_importada_sem_sobrescrever_original():
    from servicos_ui import ServicoBiblioteca
    pasta = Path(tempfile.mkdtemp())
    original = pasta / "Autor - Faixa.wav"
    original.write_bytes(b"audio-original")
    saida = pasta / "eq.wav"
    saida.write_bytes(b"audio-equalizado")
    svc = ServicoBiblioteca(pasta / "colecao.db")
    with patch.object(core, "aplicar_eq", return_value={"ok": True, "path": str(saida)}):
        svc.aplicar_eq_musica(str(original), "bass")
    afirmar(original.read_bytes() == b"audio-original")
    afirmar(svc.snapshot()["musicas"][0]["titulo"] == "Faixa [EQ: bass]")
