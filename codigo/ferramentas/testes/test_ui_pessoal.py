"""Contratos Qt dos recursos pessoais e das variantes essenciais/completas."""
import os
from pathlib import Path
from unittest.mock import patch

from executar import afirmar
from test_qt import _qt, _aguardar, _encontrar


def teste_qt_youtube_navega_fallback_e_slots_retornam_ao_qml():
    with patch.dict(os.environ, BIBLIOTECA_WEBENGINE="0"):
        app, bridge = _qt()
        if app is None:
            return
        from PySide6.QtQml import QQmlExpression
        from PySide6.QtCore import qInstallMessageHandler
        from shiboken6 import delete
        from app_qt import criar_engine
        erros = []
        anterior = qInstallMessageHandler(lambda t, c, m: erros.append(m))
        engine = criar_engine(bridge)
        try:
            afirmar(engine.rootObjects(), erros)
            bridge.navegar("youtube")
            app.processEvents()
            afirmar(bridge.secao == "youtube" and not bridge.webDisponivel)
            expr = QQmlExpression(engine.rootContext(), None, 'hub.youtubeBuscar("teste musica")', engine)
            valor, indefinido = expr.evaluate()
            afirmar(not indefinido and "search_query=teste%20musica" in valor, valor)
            expr.setExpression('hub.youtubeIr("https://youtu.be/abcdefghijk", "")')
            valor, indefinido = expr.evaluate()
            afirmar(not indefinido and valor == "https://youtu.be/abcdefghijk")
            for ruim in ("http://youtube.com/", "https://youtube.com.evil.example/", "https://x@youtube.com/", "https://youtube.com:444/"):
                afirmar(bridge.youtubeIr(ruim) == "", ruim)
            reais = [e for e in erros if any(x in e for x in ("ReferenceError", "TypeError", "Binding loop", "Unable to assign"))]
            afirmar(not reais, reais)
        finally:
            bridge.fechar()
            delete(engine)
            qInstallMessageHandler(anterior)


def teste_qt_dialogos_pessoais_saves_atalhos_e_perfis():
    app, bridge = _qt()
    if app is None:
        return
    from PySide6.QtCore import QObject, QMetaObject, qInstallMessageHandler
    from PySide6.QtTest import QTest
    from shiboken6 import delete
    from app_qt import criar_engine
    erros = []
    anterior = qInstallMessageHandler(lambda t, c, m: erros.append(m))
    engine = criar_engine(bridge)
    try:
        afirmar(engine.rootObjects(), erros)
        janela = engine.rootObjects()[0]
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        janela.setWidth(960)
        janela.setHeight(640)
        pessoal = janela.findChild(QObject, "personalToolsDialog")
        QMetaObject.invokeMethod(pessoal, "open")
        _aguardar(app, lambda: not bridge.ocupado)
        QTest.qWait(60)
        afirmar(pessoal.property("visible"))
        bridge.salvarAtalho("paleta", "Alt+K")
        afirmar(bridge.preferencias["atalhos"]["paleta"] == "Alt+K")
        bridge.trocarPerfil("Isa")
        _aguardar(app, lambda: not bridge.ocupado)
        afirmar(bridge.preferencias["ativo"] == "Isa")
        QMetaObject.invokeMethod(pessoal, "close")
        bridge.navegar("jogos")
        ferramentas = janela.findChild(QObject, "gameToolsDialog")
        ferramentas.setProperty("gid", bridge.selecionado["id"])
        QMetaObject.invokeMethod(ferramentas, "open")
        _aguardar(app, lambda: not bridge.ocupado)
        QTest.qWait(60)
        afirmar(_encontrar(janela.contentItem(), "savePathsField") is not None)
        afirmar(bridge.ferramentasJogo["pasta_screenshots"])
        QMetaObject.invokeMethod(ferramentas, "close")
        afirmar(bridge._ferramentas_gid == 0)
        reais = [e for e in erros if any(x in e for x in ("ReferenceError", "TypeError", "Binding loop", "Unable to assign", "is not defined"))]
        afirmar(not reais, reais)
    finally:
        bridge.fechar()
        delete(engine)
        qInstallMessageHandler(anterior)


def teste_qt_backup_pos_sessao_acontece_depois_de_gravar_horas():
    app, bridge = _qt()
    if app is None:
        return
    try:
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        gid = bridge._dados["jogos"][0]["id"]
        observado = []
        def backup(ident):
            observado.append(bridge.servico.jogo(ident)["horas"])
            return {"saves": {"ok": True, "arquivos": 1}}
        with patch.object(bridge.servico, "backup_pos_sessao", side_effect=backup):
            bridge._fim_jogo(gid, 2, True)
            _aguardar(app, lambda: not bridge.ocupado)
        afirmar(observado == [2], observado)
    finally:
        bridge.fechar()


def teste_youtube_mp3_por_id_sem_busca_e_importacao_local():
    import bib_core as core
    import tempfile
    from bib_nucleo.rede import videos_youtube as V
    raiz = Path(tempfile.mkdtemp())
    con = core.get_db(raiz / "b.db")
    comandos = []
    def executar(cmd, receber, timeout):
        comandos.append(cmd)
        template = cmd[cmd.index("-o") + 1]
        Path(template.replace("%(id)s", "abcdefghijk").replace("%(ext)s", "mp3")).write_bytes(b"ID3audio-teste")
        return 0
    try:
        with patch.object(V, "_ytdlp", return_value="yt-dlp.exe"), \
             patch("bib_nucleo.baixar.localizar_ffmpeg", return_value="ffmpeg.exe"), \
             patch.object(V, "info_video_youtube", return_value={"titulo": "Faixa", "canal": "Artista"}), \
             patch.object(V, "executar_com_progresso", side_effect=executar):
            r = V.baixar_audio_youtube(con, "https://youtu.be/abcdefghijk")
        afirmar(r["ok"], r)
        afirmar(core.listar_musicas(con)[0]["titulo"] == "Faixa")
        cmd = comandos[0]
        afirmar("--ignore-config" in cmd and "--no-playlist" in cmd and "--extract-audio" in cmd)
        afirmar(any("watch?v=abcdefghijk" in a for a in cmd) and not any("ytsearch" in a for a in cmd))
    finally:
        con.close()
