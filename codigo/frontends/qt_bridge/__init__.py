#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""View-model Qt: sinais, modelos e tarefas; QML não acessa banco ou processos.

Pacote por contrato (F4 do O2): `modelos`, `mix_infra`, `mix_musica`,
`mix_midia`, `mix_capas`, `mix_jogos`, `mix_integracoes`, `mix_controle`,
`mix_torrents` + `HubBridge` definida uma vez aqui. Compat total:
`from qt_bridge import HubBridge`, `qt_bridge.Qt`, `qt_bridge.ler_estados_xinput`
e `qt_bridge.QGuiApplication` (alvos de monkeypatch nos testes) continuam
iguais; `HubBridge._enviar_tecla`/`_controle_em_popup` são attrs da classe.
"""
from __future__ import annotations

import importlib.util

from bib_nucleo import online
from bib_nucleo.controles import ler_estados_xinput
from PySide6.QtCore import Property, QObject, Qt, Signal
from PySide6.QtGui import QGuiApplication

from .mix_capas import MixCapas
from .mix_controle import MixControle
from .mix_infra import MixInfra
from .mix_integracoes import MixIntegracoes
from .mix_jogos import MixJogos
from .mix_midia import MixMidia
from .mix_musica import MixMusica
from .mix_torrents import MixTorrents
from .modelos import (
    SECOES_CONTROLE,
    TECLAS_CONTROLE,
    ModeloItens,
    SinaisTarefa,
    Tarefa,
)


class HubBridge(MixInfra, MixMusica, MixMidia, MixCapas, MixJogos,
                MixIntegracoes, MixControle, MixTorrents, QObject):
    """Fachada QML: superficie Qt declarada aqui (sinais + properties),
    logica por dominio nos mixins. Os sinais e os `notify=` usam nomes nus,
    como no modulo original — referencia cruzada de Signal crasha o QML.
    """
    mudou = Signal()
    playerMudou = Signal()
    volumeMudou = Signal()
    provedoresMudou = Signal()
    conquistasMudou = Signal()
    spotifyMudou = Signal()
    downloadMusicaMudou = Signal()
    midiasMudou = Signal()
    videoMudou = Signal()
    diagnosticoPronto = Signal(str)
    letrasMudou = Signal()
    fontesMudou = Signal()
    ferramentasMudou = Signal()
    preferenciasMudou = Signal()
    videoLocalPronto = Signal(object)
    sponsorMudou = Signal()
    _progressoVideo = Signal(object)
    _progressoMusica = Signal(object)
    aviso = Signal(str, bool)
    jogoIniciado = Signal()
    jogoTerminou = Signal()
    pedirClassico = Signal()
    previewMudou = Signal()
    manutencaoMudou = Signal()
    prontosMudou = Signal()
    emusMudou = Signal()
    padsMudou = Signal()
    _sessao = Signal(int, float, bool)
    controleAcao = Signal(str)
    controleMudou = Signal()

    @Property(QObject, constant=True)
    def capasResultados(self):
        return self.artes

    @Property("QVariantMap", notify=provedoresMudou)
    def provedoresOnline(self):
        return online.estado_provedores()

    @Property("QVariantMap", notify=conquistasMudou)
    def conquistas(self):
        return self._conquistas

    @Property(QObject, constant=True)
    def spotifyItens(self):
        return self.spotify_resultados

    @Property(QObject, constant=True)
    def musicaOnlineItens(self):
        return self.musica_online_resultados

    @Property(str, notify=spotifyMudou)
    def musicaOnlineMensagem(self):
        return self._musica_online_mensagem

    @Property("QVariantList", notify=spotifyMudou)
    def musicaOnlineSelecionados(self):
        return sorted(self._musica_online_selecao)

    @Property(QObject, constant=True)
    def videosResultados(self):
        return self.video_resultados

    @Property(str, notify=videoMudou)
    def videosMensagem(self):
        return self._videos_mensagem

    @Property("QVariantMap", notify=videoMudou)
    def videoProgresso(self):
        return self._video_progresso

    @Property("QVariantMap", notify=midiasMudou)
    def midiasStatus(self):
        return self._midias_status

    @Property("QVariantMap", notify=spotifyMudou)
    def spotifyEstado(self):
        return self.servico.spotify.estado()

    @Property("QVariantList", notify=spotifyMudou)
    def spotifySelecionados(self):
        return sorted(self._spotify_selecao)

    @Property(bool, notify=spotifyMudou)
    def spotifyTemMais(self):
        return bool(self._spotify_proxima)

    @Property("QVariantList", notify=mudou)
    def filaMusicas(self):
        return self._fila_musicas

    @Property("QVariantMap", notify=downloadMusicaMudou)
    def downloadMusica(self):
        return self._download_musica

    @Property(QObject, constant=True)
    def itens(self):
        return self.modelo

    @Property(QObject, constant=True)
    def catalogo(self):
        return self.resultados

    @Property(QObject, constant=True)
    def paleta(self):
        return self.global_resultados

    @Property("QVariantMap", notify=mudou)
    def sistema(self):
        return self._sistema

    @Property("QVariantList", notify=mudou)
    def recentes(self):
        return self._sistema.get("recentes", [])

    @Property("QVariantMap", notify=mudou)
    def saude(self):
        return self._saude

    @Property("QVariantList", notify=mudou)
    def filaAudio(self):
        return [{"id": f.get("id"), "titulo": f.get("titulo", ""),
                 "artista": f.get("artista", ""), "atual": i == self._player.idx}
                for i, f in enumerate(self._player.fila)]

    @Property(int, notify=mudou)
    def paletaQuantidade(self):
        return self.global_resultados.rowCount()

    @Property(str, notify=mudou)
    def secao(self):
        return self._secao

    @Property(str, notify=mudou)
    def busca(self):
        return self._busca

    @Property(str, notify=mudou)
    def filtro(self):
        return self._filtro

    @Property(str, notify=mudou)
    def ordem(self):
        return self._ordem

    @Property(str, notify=mudou)
    def resumoLista(self):
        total = len(self._dados.get(self._secao, []))
        nomes = {"jogos": "jogos", "musicas": "músicas", "desejos": "desejos",
                 "downloads": "downloads", "videos": "vídeos"}
        resumo = f"{self.quantidade} de {total} {nomes.get(self._secao, 'itens')}"
        if self._secao == "jogos" and self._filtro != "todos":
            resumo += " · " + {"favoritos": "Favoritos", "jogando": "Jogando",
                                "pendencias": "Com pendências"}.get(self._filtro, self._filtro)
        if self._secao == "jogos":
            resumo += " · " + {"titulo": "Nome", "recentes": "Recentes",
                                "horas": "Mais jogados"}.get(self._ordem, self._ordem)
        if self._busca.strip():
            resumo += f" · busca “{self._busca.strip()}”"
        return resumo

    @Property("QVariantMap", notify=mudou)
    def selecionado(self):
        return self._selecionado

    @Property(int, notify=mudou)
    def quantidade(self):
        return len(self.modelo.itens)

    @Property(int, notify=mudou)
    def indiceSelecionado(self):
        chave = self._selecionado.get("id", self._selecionado.get("hash"))
        return next((i for i, item in enumerate(self.modelo.itens)
                     if item.get("id", item.get("hash")) == chave), -1)

    @Property("QVariantMap", notify=mudou)
    def resumo(self):
        return {k: len(v) for k, v in self._dados.items()}

    @Property(bool, notify=mudou)
    def ocupado(self):
        return bool(self._tarefas)

    @Property(bool, notify=mudou)
    def emJogo(self):
        return self._em_jogo

    @Property(str, notify=mudou)
    def atividade(self):
        return next((t[2] for t in self._tarefas.values()), "Tudo pronto")

    @Property("QVariantList", notify=mudou)
    def integracoes(self):
        return self.servico.integracoes.listar()

    @Property("QVariantMap", notify=playerMudou)
    def audio(self):
        atual = self._player.atual() or {}
        return {"titulo": self._tocando.get("titulo", "Sua trilha sonora"),
                "artista": self._tocando.get("artista", "Selecione uma faixa em Músicas"),
                "capa_url": self._tocando.get("capa_url", ""),
                "estado": "carregando" if self._audio_carregando else self._player.estado,
                "posicao": atual.get("pos_ms") or 0, "duracao": atual.get("dur_ms") or 0}

    @Property("QVariantMap", notify=volumeMudou)
    def volume(self):
        return self._volume

    @Property("QVariantMap", notify=mudou)
    def aparencia(self):
        return self._aparencia

    @Property("QVariantMap", notify=preferenciasMudou)
    def preferencias(self):
        return self._preferencias

    @Property("QVariantMap", notify=ferramentasMudou)
    def ferramentasJogo(self):
        return self._ferramentas

    @Property("QVariantMap", notify=ferramentasMudou)
    def estatisticasAno(self):
        return self._estatisticas

    @Property("QVariantMap", notify=preferenciasMudou)
    def apiLocal(self):
        return self._api_estado

    @Property("QVariantList", notify=ferramentasMudou)
    def watchProntos(self):
        return self._watch_prontos

    @Property(bool, constant=True)
    def multimediaDisponivel(self):
        try:
            return importlib.util.find_spec("PySide6.QtMultimedia") is not None
        except (ImportError, ValueError):
            return False

    @Property(QObject, constant=True)
    def emulacao(self):
        return self._emulacao

    @Property("QVariantList", notify=controleMudou)
    def controlesConectados(self):
        return list(self._controles)

    @Property("QVariantMap", notify=sponsorMudou)
    def sponsor(self):
        return self._sponsor

    @Property(bool, constant=True)
    def webDisponivel(self):
        """QtWebEngine instalado? (variante completa do bundle)."""
        import os

        from bib_nucleo.rede import rede_ativa
        if os.environ.get("BIBLIOTECA_WEBENGINE", "1") == "0" or not rede_ativa():
            return False
        try:
            return importlib.util.find_spec("PySide6.QtWebEngineQuick") is not None
        except Exception:
            return False

    @Property("QVariantMap", notify=letrasMudou)
    def letras(self):
        return self._letras

    @Property(int, notify=playerMudou)
    def letraIndice(self):
        if self._letras_faixa != (self._tocando.get("artista"), self._tocando.get("titulo")):
            return -1
        segundos = self.audio["posicao"] / 1000
        linhas = self._letras.get("linhas", [])
        return next((i for i in range(len(linhas) - 1, -1, -1)
                     if linhas[i]["t"] <= segundos), -1)

    @Property("QVariantMap", notify=fontesMudou)
    def fontesDesejo(self):
        return self._fontes_desejo

    @Property(str, notify=playerMudou)
    def modoAudioAtual(self):
        return self._modo_audio

    @Property("QVariantMap", notify=previewMudou)
    def previewImportacao(self):
        return self._preview

    @Property("QVariantMap", notify=manutencaoMudou)
    def manutencao(self):
        return self._manutencao

    @Property("QVariantMap", notify=manutencaoMudou)
    def saneamento(self):
        return self._saneamento

    @Property("QVariantList", notify=mudou)
    def pacotesPiratas(self):
        return self._pacotes_piratas

    @Property("QVariantMap", notify=prontosMudou)
    def torrentsProntos(self):
        return self._prontos

    @Property("QVariantMap", notify=emusMudou)
    def emus(self):
        return self._emus

    @Property("QVariantMap", notify=padsMudou)
    def pads(self):
        return self._pads


__all__ = ["HubBridge", "ModeloItens", "SinaisTarefa", "Tarefa",
           "SECOES_CONTROLE", "TECLAS_CONTROLE", "Qt", "QGuiApplication",
           "ler_estados_xinput"]
