"""Entrega de callbacks à thread da UI; workers nunca chamam o Tk.

O root é um objeto com after/after_cancel/bind (não há import de tkinter).
O dispatcher tem ciclo de vida próprio e descarta entregas após fechar.
"""
from __future__ import annotations

from queue import Empty, SimpleQueue


class DespachanteUi:
    def __init__(self, root, ao_erro=None, intervalo_ms=50):
        self.root = root
        self.ao_erro = ao_erro
        self.intervalo_ms = intervalo_ms
        self.fila = SimpleQueue()
        self.fechado = False
        self.timer = root.after(intervalo_ms, self._processar)
        root.bind("<Destroy>", self._ao_destruir, add="+")

    def enviar(self, callback):
        if not self.fechado:
            self.fila.put(callback)

    def _processar(self):
        if self.fechado:
            return
        for _ in range(100):
            try:
                callback = self.fila.get_nowait()
            except Empty:
                break
            if self.fechado:
                break
            try:
                callback()
            except Exception as exc:
                if not self.fechado and self.ao_erro is not None:
                    self.ao_erro(exc)
        if not self.fechado:
            self.timer = self.root.after(self.intervalo_ms, self._processar)

    def _ao_destruir(self, evento):
        if evento.widget is self.root:
            self.fechar()

    def fechar(self):
        if self.fechado:
            return
        self.fechado = True
        self.root.after_cancel(self.timer)
        while True:
            try:
                self.fila.get_nowait()
            except Empty:
                break
