"""Provas nativas em coleção descartável: capturas, Chromium e QtMultimedia.

Não usa jogos, saves, perfis nem mídias pessoais. O vídeo de prova é gerado
localmente pelo FFmpeg. Chromium recebe HTML local, com toda a rede bloqueada.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path


def esperar(app, condicao, timeout=20):
    fim = time.monotonic() + timeout
    while time.monotonic() < fim:
        app.processEvents()
        if condicao():
            return
        time.sleep(0.02)
    raise RuntimeError("Prova Qt excedeu o prazo.")


def provar(raiz, saida, extras, ffmpeg=""):
    os.environ["BIBLIOTECA_HOME"] = str(raiz)
    os.environ["BIBLIOTECA_SCAN_ROOTS"] = str(raiz / "jogos")
    # O shell de capturas não navega em páginas remotas nem sob atalhos
    # acidentais. O Chromium completo é provado abaixo em uma janela própria,
    # com about:blank e interceptor bloqueando todos os transportes remotos.
    os.environ["BIBLIOTECA_WEBENGINE"] = "0"
    sys.dont_write_bytecode = True
    for p in (Path(__file__).parent, Path(__file__).parent.parent,
              Path(__file__).parent.parent / "frontends"):
        sys.path.insert(0, str(p))
    from PySide6.QtCore import QObject, QUrl, QMetaObject, Q_ARG, qInstallMessageHandler
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtQml import QQmlExpression
    from shiboken6 import delete
    if extras == "completo":
        from PySide6.QtWebEngineQuick import QtWebEngineQuick
        QtWebEngineQuick.initialize()
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication.instance() or QGuiApplication([])
    import bib_core as core
    from qt_bridge import HubBridge
    from app_qt import criar_engine
    core.garantir_dirs()
    audio = raiz / ("caminho-de-audio-longo-" * 4) / "prova.wav"
    audio.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(audio), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(22050)
        wav.writeframes(b"\0" * 22050 * 2 * 3)
    audio_sha = hashlib.sha256(audio.read_bytes()).hexdigest()
    con = core.get_db(core.DEFAULT_DB)
    for i in range(18):
        core.criar_jogo(con, {"titulo": f"Aventura local {i + 1:02d}", "status": "backlog",
                             "executable_path": str(raiz / "jogos" / f"game{i}.exe")})
    core.criar_musica(con, {"titulo": "Faixa de prova", "artista": "TucoTeca",
                            "musica_path": str(audio), "musica_sha": audio_sha})
    core.adicionar_desejo(con, "123", "Desejo de prova")
    con.close()
    bridge = HubBridge(core.DEFAULT_DB)
    avisos = []
    bridge.aviso.connect(lambda texto, erro: avisos.append({"texto": texto, "erro": erro}))
    mensagens = []
    def mensagem(t, c, m):
        mensagens.append(m)
        print(m, file=sys.stderr, flush=True)  # Qt fatal não passa pelo finally
    anterior = qInstallMessageHandler(mensagem)
    engine = criar_engine(bridge)
    perfil = bloqueio = browser_window = player_window = None
    qml_dir = Path(__import__("app_qt").__file__).with_name("qml")
    resultado = {"extras": extras, "capturas": [], "webengine": "ausente", "multimedia": "ausente"}
    try:
        if not engine.rootObjects():
            raise RuntimeError("QML não carregou: " + "\n".join(mensagens))
        window = engine.rootObjects()[0]
        bridge.atualizar()
        esperar(app, lambda: not bridge.ocupado)
        bridge._letras_faixa = ("TucoTeca", "Faixa de prova")
        bridge._letras = {"ok": True, "sincronizadas": True, "linhas": [
            {"t": 0, "texto": "Início"}, {"t": 0.2, "texto": "Segundo trecho"}], "texto": ""}
        bridge.tocar(bridge._dados["musicas"][0]["id"])
        try:
            esperar(app, lambda: bridge.audio["estado"] == "tocando" and bridge.letraIndice == 1, 20)
        except RuntimeError as e:
            raise RuntimeError("Áudio/LRC nativo: " + json.dumps(
                {"audio": bridge.audio, "indice_lrc": bridge.letraIndice, "avisos": avisos},
                ensure_ascii=False)) from e
        resultado["audio_lrc"] = {"posicao_ms": bridge.audio["posicao"], "indice": bridge.letraIndice,
                                  "caminho_original_caracteres": len(str(audio)),
                                  "caminho_mci_caracteres": len(bridge._player.backend._aberto),
                                  "origem": "WAV silencioso e LRC sintéticos; não consulta LRCLIB"}
        bridge.transporte("parar")
        if hashlib.sha256(audio.read_bytes()).hexdigest() != audio_sha:
            raise RuntimeError("Player alterou o áudio original de prova.")
        for width, height in ((1440, 920), (960, 640)):
            window.setWidth(width)
            window.setHeight(height)
            for secao in ("inicio", "jogos", "musicas", "desejos", "videos", "integracoes"):
                bridge.navegar(secao)
                esperar(app, lambda: not bridge.ocupado)
                for _ in range(6):
                    app.processEvents()
                    time.sleep(0.03)
                dest = saida / f"{secao}-{width}x{height}.png"
                if not window.grabWindow().save(str(dest)):
                    raise RuntimeError("Não capturou " + str(dest))
                resultado["capturas"].append(dest.name)
        if extras == "essencial":
            bridge.navegar("youtube")
            app.processEvents()
            if bridge.webDisponivel:
                raise RuntimeError("Variante essencial carregou Chromium.")
            resultado["webengine"] = "fallback OK"
        else:
            # Instancia o componente real do navegador, sem qualquer página remota.
            from PySide6.QtWebEngineCore import QWebEngineUrlRequestInterceptor
            class BloquearRede(QWebEngineUrlRequestInterceptor):
                def interceptRequest(self, info):
                    if info.requestUrl().scheme() in ("http", "https", "ftp", "ws", "wss"):
                        info.block(True)
            engine.loadData(b'import QtQuick; import QtQuick.Controls; ApplicationWindow { visible: true; width: 800; height: 500; NavegadorEmbed { objectName: "browserProbe"; anchors.fill: parent; urlInicial: "about:blank" } }', QUrl.fromLocalFile(str(qml_dir / "ProvaBrowser.qml")))
            browser_window = engine.rootObjects()[-1]
            browser = browser_window.findChild(QObject, "browserProbe")
            if browser is None:
                raise RuntimeError("Navegador QML não carregou.")
            perfil = browser.property("perfil")
            bloqueio = BloquearRede(perfil)
            perfil.setUrlRequestInterceptor(bloqueio)
            if not perfil.isOffTheRecord():
                raise RuntimeError("Perfil Chromium não é privado.")
            view = browser.findChild(QObject, "navegadorEmbed")
            QMetaObject.invokeMethod(view, "reload")
            esperar(app, lambda: not browser.property("carregando") and view.property("renderProcessPid") > 0, 20)
            expr_js = QQmlExpression(engine.rootContext(), view, "", engine)
            script = "document.body.innerHTML='<h1>Prova local</h1>';document.title='TucoTeca Chromium local';window.prova=42;"
            expr_js.setExpression("runJavaScript(" + json.dumps(script) + ")")
            expr_js.evaluate()
            esperar(app, lambda: browser.property("titulo") == "TucoTeca Chromium local", 40)
            expr = QQmlExpression(engine.rootContext(), browser, "permitirNavegacao('https://youtube.com.evil.invalid')", engine)
            if expr.evaluate()[0]:
                raise RuntimeError("Navegação fora do YouTube foi aceita.")
            expr.setExpression("permitirNavegacao('https://www.youtube.com/watch?v=abcdefghijk')")
            if not expr.evaluate()[0]:
                raise RuntimeError("Navegação válida foi recusada.")
            expr.setExpression("(function(){var r='';urlAtualAsync(function(u){r=u});return r;})()")
            if expr.evaluate()[0] != "about:blank":
                raise RuntimeError("Ação do vídeo atual não recebeu a URL real do navegador.")
            resultado["webengine"] = "Chromium, HTML, perfil privado e allowlist OK (sem rede)"
            browser_window.setVisible(False)
            if ffmpeg:
                video = raiz / "prova.mp4"
                r = subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x180:r=25",
                                    "-t", "3", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)], capture_output=True, timeout=30)
                if r.returncode:
                    raise RuntimeError("FFmpeg de prova: " + r.stderr.decode("utf-8", "replace"))
                engine.rootContext().setContextProperty("provaVideo", {"url": video.as_uri(), "sha": "b" * 64, "posicao": 0})
                engine.loadData(b'import QtQuick; import QtQuick.Controls; ApplicationWindow { visible: true; width: 800; height: 500; PlayerVideo { objectName: "playerProbe"; anchors.fill: parent; video: provaVideo } }', QUrl.fromLocalFile(str(qml_dir / "ProvaPlayer.qml")))
                player_window = engine.rootObjects()[-1]
                player = player_window.findChild(QObject, "playerProbe")
                if player is None:
                    raise RuntimeError("Player QML não carregou.")
                esperar(app, lambda: player.property("posicao") > 300, 20)
                resultado["multimedia"] = {"reproducao": "OK", "posicao_ms": player.property("posicao"), "duracao_ms": player.property("duracao")}
                QMetaObject.invokeMethod(player, "parar")
                esperar(app, lambda: not bridge.ocupado)
                persistido = json.loads((core.DADOS_DIR / "videos-posicoes.json").read_text(encoding="utf-8"))
                assert persistido["b" * 64] >= 300
                retomada = max(1000, persistido["b" * 64])
                engine.rootContext().setContextProperty("provaVideo", {"url": "", "sha": "b" * 64, "posicao": 0})
                app.processEvents()
                engine.rootContext().setContextProperty("provaVideo", {"url": video.as_uri(), "sha": "b" * 64, "posicao": retomada})
                esperar(app, lambda: player.property("retomou") and player.property("posicao") >= retomada, 20)
                resultado["multimedia"]["retomada_ms"] = player.property("posicao")
                QMetaObject.invokeMethod(player, "parar")
        reais = [m for m in mensagens if any(e in m for e in ("ReferenceError", "TypeError", "Binding loop", "Unable to assign", "is not defined"))]
        if reais:
            raise RuntimeError("Erros QML: " + "\n".join(reais))
        resultado["mensagens_qt"] = mensagens
        return resultado
    finally:
        bridge.fechar()
        if perfil is not None:
            perfil.setUrlRequestInterceptor(None)
        delete(engine)
        qInstallMessageHandler(anterior)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extras", choices=("essencial", "completo"), default="essencial")
    parser.add_argument("--saida", required=True)
    parser.add_argument("--ffmpeg", default="")
    args = parser.parse_args()
    saida = Path(args.saida).resolve()
    saida.mkdir(parents=True, exist_ok=True)
    # Limpa overrides herdados antes de importar o núcleo (constantes são locais).
    for chave in list(os.environ):
        if chave.startswith("BIBLIOTECA_"):
            os.environ.pop(chave)
    with tempfile.TemporaryDirectory(prefix="qt-nativo-", dir=saida) as tmp:
        resultado = provar(Path(tmp), saida, args.extras, args.ffmpeg)
    (saida / "qt-runtime.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in resultado.items() if k != "mensagens_qt"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
