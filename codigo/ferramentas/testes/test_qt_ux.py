"""Bridge Qt: aparência, diagnóstico e auto-backup de sessão."""
from __future__ import annotations

import sys
from pathlib import Path

from executar import afirmar


def _bridge():
    sys.path.insert(0, str(Path(__file__).parents[3] / "frontends"))
    from qt_bridge import HubBridge
    return HubBridge(":memory:")


def teste_bridge_aparencia_e_diagnostico():
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication.instance() or QGuiApplication([])
    bridge = _bridge()
    try:
        ap = bridge.aparencia
        afirmar(ap["tema"] in ("escuro", "claro"), ap)
        afirmar(ap["densidade"] in ("compacto", "conforto", "bigpicture"), ap)
        afirmar(isinstance(ap.get("modo_simples"), bool), ap)

        # definir_aparencia grava e devolve o estado validado
        r = bridge.servico.definir_aparencia("claro", "compacto")
        afirmar(r == {"tema": "claro", "densidade": "compacto", "auto_backup": ap["auto_backup"],
                      "modo_simples": ap["modo_simples"]}, r)
        r = bridge.servico.definir_aparencia("roxo", "")
        afirmar(r["tema"] == "claro" and r["densidade"] == "compacto", r)

        # diagnóstico roda sem levantar (pode falhar, mas devolve texto/json)
        recebido = []
        bridge.diagnosticoPronto.connect(lambda t: recebido.append(t))
        bridge.rodarDiagnostico()
        import time
        prazo = time.time() + 30
        while not recebido and time.time() < prazo:
            app.processEvents()
            time.sleep(0.02)
        afirmar(recebido and ("python" in recebido[0] or "erro" in recebido[0]), recebido[:1])
    finally:
        bridge.fechar()


def teste_bridge_auto_backup_opt_out():
    bridge = _bridge()
    try:
        # auto_backup desligado: nada de tarefa de backup é criada
        bridge.servico.definir_aparencia("", "", False)
        before = len(bridge._tarefas)
        bridge._auto_backup_sessao(123)
        afirmar(len(bridge._tarefas) == before, "auto-backup desligado não deve agendar")
        # ligado e com gid válido: agenda uma tarefa
        bridge.servico.definir_aparencia("", "", True)
        bridge._auto_backup_sessao(123)
        afirmar(len(bridge._tarefas) == before + 1, "auto-backup ligado deve agendar backup")
        # sem gid: nunca agenda
        before = len(bridge._tarefas)
        bridge._auto_backup_sessao(0)
        afirmar(len(bridge._tarefas) == before, "sem jogo não há backup")
    finally:
        bridge.fechar()
