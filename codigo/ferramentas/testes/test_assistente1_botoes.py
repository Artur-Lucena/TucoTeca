"""Botões Qt: pílula, grandes e organizados por tokens.

Sucesso = Theme expõe btnAlto/btnTexto/btnMargem com variação por densidade;
ActionButton usa pílula (raio = altura/2), altura e texto dos tokens, com
variante compact declarada; nenhuma tela fixa altura mágica em ActionButton.
Cancelamento/falha não se aplicam (mudança visual); a prova de carga é o
Main.qml abrindo sem erro de QML (coberta por test_qt) mais a altura real
do botão abaixo.
Estática roda em stdlib; carga QML pula sem PySide6.
"""
import re
from pathlib import Path

from executar import afirmar

QML = Path(__file__).resolve().parents[2] / "frontends" / "qml"


def _ler(nome):
    return (QML / nome).read_text(encoding="utf-8")


def teste_theme_tem_tokens_de_botao():
    tema = _ler("Theme.qml")
    for token in ("btnAlto", "btnTexto", "btnMargem"):
        m = re.search(r"readonly property int " + token + r":([^\n]+)", tema)
        afirmar(m, "Theme sem token " + token)
    corpo = re.search(r"readonly property int btnAlto:([^\n]+)", tema).group(1)
    afirmar("bigpicture" in corpo and "compacto" in corpo,
            "btnAlto sem variação por densidade: " + corpo)
    numeros = [int(n) for n in re.findall(r"\d+", corpo)]
    afirmar(numeros and min(numeros) >= 44, "btnAlto menor que 44: " + corpo)


def teste_actionbutton_e_pilula_por_token():
    btn = _ler("ActionButton.qml")
    afirmar("radius: control.height / 2" in btn, "botão sem raio em pílula")
    afirmar("implicitHeight: Theme.btnAlto" in btn, "altura sem token")
    afirmar("font.pixelSize: control.compact ? Theme.subtitle : Theme.btnTexto" in btn,
            "texto sem token")
    afirmar("implicitHeight: 42" not in btn and "radius: 10" not in btn,
            "número mágico antigo ainda no ActionButton")
    afirmar("property bool compact" in btn, "variante compacta sem declaração")


def teste_telas_sem_altura_magica_em_botao():
    """Sem 32/36/44 literais no Main.qml: botões, combos e campos usam o token."""
    for i, linha in enumerate(_ler("Main.qml").splitlines(), 1):
        afirmar(not re.search(r"implicitHeight: (32|36|44)\b", linha),
                f"Main.qml:{i} com altura mágica: {linha.strip()[:80]}")


def teste_qt_botao_grande_e_redondo():
    from test_qt import _encontrar, _qt
    app, bridge = _qt()
    if app is None:
        return
    from PySide6.QtCore import QUrl, qInstallMessageHandler
    from PySide6.QtQml import QQmlApplicationEngine
    from shiboken6 import delete
    erros = []
    anterior = qInstallMessageHandler(lambda t, c, m: erros.append(m))
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("hub", bridge)
    try:
        engine.load(QUrl.fromLocalFile(str(QML / "Main.qml")))
        afirmar(engine.rootObjects(), erros)
        janela = engine.rootObjects()[0]
        botao = _encontrar(janela.contentItem(), "collectionAddButton")
        afirmar(botao is not None, "botão da coleção sumiu")
        altura = botao.property("implicitHeight")
        afirmar(altura is not None and altura >= 44,
                f"botão não cresceu (implicitHeight={altura})")
        fundo = botao.property("background")
        afirmar(fundo is not None, "botão sem fundo")
        raio = fundo.property("radius")
        afirmar(raio == altura / 2, f"pílula quebrada (raio={raio}, altura={altura})")
        busca = _encontrar(janela.contentItem(), "searchField")
        afirmar(busca is not None, "campo de busca sumiu")
        afirmar(busca.property("implicitHeight") == altura,
                "campo vizinho fora da escala do botão")
        erros_reais = [e for e in erros if any(x in e for x in
                       ("ReferenceError", "TypeError", "Unable to assign", "failed to load"))]
        afirmar(not erros_reais, "\n".join(erros_reais))
    finally:
        bridge.fechar()
        delete(engine)
        qInstallMessageHandler(anterior)
