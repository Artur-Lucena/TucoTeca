"""Controle XInput e wishlist Steam: ações puras, ligações Qt sem janela e backup antes de gravar."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import bib_core as core
from executar import afirmar
from navegacao_controle import ATRASO_REPETICAO, INTERVALO_REPETICAO, Navegador, acoes_do_estado


def _recusa(acao, trecho):
    try:
        acao()
    except ValueError as e:
        afirmar(trecho in str(e), e)
    else:
        afirmar(False, "deveria recusar: " + trecho)


def teste_acoes_do_estado_mapeia_botoes_e_analogico():
    afirmar(acoes_do_estado(None) == frozenset())
    afirmar(acoes_do_estado({"botoes": {12}}) == {"confirmar"})
    afirmar(acoes_do_estado({"botoes": {13, 4}}) == {"voltar", "menu"})
    afirmar(acoes_do_estado({"botoes": {8, 9}}) == {"anterior", "proxima"})
    afirmar(acoes_do_estado({"botoes": set(), "lx": 0, "ly": 20000}) == {"cima"})
    afirmar(acoes_do_estado({"botoes": set(), "lx": 20000, "ly": -20000}) == {"direita", "baixo"})
    afirmar(acoes_do_estado({"botoes": set(), "lx": 15000, "ly": 15000}) == frozenset())


def teste_navegador_dispara_uma_vez_e_repete_so_o_direcional():
    t = [0.0]
    nav = Navegador(relogio=lambda: t[0])
    afirmar(nav.atualizar({"baixo"}) == ["baixo"])
    t[0] = ATRASO_REPETICAO - 0.01
    afirmar(nav.atualizar({"baixo"}) == [])
    t[0] = ATRASO_REPETICAO + 0.01
    afirmar(nav.atualizar({"baixo"}) == ["baixo"])
    t[0] += INTERVALO_REPETICAO + 0.001
    afirmar(nav.atualizar({"baixo"}) == ["baixo"])
    afirmar(nav.atualizar(set()) == [])
    afirmar(nav.atualizar({"confirmar"}) == ["confirmar"])
    t[0] += 10
    afirmar(nav.atualizar({"confirmar"}) == [], "confirmar não deve repetir")


def teste_bundle_inclui_navegacao_e_leitura_xinput_sem_hardware():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from bib_nucleo.controles import ler_estados_xinput
    from montar_portatil import APP_ARQS
    afirmar(("codigo/frontends/navegacao_controle.py", "navegacao_controle.py") in APP_ARQS)
    afirmar(isinstance(ler_estados_xinput(), dict))


def teste_qt_controle_avisa_conexao_e_so_age_com_janela_ativa():
    import qt_bridge
    from test_qt import _aguardar, _qt
    app, bridge = _qt()
    if app is None:
        return
    try:
        bridge._timer_controle.stop()
        acoes, conexoes = [], []
        bridge.controleAcao.connect(acoes.append)
        bridge.controleMudou.connect(lambda: conexoes.append(True))
        estado = {0: {"botoes": {12}, "lt": 0, "rt": 0, "lx": 0, "ly": 0, "rx": 0, "ry": 0}}
        with patch.object(qt_bridge, "ler_estados_xinput", return_value=estado):
            bridge._ler_controle()
            bridge._ler_controle()
        afirmar(bridge.controlesConectados == ["Controle 1"], bridge.controlesConectados)
        afirmar(len(conexoes) == 1, "hotplug deveria avisar uma vez")
        afirmar(not acoes, "agiu sem janela ativa")
        bridge._agir_controle("menu")
        afirmar(acoes == ["menu"], acoes)
        bridge.navegar("inicio")
        bridge.atualizar()
        _aguardar(app, lambda: not bridge.ocupado)
        bridge._agir_controle("proxima")
        afirmar(bridge.secao == "jogos", bridge.secao)
        bridge._agir_controle("anterior")
        afirmar(bridge.secao == "inicio", bridge.secao)
        afirmar(bridge._enviar_tecla(qt_bridge.Qt.Key.Key_Down) is False)
    finally:
        bridge.fechar()


def teste_wishlist_steam_sincroniza_com_backup_e_recusa_conta_ausente():
    from bib_nucleo.rede import fontes
    from servicos_ui import ServicoBiblioteca
    db = Path(tempfile.mkdtemp(prefix="wishlist-")) / "colecao.db"
    core.get_db(db).close()
    servico = ServicoBiblioteca(db)
    with patch.object(fontes, "steam_principal", return_value={}):
        _recusa(servico.sincronizar_desejos_steam, "Conta Steam")
    itens = [{"appid": "10", "titulo": "Jogo A"}, {"appid": "20", "titulo": "Jogo B"}]
    with patch.object(fontes, "steam_principal", return_value={"steamid": "7656119"}), \
            patch.object(fontes, "ler_wishlist", return_value={"itens": itens, "erros": []}):
        r = servico.sincronizar_desejos_steam()
    afirmar(r["avisos"][0].startswith("Wishlist (Steam): 2 novos"), r)
    afirmar(len(servico.snapshot()["desejos"]) == 2)
    afirmar(list(core.BACKUP_DIR.glob("*.db")), "sincronização sem backup")
