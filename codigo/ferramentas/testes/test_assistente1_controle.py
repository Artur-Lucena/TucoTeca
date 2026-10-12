"""A1-06: controle neutro apos conexao/foco, pausa com jogo, popup/modal e repeticao direcional.

Sucesso = acao entregue uma vez (direcional repete ao ser segurado).
Cancelamento = bloqueio ate o neutro (hotplug/foco/jogo) ou troca de secao
barrada atras de popup/modal.
Falha = botao desconhecido ignorado, limiar do analogico nao cruzado e troca
parcial de botoes sem neutro nao gera clique.
Sem hardware: hotplug, foco e botoes segurados sao simulados."""
from unittest.mock import patch

from executar import afirmar
from navegacao_controle import (
    ATRASO_REPETICAO,
    INTERVALO_REPETICAO,
    REPETIVEIS,
    Navegador,
    acoes_do_estado,
)

ESTADO_BASE = {"lt": 0, "rt": 0, "lx": 0, "ly": 0, "rx": 0, "ry": 0}


def _estado(botoes):
    return {0: {**ESTADO_BASE, "botoes": set(botoes)}}


def _relogio(t):
    return lambda: t[0]


def teste_so_o_direcional_repete():
    afirmar(REPETIVEIS == frozenset({"cima", "baixo", "esquerda", "direita"}), REPETIVEIS)
    for acao in ("cima", "baixo", "esquerda", "direita"):
        t = [0.0]
        nav = Navegador(relogio=_relogio(t))
        afirmar(nav.atualizar({acao}) == [acao], acao)
        t[0] = ATRASO_REPETICAO - 0.01
        afirmar(nav.atualizar({acao}) == [], acao)
        t[0] = ATRASO_REPETICAO + 0.01
        afirmar(nav.atualizar({acao}) == [acao], acao)
        t[0] += INTERVALO_REPETICAO + 0.001
        afirmar(nav.atualizar({acao}) == [acao], acao)
        afirmar(nav.atualizar(set()) == [], acao)
    for acao in ("confirmar", "voltar", "menu", "anterior", "proxima"):
        t = [0.0]
        nav = Navegador(relogio=_relogio(t))
        afirmar(nav.atualizar({acao}) == [acao], acao)
        t[0] = 30.0
        afirmar(nav.atualizar({acao}) == [], acao + " repetiu ao ser segurado")


def teste_direcional_e_botao_segurados_juntos():
    t = [0.0]
    nav = Navegador(relogio=_relogio(t))
    afirmar(sorted(nav.atualizar({"baixo", "confirmar"})) == ["baixo", "confirmar"])
    t[0] = ATRASO_REPETICAO + 0.01
    afirmar(nav.atualizar({"baixo", "confirmar"}) == ["baixo"], "confirmar repetiu ou direcional parou")
    afirmar(nav.atualizar({"confirmar"}) == [], "soltar o direcional repetiu o botao")
    afirmar(nav.atualizar(set()) == [])


def teste_hotplug_com_botao_segurado_exige_neutro_total():
    nav = Navegador()
    afirmar(nav.atualizar({"confirmar"}) == ["confirmar"])
    nav.bloquear_ate_neutro()  # hotplug simulado com o botao ainda segurado
    afirmar(nav.atualizar({"confirmar", "baixo"}) == [])
    afirmar(nav.atualizar({"baixo"}) == [], "troca parcial sem neutro gerou clique")
    afirmar(nav.atualizar(set()) == [])
    afirmar(nav.atualizar({"baixo"}) == ["baixo"], "neutro total nao reabilitou")


def teste_retorno_de_foco_exige_neutro():
    t = [0.0]
    nav = Navegador(relogio=_relogio(t))
    afirmar(nav.atualizar({"cima"}) == ["cima"])
    nav.bloquear_ate_neutro()  # perda de foco; retorno com o direcional segurado
    afirmar(nav.atualizar({"cima"}) == [], "retorno de foco com botao segurado clicou")
    afirmar(nav.atualizar(set()) == [])
    t[0] = ATRASO_REPETICAO + 5
    afirmar(nav.atualizar({"cima"}) == ["cima"], "neutro nao reabilitou apos o foco")
    nav.bloquear_ate_neutro()  # perda com nada segurado pede um ciclo neutro
    afirmar(nav.atualizar(set()) == [])
    afirmar(nav.atualizar({"confirmar"}) == ["confirmar"])


def teste_repeticao_rearma_apos_soltar():
    t = [0.0]
    nav = Navegador(relogio=_relogio(t))
    afirmar(nav.atualizar({"baixo"}) == ["baixo"])
    t[0] = ATRASO_REPETICAO + 0.01
    afirmar(nav.atualizar({"baixo"}) == ["baixo"])
    afirmar(nav.atualizar(set()) == [])
    t[0] += 0.01
    afirmar(nav.atualizar({"baixo"}) == ["baixo"], "pressionar de novo nao disparou")
    afirmar(nav.atualizar({"baixo"}) == [], "repeticao nao rearmou o atraso")


def teste_limiar_analogico_botao_desconhecido_e_vazio():
    afirmar(acoes_do_estado(None) == frozenset())
    afirmar(acoes_do_estado({}) == frozenset())
    afirmar(acoes_do_estado({"botoes": {99}}) == frozenset(), "botao desconhecido virou acao")
    afirmar(acoes_do_estado({"botoes": set(), "lx": 0, "ly": 16000}) == {"cima"})
    afirmar(acoes_do_estado({"botoes": set(), "lx": 0, "ly": 15999}) == frozenset())
    afirmar(acoes_do_estado({"botoes": set(), "lx": 0, "ly": -16000}) == {"baixo"})
    afirmar(acoes_do_estado({"botoes": set(), "lx": -16000, "ly": 0}) == {"esquerda"})
    afirmar(acoes_do_estado({"botoes": set(), "lx": 16000, "ly": 0}) == {"direita"})
    afirmar(acoes_do_estado({"botoes": {0, 1, 2, 3, 4, 8, 9, 12, 13}})
            == {"cima", "baixo", "esquerda", "direita", "menu", "anterior",
                "proxima", "confirmar", "voltar"})


def _gui_falsa(janela=None, modal=None, foco=None):
    class Gui:
        @staticmethod
        def focusWindow():
            return janela

        @staticmethod
        def modalWindow():
            return modal

        @staticmethod
        def focusObject():
            return foco

    return Gui


def _ler(bridge, qt_bridge, gui, estado):
    with patch.object(qt_bridge, "ler_estados_xinput", return_value=estado), \
            patch.object(qt_bridge, "QGuiApplication", gui):
        bridge._ler_controle()


def _janela_ativa(ativa=True):
    class Janela:
        def isActive(self):
            return ativa

    return Janela()


def teste_ponte_pausa_com_jogo_e_exige_neutro():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    import qt_bridge
    try:
        bridge._timer_controle.stop()
        janela = _janela_ativa(True)
        gui = _gui_falsa(janela=janela)
        feitas = []
        bridge._agir_controle = feitas.append
        segurado, neutro = _estado({12}), _estado(set())
        _ler(bridge, qt_bridge, gui, segurado)  # hotplug com A segurado
        _ler(bridge, qt_bridge, gui, segurado)
        afirmar(not feitas, "agiu com botao segurado no hotplug")
        afirmar(bridge.controlesConectados == ["Controle 1"], bridge.controlesConectados)
        bridge._em_jogo = True
        _ler(bridge, qt_bridge, gui, segurado)
        afirmar(not feitas, "agiu com jogo aberto")
        bridge._em_jogo = False
        _ler(bridge, qt_bridge, gui, segurado)
        afirmar(not feitas, "agiu apos o jogo sem neutro")
        _ler(bridge, qt_bridge, gui, neutro)
        _ler(bridge, qt_bridge, gui, segurado)
        afirmar(feitas == ["confirmar"], feitas)
    finally:
        bridge.fechar()


def teste_ponte_perda_e_retorno_de_foco_exigem_neutro():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    import qt_bridge
    try:
        bridge._timer_controle.stop()
        janela = _janela_ativa(True)
        gui = _gui_falsa(janela=janela)
        feitas = []
        bridge._agir_controle = feitas.append
        segurado, neutro = _estado({12}), _estado(set())
        _ler(bridge, qt_bridge, gui, segurado)
        _ler(bridge, qt_bridge, gui, neutro)
        _ler(bridge, qt_bridge, gui, segurado)
        afirmar(feitas == ["confirmar"], feitas)
        janela.ativa = False  # perda de foco com o botao segurado
        _ler(bridge, qt_bridge, gui, segurado)
        janela.ativa = True  # retorno com o botao ainda segurado
        _ler(bridge, qt_bridge, gui, segurado)
        afirmar(feitas == ["confirmar"], "retorno de foco com botao segurado clicou")
        _ler(bridge, qt_bridge, gui, neutro)
        _ler(bridge, qt_bridge, gui, segurado)
        afirmar(feitas == ["confirmar", "confirmar"], feitas)
    finally:
        bridge.fechar()


def teste_ponte_popup_bloqueia_troca_de_secao_e_menu():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    import qt_bridge
    try:
        enviadas = []
        acoes = []
        bridge.controleAcao.connect(acoes.append)
        with patch.object(qt_bridge.HubBridge, "_enviar_tecla",
                          staticmethod(lambda tecla: enviadas.append(tecla) or True)), \
                patch.object(qt_bridge.HubBridge, "_controle_em_popup", staticmethod(lambda: True)):
            bridge.navegar("inicio")
            bridge._agir_controle("proxima")
            afirmar(bridge.secao == "inicio", "trocou de secao atras de popup")
            bridge._agir_controle("anterior")
            afirmar(bridge.secao == "inicio", "voltou de secao atras de popup")
            bridge._agir_controle("menu")
            afirmar(acoes == [], "abriu a paleta atras de popup")
            bridge._agir_controle("baixo")
            bridge._agir_controle("confirmar")
            afirmar(enviadas == [qt_bridge.Qt.Key.Key_Down, qt_bridge.Qt.Key.Key_Return], enviadas)
        with patch.object(qt_bridge.HubBridge, "_controle_em_popup", staticmethod(lambda: False)):
            bridge._agir_controle("proxima")
            afirmar(bridge.secao == "jogos", bridge.secao)
            bridge._agir_controle("menu")
            afirmar(acoes == ["menu"], acoes)
    finally:
        bridge.fechar()


def teste_controle_em_popup_detecta_modal_e_dialogo():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    import qt_bridge
    try:
        class Meta:
            def __init__(self, nome):
                self._nome = nome

            def className(self):
                return self._nome

        class No:
            def __init__(self, nome, pai=None):
                self._meta = Meta(nome)
                self._pai = pai

            def metaObject(self):
                return self._meta

            def parent(self):
                return self._pai

        with patch.object(qt_bridge, "QGuiApplication", _gui_falsa()):
            afirmar(bridge._controle_em_popup() is False)
        with patch.object(qt_bridge, "QGuiApplication", _gui_falsa(modal=object())):
            afirmar(bridge._controle_em_popup() is True)
        campo = No("QQuickTextField", No("QQuickDialog"))
        with patch.object(qt_bridge, "QGuiApplication", _gui_falsa(foco=campo)):
            afirmar(bridge._controle_em_popup() is True)
        solto = No("QQuickItem", No("QQuickWindow"))
        with patch.object(qt_bridge, "QGuiApplication", _gui_falsa(foco=solto)):
            afirmar(bridge._controle_em_popup() is False)
    finally:
        bridge.fechar()
