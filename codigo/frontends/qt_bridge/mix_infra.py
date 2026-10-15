#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ponte Qt: ciclo de vida, tarefas, navegacao, preferencias e volume."""
from __future__ import annotations

import threading

import bib_core as core
from navegacao_controle import Navegador
from PySide6.QtCore import (
    Qt,
    QThreadPool,
    QTimer,
    Slot,
)
from qt_emulacao import FerramentasEmulador
from servicos_ui import ServicoBiblioteca

from .modelos import ModeloItens, Tarefa


class MixInfra:
    def __init__(self, db_path, parent=None, servico=None):
        super().__init__(parent)
        self.servico = servico or ServicoBiblioteca(db_path)
        self.modelo = ModeloItens(self)
        self.resultados = ModeloItens(self)
        self.global_resultados = ModeloItens(self)
        self.artes = ModeloItens(self)
        self.spotify_resultados = ModeloItens(self)
        self.musica_online_resultados = ModeloItens(self)
        self.video_resultados = ModeloItens(self)
        self._videos_geracao = 0
        self._videos_mensagem = "Busque um vídeo/canal ou importe arquivos locais."
        self._video_progresso = {"rotulo": "", "pct": 0}
        self._letras = {"ok": False, "sincronizadas": False, "linhas": [], "texto": "", "erro": ""}
        self._letras_geracao = self._fontes_geracao = 0
        self._letras_faixa = ("", "")
        self._fontes_desejo = {"steamrip": [], "fitgirl": [], "erros": []}
        self._midias_status = {"imagens": {}, "equalizadores": {}, "videos": {}, "eq_presets": []}
        self._progressoVideo.connect(self._mostrar_progresso_video, Qt.QueuedConnection)
        self._musica_online_selecao = set()
        self._musica_online_geracao = 0
        self._musica_online_mensagem = "Busca sem conta: Deezer, iTunes e MusicBrainz."
        self._arte_contexto = None
        self._arte_geracao = 0
        self._fila_musicas = []
        self._conquistas = {"itens": [], "total": 0, "desbloqueadas": 0, "avaliaveis": 0,
                            "status": "Sincronize o catálogo de referência para começar.", "appid": "", "save": ""}
        self._conquistas_gid = 0
        self._conquistas_geracao = 0
        self._jogo_gid = 0
        self._spotify_selecao = set()
        self._spotify_proxima = ""
        self._spotify_contexto = ("busca", "")
        self._spotify_geracao = 0
        self._cancelar_musicas = threading.Event()
        self._download_musica = {"rotulo": "", "pct": 0, "id": 0, "cancelando": False}
        self._progressoMusica.connect(self._mostrar_progresso_musica, Qt.QueuedConnection)
        self._secao, self._busca, self._filtro, self._ordem = "inicio", "", "todos", "titulo"
        self._dados = {"jogos": [], "musicas": [], "desejos": [], "downloads": [], "videos": []}
        self._pacotes_piratas = []
        self._sistema = {"jogos": 0, "musicas": 0, "desejos": 0, "downloads": 0,
                         "pendentes": 0, "backup": "…", "disco_livre_gb": 0,
                         "backup_idade_dias": None, "backup_estado": "carregando",
                         "disco_total_gb": 0, "recentes": []}
        self._saude = {"total": 0, "problemas": [], "ok": 0, "pendentes": 0,
                       "ids_pendentes": [], "verificada": False}
        self._paleta = ""
        self._modo_audio = "sequencia"
        self._selecionado = {}
        self._tarefas, self._numero = {}, 0
        self._precos = {}
        self._aparencia = self.servico.aparencia()
        from bib_nucleo.preferencias_pessoais import ler_preferencias
        self._preferencias = ler_preferencias()
        perfil = self._preferencias["perfis"][self._preferencias["ativo"]]
        self._filtro = perfil.get("filtro", "todos")
        self._ordem = perfil.get("ordem", "titulo")
        self._ferramentas = {"saves": [], "snapshots": [], "screenshots": [], "pasta_screenshots": ""}
        self._ferramentas_gid = 0
        self._estatisticas = {"ano": 2026, "meses": [0] * 12, "total_horas": 0, "jogos": []}
        self._watch_prontos = []
        self._api = None
        self._api_estado = {"ativa": False, "url": "", "token": ""}
        self._sponsor = {"video": "", "segmentos": []}
        self._vigia = None
        self._geracao = 0
        self._catalogo_geracao = 0
        self._fechado = False
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(3)
        self._player = core.Player()
        self._audio_lock = threading.Lock()
        self._audio_token = 0
        self._audio_carregando = False
        self._tocando = {}
        self._em_jogo = False
        self._volume = {"ok": False, "nivel": 0, "mudo": False}
        self._sessao.connect(self._fim_jogo)
        self._busca_timer = QTimer(self)
        self._busca_timer.setSingleShot(True)
        self._busca_timer.setInterval(120)
        self._busca_timer.timeout.connect(self._filtrar)
        self._timer_player = QTimer(self)
        self._timer_player.setInterval(750)
        self._timer_player.timeout.connect(self._vigiar_audio)
        self._timer_player.start()
        self._timer_downloads = QTimer(self)
        self._timer_downloads.setInterval(5000)
        self._timer_downloads.timeout.connect(self._atualizar_downloads)
        self._timer_volume = QTimer(self)
        self._timer_volume.setInterval(1000)
        self._timer_volume.timeout.connect(self.consultarVolume)
        self._timer_volume.start()
        QTimer.singleShot(0, self.consultarVolume)
        self._timer_conquistas = QTimer(self)
        self._timer_conquistas.setInterval(5000)
        self._timer_conquistas.timeout.connect(self._atualizar_conquistas)
        self._timer_conquistas.start()
        self._timer_spotify = QTimer(self)
        self._timer_spotify.setInterval(500)
        self._timer_spotify.timeout.connect(self._callback_spotify)
        self._timer_spotify.start()
        self._timer_watch = QTimer(self)
        self._timer_watch.setInterval(15000)
        self._timer_watch.timeout.connect(self._consultar_watch)
        self._timer_watch.start()
        self._timer_screenshots = QTimer(self)
        self._timer_screenshots.setInterval(5000)
        self._timer_screenshots.timeout.connect(self._atualizar_screenshots)
        self._timer_screenshots.start()
        self._emulacao = FerramentasEmulador(self)
        self._preview = {"itens": [], "info": {}, "raizes": [], "origem": "", "erro": ""}
        self._manutencao = {"gid": 0, "titulo": "", "exe": {}, "rom": {}}
        self._saneamento = {"ok": False, "pasta": "", "exe": None,
                            "precisa_instalar": False, "quarentenaveis": 0,
                            "avisos": [], "erro": ""}
        self._prontos = {"itens": [], "erros": []}
        self._emus = {"itens": [], "consulta": {}}
        self._emu_infos: dict[str, dict] = {}
        self._pads = {"pads": [], "presets": [], "tipos": [], "estado": ""}
        self._controles: list[str] = []
        self._navegador = Navegador()
        self._navegador.bloquear_ate_neutro()
        self._janela_controle = None
        self._timer_controle = QTimer(self)
        self._timer_controle.setInterval(33)
        self._timer_controle.timeout.connect(self._ler_controle)
        self._timer_controle.start()


    @Slot(str)
    def trocarPerfil(self, nome):
        from bib_nucleo.preferencias_pessoais import trocar_perfil
        if self.ocupado or self._em_jogo:
            self.aviso.emit("Aguarde a operação/sessão para trocar de perfil.", False)
            return
        self._preferencias = trocar_perfil(nome)
        perfil = self._preferencias["perfis"][nome]
        self._filtro = perfil.get("filtro", "todos")
        self._ordem = perfil.get("ordem", "titulo")
        self.preferenciasMudou.emit()
        self.consultarEstatisticas()
        self.atualizar()

    @Slot()
    def salvarFiltroPerfil(self):
        from bib_nucleo.preferencias_pessoais import salvar_filtro
        self._preferencias = salvar_filtro(self._filtro, self._ordem)
        self.preferenciasMudou.emit()

    @Slot(str, str)
    def salvarAtalho(self, acao, sequencia):
        from bib_nucleo.preferencias_pessoais import salvar_atalhos
        try:
            self._preferencias = salvar_atalhos({**self._preferencias["atalhos"], acao: sequencia})
            self.preferenciasMudou.emit()
        except ValueError as e:
            self.aviso.emit(str(e), True)

    def executar(self, rotulo, trabalho, pronto=None, falha=None):
        if self._fechado:
            return
        self._numero += 1
        tarefa = Tarefa(self._numero, trabalho)
        tarefa.sinais.terminou.connect(self._concluir, Qt.QueuedConnection)
        self._tarefas[self._numero] = (tarefa, pronto, rotulo, falha)
        self.mudou.emit()
        self._pool.start(tarefa)

    @Slot(int, object, str)
    def _concluir(self, numero, resultado, erro):
        entrada = self._tarefas.pop(numero, None)
        if self._fechado or entrada is None:
            return
        try:
            if erro:
                if entrada[3]:
                    entrada[3](erro)
                else:
                    self.aviso.emit(erro, True)
            elif entrada[1]:
                entrada[1](resultado)
        except Exception as exc:
            self.aviso.emit(str(exc), True)
        finally:
            if entrada[2] == "Autorizando Spotify…":
                self.spotifyMudou.emit()
            self.mudou.emit()

    @Slot()
    def atualizar(self):
        self._geracao += 1
        geracao = self._geracao

        def saude_pronta(saude):
            if geracao == self._geracao:
                self._saude = dict(saude, verificada=True)
                if self._secao == "jogos" and self._filtro == "pendencias":
                    self._filtrar()
                else:
                    self.mudou.emit()

        def pronto(dados):
            if geracao == self._geracao:
                self._sistema = dados.pop("sistema", self._sistema)
                self._fila_musicas = dados.pop("fila_musicas", [])
                self._dados.update(dados)
                self._filtrar()
                self.buscarPaleta(self._paleta)
                self.executar("Verificando saúde da coleção…", self.servico.saude,
                              saude_pronta)
        self.executar("Carregando sua coleção…", self.servico.snapshot, pronto)
        if self._secao == "downloads":
            self._atualizar_downloads()

    @Slot(str)
    def navegar(self, secao):
        if secao not in (*self._dados, "integracoes", "inicio", "youtube") or secao == self._secao:
            return
        self._secao, self._busca, self._selecionado = secao, "", {}
        self._busca_timer.stop()
        if secao == "downloads":
            self._timer_downloads.start()
            self._atualizar_downloads()
        else:
            self._timer_downloads.stop()
        self._filtrar()

    @Slot(str)
    def pesquisar(self, texto):
        self._busca = texto
        self._busca_timer.start()

    @Slot(str)
    def filtrar(self, filtro):
        if filtro not in ("todos", "favoritos", "jogando", "PC", "3DS", "NDS", "pendencias"):
            return
        self._filtro = filtro
        self._filtrar()

    @Slot()
    def limparFiltros(self):
        self._busca_timer.stop()
        self._busca = ""
        if self._secao == "jogos":
            self._filtro = "todos"
        self._filtrar()

    @Slot()
    def verPendencias(self):
        self.navegar("jogos")
        self._busca_timer.stop()
        self._busca, self._filtro = "", "pendencias"
        self._filtrar()

    @Slot(str)
    def ordenar(self, ordem):
        self._ordem = ordem
        self._filtrar()

    @Slot(str)
    def buscarPaleta(self, termo):
        from servicos_ui import busca_global
        self._paleta = termo
        self.global_resultados.substituir(
            busca_global(self._dados["jogos"], self._dados["musicas"],
                         self._dados["desejos"], self._dados["downloads"], termo))
        self.mudou.emit()

    @Slot()
    def abrirPrimeiraPaleta(self):
        if self.global_resultados.itens:
            self.abrirPaleta(dict(self.global_resultados.itens[0]))

    @Slot(int, result="QVariantMap")
    def paletaItem(self, idx):
        try:
            idx = int(idx)
            if 0 <= idx < len(self.global_resultados.itens):
                return dict(self.global_resultados.itens[idx])
        except (TypeError, ValueError):
            pass
        return {}

    @Slot("QVariantMap")
    def abrirPaleta(self, item):
        tipo = (item or {}).get("tipo")
        secao = {"jogo": "jogos", "musica": "musicas", "desejo": "desejos",
                 "download": "downloads"}.get(tipo)
        if secao is None:
            return
        self.navegar(secao)
        self.limparFiltros()
        idx = next((i for i, entrada in enumerate(self.modelo.itens)
                    if entrada.get("id", entrada.get("hash")) == item.get("id")), -1)
        if idx >= 0:
            self.selecionar(idx)
            if tipo == "musica":
                self.tocar(item["id"])
        else:
            self.aviso.emit("Este resultado não está mais na coleção. Atualize a busca.", False)

    def _filtrar(self):
        itens = list(self._dados.get(self._secao, []))
        if self._secao == "jogos":
            if self._filtro == "favoritos":
                itens = [j for j in itens if j.get("favorito")]
            elif self._filtro in ("PC", "3DS", "NDS"):
                itens = [j for j in itens if j.get("plataforma") == self._filtro]
            elif self._filtro == "jogando":
                itens = [j for j in itens if j.get("status") == "jogando"]
            elif self._filtro == "pendencias":
                pendentes = set(self._saude.get("ids_pendentes", []))
                itens = [j for j in itens if j.get("id") in pendentes]
            if self._ordem == "recentes":
                itens.sort(key=lambda j: j.get("ultima_execucao") or "", reverse=True)
            elif self._ordem == "horas":
                itens.sort(key=lambda j: float(j.get("horas") or 0), reverse=True)
            else:
                itens.sort(key=lambda j: j["titulo"].casefold())
        palavras = self._busca.casefold().split()
        if palavras:
            import unicodedata

            def _sem(s):
                return "".join(c for c in unicodedata.normalize(
                    "NFD", str(s or "").casefold()) if unicodedata.category(c) != "Mn")

            alvos = [_sem(p) for p in palavras]
            itens = [j for j in itens if all(p in _sem(" ".join(str(j.get(k) or "") for k in
                     ("titulo", "nome", "artista", "album", "etiquetas", "canal"))) for p in alvos)]
        anterior = self._selecionado.get("id", self._selecionado.get("hash"))
        self.modelo.substituir(itens)
        self._selecionado = next((j for j in itens if j.get("id", j.get("hash")) == anterior),
                                itens[0] if itens else {})
        self.mudou.emit()

    @Slot(int)
    def selecionar(self, indice):
        if 0 <= indice < len(self.modelo.itens):
            self._selecionado = self.modelo.itens[indice]
            self.mudou.emit()

    def _alterar(self, rotulo, operacao, apos=None):
        if self.ocupado:
            self.aviso.emit("Aguarde a operação atual terminar.", False)
            return

        def pronto(resultado):
            if isinstance(resultado, dict) and resultado.get("ok") is False:
                raise ValueError(resultado.get("erro", "A operação não foi concluída."))
            erros = resultado.get("erros", []) if isinstance(resultado, dict) else []
            avisos = resultado.get("avisos", []) if isinstance(resultado, dict) else []
            mensagem = "; ".join(erros or avisos) if erros or avisos else "Operação concluída."
            self.aviso.emit(mensagem, bool(erros))
            self.atualizar()
            if apos:
                apos(resultado)
        self.executar(rotulo, operacao, pronto)

    @Slot(bool)
    def definirApiLocal(self, ativa):
        if self.ocupado:
            self.aviso.emit("Aguarde a operação atual para alterar a API local.", False)
            return
        from bib_nucleo.api_local import ApiLocal
        def trabalho():
            if self._api:
                self._api.fechar()
                self._api = None
            if ativa:
                self._api = ApiLocal(self.servico)
                return self._api.iniciar()
            return {"ativa": False, "url": "", "token": ""}
        def pronto(r):
            self._api_estado = r
            self.preferenciasMudou.emit()
        self.executar("Alterando API local…", trabalho, pronto)

    @Slot()
    def consultarVolume(self):
        if self._fechado:
            return
        self._volume = core.ler_volume_pc()
        self.volumeMudou.emit()

    @Slot()
    def rodarDiagnostico(self):
        """Diagnostico somente-leitura; resultado vira texto no relatorio."""
        import json as _json
        from pathlib import Path as _P

        from ferramentas.diagnosticar import diagnosticar

        def trabalho():
            try:
                d = diagnosticar(_P(core.__file__).resolve().parents[1],
                                 _P(self.servico.db_path))
                return _json.dumps(d, ensure_ascii=False, indent=2)
            except Exception as e:  # diagnostico nunca deve derrubar a UI
                return _json.dumps({"erro": str(e)}, ensure_ascii=False, indent=2)

        self.executar("Diagnosticando a instalacao", trabalho,
                      lambda texto: self.diagnosticoPronto.emit(texto))

    @Slot(float)
    def definirVolume(self, nivel):
        self._volume = core.definir_volume_pc(nivel)
        if not self._volume.get("ok"):
            self.aviso.emit(self._volume.get("erro", "Volume indisponível."), True)
        self.volumeMudou.emit()

    @Slot()
    def silenciar(self):
        self._volume = core.alternar_mudo_pc()
        self.volumeMudou.emit()

    @Slot()
    def consultarEstatisticas(self):
        def pronto(r):
            self._estatisticas = r
            self.ferramentasMudou.emit()
        self.executar("Lendo histórico local…", self.servico.estatisticas, pronto)

    @Slot(str, str, str, bool, bool)
    def definirAparencia(self, tema, densidade, auto_backup=True, modo_simples=False):
        def pronto(r):
            self._aparencia = r
            self.mudou.emit()
        self.executar("Salvando aparência…",
                      lambda: self.servico.definir_aparencia(tema, densidade, auto_backup, modo_simples),
                      pronto)

    @Slot(float)
    def definirEscalaTexto(self, escala):
        """Escala de texto em % (0.8–1.5); persiste e reemite para o QML aplicar."""
        def pronto(r):
            self._aparencia = r
            self.mudou.emit()
        self.executar("Salvando escala de texto…",
                      lambda: self.servico.definir_aparencia(escala_texto=escala),
                      pronto)

    def fechar(self):
        self._fechado = True
        self._audio_token += 1
        self._timer_player.stop()
        self._timer_downloads.stop()
        self._timer_volume.stop()
        self._timer_conquistas.stop()
        self._timer_spotify.stop()
        self._timer_watch.stop()
        self._timer_screenshots.stop()
        self._timer_controle.stop()
        self._busca_timer.stop()
        self._pool.waitForDone()
        if self._api:
            self._api.fechar()
        self._player.parar()
        self._player.backend.close()
        self.servico.spotify.fechar()


__all__ = ["MixInfra"]
