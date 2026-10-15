#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ponte Qt: integracoes, abrir destinos e troca de interface."""
from __future__ import annotations

from pathlib import Path

import bib_core as core
from PySide6.QtCore import (
    QUrl,
    Slot,
)
from PySide6.QtGui import QDesktopServices


class MixIntegracoes:

    @Slot(str, str, str, str, str)
    def adicionarIntegracao(self, chave, nome, descricao, tipo, url):
        try:
            item = self.servico.adicionar_integracao(
                {"chave": chave, "nome": nome, "descricao": descricao, "tipo": tipo, "url": url})
        except ValueError as e:
            self.aviso.emit(str(e), True)
            return
        self.mudou.emit()
        self.aviso.emit(f"Integração '{item['nome']}' adicionada.", False)

    @Slot(str)
    def removerIntegracao(self, chave):
        try:
            self.servico.remover_integracao(chave)
        except ValueError as e:
            self.aviso.emit(str(e), True)
            return
        self.mudou.emit()
        self.aviso.emit("Integração removida.", False)

    @Slot(str, str)
    def abrirIntegracao(self, chave, termo=""):
        try:
            self.abrirUrl(self.servico.url_integracao(chave, termo))
        except ValueError as e:
            self.aviso.emit(str(e), True)

    @Slot(str, str)
    def buscarIntegracao(self, chave, termo):
        self._catalogo_geracao += 1
        geracao = self._catalogo_geracao
        self.resultados.substituir([])

        def pronto(resultado):
            if geracao != self._catalogo_geracao:
                return
            self.resultados.substituir(resultado.get("itens", []))
            if resultado.get("erros"):
                self.aviso.emit("; ".join(resultado["erros"]), True)
            elif not resultado.get("itens"):
                self.aviso.emit("Nenhum resultado encontrado nesta fonte.", False)
        self.executar("Pesquisando catálogo…", lambda: self.servico.integracoes.buscar(chave, termo), pronto)

    @Slot(str)
    def abrirUrl(self, texto):
        from bib_nucleo.rede import rede_ativa
        if not rede_ativa():
            self.aviso.emit("Rede desligada (BIBLIOTECA_REDE=0).", True)
            return
        url = QUrl(texto)
        if url.scheme() not in ("http", "https") or not url.host():
            self.aviso.emit("Endereço inválido.", True)
        elif not QDesktopServices.openUrl(url):
            self.aviso.emit("Não foi possível abrir o navegador.", True)

    @Slot(str)
    def abrirPasta(self, caminho):
        p = Path(core.traduzir_para_atual(caminho))
        if not p.exists():
            self.aviso.emit("O caminho não existe nesta máquina.", True)
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(p if p.is_dir() else p.parent))):
            self.aviso.emit("Não foi possível abrir a pasta.", True)

    @Slot()
    def classico(self):
        if self.ocupado or self._em_jogo:
            self.aviso.emit("Aguarde a operação ou sessão atual antes de trocar de interface.", False)
        else:
            self.pedirClassico.emit()


__all__ = ["MixIntegracoes"]
