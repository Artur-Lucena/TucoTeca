"""Callbacks de worker só executam na UI; fechar invalida entregas pendentes."""
import threading
from types import SimpleNamespace

from despacho import DespachanteUi
from executar import afirmar


class RootFake:
    def __init__(self):
        self.thread = threading.get_ident()
        self.agendados = {}
        self.proximo = 0

    def after(self, _ms, callback):
        afirmar(threading.get_ident() == self.thread, "worker chamou Tk.after")
        self.proximo += 1
        self.agendados[self.proximo] = callback
        return self.proximo

    def after_cancel(self, timer):
        self.agendados.pop(timer, None)

    def bind(self, *_a, **_k):
        pass


def teste_despacho_worker_e_fechamento():
    root = RootFake()
    dispatcher = DespachanteUi(root)
    executados = []
    th = threading.Thread(target=lambda: dispatcher.enviar(
        lambda: executados.append(threading.get_ident())))
    th.start()
    th.join(2)
    afirmar(executados == [], "worker executou callback antes da UI")
    dispatcher._processar()
    afirmar(executados == [root.thread])
    dispatcher.enviar(lambda: executados.append("tarde"))
    dispatcher._ao_destruir(SimpleNamespace(widget=root))
    dispatcher.enviar(lambda: executados.append("mais tarde"))
    dispatcher._processar()
    afirmar(executados == [root.thread], executados)


def teste_despacho_erro_nao_interrompe_fila():
    erros, feitos = [], []
    dispatcher = DespachanteUi(RootFake(), ao_erro=erros.append)
    dispatcher.enviar(lambda: 1 / 0)
    dispatcher.enviar(lambda: feitos.append("ok"))
    dispatcher._processar()
    afirmar(len(erros) == 1 and feitos == ["ok"])
    dispatcher.fechar()
