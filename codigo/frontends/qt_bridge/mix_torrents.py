#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ponte Qt: downloads e torrents (qBittorrent local)."""
from __future__ import annotations

import bib_core as core
from PySide6.QtCore import (
    Slot,
)


class MixTorrents:
    def _atualizar_downloads(self):
        if any(t[2] == "Consultando downloads…" for t in self._tarefas.values()):
            return

        def pronto(resultado):
            self._dados["downloads"] = resultado.get("torrents", [])
            if self._secao == "downloads":
                self._filtrar()
        self.executar("Consultando downloads…", core.listar_torrents, pronto)

    @Slot(str, str)
    def controlarDownload(self, ident, acao):
        self._alterar("Atualizando download…", lambda: core.qbit_controlar(ident, acao))

    @Slot(str)
    def baixarTorrent(self, url):
        def pronto(r):
            self.aviso.emit(f"Torrent no cliente do Hub → {r.get('destino', 'Meus Jogos Locais/')}.", False)
            self._atualizar_downloads()
        self.executar("Adicionando torrent no Hub…", lambda: self.servico.baixar_torrent_hub(url), pronto)

    @Slot(str, result=bool)
    def foraDoDestino(self, caminho):
        return self.servico.fora_do_destino(caminho)

    @Slot(str)
    def organizarDownload(self, caminho):
        def pronto(r):
            msg = "Já estava em Meus Jogos Locais/." if not r.get("movido") else \
                f"Movido p/ Meus Jogos Locais. {r.get('aviso', '')}"
            self.aviso.emit(msg, False)
            self._atualizar_downloads()
        self.executar("Organizando em Meus Jogos Locais…", lambda: self.servico.organizar_download(caminho), pronto)

    @Slot()
    def iniciarDownloads(self):
        self._alterar("Iniciando qBittorrent…", core.qbit_iniciar)


    @Slot()
    def consultarTorrentsProntos(self):
        def pronto(r):
            self._prontos = {"itens": list((r or {}).get("itens") or []),
                             "erros": list((r or {}).get("erros") or [])}
            self.prontosMudou.emit()
        self.executar("Verificando concluídos…", self.servico.torrents_prontos, pronto)

    @Slot(str)
    def importarTorrent(self, save_path):
        def apos(_r):
            self.consultarTorrentsProntos()
        self._alterar("Importando concluído…",
                      lambda: self.servico.importar_torrent(save_path), apos)


__all__ = ["MixTorrents"]
