#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ponte Qt: controle, emuladores e pads (lê XInput, navega sem trocar atrás de modal)."""
from __future__ import annotations

import qt_bridge as _Q
from navegacao_controle import acoes_do_estado
from PySide6.QtCore import (
    QCoreApplication,
    QEvent,
    Qt,
    Slot,
)
from PySide6.QtGui import QKeyEvent

from .modelos import SECOES_CONTROLE, TECLAS_CONTROLE


class MixControle:


    @Slot()
    def consultarEmus(self):
        self.executar("Lendo emuladores…", self.servico.emus_status,
                      lambda r: (self._emus.update(itens=list((r or {}).get("itens") or [])),
                                 self.emusMudou.emit()))

    @Slot(str)
    def consultarEmu(self, chave):
        def pronto(r):
            r = dict(r or {})
            self._emu_infos[r.get("chave", chave)] = dict(r.get("info") or {})
            self._emus = {"itens": [r], "consulta": {
                k: v for k, v in r.items() if k != "info"}}
            self.emusMudou.emit()
        self.executar("Consultando release…",
                      lambda: self.servico.emu_consultar(chave), pronto)

    @Slot(str)
    def atualizarEmu(self, chave):
        """Instala o release consultado. A confirmação expressa é da QML."""
        info = self._emu_infos.get(chave)
        if not info:
            self.aviso.emit("Consulte o release antes de atualizar.", True)
            return

        def apos(_r):
            self._emu_infos.pop(chave, None)
            self.consultarEmus()
        self._alterar("Baixando e instalando…",
                      lambda: self.servico.emu_atualizar(chave, info), apos)

    @Slot()
    def consultarPads(self):
        def trabalho():
            return {"pads": self.servico.controles_pads().get("pads", []),
                    "presets": self.servico.controles_presets().get("presets", []),
                    "tipos": self.servico.controles_tipos().get("tipos", []),
                    "estado": self._pads.get("estado", "")}

        def pronto(r):
            self._pads = dict(r or {})
            self.padsMudou.emit()
        self.executar("Lendo controles…", trabalho, pronto)

    @Slot(str)
    def fotografarControle(self, nome):
        self._alterar("Salvando preset…",
                      lambda: self.servico.controle_fotografar(nome),
                      lambda _r: self.consultarPads())

    @Slot(str)
    def aplicarControle(self, nome):
        self._alterar("Aplicando preset…",
                      lambda: self.servico.controle_aplicar(nome))

    @Slot(str)
    def gerarControle(self, tipo):
        self._alterar("Gerando mapa…",
                      lambda: self.servico.controle_gerar(tipo),
                      lambda _r: self.consultarPads())

    @Slot()
    def lerEstadoControle(self):
        def pronto(r):
            self._pads = {**self._pads, "estado": (r or {}).get("resumo", "")}
            self.padsMudou.emit()
        self.executar("Lendo controle…", self.servico.controle_estado, pronto)

    def _ler_controle(self):
        if self._fechado:
            return
        estados = _Q.ler_estados_xinput()
        conectados = [f"Controle {slot + 1}" for slot in sorted(estados)]
        if conectados != self._controles:
            self._controles = conectados
            self._navegador.bloquear_ate_neutro()
            self.controleMudou.emit()
        acoes = set()
        for estado in estados.values():
            acoes |= acoes_do_estado(estado)
        janela = _Q.QGuiApplication.focusWindow()
        habilitado = janela is not None and janela.isActive() and not self.emJogo
        if not habilitado or janela is not self._janela_controle:
            self._navegador.bloquear_ate_neutro()
            self._janela_controle = janela if habilitado else None
        if habilitado:
            for acao in self._navegador.atualizar(acoes):
                self._agir_controle(acao)

    def _agir_controle(self, acao):
        if acao in ("anterior", "proxima", "menu") and self._controle_em_popup():
            return  # Não trocar a tela por trás de uma confirmação/seleção modal.
        if acao in ("anterior", "proxima"):
            atual = SECOES_CONTROLE.index(self._secao) if self._secao in SECOES_CONTROLE else 0
            self.navegar(SECOES_CONTROLE[(atual + (1 if acao == "proxima" else -1)) % len(SECOES_CONTROLE)])
        elif acao == "menu":
            self.controleAcao.emit("menu")
        elif acao in TECLAS_CONTROLE:
            self._enviar_tecla(TECLAS_CONTROLE[acao])

    @staticmethod
    def _controle_em_popup():
        if _Q.QGuiApplication.modalWindow() is not None:
            return True
        alvo = _Q.QGuiApplication.focusObject()
        while alvo is not None:
            if "Popup" in alvo.metaObject().className() or "Dialog" in alvo.metaObject().className():
                return True
            alvo = alvo.parentItem() if hasattr(alvo, "parentItem") else alvo.parent()
        return False

    @staticmethod
    def _enviar_tecla(tecla):
        alvo = _Q.QGuiApplication.focusObject()
        if alvo is None:
            return False
        for tipo in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            QCoreApplication.sendEvent(alvo, QKeyEvent(tipo, tecla, Qt.KeyboardModifier.NoModifier))
        return True


__all__ = ["MixControle"]
