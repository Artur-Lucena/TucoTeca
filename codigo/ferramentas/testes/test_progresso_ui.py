"""Progresso visível: downloads (recebido/total + espaço) e player no rodapé.

Os dados vêm prontos do núcleo/ponte — `total`/`feito` por download (API do
qBittorrent ou .fastresume) e `audio.posicao`/`audio.duracao` reemitidos a cada
750 ms. Aqui garantimos, por estática (roda sem PySide6), que o QML mostra e
formata; a compilação dos QML é coberta pelo gate do venv.
"""
from pathlib import Path

from executar import afirmar

QML = Path(__file__).resolve().parents[2] / "frontends" / "qml"


def _ler(rel):
    return (QML / rel).read_text(encoding="utf-8")


def teste_downloads_mostram_recebido_total_e_espaco_livre():
    colecao = _ler("secoes/Colecao.qml")
    afirmar("function tamanho(" in colecao, "sem formatação GB/MB")
    afirmar("1073741824" in colecao and "1048576" in colecao,
            "formatação de bytes com divisor errado")
    afirmar("row.item.feito" in colecao and "row.item.total" in colecao,
            "downloads sem recebido/total")
    main = _ler("Main.qml")
    afirmar("disco_livre_gb" in main and '" GB livres"' in main,
            "resumo de downloads sem espaço livre")


def teste_footer_do_player_mostra_tempo_e_progresso():
    main = _ler("Main.qml")
    for trecho in ("function tempoAudio(", "var r = s % 60",
                   "hub.audio.posicao", "hub.audio.duracao",
                   'objectName: "playerProgresso"', 'objectName: "playerTempo"'):
        afirmar(trecho in main, "rodapé sem: " + trecho)
    # progresso do rodapé só aparece com faixa carregada (duracao conhecida)
    afirmar("(hub.audio.duracao || 0) > 0" in main, "rodapé sem guarda de visibilidade")
