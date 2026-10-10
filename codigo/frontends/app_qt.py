#!/usr/bin/env python3
"""Frontend Qt Quick. Mesmo núcleo e coleção; uma única interface por lock."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from shiboken6 import delete

import bib_core as core
from qt_bridge import HubBridge


def criar_engine(bridge):
    engine = QQmlApplicationEngine()
    engine.warnings.connect(lambda erros: [print(e.toString(), file=sys.stderr) for e in erros])
    engine.rootContext().setContextProperty("hub", bridge)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("qml") / "Main.qml")))
    return engine


def main(argv=None):
    parser = argparse.ArgumentParser(description="TucoTeca — desktop Qt Quick")
    parser.add_argument("--db", default=str(core.DEFAULT_DB))
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--big-picture", action="store_true")
    parser.add_argument("--screenshot", help="Captura local da janela no selftest")
    args = parser.parse_args(argv)
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication.instance() or QGuiApplication([sys.argv[0]])
    app.setApplicationName("TucoTeca")
    app.setOrganizationName("TucoTeca")
    core.garantir_dirs()
    lock = core.adquirir_lock()
    if not lock.get("ok"):
        # Janela QML mínima: processo sem console também comunica o bloqueio.
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("motivo", lock.get("erro", "TucoTeca já está aberto."))
        engine.loadData(b'import QtQuick; import QtQuick.Controls; ApplicationWindow { visible: true; width: 520; height: 160; title: "TucoTeca"; Label { anchors.fill: parent; anchors.margins: 24; text: motivo; wrapMode: Text.WordWrap } }')
        if args.selftest:
            return 2
        app.exec()
        return 2
    bridge = engine = None
    try:
        bridge = HubBridge(Path(args.db))
        engine = criar_engine(bridge)
        if not engine.rootObjects():
            return 1
        window = engine.rootObjects()[0]
        bridge.pedirClassico.connect(lambda: app.exit(42))
        if args.big_picture:
            window.toggleImmersive()
        bridge.atualizar()
        if args.selftest:
            erros = []
            bridge.aviso.connect(lambda texto, erro: erros.append(texto) if erro else None)
            ticks = [0]
            timer = QTimer()
            timer.setInterval(100)

            def verificar():
                ticks[0] += 1
                if bridge.ocupado and ticks[0] < 150:
                    return
                if bridge.ocupado:
                    app.exit(1)
                    return
                if erros:
                    print("[erro] " + "; ".join(erros), file=sys.stderr)
                    app.exit(1)
                    return
                if args.screenshot and not window.grabWindow().save(args.screenshot):
                    app.exit(1)
                    return
                print(f"[ok] selftest Qt Quick: {bridge.quantidade} jogos; navegação, modelos e QML carregados")
                app.exit(0)
            timer.timeout.connect(verificar)
            timer.start()
        return app.exec()
    finally:
        if bridge is not None:
            bridge.fechar()
        if engine is not None:
            delete(engine)  # QML morre antes de seus context properties Python.
        core.liberar_lock()


if __name__ == "__main__":
    raise SystemExit(main())
