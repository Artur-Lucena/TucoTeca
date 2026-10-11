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


def _encontrar(item, nome):
    if item.objectName() == nome:
        return item
    for filho in item.childItems():
        achado = _encontrar(filho, nome)
        if achado is not None:
            return achado
    return None


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
        afirmar({"spotify", "capas", "steamrip", "fitgirl", "azahar", "desmume", "qbittorrent"} ==
                {i["chave"] for i in bridge.integracoes})
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
        afirmar(bridge.filaAudio[0]["atual"], "primeira faixa não está marcada como atual")
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

    encontrar = _encontrar
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
        afirmar(bridge.paletaItem(-1) == {}, "índice negativo abriu o último resultado")
    finally:
        bridge.fechar()


def teste_servico_integracao_personalizada_persiste_e_valida():
    from servicos_ui import (INTEGRACAO_TIPOS, carregar_personalizadas, integracoes_padrao,
                             url_integracao)
    from bib_nucleo import online
    servico = ServicoBiblioteca(_base())
    n_antes = len(servico.integracoes.listar())
    for ruim in ({"chave": "x", "nome": "N", "descricao": "", "tipo": "link", "url": "https://a.example/"},
                 {"chave": "ok", "nome": "N", "descricao": "", "tipo": "virus", "url": "https://a.example/"},
                 {"chave": "ok", "nome": "N", "descricao": "", "tipo": "link", "url": "http://inseguro.example/"},
                 {"chave": "ok", "nome": "N", "descricao": "", "tipo": "link", "url": "javascript:alert(1)"},
                 {"chave": "steamrip", "nome": "Clone", "descricao": "", "tipo": "link", "url": "https://a.example/"}):
        try:
            servico.adicionar_integracao(ruim)
        except ValueError:
            pass
        else:
            raise AssertionError(f"aceitou integração inválida: {ruim}")
    item = servico.adicionar_integracao({"chave": "meu-site", "nome": "Meu Site",
                                         "descricao": "Busca de mods",
                                         "tipo": "catalogo", "url": "https://a.example/busca?q={q}"})
    afirmar(item["inicial"] and item["cor"].startswith("#"), item)
    chaves = {i["chave"] for i in servico.integracoes.listar()}
    afirmar(len(chaves) == n_antes + 1 and "meu-site" in chaves, chaves)
    afirmar("buscar" not in servico.integracoes.listar()[-1], "callable vazou no DTO")
    url = servico.url_integracao("meu-site", "zelda rpg")
    afirmar(url == "https://a.example/busca?q=zelda+rpg", url)
    try:
        servico.url_integracao("azahar")
    except ValueError:
        pass
    else:
        raise AssertionError("abriu URL de integração sem URL")
    try:
        servico.remover_integracao("steamrip")
    except ValueError:
        pass
    else:
        raise AssertionError("removeu integração padrão")
    servico.remover_integracao("meu-site")
    afirmar("meu-site" not in {i["chave"] for i in servico.integracoes.listar()})
    afirmar(isinstance(carregar_personalizadas(), list))
    afirmar("link" in INTEGRACAO_TIPOS and isinstance(online.ler_json(
        online.base.DADOS_DIR / "integracoes-usuario.json", []), list))


def teste_qt_torrent_hub_organizar_e_botao_magnet():
    app, bridge = _qt()
    if app is None:
        return
    from PySide6.QtCore import QMetaObject, QObject, qInstallMessageHandler
    from shiboken6 import delete
    from app_qt import criar_engine
    from unittest.mock import patch
    avisos = []
    anterior = qInstallMessageHandler(lambda t, c, m: avisos.append(m))
    engine = criar_engine(bridge)
    try:
        afirmar(engine.rootObjects(), avisos)
        janela = engine.rootObjects()[0]
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        afirmar(bridge.foraDoDestino("C:/Downloads/Jogo") and not bridge.foraDoDestino(""), "foraDoDestino")
        msgs = []
        bridge.aviso.connect(lambda m, e: msgs.append((m, e)))
        magnet = "magnet:?xt=urn:btih:" + "b" * 40
        with patch.object(bridge.servico, "baixar_torrent_hub",
                          return_value={"ok": True, "destino": "P:/Meus Jogos Locais"}) as add:
            bridge.baixarTorrent(magnet)
            _aguardar(app, lambda: not bridge.ocupado)
            afirmar(add.call_args.args == (magnet,), add.call_args)
            afirmar(any("P:/Meus Jogos Locais" in m for m, _e in msgs), msgs)
        with patch.object(bridge.servico, "organizar_download",
                          return_value={"ok": True, "path": "P:/Meus Jogos Locais/Jogo", "movido": True}):
            bridge.organizarDownload("C:/Downloads/Jogo")
            _aguardar(app, lambda: not bridge.ocupado)
            afirmar(any("Movido" in m for m, _e in msgs), msgs)
        with patch.object(bridge.servico.integracoes, "buscar", return_value={
                "itens": [{"titulo": "Jogo [FitGirl]", "url": magnet}], "erros": []}):
            bridge.buscarIntegracao("fitgirl", "algum jogo")
            _aguardar(app, lambda: not bridge.ocupado)
        dialogo = janela.findChild(QObject, "catalogDialog")
        afirmar(dialogo is not None)
        dialogo.setProperty("provider", "fitgirl")
        QMetaObject.invokeMethod(dialogo, "open")
        app.processEvents()
        botao = _encontrar(janela.contentItem(), "hubDownloadButton")
        afirmar(botao is not None and botao.property("visible"), "botão Baixar no Hub sumiu p/ magnet")
        QMetaObject.invokeMethod(dialogo, "close")
        erros = [m for m in avisos if any(x in m for x in
                 ("ReferenceError", "TypeError", "Unable to assign", "Binding loop", "is not defined"))]
        afirmar(not erros, "\n".join(erros))
    finally:
        bridge.fechar()
        delete(engine)
        qInstallMessageHandler(anterior)


def teste_qt_musica_online_busca_seleciona_enfileira():
    app, bridge = _qt()
    if app is None:
        return
    from PySide6.QtCore import QMetaObject, QObject, qInstallMessageHandler
    from shiboken6 import delete
    from app_qt import criar_engine
    from unittest.mock import patch
    faixas = [{"titulo": "Faixa Grátis", "artista": "Artista", "album": "Álbum",
               "duracao_ms": 200000, "capa_url": "", "url": "https://www.deezer.com/track/9",
               "uri": "deezer:track:9", "fonte": "deezer", "nome_fonte": "Deezer"}]
    avisos = []
    anterior = qInstallMessageHandler(lambda t, c, m: avisos.append(m))
    engine = criar_engine(bridge)
    try:
        afirmar(engine.rootObjects(), avisos)
        janela = engine.rootObjects()[0]
        janela.setWidth(960)
        janela.setHeight(640)
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        afirmar("sem conta" in bridge.musicaOnlineMensagem, bridge.musicaOnlineMensagem)
        with patch.object(bridge.servico, "buscar_musicas_online",
                          return_value={"itens": faixas, "erros": [], "cache": False}):
            bridge.pesquisarMusicas("artista faixa", "todas")
            _aguardar(app, lambda: not bridge.ocupado)
        afirmar(len(bridge.musicaOnlineItens.itens) == 1, bridge.musicaOnlineMensagem)
        afirmar("1 resultado" in bridge.musicaOnlineMensagem, bridge.musicaOnlineMensagem)
        bridge.alternarMusicaOnline("deezer:track:9", True)
        afirmar(bridge.musicaOnlineSelecionados == ["deezer:track:9"])
        bridge.alternarMusicaOnline("deezer:track:9", False)
        afirmar(bridge.musicaOnlineSelecionados == [])
        bridge.selecionarTodasMusicasOnline(True)
        bridge.enfileirarMusicasOnline(False)
        _aguardar(app, lambda: not bridge.ocupado)
        fila = bridge.filaMusicas
        # URI é identidade estável do catálogo; URL é o endereço de navegação.
        afirmar(len(fila) == 1 and fila[0]["uri"] == faixas[0]["uri"], fila)
        dialogo = janela.findChild(QObject, "spotifyDialog")
        QMetaObject.invokeMethod(dialogo, "open")
        app.processEvents()
        for nome in ("spotifySearchField", "musicSourceBox", "musicSearchStatus"):
            afirmar(_encontrar(janela.contentItem(), nome) is not None, nome)
        QMetaObject.invokeMethod(dialogo, "close")
        erros = [m for m in avisos if any(x in m for x in
                 ("ReferenceError", "TypeError", "Unable to assign", "Binding loop", "is not defined"))]
        afirmar(not erros, "\n".join(erros))
    finally:
        bridge.fechar()
        delete(engine)
        qInstallMessageHandler(anterior)


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
    for nome in ("VolumeControl", "ProvidersDialog", "CoversDialog", "AchievementsDialog",
                 "SpotifyDialog", "MusicDownloadsDialog"):
        afirmar((dest / "qml" / (nome + ".qml")).is_file(), "bundle sem " + nome)
    for nome in ("capas", "conquistas"):
        afirmar((dest / "bib_nucleo" / (nome + ".py")).is_file(), "bundle sem domínio " + nome)
    afirmar((dest / "bib_nucleo" / "rede" / "__init__.py").is_file(), "bundle sem bib_nucleo/rede")
    for nome in ("online", "spotify"):
        afirmar((dest / "bib_nucleo" / "rede" / (nome + ".py")).is_file(),
                "bundle sem domínio de rede " + nome)
    afirmar(any(p == "codigo/bib_nucleo/rede/online.py" for p in fontes),
            "entrega sem bib_nucleo/rede/online.py")


def teste_servico_saude_total_real_e_idade_backup():
    from unittest.mock import patch
    from servicos_ui import resumo_sistema, saude_colecao
    servico = ServicoBiblioteca(_base())
    jogos = servico.snapshot()["jogos"]
    saude = saude_colecao(jogos)
    afirmar(saude["total"] == 18 and saude["ok"] == 0 and saude["pendentes"] == 18, saude)
    afirmar(len(saude["problemas"]) == 8 and len(saude["ids_pendentes"]) == 18,
            "limite de resumo truncou o diagnóstico")
    sem_lista = saude_colecao(jogos, limite=0)
    afirmar(sem_lista["ok"] == 0 and not sem_lista["problemas"])
    for idade, estado in ((None, "ausente"), (0.5, "recente"), (6.99, "recente"), (7, "antigo")):
        with patch.object(core, "idade_ultimo_backup_dias", return_value=idade):
            resumo = resumo_sistema([], [], [])
            afirmar(resumo["backup_estado"] == estado, resumo)
            afirmar(resumo["backup_idade_dias"] == idade)
    with patch.object(core, "idade_ultimo_backup_dias", side_effect=OSError("indisponível")):
        afirmar(resumo_sistema([], [], [])["backup_estado"] == "indisponivel")


def teste_qt_paleta_supera_filtros_e_seleciona_resultado_exato():
    app, bridge = _qt()
    if app is None:
        return
    try:
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        bridge.navegar("jogos")
        bridge.filtrar("favoritos")
        bridge.pesquisar("sem resultado")
        _aguardar(app, lambda: bridge.quantidade == 0)
        bridge.buscarPaleta("aventura 00")
        alvo = bridge.paletaItem(0)
        bridge.abrirPaleta(alvo)
        afirmar(bridge.filtro == "todos" and bridge.busca == "")
        afirmar(bridge.selecionado["id"] == alvo["id"], "paleta selecionou outro jogo")
        bridge.verPendencias()
        afirmar(bridge.quantidade == 18, "filtro de pendências escondeu jogos além dos 8 do resumo")
        afirmar("Com pendências" in bridge.resumoLista and "18 de 18 jogos" in bridge.resumoLista)
        bridge.pesquisar("aventura 01")
        _aguardar(app, lambda: bridge.quantidade == 1)
        afirmar("busca “aventura 01”" in bridge.resumoLista)
        bridge.limparFiltros()
        afirmar(bridge.quantidade == 18 and bridge.busca == "" and bridge.filtro == "todos")
        bridge.servico.adicionar_desejo("456", "Segundo desejo")
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        bridge.buscarPaleta("segundo desejo")
        desejo = bridge.paletaItem(0)
        bridge.abrirPaleta(desejo)
        afirmar(bridge.secao == "desejos" and bridge.selecionado["id"] == desejo["id"])
        bridge._atualizar_downloads = lambda: None
        bridge._dados["downloads"] = [{"hash": "um", "nome": "Primeiro"},
                                     {"hash": "dois", "nome": "Segundo"}]
        bridge.buscarPaleta("segundo")
        download = next(i for i in bridge.global_resultados.itens if i["tipo"] == "download")
        bridge.abrirPaleta(download)
        afirmar(bridge.secao == "downloads" and bridge.selecionado["hash"] == "dois")
    finally:
        bridge.fechar()


def teste_servico_sessao_registra_na_colecao_certa_e_fecha_marcador():
    servico = ServicoBiblioteca(_base())
    gid = servico.snapshot()["jogos"][0]["id"]
    outra = core.get_db(core.DEFAULT_DB)
    try:
        core.criar_jogo(outra, {"titulo": "Outra coleção", "horas": 7})
    finally:
        outra.close()
    sessao = core.iniciar_sessao_manual(gid, "Aventura 00")
    afirmar(sessao["ok"], sessao)
    marcador = Path(sessao["arquivo"])
    for horas in (-1, 0, float("nan"), float("inf")):
        try:
            servico.encerrar_sessao(str(marcador), horas)
        except ValueError:
            pass
        else:
            raise AssertionError("aceitou horas inválidas")
        afirmar(marcador.is_file(), "entrada inválida removeu a sessão")
    resultado = servico.encerrar_sessao(str(marcador), 1.5)
    afirmar(resultado["ok"] and resultado["somado"] == 1.5, resultado)
    afirmar(servico.jogo(gid)["horas"] == 1.5 and not marcador.exists())
    afirmar((core.BACKUP_DIR / "sessoes" / marcador.name).is_file(), "marcador sem backup")
    backup = core.get_db(next(core.BACKUP_DIR.glob("biblioteca-*.db")))
    try:
        afirmar(backup.execute("SELECT horas FROM jogos WHERE id=?", (gid,)).fetchone()[0] == 0,
                "backup foi feito depois de somar as horas")
    finally:
        backup.close()
    try:
        servico.encerrar_sessao(str(marcador), 1.5)
    except ValueError:
        pass
    else:
        raise AssertionError("repetiu o registro de uma sessão encerrada")
    afirmar(servico.jogo(gid)["horas"] == 1.5)
    outra = core.get_db(core.DEFAULT_DB)
    try:
        afirmar(core.listar_jogos(outra)[0]["horas"] == 7, "escreveu no banco padrão")
    finally:
        outra.close()


def teste_qt_qol_avisos_fifo_controles_compactos_e_registro_horas():
    app, bridge = _qt()
    if app is None:
        return
    from PySide6.QtCore import QMetaObject, QObject, Qt, qInstallMessageHandler
    from PySide6.QtTest import QTest
    from shiboken6 import delete
    from app_qt import criar_engine
    avisos = []
    anterior = qInstallMessageHandler(lambda t, c, m: avisos.append(m))
    engine = criar_engine(bridge)
    try:
        afirmar(engine.rootObjects(), avisos)
        janela = engine.rootObjects()[0]
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        health_more = _encontrar(janela.contentItem(), "healthMore")
        afirmar(health_more.property("text") == "+13 outros jogos com pendências")
        toast = janela.findChild(QObject, "notificationToast")
        for texto, erro in (("Primeiro", False), ("Segundo", True), ("Terceiro", False)):
            bridge.aviso.emit(texto, erro)
        _aguardar(app, lambda: toast.property("visible"))
        afirmar(toast.property("message") == "Primeiro", "aviso inicial foi sobrescrito")
        QMetaObject.invokeMethod(toast, "close")
        _aguardar(app, lambda: toast.property("message") == "Segundo")
        afirmar(toast.property("error"), "erro perdeu sua severidade na fila")
        QMetaObject.invokeMethod(toast, "close")
        _aguardar(app, lambda: toast.property("message") == "Terceiro")
        QMetaObject.invokeMethod(toast, "close")
        _aguardar(app, lambda: not janela.property("showingNotification"))
        for largura, altura in ((960, 640), (1200, 800), (1440, 920)):
            janela.setWidth(largura)
            janela.setHeight(altura)
            QTest.qWait(60)  # Qt Quick faz o polish dos layouts no próximo frame.
            for nome in ("nav_integracoes", "globalSearchButton", "immersiveButton", "settingsButton"):
                botao = _encontrar(janela.contentItem(), nome)
                ponto = botao.mapToItem(janela.contentItem(), botao.width(), 0)
                afirmar(ponto.x() <= largura, f"{nome} cortado em {largura}: {ponto.x()}; "
                        f"janela={janela.width()}, botão={botao.property('text')}, "
                        f"largura={botao.width()}, layout={botao.parentItem().width()}")
        janela.setWidth(960)
        janela.setHeight(640)
        janela.requestActivate()
        app.processEvents()
        QTest.keyClick(janela, Qt.Key_F, Qt.ControlModifier)
        paleta = janela.findChild(QObject, "globalPalette")
        _aguardar(app, lambda: paleta.property("visible"))
        QMetaObject.invokeMethod(paleta, "close")
        bridge.navegar("jogos")
        bridge.selecionar(0)
        QTest.qWait(60)
        grade = _encontrar(janela.contentItem(), "gamesGrid")
        afirmar(grade.property("cellHeight") <= grade.height(), "primeira linha de cards cortou o status/horas")
        gid = bridge.selecionado["id"]
        details = janela.findChild(QObject, "gameDetails")
        QMetaObject.invokeMethod(details, "open")
        app.processEvents()
        QMetaObject.invokeMethod(_encontrar(janela.contentItem(), "registerGameHoursButton"), "clicked")
        dialogo = janela.findChild(QObject, "sessionDialog")
        _aguardar(app, lambda: dialogo.property("visible"))
        campo = _encontrar(janela.contentItem(), "sessionHoursField")
        salvar = _encontrar(janela.contentItem(), "saveSessionButton")
        afirmar(not salvar.property("enabled"), "aceitou horas vazias")
        campo.setProperty("text", "1,5")
        app.processEvents()
        afirmar(salvar.property("enabled"), "não aceitou vírgula decimal")
        QMetaObject.invokeMethod(salvar, "clicked")
        _aguardar(app, lambda: not bridge.ocupado)
        afirmar(bridge.servico.jogo(gid)["horas"] == 1.5, "diálogo não registrou as horas")
        afirmar(not dialogo.property("visible"), "diálogo ficou preso após registrar")
        QMetaObject.invokeMethod(details, "close")
        sessao = core.iniciar_sessao_manual(gid, bridge.selecionado["titulo"])
        afirmar(sessao["ok"], sessao)
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        sistema = janela.findChild(QObject, "systemDialog")
        QMetaObject.invokeMethod(sistema, "open")
        _aguardar(app, lambda: _encontrar(janela.contentItem(), "registerPendingSessionButton") is not None)
        QMetaObject.invokeMethod(_encontrar(janela.contentItem(), "registerPendingSessionButton"), "clicked")
        _aguardar(app, lambda: dialogo.property("visible"))
        afirmar(dialogo.property("file") == sessao["arquivo"], "diálogo perdeu o marcador pendente")
        campo.setProperty("text", "0")
        app.processEvents()
        afirmar(not salvar.property("enabled"), "aceitou encerrar sessão com horas zeradas")
        campo.setProperty("text", "2")
        app.processEvents()
        QMetaObject.invokeMethod(salvar, "clicked")
        _aguardar(app, lambda: not bridge.ocupado)
        afirmar(bridge.servico.jogo(gid)["horas"] == 3.5 and not bridge.listarSessoes(),
                "registro da GUI deixou a sessão aberta ou somou horas erradas")
        QMetaObject.invokeMethod(sistema, "close")
        erros = [m for m in avisos if any(x in m for x in
                 ("ReferenceError", "TypeError", "Unable to assign", "Binding loop", "failed to load", "is not defined"))]
        afirmar(not erros, "\n".join(erros))
    finally:
        bridge.fechar()
        delete(engine)
        qInstallMessageHandler(anterior)


def teste_qt_volume_pc_barra_visivel_teclado_e_polling_sem_sobrescrever():
    from unittest.mock import patch
    estado = {"ok": True, "nivel": 55, "mudo": False}
    escritas = []

    def definir(nivel):
        escritas.append(nivel)
        estado["nivel"] = nivel
        return dict(estado)

    with patch.object(core, "ler_volume_pc", side_effect=lambda: dict(estado)), \
            patch.object(core, "definir_volume_pc", side_effect=definir):
        app, bridge = _qt()
        if app is None:
            return
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from shiboken6 import delete
        from app_qt import criar_engine
        engine = criar_engine(bridge)
        try:
            janela = engine.rootObjects()[0]
            janela.setWidth(960)
            janela.setHeight(640)
            QTest.qWait(60)
            bridge.consultarVolume()
            slider = _encontrar(janela.contentItem(), "pcVolumeSlider")
            afirmar(slider is not None and slider.width() >= 70 and slider.property("visible"),
                    "barra de volume ausente/colapsada")
            afirmar(slider.property("value") == 55 and not escritas, "abrir o Hub mudou o volume")
            slider.forceActiveFocus()
            QTest.keyClick(janela, Qt.Key_Left)
            QTest.qWait(120)
            afirmar(escritas and escritas[-1] == 54, "teclado não mudou volume do PC")
            estado["nivel"] = 23
            bridge.consultarVolume()
            app.processEvents()
            afirmar(slider.property("value") == 23 and len(escritas) == 1,
                    "polling sobrescreveu o mixer ou não refletiu a mudança externa")
        finally:
            bridge.fechar()
            delete(engine)


def teste_qt_provedores_dialogos_e_spotify_enfileira_sem_bloquear_ui():
    app, bridge = _qt()
    if app is None:
        return
    from PySide6.QtCore import QMetaObject, QObject, qInstallMessageHandler
    from shiboken6 import delete
    from app_qt import criar_engine
    from bib_nucleo.rede.spotify import normalizar_faixa
    from unittest.mock import patch
    avisos = []
    anterior = qInstallMessageHandler(lambda t, c, m: avisos.append(m))
    engine = criar_engine(bridge)
    try:
        afirmar(engine.rootObjects(), avisos)
        janela = engine.rootObjects()[0]
        janela.setWidth(960); janela.setHeight(640)
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        gid = bridge._dados["jogos"][0]["id"]
        bridge.navegar("jogos")
        QMetaObject.invokeMethod(_encontrar(janela.contentItem(), "collectionAddButton"), "clicked")
        editor = janela.findChild(QObject, "gameEditorDialog")
        app.processEvents()
        afirmar(editor.property("visible") and editor.property("height") <= 600,
                "editor de jogo saiu da janela compacta")
        QMetaObject.invokeMethod(editor, "reject")
        for nome in ("providersDialog", "musicDownloadsDialog", "spotifyDialog",
                       "newIntegrationDialog"):
            dialogo = janela.findChild(QObject, nome)
            afirmar(dialogo is not None, nome)
            QMetaObject.invokeMethod(dialogo, "open")
            app.processEvents()
            afirmar(dialogo.property("visible"), nome)
            QMetaObject.invokeMethod(dialogo, "close")
        bridge.adicionarIntegracao("minha-fonte", "Minha Fonte", "Atalho de teste", "link",
                                   "https://example.com/")
        _aguardar(app, lambda: any(i["chave"] == "minha-fonte" for i in bridge.integracoes))
        bridge.navegar("integracoes")
        app.processEvents()
        afirmar(_encontrar(janela.contentItem(), "addIntegrationButton") is not None,
                "botão Adicionar sumiu das integrações")
        bridge.removerIntegracao("minha-fonte")
        _aguardar(app, lambda: all(i["chave"] != "minha-fonte" for i in bridge.integracoes))
        with patch.object(bridge.servico, "buscar_capas", return_value={"itens": [
                {"titulo": "Arte", "provedor": "steam", "fonte": "Steam", "url": "https://example.com/arte", "preview_url": ""}], "erros": []}):
            dialogo = janela.findChild(QObject, "coversDialog")
            dialogo.setProperty("ident", gid)
            QMetaObject.invokeMethod(dialogo, "open")
            _aguardar(app, lambda: not bridge.ocupado)
            afirmar(bridge.artes.itens[0]["titulo"] == "Arte")
            QMetaObject.invokeMethod(dialogo, "close")
        with patch.object(bridge.servico, "avaliar_conquistas", return_value={"itens": [], "total": 10,
                "desbloqueadas": 2, "avaliaveis": 3, "status": "Save local", "appid": "123", "save": "local.json"}):
            dialogo = janela.findChild(QObject, "achievementsDialog")
            dialogo.setProperty("gid", gid)
            dialogo.setProperty("gameTitle", "Jogo de teste")
            QMetaObject.invokeMethod(dialogo, "open")
            _aguardar(app, lambda: not bridge.ocupado)
            afirmar(bridge.conquistas["desbloqueadas"] == 2)
            QMetaObject.invokeMethod(dialogo, "close")
        faixa = normalizar_faixa({"id": "a" * 22, "name": "Outra faixa", "artists": [{"name": "Autor"}], "album": {"name": "Álbum"}})
        with patch.object(bridge.servico.spotify, "consultar", return_value={"itens": [faixa], "next": ""}):
            bridge.consultarSpotify("busca", "Outra faixa")
            _aguardar(app, lambda: not bridge.ocupado)
        bridge.selecionarTodasSpotify(True)
        afirmar(bridge.spotifySelecionados == [faixa["uri"]])
        bridge.enfileirarSpotify(False)
        _aguardar(app, lambda: not bridge.ocupado)
        afirmar(any(d["titulo"] == "Outra faixa" for d in bridge.filaMusicas), "seleção não entrou na fila")
        bridge.navegar("musicas")
        afirmar(any(i["chave"] == "spotify" for i in bridge.integracoes))
        erros = [m for m in avisos if any(x in m for x in
                 ("ReferenceError", "TypeError", "Unable to assign", "Binding loop", "is not defined"))]
        afirmar(not erros, "\n".join(erros))
    finally:
        bridge.fechar()
        delete(engine)
        qInstallMessageHandler(anterior)
