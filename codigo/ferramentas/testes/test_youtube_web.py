"""YouTube embutido: validação de URL/hosts no bridge (hermético, sem rede)."""
from __future__ import annotations

import sys
from pathlib import Path

from executar import afirmar, fundo_segundo_plano


def _bridge():
    sys.path.insert(0, str(Path(__file__).parents[3] / "frontends"))
    from qt_bridge import HubBridge
    return HubBridge(":memory:")


def _app():
    fundo_segundo_plano()
    try:
        from PySide6.QtGui import QGuiApplication
    except ImportError:
        print("[pula] PySide6 opcional não instalado")
        return None
    return QGuiApplication.instance() or QGuiApplication([])


def teste_youtube_ir_aceita_so_https_e_hosts_youtube():
    app = _app()
    if app is None:
        return
    bridge = _bridge()
    try:
        ok = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        afirmar(bridge.youtubeIr(ok, "") == ok, "watch do YouTube deve passar")
        afirmar(bridge.youtubeIr("https://youtu.be/dQw4w9WgXcQ", "").startswith("https://youtu.be/"))
        afirmar(bridge.youtubeIr("http://www.youtube.com/", "") == "", "http puro deve ser recusado")
        afirmar(bridge.youtubeIr("https://evil.example/www.youtube.com", "") == "", "host estranho recusado")
        afirmar(bridge.youtubeIr("https://www.youtube.com.evil.example/", "") == "", "host imitado recusado")
        afirmar(bridge.youtubeIr("javascript:alert(1)", "") == "", "esquema javascript recusado")
        afirmar(bridge.youtubeIr("", "pokemon").startswith("https://www.youtube.com/results?search_query="),
                "sem URL, o termo vira busca")
    finally:
        bridge.fechar()


def teste_youtube_buscar_codifica_e_limita_termo():
    app = _app()
    if app is None:
        return
    bridge = _bridge()
    try:
        url = bridge.youtubeBuscar("pokemon x")
        afirmar(url == "https://www.youtube.com/results?search_query=pokemon%20x", url)
        afirmar(bridge.youtubeBuscar("a") == "", "termo curto não busca")
        url = bridge.youtubeBuscar("a&b=c")
        afirmar("a%26b%3Dc" in url, "caracteres especiais devem ser codificados")
    finally:
        bridge.fechar()


def teste_youtube_baixar_so_com_id_valido_e_sem_rede():
    app = _app()
    if app is None:
        return
    bridge = _bridge()
    chamadas = []
    bridge.baixarVideo = lambda vid: chamadas.append(vid)  # não toca a rede
    try:
        bridge.youtubeBaixarUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        afirmar(chamadas == ["dQw4w9WgXcQ"], chamadas)
        bridge.youtubeBaixarUrl("https://evil.example/x")
        bridge.youtubeBaixarUrl("")
        afirmar(chamadas == ["dQw4w9WgXcQ"], "entrada inválida não pode disparar download")
    finally:
        bridge.fechar()


def teste_youtube_web_disponivel_reflete_o_bundle():
    app = _app()
    if app is None:
        return
    bridge = _bridge()
    try:
        from importlib.util import find_spec
        afirmar(bridge.webDisponivel == (find_spec("PySide6.QtWebEngineQuick") is not None))
    finally:
        bridge.fechar()
