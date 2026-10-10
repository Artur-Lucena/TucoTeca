"""Contratos desktop e GUI Qt Quick offscreen, sem rede/jogos/áudio reais."""
import os
import tempfile
import threading
import time
from pathlib import Path

import bib_core as core
from executar import afirmar
from servicos_ui import Integracao, RegistroIntegracoes, ServicoBiblioteca


def _base():
    db = Path(tempfile.mkdtemp()) / "colecao.db"
    con = core.get_db(db)
    for i in range(18):
        core.criar_jogo(con, {"titulo": f"Aventura {i:02d}", "favorito": i % 2,
                              "executable_path": str(db.parent / f"game{i}.exe")})
    core.adicionar_desejo(con, "123", "Jogo desejado")
    core.criar_musica(con, {"titulo": "Faixa de teste", "musica_path": str(db.parent / "teste.wav"),
                           "musica_sha": "a" * 64, "artista": "Artista"})
    con.close()
    return db


def _qt():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ["QML_DISABLE_DISK_CACHE"] = "1"
    try:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQuickControls2 import QQuickStyle
        from qt_bridge import HubBridge
    except ImportError:
        print("[pula] PySide6 opcional não instalado")
        return None, None
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication.instance() or QGuiApplication([])
    bridge = HubBridge(_base())
    return app, bridge


def _aguardar(app, condicao, segundos=10):
    fim = time.monotonic() + segundos
    while time.monotonic() < fim:
        app.processEvents()
        if condicao():
            app.processEvents()
            return
        time.sleep(0.01)
    raise AssertionError("Qt não concluiu a operação no prazo")


def teste_servico_desktop_crud_backup_e_snapshot():
    servico = ServicoBiblioteca(_base())
    dados = servico.snapshot()
    afirmar(len(dados["jogos"]) == 18 and len(dados["musicas"]) == 1)
    jogo = dados["jogos"][0]
    servico.favorito(jogo["id"])
    afirmar(servico.jogo(jogo["id"])["favorito"] != jogo["favorito"])
    servico.salvar_jogo(jogo["id"], {"titulo": "Renomeado"})
    afirmar(servico.jogo(jogo["id"])["titulo"] == "Renomeado")
    afirmar(list(core.BACKUP_DIR.glob("*.db")), "alteração sem backup")
    servico.excluir("desejos", dados["desejos"][0]["id"])
    afirmar(not servico.snapshot()["desejos"])


def teste_servico_registro_integracoes_extensivel():
    registro = RegistroIntegracoes()
    registro.registrar(Integracao("teste", "Teste", "Adaptador fake", "catalogo", "T", "#fff",
                                  lambda q: {"itens": [{"titulo": q}], "erros": []}))
    afirmar("buscar" not in registro.listar()[0], "callable vazou no DTO")
    afirmar(registro.buscar("teste", "Jogo")["itens"][0]["titulo"] == "Jogo")
    try:
        registro.registrar(Integracao("teste", "Outro", "", "", "", ""))
    except ValueError:
        pass
    else:
        raise AssertionError("registro sobrescreveu adaptador existente")


def teste_qt_modelos_filtros_e_categorias():
    app, bridge = _qt()
    if app is None:
        return
    try:
        erros = []
        bridge.aviso.connect(lambda m, e: erros.append(m) if e else None)
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        afirmar(bridge.secao == "inicio" and bridge.sistema["jogos"] == 18, bridge.secao)
        bridge.navegar("jogos")
        afirmar(bridge.quantidade == 18)
        bridge.selecionar(5)
        gid = bridge.selecionado["id"]
        bridge.ordenar("horas")
        afirmar(bridge.selecionado["id"] == gid, "ordenação perdeu identidade")
        bridge.filtrar("favoritos")
        afirmar(bridge.quantidade == 9)
        bridge.pesquisar("não existe")
        _aguardar(app, lambda: bridge.quantidade == 0)
        afirmar(bridge.selecionado == {})
        bridge.navegar("musicas")
        afirmar(bridge.quantidade == 1 and bridge.busca == "")
        bridge.navegar("desejos")
        afirmar(bridge.selecionado["appid"] == "123")
        bridge.navegar("integracoes")
        afirmar(len(bridge.integracoes) == 5)
        afirmar(not erros, erros)
    finally:
        bridge.fechar()


def teste_qt_workers_entregam_na_thread_da_ui():
    app, bridge = _qt()
    if app is None:
        return
    try:
        ui = threading.get_ident()
        resultado = []
        bridge.executar("Prova", threading.get_ident,
                        lambda tid: resultado.append((tid, threading.get_ident())))
        _aguardar(app, lambda: not bridge.ocupado)
        afirmar(resultado and resultado[0][0] != ui and resultado[0][1] == ui, resultado)
        erros = []
        bridge.aviso.connect(lambda m, e: erros.append(m) if e else None)
        bridge.executar("Falha simulada", lambda: 1 / 0)
        _aguardar(app, lambda: not bridge.ocupado)
        afirmar(erros, "falha de worker ficou silenciosa")
    finally:
        bridge.fechar()


def teste_qt_audio_preparo_worker_transporte_ui_e_navegacao():
    app, bridge = _qt()
    if app is None:
        return
    chamadas = []

    class Fake(core.NuloBackend):
        def preparar(self, path):
            chamadas.append(("preparar", threading.get_ident()))
            return {"ok": True, "alvo": path}

        def open(self, path):
            chamadas.append(("open", threading.get_ident()))
            return {"ok": True}

        def play(self):
            chamadas.append(("play", threading.get_ident()))
            return {"ok": True}

        def terminou(self):
            return False

    try:
        bridge._player = core.Player(Fake())
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        bridge.navegar("musicas")
        bridge.tocar(bridge.selecionado["id"])
        _aguardar(app, lambda: not bridge.ocupado)
        afirmar(bridge.audio["estado"] == "tocando")
        bridge.navegar("jogos")
        afirmar(bridge.audio["estado"] == "tocando", "troca de categoria parou a faixa")
        ui = threading.get_ident()
        afirmar(chamadas[0][1] != ui and all(t == ui for _c, t in chamadas[1:]), chamadas)
        bridge.transporte("parar")
        afirmar(bridge.audio["estado"] == "parado")
    finally:
        bridge.fechar()


def teste_qt_qml_hud_todas_categorias_em_tela_cheia():
    app, bridge = _qt()
    if app is None:
        return
    from PySide6.QtCore import QMetaObject, qInstallMessageHandler
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtCore import QUrl
    from shiboken6 import delete
    erros = []
    anterior = qInstallMessageHandler(lambda t, c, m: erros.append(m))
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("hub", bridge)
    caminho = Path(__file__).parents[2] / "frontends/qml/Main.qml"

    def encontrar(item, nome):
        if item.objectName() == nome:
            return item
        for filho in item.childItems():
            achado = encontrar(filho, nome)
            if achado is not None:
                return achado
        return None
    try:
        engine.load(QUrl.fromLocalFile(str(caminho)))
        afirmar(engine.rootObjects(), erros)
        janela = engine.rootObjects()[0]
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        QMetaObject.invokeMethod(janela, "toggleImmersive")
        afirmar(janela.property("immersive"), "não entrou em tela cheia")
        for secao in ("inicio", "musicas", "desejos", "downloads", "integracoes", "jogos"):
            botao = encontrar(janela.contentItem(), "nav_" + secao)
            afirmar(botao is not None and botao.property("visible"), "aba ausente: " + secao)
            QMetaObject.invokeMethod(botao, "clicked")
            _aguardar(app, lambda: not bridge.ocupado)
            afirmar(bridge.secao == secao and janela.property("immersive"), "navegação saiu do modo imersivo")
        for largura, altura in ((960, 640), (1440, 920)):
            janela.setWidth(largura)
            janela.setHeight(altura)
            app.processEvents()
        QMetaObject.invokeMethod(janela, "toggleImmersive")
        afirmar(not janela.property("immersive"))
        janela.setWidth(960)
        janela.setHeight(640)
        app.processEvents()
        grade = encontrar(janela.contentItem(), "gamesGrid")
        afirmar(grade.height() >= 200, "HUD engoliu a grade na janela compacta")
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        grade.forceActiveFocus()
        antes = bridge.indiceSelecionado
        QTest.keyClick(janela, Qt.Key_Right)
        app.processEvents()
        afirmar(bridge.indiceSelecionado == antes + 1, "teclado não navegou na grade")
        erros_reais = [e for e in erros if any(x in e for x in
                       ("ReferenceError", "TypeError", "Unable to assign", "Binding loop", "failed to load", "is not defined"))]
        afirmar(not erros_reais, "\n".join(erros_reais))
    finally:
        bridge.fechar()
        delete(engine)
        qInstallMessageHandler(anterior)


def teste_qt_resposta_catalogo_obsoleta_nao_sobrescreve():
    app, bridge = _qt()
    if app is None:
        return
    liberar = threading.Event()
    entrou = threading.Event()

    def busca(termo):
        if termo == "antigo":
            entrou.set()
            liberar.wait(5)
        return {"itens": [{"titulo": termo, "url": "https://example.com"}]}
    bridge.servico.integracoes.registrar(Integracao("fake", "Fake", "", "catalogo", "", "", busca))
    try:
        bridge.buscarIntegracao("fake", "antigo")
        afirmar(entrou.wait(2))
        bridge.buscarIntegracao("fake", "novo")
        _aguardar(app, lambda: bridge.resultados.rowCount() == 1)
        liberar.set()
        _aguardar(app, lambda: not bridge.ocupado)
        afirmar(bridge.resultados.itens[0]["titulo"] == "novo")
    finally:
        liberar.set()
        bridge.fechar()


def teste_qt_parar_durante_preparo_nao_inicia_audio_tardio():
    app, bridge = _qt()
    if app is None:
        return
    liberar = threading.Event()
    iniciou = threading.Event()
    aberturas = []

    class Fake(core.NuloBackend):
        def preparar(self, path):
            iniciou.set()
            liberar.wait(5)
            return {"ok": True, "alvo": path}

        def open(self, path):
            aberturas.append(path)
            return {"ok": True}

    try:
        bridge._player = core.Player(Fake())
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        bridge.navegar("musicas")
        bridge.tocar(bridge.selecionado["id"])
        afirmar(iniciou.wait(2))
        bridge.transporte("parar")
        liberar.set()
        _aguardar(app, lambda: not bridge.ocupado)
        afirmar(not aberturas and bridge.audio["estado"] == "parado", "preparo obsoleto abriu áudio")
    finally:
        liberar.set()
        bridge.fechar()


def teste_qt_inicio_paleta_e_sistema_local():
    app, bridge = _qt()
    if app is None:
        return
    try:
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        afirmar(bridge.sistema["jogos"] == 18 and bridge.sistema["musicas"] == 1, bridge.sistema)
        afirmar("backup" in bridge.sistema and "disco_livre_gb" in bridge.sistema)
        afirmar(len(bridge.recentes) <= 4)
        bridge.buscarPaleta("aventura 01")
        afirmar(bridge.paletaQuantidade >= 1, "paleta não achou jogo local")
        primeiro = dict(bridge.global_resultados.itens[0])
        afirmar(primeiro["tipo"] == "jogo")
        bridge.buscarPaleta("faixa de teste")
        afirmar(bridge.global_resultados.itens[0]["tipo"] == "musica")
        bridge.buscarPaleta("zzz sem resultado")
        afirmar(bridge.paletaQuantidade == 0)
        bridge.buscarPaleta("")
        afirmar(bridge.paletaQuantidade == 0, "paleta vazia deveria limpar")
    finally:
        bridge.fechar()


def teste_qt_qol_biblioteca_player_sistema():
    app, bridge = _qt()
    if app is None:
        return
    try:
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        saude = bridge.saude
        afirmar(saude["total"] == 18 and "problemas" in saude, saude)
        bridge.navegar("jogos")
        gid = bridge.selecionado["id"]
        bridge.salvarJogo(gid, bridge.selecionado["titulo"], "", "", "jogando", "9", "rpg, qol")
        _aguardar(app, lambda: not bridge.ocupado)
        afirmar(bridge.servico.jogo(gid)["nota"] == 9, "nota não gravou")
        afirmar("qol" in (bridge.servico.jogo(gid)["etiquetas"] or ""), "etiqueta não gravou")
        bridge.modoAudio("aleatorio")
        afirmar(bridge.modoAudioAtual == "aleatorio")
        bridge.modoAudio("repetir")
        afirmar(bridge.modoAudioAtual == "repetir")
        bridge.navegar("musicas")
        bridge.tocar(bridge.selecionado["id"])
        _aguardar(app, lambda: not bridge.ocupado)
        afirmar(len(bridge.filaAudio) == 1 and bridge.filaAudio[0]["titulo"] == "Faixa de teste",
                bridge.filaAudio)
        afirmar(isinstance(bridge.listarBackups(), list))
        afirmar(isinstance(bridge.listarSessoes(), list))
        afirmar(isinstance(bridge.verLog(), str) and bridge.verLog(), "log vazio")
        bridge.buscarPaleta("aventura")
        afirmar(bridge.paletaQuantidade >= 1)
        item = bridge.paletaItem(0)
        afirmar(item.get("titulo"), "paletaItem não devolveu DTO")
        afirmar(bridge.paletaItem(9999) == {}, "índice inválido deveria ser {}")
    finally:
        bridge.fechar()


def teste_qt_fontes_e_builders_incluem_recursos_qml():
    import sys
    sys.path.insert(0, str(Path(__file__).parents[1]))
    import empacotar_fontes as pacote
    import montar_portatil as montar
    repo = Path(__file__).parents[3]
    fontes = {p.relative_to(repo).as_posix() for p in pacote.listar_fontes(repo)}
    for nome in ("requirements-ui.txt", "codigo/frontends/qml/qmldir",
                 "codigo/frontends/qml/Main.qml", "codigo/frontends/desktop.py"):
        afirmar(nome in fontes, "entrega sem " + nome)
    dest = Path(tempfile.mkdtemp()) / "app"
    montar.copiar_app(dest)
    afirmar((dest / "qml/Main.qml").is_file() and (dest / "qml/qmldir").is_file())
    afirmar((dest / "qt_bridge.py").is_file() and (dest / "desktop.py").is_file())
