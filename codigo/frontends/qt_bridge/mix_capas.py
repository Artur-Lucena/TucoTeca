#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ponte Qt: capas, provedores online e conquistas."""
from __future__ import annotations

from PySide6.QtCore import (
    Slot,
)


class MixCapas:


    @Slot(str, str, str)
    @Slot(str, str, str, str)
    def configurarProvedores(self, steam, steamgrid, spotify_id, spotify_secret=""):
        def pronto(_r):
            self.provedoresMudou.emit()
            self.spotifyMudou.emit()
            self.aviso.emit("Configuração dos provedores salva nesta coleção.", False)
        self.executar("Salvando provedores…", lambda: self.servico.configurar_provedores(
            steam, steamgrid, spotify_id, spotify_secret), pronto)

    @Slot(str, int, str, bool)
    def buscarCapas(self, categoria, ident, provedor, atualizar=False):
        self._arte_geracao += 1
        geracao = self._arte_geracao
        self._arte_contexto = (categoria, ident)
        self.artes.substituir([])
        def pronto(r):
            if geracao != self._arte_geracao:
                return
            self.artes.substituir(r.get("itens", []))
            if r.get("erros"):
                self.aviso.emit("; ".join(r["erros"]), not bool(r.get("itens")))
            elif not r.get("itens"):
                self.aviso.emit("Nenhuma capa encontrada neste provedor.", False)
        self.executar("Pesquisando capas…", lambda: self.servico.buscar_capas(categoria, ident, provedor, atualizar), pronto)

    @Slot(int)
    def aplicarCapa(self, indice):
        if self._arte_contexto and 0 <= indice < len(self.artes.itens):
            categoria, ident = self._arte_contexto
            candidato = dict(self.artes.itens[indice])
            self._alterar("Salvando capa local…", lambda: self.servico.aplicar_capa(categoria, ident, candidato))

    @Slot(int)
    def monitorarConquistas(self, gid):
        if gid != self._conquistas_gid:
            self._conquistas = {"itens": [], "total": 0, "desbloqueadas": 0, "avaliaveis": 0,
                                "status": "Lendo save local…" if gid else "", "appid": "", "save": ""}
            self.conquistasMudou.emit()
        self._conquistas_gid = gid
        self._conquistas_geracao += 1
        self._atualizar_conquistas()

    def _atualizar_conquistas(self):
        gid = self._conquistas_gid or self._jogo_gid
        if not gid or self._fechado or any(t[2] == "Lendo save local…" for t in self._tarefas.values()):
            return
        geracao = self._conquistas_geracao
        def pronto(r):
            if geracao == self._conquistas_geracao:
                self._conquistas = r
                self.conquistasMudou.emit()
            else:
                self._atualizar_conquistas()
        self.executar("Lendo save local…", lambda: self.servico.avaliar_conquistas(gid), pronto)

    @Slot(int, str, str)
    def sincronizarConquistas(self, gid, appid, save):
        self._conquistas_gid = gid
        self._conquistas_geracao += 1
        geracao = self._conquistas_geracao
        def pronto(r):
            if geracao == self._conquistas_geracao:
                self._conquistas = r
                self.conquistasMudou.emit()
            self.aviso.emit("Catálogo de referência salvo. Desbloqueios serão calculados pelo Hub no save local.", False)
        self.executar("Consultando referência Steam…", lambda: self.servico.sincronizar_conquistas(gid, appid, save), pronto)

    @Slot(int, str)
    def salvarRegrasConquistas(self, gid, texto):
        def pronto(r):
            self._conquistas = r
            self.conquistasMudou.emit()
            self.aviso.emit("Regras locais salvas e avaliadas.", False)
        self.executar("Avaliando regras do save…", lambda: self.servico.regras_conquistas(gid, texto), pronto)


__all__ = ["MixCapas"]
