"""View-model Qt: sinais, modelos e tarefas; QML não acessa banco ou processos."""
from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import (QAbstractListModel, QModelIndex, QObject, Property,
                            QRunnable, Qt, QThreadPool, QTimer, QUrl, Signal, Slot)
from PySide6.QtGui import QDesktopServices

import bib_core as core
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
        self._secao, self._busca, self._filtro, self._ordem = "inicio", "", "todos", "titulo"
        self._dados = {"jogos": [], "musicas": [], "desejos": [], "downloads": []}
        self._sistema = {"jogos": 0, "musicas": 0, "desejos": 0, "downloads": 0,
                         "pendentes": 0, "backup": "…", "disco_livre_gb": 0,
                         "disco_total_gb": 0, "recentes": []}
        self._saude = {"total": 0, "problemas": [], "ok": 0}
        self._paleta = ""
        self._modo_audio = "sequencia"
        self._selecionado = {}
        self._tarefas, self._numero = {}, 0
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
                 "artista": f.get("artista", ""), "atual": i == (self._player.idx or -1)}
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

    @Property("QVariantList", constant=True)
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

    @Slot()
    def consultarVolume(self):
        self._volume = core.ler_volume_pc()
        self.volumeMudou.emit()

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

    def executar(self, rotulo, trabalho, pronto=None):
        if self._fechado:
            return
        self._numero += 1
        tarefa = Tarefa(self._numero, trabalho)
        tarefa.sinais.terminou.connect(self._concluir, Qt.QueuedConnection)
        self._tarefas[self._numero] = (tarefa, pronto, rotulo)
        self.mudou.emit()
        self._pool.start(tarefa)

    @Slot(int, object, str)
    def _concluir(self, numero, resultado, erro):
        entrada = self._tarefas.pop(numero, None)
        if self._fechado or entrada is None:
            return
        try:
            if erro:
                self.aviso.emit(erro, True)
            elif entrada[1]:
                entrada[1](resultado)
        except Exception as exc:
            self.aviso.emit(str(exc), True)
        finally:
            self.mudou.emit()

    @Slot()
    def atualizar(self):
        self._geracao += 1
        geracao = self._geracao

        def pronto(dados):
            if geracao == self._geracao:
                self._sistema = dados.pop("sistema", self._sistema)
                self._dados.update(dados)
                self._filtrar()
                self.buscarPaleta(self._paleta)
                self.executar("Verificando saúde da coleção…", self.servico.saude,
                              lambda s: (setattr(self, "_saude", s), self.mudou.emit()))
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
        self._filtro = filtro
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
            return dict(self.global_resultados.itens[int(idx)])
        except (IndexError, TypeError, ValueError):
            return {}

    @Slot("QVariantMap")
    def abrirPaleta(self, item):
        tipo = (item or {}).get("tipo")
        if tipo == "jogo":
            self.navegar("jogos")
            idx = next((i for i, j in enumerate(self.modelo.itens)
                        if j.get("id") == item.get("id")), -1)
            if idx >= 0:
                self.selecionar(idx)
        elif tipo == "musica":
            self.navegar("musicas")
            idx = next((i for i, m in enumerate(self.modelo.itens)
                        if m.get("id") == item.get("id")), -1)
            if idx >= 0:
                self.selecionar(idx)
                self.tocar(item["id"])
        elif tipo == "desejo":
            self.navegar("desejos")
        elif tipo == "download":
            self.navegar("downloads")

    def _filtrar(self):
        itens = list(self._dados.get(self._secao, []))
        if self._secao == "jogos":
            if self._filtro == "favoritos":
                itens = [j for j in itens if j.get("favorito")]
            elif self._filtro in ("PC", "3DS", "NDS"):
                itens = [j for j in itens if j.get("plataforma") == self._filtro]
            elif self._filtro == "jogando":
                itens = [j for j in itens if j.get("status") == "jogando"]
            if self._ordem == "recentes":
                itens.sort(key=lambda j: j.get("ultima_execucao") or "", reverse=True)
            elif self._ordem == "horas":
                itens.sort(key=lambda j: float(j.get("horas") or 0), reverse=True)
            else:
                itens.sort(key=lambda j: j["titulo"].casefold())
        palavras = self._busca.casefold().split()
        if palavras:
            itens = [j for j in itens if all(p in " ".join(str(j.get(k) or "") for k in
                     ("titulo", "nome", "artista", "album", "etiquetas")).casefold() for p in palavras)]
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
            mensagem = "; ".join(erros) if erros else "Operação concluída."
            self.aviso.emit(mensagem, bool(erros))
            self.atualizar()
        self.executar(rotulo, operacao, pronto)

    @Slot(int)
    def favorito(self, gid):
        self._alterar("Atualizando favorito…", lambda: self.servico.favorito(gid))

    @Slot(int, str, str, str, str, str, str)
    def salvarJogo(self, gid, titulo, exe, argumentos, status, nota="", etiquetas=""):
        try:
            nota_v = int(nota) if str(nota).strip() not in ("", "None") else None
        except (TypeError, ValueError):
            self.aviso.emit("Nota deve ser inteiro 0-10 ou vazio.", True)
            return
        dados = {"titulo": titulo, "executable_path": exe, "launch_options": argumentos,
                 "status": status or "backlog", "nota": nota_v, "etiquetas": etiquetas}
        self._alterar("Salvando jogo…", lambda: self.servico.salvar_jogo(gid, dados))

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
        if rastreado:
            self.executar("Registrando sessão…", lambda: self.servico.registrar_sessao(gid, horas),
                          lambda _r: self.atualizar())
            self.jogoTerminou.emit()
        else:
            self.aviso.emit("Sessão sem rastreio: registre as horas nas ferramentas clássicas.", False)
        self.mudou.emit()

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

    @Slot()
    def iniciarDownloads(self):
        self._alterar("Iniciando qBittorrent…", core.qbit_iniciar)

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
        self._busca_timer.stop()
        self._pool.waitForDone()
        self._player.parar()
        self._player.backend.close()
