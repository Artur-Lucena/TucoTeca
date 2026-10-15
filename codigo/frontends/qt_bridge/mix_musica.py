#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ponte Qt: Spotify, musicas online e player de audio."""
from __future__ import annotations

import bib_core as core
from bib_nucleo import spotify
from PySide6.QtCore import (
    QUrl,
    Slot,
)


class MixMusica:


    @Slot()
    def conectarSpotify(self):
        try:
            self.abrirUrl(self.servico.spotify.iniciar_login())
            self.spotifyMudou.emit()
        except ValueError as e:
            self.aviso.emit(str(e), True)

    def _callback_spotify(self):
        resposta = self.servico.spotify.receber_callback()
        if resposta is not None:
            def pronto(_r):
                self.spotifyMudou.emit()
                self.aviso.emit("Spotify conectado. Escolha suas músicas ou playlists.", False)
            self.executar("Autorizando Spotify…", lambda: self.servico.spotify.finalizar_login(resposta), pronto)

    @Slot()
    def desconectarSpotify(self):
        self.servico.spotify.desconectar()
        self._spotify_selecao.clear()
        self.spotifyMudou.emit()

    @Slot(str)
    def colarCodigoSpotify(self, codigo):
        def pronto(_r):
            self.spotifyMudou.emit()
            self.aviso.emit("Spotify conectado. Escolha suas músicas ou playlists.", False)
        self.executar("Autorizando Spotify…", lambda: self.servico.spotify.trocar_codigo(codigo), pronto)

    @Slot(str, str, bool)
    def consultarSpotify(self, modo, termo, mais=False):
        link = spotify.identificar_spotify(termo)
        if link:
            modo = {"track": "faixa", "album": "album", "playlist": "playlist"}[link[0]]
            termo = link[1]
        self._spotify_geracao += 1
        geracao = self._spotify_geracao
        if not mais:
            self._spotify_contexto = (modo, termo)
            self._spotify_selecao.clear()
            self.spotify_resultados.substituir([])
        else:
            modo, termo = self._spotify_contexto
        pagina = self._spotify_proxima if mais else ""
        def pronto(r):
            if geracao != self._spotify_geracao:
                return
            self.spotify_resultados.substituir((self.spotify_resultados.itens if mais else []) + r["itens"])
            self._spotify_proxima = r.get("next") or ""
            self.musica_online_resultados.substituir([dict(f, fonte="spotify", nome_fonte="Spotify") for f in self.spotify_resultados.itens])
            self._musica_online_selecao.clear()
            self._musica_online_mensagem = r.get("aviso") or f'{len(self.spotify_resultados.itens)} resultado(s) do Spotify'
            self.spotifyMudou.emit()
            if r.get("aviso"):
                self.aviso.emit(r["aviso"], False)
        self.executar("Consultando catálogo Spotify…", lambda: self.servico.spotify.consultar(modo, termo, pagina), pronto)

    @Slot(str, bool)
    def selecionarSpotify(self, uri, selecionar):
        if selecionar:
            self._spotify_selecao.add(uri)
        else:
            self._spotify_selecao.discard(uri)
        self.spotifyMudou.emit()

    @Slot(bool)
    def selecionarTodasSpotify(self, selecionar):
        self._spotify_selecao = {i["uri"] for i in self.spotify_resultados.itens if i.get("uri")} if selecionar else set()
        self.spotifyMudou.emit()

    @Slot(bool)
    def enfileirarSpotify(self, baixar=False):
        itens = [i for i in self.spotify_resultados.itens if i.get("uri") in self._spotify_selecao]
        if not itens:
            return
        def pronto(r):
            self.aviso.emit(f'{r["novos"]} faixa(s) na fila; {r["ignorados"]} já existentes.', False)
            if baixar:
                self.baixarFilaMusicas()
            else:
                self.atualizar()
        self.executar("Enfileirando músicas…", lambda: self.servico.enfileirar_musicas(itens), pronto)

    @Slot(str, str)
    @Slot(str, str, bool)
    def pesquisarMusicas(self, termo, fonte="todas", atualizar=False):
        self._musica_online_geracao += 1
        geracao = self._musica_online_geracao
        self._musica_online_selecao.clear()
        self.musica_online_resultados.substituir([])
        self._musica_online_mensagem = "Buscando nas bibliotecas…"
        self.spotifyMudou.emit()
        def pronto(r):
            if geracao != self._musica_online_geracao:
                return
            self.musica_online_resultados.substituir(r.get("itens", []))
            if r.get("aviso") and not r.get("itens"):
                self._musica_online_mensagem = r["aviso"]
            elif r.get("erros"):
                self._musica_online_mensagem = "; ".join(r["erros"])
            elif not r.get("itens"):
                self._musica_online_mensagem = "Nada encontrado. Tente artista + faixa."
            else:
                self._musica_online_mensagem = (f'{len(r["itens"])} resultado(s)'
                                                + (" (do cache local)" if r.get("cache") else ""))
            self.spotifyMudou.emit()
        self.executar("Buscando músicas…",
                      lambda: self.servico.buscar_musicas_online(termo, fonte, atualizar), pronto,
                      lambda erro: self._erro_busca_musicas(geracao, erro))

    def _erro_busca_musicas(self, geracao, erro):
        if geracao == self._musica_online_geracao:
            self._musica_online_mensagem = erro
            self.spotifyMudou.emit()

    @Slot(str, bool)
    def alternarMusicaOnline(self, uri, selecionar):
        if selecionar:
            self._musica_online_selecao.add(uri)
        else:
            self._musica_online_selecao.discard(uri)
        self.spotifyMudou.emit()

    @Slot(bool)
    def selecionarTodasMusicasOnline(self, selecionar):
        self._musica_online_selecao = {
            i["uri"] for i in self.musica_online_resultados.itens if i.get("uri")} if selecionar else set()
        self.spotifyMudou.emit()

    @Slot(bool)
    def enfileirarMusicasOnline(self, baixar=False):
        itens = [dict(i, uri=i.get("uri") or i.get("url", ""))
                 for i in self.musica_online_resultados.itens
                 if i.get("uri") in self._musica_online_selecao]
        if not itens:
            return
        def pronto(r):
            self.aviso.emit(f'{r["novos"]} faixa(s) na fila; {r["ignorados"]} já existentes.', False)
            if baixar:
                self.baixarFilaMusicas()
            else:
                self.atualizar()
        self.executar("Enfileirando músicas…", lambda: self.servico.enfileirar_musicas(itens), pronto)

    @Slot()
    def baixarFilaMusicas(self):
        if self.ocupado:
            self.aviso.emit("Aguarde a operação atual terminar para baixar a fila.", False)
            return
        self._cancelar_musicas.clear()
        def pronto(r):
            self._download_musica = {"rotulo": "", "pct": 0, "id": 0, "cancelando": False}
            self.downloadMusicaMudou.emit()
            self.aviso.emit(f'{r["novas"]} faixa(s) salvas e importadas.' + ("; ".join(r["erros"][:3]) if r["erros"] else ""), bool(r["erros"]))
            self.atualizar()
        def trabalho():
            try:
                return self.servico.baixar_musicas(self._cancelar_musicas, self._progressoMusica.emit)
            finally:
                self._progressoMusica.emit({"id": 0, "rotulo": "", "pct": 0})
        self.executar("Baixando e importando músicas…", trabalho, pronto)

    @Slot()
    def pararDownloadMusicas(self):
        self._cancelar_musicas.set()
        self._download_musica = dict(self._download_musica, cancelando=True)
        self.downloadMusicaMudou.emit()

    @Slot(object)
    def _mostrar_progresso_musica(self, dados):
        if self._fechado:
            return
        self._download_musica = dict(dados, cancelando=bool(dados.get("rotulo")) and self._cancelar_musicas.is_set())
        self.downloadMusicaMudou.emit()

    @Slot()
    def instalarAudio(self):
        self._alterar("Instalando dependências de áudio…", self.servico.instalar_audio)

    @Slot(QUrl)
    def importarCsvMusicas(self, url):
        caminho = url.toLocalFile()
        def trabalho():
            dados = core.ler_csv_exportify(caminho)
            if dados["erros"]:
                raise ValueError("; ".join(dados["erros"]))
            return self.servico.enfileirar_musicas(dados["itens"])
        self._alterar("Importando CSV de músicas…", trabalho)

    @Slot(str)
    def modoAudio(self, modo):
        if modo in ("sequencia", "aleatorio", "repetir"):
            self._modo_audio = modo
            self.playerMudou.emit()


    @Slot(int)
    def tocar(self, mid):
        faixas = self._dados["musicas"]
        indice = next((i for i, m in enumerate(faixas) if m["id"] == mid), None)
        if indice is None:
            return
        self._audio_token += 1
        token = self._audio_token
        self._audio_carregando = True
        self._player.carregar([dict(m, path=m["musica_path"]) for m in faixas], indice)
        self._tocando = dict(faixas[indice])
        self.playerMudou.emit()

        def preparar():
            with self._audio_lock:
                try:
                    return self._player.preparar(faixas[indice]["musica_path"])
                except Exception as exc:
                    return {"ok": False, "erro": str(exc)}

        def pronto(resultado):
            if token != self._audio_token:
                return
            self._audio_carregando = False
            res = self._player.tocar_preparado(indice, resultado)
            if not res.get("ok"):
                self.aviso.emit(res.get("erro", "Falha ao reproduzir áudio."), True)
            self.playerMudou.emit()
        self.executar("Preparando áudio…", preparar, pronto)

    @Slot(str)
    def transporte(self, acao):
        if acao == "parar":
            self._audio_token += 1
            self._audio_carregando = False
            self._player.parar()
        elif self._audio_carregando:
            return
        elif acao in ("anterior", "proxima"):
            i = (self._player.idx or 0) + (1 if acao == "proxima" else -1)
            if 0 <= i < len(self._player.fila):
                self.tocar(self._player.fila[i]["id"])
            else:
                self._player.parar()
        elif acao == "alternar":
            if self._player.estado == "parado":
                if self._tocando:
                    self.tocar(self._tocando["id"])
            else:
                resultado = self._player.alternar()
                if not resultado.get("ok"):
                    self.aviso.emit(resultado.get("erro", "Falha no player."), True)
        self.playerMudou.emit()

    def _vigiar_audio(self):
        if self._player.terminou() and not self._audio_carregando:
            if self._modo_audio == "repetir" and self._player.idx is not None:
                self.tocar(self._player.fila[self._player.idx]["id"])
            elif self._modo_audio == "aleatorio" and len(self._player.fila) > 1:
                import random
                disponiveis = [f for f in self._player.fila
                               if f["id"] != (self._tocando.get("id"))]
                self.tocar(random.choice(disponiveis or self._player.fila)["id"])
            else:
                self.transporte("proxima")
        self.playerMudou.emit()


__all__ = ["MixMusica"]
