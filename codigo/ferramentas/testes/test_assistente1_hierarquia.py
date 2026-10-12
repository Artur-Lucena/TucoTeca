"""Lote 1 visual: escala tipográfica por tokens, status com ordem e vazio com ação.

QML só carrega com PySide6 (gate da CI); aqui valemos por estática que os
tokens existem e são usados onde a hierarquia manda, sem número mágico.
"""
import re
from pathlib import Path

from executar import afirmar

QML = Path(__file__).resolve().parents[2] / "frontends" / "qml"


def _ler(nome):
    return (QML / nome).read_text(encoding="utf-8")


def teste_theme_tem_escala_display_e_headline():
    tema = _ler("Theme.qml")
    for token in ("display", "headline"):
        m = re.search(r"readonly property int " + token + r":([^\n]+)", tema)
        afirmar(m, "Theme sem token " + token)
        corpo = m.group(1)
        afirmar("bigpicture" in corpo and "compacto" in corpo,
                token + " sem variação por densidade: " + corpo)


def teste_cabecalho_e_hero_usam_tokens():
    main = _ler("Main.qml")
    afirmar("Theme.display" in main, "título da seção sem Theme.display")
    afirmar("Theme.headline" in main, "hero/vazio sem Theme.headline")
    afirmar("pixelSize: 21" not in main and "pixelSize: window.immersive ? 30 : 25" not in main,
            "tamanho mágico antigo ainda no Main.qml")


def teste_vazio_tem_acao_por_secao():
    main = _ler("Main.qml")
    afirmar('objectName: "emptyStateAction"' in main, "botão do vazio sem objectName")
    for trecho in ("window.editGame({})", "musicFolder.open()", "wishDialog.open()",
                   "videoFolder.open()", "hub.iniciarDownloads()"):
        afirmar(trecho in main, "vazio sem ação: " + trecho)


def teste_lista_usa_tokens_de_texto():
    colecao = _ler("secoes/Colecao.qml")
    afirmar("font { pixelSize: Theme.card" in colecao, "título da lista sem Theme.card")
    afirmar("font.pixelSize: Theme.subtitle" in colecao, "subtítulo da lista sem Theme.subtitle")


def teste_resumo_mostra_ordem_nos_jogos():
    ponte = (QML.parent / "qt_bridge.py").read_text(encoding="utf-8")
    afirmar('"titulo": "Nome"' in ponte and '"horas": "Mais jogados"' in ponte,
            "resumoLista sem rótulo de ordem")
