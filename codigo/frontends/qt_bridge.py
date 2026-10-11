"""View-model Qt: sinais, modelos e tarefas; QML não acessa banco ou processos."""
from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import (QAbstractListModel, QModelIndex, QObject, Property,
                            QRunnable, Qt, QThreadPool, QTimer, QUrl, Signal, Slot)
from PySide6.QtGui import QDesktopServices

import bib_core as core
from bib_nucleo import online, spotify
from servicos_ui import ServicoBiblioteca


class ModeloItens(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.itens = []

    def roleNames(self):
        return {Qt.UserRole + 1: b"item"}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.itens)

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and 0 <= index.row() < len(self.itens):
            if role == Qt.UserRole + 1:
                return self.itens[index.row()]
        return None

    def substituir(self, itens):
        self.beginResetModel()
        self.itens = list(itens)
        self.endResetModel()


class SinaisTarefa(QObject):
    terminou = Signal(int, object, str)


class Tarefa(QRunnable):
    def __init__(self, numero, trabalho):
        super().__init__()
        self.numero, self.trabalho = numero, trabalho
        self.sinais = SinaisTarefa()

    def run(self):
        try:
            resultado, erro = self.trabalho(), ""
        except Exception as exc:
            resultado, erro = None, str(exc) or type(exc).__name__
        self.sinais.terminou.emit(self.numero, resultado, erro)


class HubBridge(QObject):
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
    _progressoVideo = Signal(object)
    _progressoMusica = Signal(object)
    aviso = Signal(str, bool)
    jogoIniciado = Signal()
    jogoTerminou = Signal()
    pedirClassico = Signal()
    _sessao = Signal(int, float, bool)

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
        self._aparencia = {"tema": "escuro", "densidade": "conforto"}
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

    @Slot()
    def consultarMidias(self):
        def pronto(r):
            self._midias_status = r
            self.midiasMudou.emit()
        self.executar("Detectando ferramentas de mídia…", self.servico.midias_status, pronto)

    @Slot(str, str, str)
    def abrirFerramentaMidia(self, tipo, nome, caminho):
        self.executar("Abrindo ferramenta de mídia…",
                      lambda: self.servico.abrir_ferramenta_midia(tipo, nome, caminho))

    @Slot(str, str)
    def aplicarEqualizacao(self, caminho, preset):
        self._alterar("Equalizando cópia de áudio…", lambda: self.servico.aplicar_eq_musica(caminho, preset))

    @Slot(QUrl)
    def importarVideos(self, url):
        caminho = url.toLocalFile()
        if caminho:
            self._alterar("Importando videoteca…", lambda: self.servico.importar_videos(caminho))

    @Slot(int, str)
    def reproduzirVideo(self, ident, reprodutor="auto"):
        self.executar("Abrindo vídeo…", lambda: self.servico.reproduzir_video(ident, reprodutor))

    @Slot(str, bool)
    def buscarVideos(self, termo, atualizar=False):
        self._videos_geracao += 1
        geracao = self._videos_geracao
        self._videos_mensagem = "Buscando no YouTube…"
        self.videoMudou.emit()
        def pronto(r):
            if geracao == self._videos_geracao:
                self.video_resultados.substituir(r.get("itens", []))
                self._videos_mensagem = "; ".join(r.get("erros", [])) or f'{len(r.get("itens", []))} resultado(s)'
                self.videoMudou.emit()
        def falha(erro):
            if geracao == self._videos_geracao:
                self._videos_mensagem = erro
                self.videoMudou.emit()
        self.executar("Buscando vídeos…", lambda: self.servico.buscar_videos_online(termo, atualizar=atualizar), pronto, falha)

    @Slot(str)
    def baixarVideo(self, video_id):
        if self.ocupado:
            return
        def trabalho():
            try:
                return self.servico.baixar_video_online(video_id, lambda vid, pct:
                    self._progressoVideo.emit({"rotulo": vid, "pct": pct}))
            finally:
                self._progressoVideo.emit({"rotulo": "", "pct": 0})
        self._alterar("Baixando vídeo para a videoteca…", trabalho)

    @Slot(object)
    def _mostrar_progresso_video(self, dados):
        if not self._fechado:
            self._video_progresso = dados
            self.videoMudou.emit()

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
        return self.servico.aparencia()

    @Slot(str, str, bool, bool)
    def definirAparencia(self, tema, densidade, auto_backup=True, modo_simples=False):
        def pronto(r):
            self._aparencia = r
            self.mudou.emit()
        self.executar("Salvando aparência…",
                      lambda: self.servico.definir_aparencia(tema, densidade, auto_backup, modo_simples),
                      pronto)

    @Slot(int, str)
    def salvarObservacoes(self, gid, texto):
        self._alterar("Salvando notas do jogo…", lambda: self.servico.salvar_observacoes(gid, texto))

    @Slot(QUrl)
    def exportarColecao(self, url):
        pasta = url.toLocalFile()
        if not pasta:
            return

        def pronto(_r):
            self.aviso.emit("Coleção exportada para a pasta escolhida (pacote ZIP).", False)

        self.executar("Exportando coleção…",
                      lambda: self.servico.exportar_colecao_para(pasta), pronto,
                      lambda erro: self.aviso.emit(f"Exportação falhou: {erro}", True))

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
        if secao not in (*self._dados, "integracoes", "inicio") or secao == self._secao:
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

    def _alterar(self, rotulo, operacao):
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
        self.executar(rotulo, operacao, pronto)

    @Slot(int)
    def favorito(self, gid):
        self._alterar("Atualizando favorito…", lambda: self.servico.favorito(gid))

    @Slot(int, str, str, str, str, str, str)
    @Slot(int, str, str, str, str, str, str, bool)
    def salvarJogo(self, gid, titulo, exe, argumentos, status, nota="", etiquetas="", sincronizar=False):
        try:
            nota_v = int(nota) if str(nota).strip() not in ("", "None") else None
        except (TypeError, ValueError):
            self.aviso.emit("Nota deve ser inteiro 0-10 ou vazio.", True)
            return
        dados = {"titulo": titulo, "executable_path": exe, "launch_options": argumentos,
                 "status": status or "backlog", "nota": nota_v, "etiquetas": etiquetas}
        self._alterar("Salvando jogo…", lambda: self.servico.salvar_jogo(gid, dados, sincronizar))

    @Slot(str)
    def modoAudio(self, modo):
        if modo in ("sequencia", "aleatorio", "repetir"):
            self._modo_audio = modo
            self.playerMudou.emit()

    @Property(str, notify=playerMudou)
    def modoAudioAtual(self):
        return self._modo_audio

    @Slot(result="QVariantList")
    def listarBackups(self):
        return self.servico.backups()

    @Slot(result="QVariantList")
    def listarSessoes(self):
        return self.servico.sessoes()

    @Slot(result=str)
    def verLog(self):
        return self.servico.log_cauda()

    @Slot(int, float)
    def registrarSessao(self, gid, horas):
        self._alterar("Registrando sessão…", lambda: self.servico.registrar_sessao(gid, horas))

    @Slot(str, float)
    def encerrarSessao(self, arquivo, horas):
        self._alterar("Encerrando sessão…", lambda: self.servico.encerrar_sessao(arquivo, horas))

    @Slot(str, int)
    def excluir(self, categoria, ident):
        self._alterar("Removendo da coleção…", lambda: self.servico.excluir(categoria, ident))

    @Slot(str, str)
    def adicionarDesejo(self, appid, titulo):
        self._alterar("Salvando desejo…", lambda: self.servico.adicionar_desejo(appid, titulo))

    @Slot(QUrl)
    def importarMusicas(self, url):
        pasta = url.toLocalFile()
        if pasta:
            self._alterar("Importando músicas…", lambda: self.servico.importar_musicas(pasta))

    @Slot()
    def backup(self):
        self._alterar("Criando backup…", lambda: core.fazer_backup(self.servico.db_path))

    @Slot(int)
    def jogar(self, gid):
        if self.ocupado or self._em_jogo:
            return
        self._em_jogo = True
        self._jogo_gid = gid
        self.mudou.emit()

        def trabalho():
            try:
                return self.servico.iniciar_jogo(gid, lambda h, r: self._sessao.emit(gid, h, r))
            except Exception:
                self._sessao.emit(gid, 0, True)
                raise

        def pronto(resultado):
            self.aviso.emit(resultado.get("aviso") or "Jogo iniciado. Boa diversão!", False)
            self.jogoIniciado.emit()
        self.executar("Preparando jogo…", trabalho, pronto)

    @Slot(int, float, bool)
    def _fim_jogo(self, gid, horas, rastreado):
        self._em_jogo = False
        self._atualizar_conquistas()
        jogo_gid, self._jogo_gid = self._jogo_gid, 0
        if rastreado:
            self.executar("Registrando sessão…", lambda: self.servico.registrar_sessao(gid, horas),
                          lambda _r: self.atualizar())
            self.jogoTerminou.emit()
            self._auto_backup_sessao(jogo_gid or gid)
        else:
            self.aviso.emit("Sessão sem rastreio: registre as horas nas ferramentas clássicas.", False)
        self.mudou.emit()

    def _auto_backup_sessao(self, gid):
        """Backup da coleção ao encerrar sessão rastreada (opt-in, default ligado)."""
        if self._fechado or not gid:
            return
        if self.aparencia.get("auto_backup", True) is False:
            return

        def pronto(_r):
            if not self._fechado:
                self.aviso.emit("Backup da coleção criado após a sessão.", False)

        self.executar("Guardando backup pós-sessão…",
                      lambda: core.fazer_backup(self.servico.db_path), pronto)

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

    def fechar(self):
        self._fechado = True
        self._audio_token += 1
        self._timer_player.stop()
        self._timer_downloads.stop()
        self._timer_volume.stop()
        self._timer_conquistas.stop()
        self._timer_spotify.stop()
        self._busca_timer.stop()
        self._pool.waitForDone()
        self._player.parar()
        self._player.backend.close()
        self.servico.spotify.fechar()
