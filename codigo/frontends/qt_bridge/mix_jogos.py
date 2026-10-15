#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ponte Qt: jogos, scans, pacotes, sessoes e biblioteca."""
from __future__ import annotations

from pathlib import Path

import bib_core as core
from PySide6.QtCore import (
    QUrl,
    Slot,
)


class MixJogos:


    @Slot(int)
    def consultarFerramentasJogo(self, gid):
        self._ferramentas_gid = gid
        if not gid:
            return
        def pronto(r):
            if gid == self._ferramentas_gid:
                self._ferramentas = r
                self.ferramentasMudou.emit()
        self.executar("Lendo ferramentas do jogo…", lambda: self.servico.ferramentas_jogo(gid), pronto)

    def _atualizar_screenshots(self):
        if not self._fechado and self._ferramentas_gid and not self.ocupado:
            self.consultarFerramentasJogo(self._ferramentas_gid)

    @Slot(int, str)
    def configurarSaves(self, gid, texto):
        self._alterar("Configurando saves…", lambda: self.servico.configurar_saves(
            gid, [p.strip() for p in texto.splitlines() if p.strip()]))

    @Slot(int)
    def snapshotSaves(self, gid):
        self._alterar("Guardando snapshot dos saves…", lambda: self.servico.backup_pos_sessao(gid),
                      lambda r: self.consultarFerramentasJogo(gid))

    @Slot(int, str)
    def restaurarSaves(self, gid, caminho):
        if self._em_jogo:
            self.aviso.emit("Encerre o jogo antes de restaurar seus saves.", True)
            return
        self._alterar("Guardando atuais e restaurando saves…", lambda: self.servico.restaurar_saves(gid, caminho),
                      lambda r: self.consultarFerramentasJogo(gid))

    @Slot(int)
    def medirDiscoJogo(self, gid):
        self.executar("Medindo pasta do jogo…", lambda: self.servico.disco_jogo(gid),
                      lambda r: self.aviso.emit(f'{r["bytes"] / 1024 ** 3:.2f} GB · {r["arquivos"]} arquivos'
                          + (" (parcial)" if r["parcial"] else ""), False))

    @Slot(QUrl, bool)
    def importarColecao(self, url, restaurar_saves=False):
        self._alterar("Importando pacote de coleção…", lambda: self.servico.importar_colecao(
            url.toLocalFile(), restaurar_saves))

    @Slot(QUrl)
    def importarJogos(self, url):
        self._alterar("Procurando jogos locais…", lambda: self.servico.importar_jogos(url.toLocalFile()))

    @Slot(QUrl)
    def importarRepack(self, url):
        self._alterar("Importando pacote de jogo…", lambda: self.servico.importar_repack_local(url.toLocalFile()))


    def _preview_pronta(self, r):
        r = dict(r or {})
        self._preview = {"itens": list(r.get("itens") or []),
                         "info": dict(r.get("info") or {}),
                         "raizes": list(r.get("raizes") or []),
                         "origem": str(r.get("origem") or ""),
                         "erro": str(r.get("erro") or "")}
        self.previewMudou.emit()
        if not r.get("ok"):
            self.aviso.emit(self._preview["erro"] or "Falha na varredura.", True)

    @Slot(QUrl)
    def preverPasta(self, url):
        pasta = url.toLocalFile()
        self.executar("Varrendo pasta…",
                      lambda: dict(self.servico.prever_pasta(pasta), origem="pasta"),
                      self._preview_pronta)

    @Slot(QUrl)
    def analisarArquivo(self, url):
        caminho = url.toLocalFile()

        def trabalho():
            ana = self.servico.analisar_arquivo(caminho)
            if not ana.get("ok"):
                return dict(ana, origem="arquivo")
            tipo = ana.get("tipo")
            if tipo == "pasta":
                return dict(self.servico.prever_pasta(caminho), origem="pasta")
            if tipo in ("rom", "jogo") and isinstance(ana.get("item"), dict):
                item = dict(ana["item"])
                return {"ok": True, "raizes": [], "itens": [item],
                        "info": {"vistos": 1, "truncado": False,
                                 "raizes": [], "origem": "arquivo"},
                        "erro": "", "origem": "arquivo",
                        "detalhe": ana.get("detalhe", ""),
                        "aviso": ana.get("aviso")}
            return {"ok": True, "raizes": [], "itens": [],
                    "info": {"vistos": 0, "truncado": False, "raizes": []},
                    "erro": "", "origem": "arquivo",
                    "detalhe": ana.get("detalhe", ""),
                    "aviso": ana.get("aviso"),
                    "tipo": tipo}
        self.executar("Analisando arquivo…", trabalho, self._preview_pronta)

    @Slot("QVariantList")
    def importarSelecionados(self, indices):
        try:
            idx = [int(i) for i in (indices or [])]
        except (TypeError, ValueError):
            self.aviso.emit("Seleção inválida.", True)
            return
        itens = self._preview.get("itens") or []
        sel = [itens[i] for i in idx if 0 <= i < len(itens)]
        if not sel:
            self.aviso.emit("Nada selecionado para importar.", False)
            return

        def apos(_r):
            self._preview = {"itens": [], "info": {}, "raizes": [], "origem": "", "erro": ""}
            self.previewMudou.emit()
        self._alterar("Importando selecionados…",
                      lambda: self.servico.importar_selecionados(sel), apos)

    @Slot()
    def limparPreview(self):
        self._preview = {"itens": [], "info": {}, "raizes": [], "origem": "", "erro": ""}
        self.previewMudou.emit()


    def _limpar_manutencao(self):
        self._manutencao = {"gid": 0, "titulo": "", "exe": {}, "rom": {}}
        self.manutencaoMudou.emit()

    @Slot(QUrl)
    def planejarSaneamento(self, url):
        def trabalho():
            return self.servico.sanear_plano(url.toLocalFile())
        self._saneamento = {"ok": False, "pasta": "", "exe": None,
                            "precisa_instalar": False, "quarentenaveis": 0,
                            "avisos": [], "erro": "analisando…"}
        self.manutencaoMudou.emit()
        self.executar("Analisando pasta…", trabalho, self._saneamento_pronto)

    def _saneamento_pronto(self, r):
        self._saneamento = dict(r or {})
        self.manutencaoMudou.emit()
        if not (r or {}).get("ok"):
            self.aviso.emit(self._saneamento.get("erro") or "Falha ao analisar a pasta.", True)

    @Slot(str)
    def aplicarSaneamento(self, pasta):
        self._alterar("Sanear, organizar e aplicar…",
                      lambda: self.servico.sanear_pasta(pasta))

    @Slot(int)
    def diagnosticarJogo(self, gid):
        def trabalho():
            return self.servico.diagnosticar_jogo(int(gid))
        self.executar("Diagnosticando exe/ROM…", trabalho, self._diagnostico_pronto)

    def _diagnostico_pronto(self, r):
        r = dict(r or {})
        self._manutencao = {"gid": r.get("gid", 0), "titulo": r.get("titulo", ""),
                            "exe": dict(r.get("exe") or {}),
                            "rom": dict(r.get("rom") or {})}
        self.manutencaoMudou.emit()

    @Slot(int, str, str)
    def religarJogo(self, gid, campo, caminho):
        self._alterar("Religando jogo…",
                      lambda: self.servico.religar_jogo(int(gid), campo, caminho),
                      lambda _r: self.diagnosticarJogo(int(gid)))

    @Slot(int)
    def jogarElevado(self, gid):
        if self.ocupado or self._em_jogo:
            self.aviso.emit("Aguarde a operação/sessão atual terminar.", False)
            return
        self._em_jogo = True
        self._jogo_gid = gid
        self.mudou.emit()
        self.executar("Pedindo elevação…", lambda: self.servico.iniciar_jogo_elevado(int(gid)),
                      self._jogo_elevado_pronto)

    def _jogo_elevado_pronto(self, r):
        self.aviso.emit((r or {}).get("aviso") or
                        "Iniciado com elevação. Registre a sessão ao terminar.", False)
        self.jogoIniciado.emit()
        self.mudou.emit()


    @Slot()
    def atualizarPacotes(self):
        self.executar("Lendo pacotes em Piratas…", self.servico.pacotes_piratas,
                      self._pacotes_prontos)

    def _pacotes_prontos(self, itens):
        self._pacotes_piratas = list(itens or [])
        self.mudou.emit()

    @Slot(result=bool)
    def tem7z(self):
        return core.ferramenta_7z() is not None

    @Slot(str)
    def prepararPacote(self, arquivo):
        self.executar("Extraindo pacote…", lambda: self.servico.preparar_pacote(arquivo),
                      self._pacote_preparado)

    def _pacote_preparado(self, r):
        avisar = r.get("estado") == "sem_exe"
        if r.get("estado") == "pronta":
            msg = "Pacote extraído e com executável pronto. Importe para a coleção."
        elif r.get("estado") == "instalar":
            msg = "Pacote extraído: só há instalador. Abra o instalador e depois importe."
        else:
            msg = "Pacote extraído, mas nenhum executável foi encontrado."
        self.aviso.emit(msg, avisar)
        self._recarregar_pacotes()

    @Slot(str)
    def abrirInstaladorPacote(self, exe):
        def pronto(_r):
            self.aviso.emit("Instalador aberto. Conclua a instalação e importe o jogo.", False)
        self.executar("Abrir instalador…", lambda: self.servico.abrir_instalador_pacote(exe), pronto)

    @Slot(str, str)
    def importarPacote(self, pasta, exe):
        def pronto(r):
            avisos = "; ".join(r.get("avisos") or [])
            self.aviso.emit(f"'{r.get('titulo', 'Jogo')}' entrou na coleção. {avisos}".strip(), False)
            self.atualizar()
            self._recarregar_pacotes()
        self.executar("Importando pacote…",
                      lambda: self.servico.importar_pacote(pasta, exe), pronto)

    def _recarregar_pacotes(self):
        self.executar("Atualizando pacotes…", self.servico.pacotes_piratas,
                      self._pacotes_prontos)

    @Slot(str, str, str)
    def aplicarPatchRom(self, rom, patch, destino):
        from bib_nucleo.patches_rom import aplicar_patch
        self._alterar("Aplicando patch em uma nova ROM…", lambda: aplicar_patch(rom, patch, destino))

    @Slot(str, str, bool)
    def copiarJogo(self, origem, destino, hardlinks=False):
        from bib_nucleo.organizacao_local import copiar_ou_ligar
        self._alterar("Organizando cópia do jogo…", lambda: copiar_ou_ligar(origem, destino, hardlinks))

    @Slot(str)
    def configurarWatch(self, pasta, automatico):
        from bib_nucleo.preferencias_pessoais import atualizar
        if self.ocupado or self._em_jogo:
            self.aviso.emit("Aguarde a operação/sessão para mudar a pasta vigiada.", False)
            return
        if pasta and not Path(pasta).is_dir():
            self.aviso.emit("Pasta vigiada não encontrada.", True)
            return
        self._preferencias = atualizar(watch=pasta, watch_auto=automatico)
        self._vigia = None
        self.preferenciasMudou.emit()

    def _consultar_watch(self):
        import os

        from bib_nucleo.pastas_vigiadas import VigiaPasta
        if self._fechado or self.ocupado or self._em_jogo:
            return
        pasta = os.environ.get("BIBLIOTECA_WATCH", "") or self._preferencias["watch"]
        if not pasta:
            return
        if self._vigia is None or str(self._vigia.pasta) != pasta:
            self._vigia = VigiaPasta(pasta)
        def trabalho():
            prontos = self._vigia.consultar()
            if self._preferencias["watch_auto"]:
                for item in prontos:
                    item["resultado"] = self.servico.importar_repack_local(item["path"])
            return prontos
        def pronto(itens):
            if itens:
                self._watch_prontos.extend(itens)
                self._watch_prontos = self._watch_prontos[-100:]
                self.ferramentasMudou.emit()
                self.aviso.emit(f"Pasta vigiada: {len(itens)} pacote(s) detectado(s). Veja em Ferramentas pessoais.", False)
                if self._preferencias["watch_auto"]:
                    self.atualizar()
        self.executar("Verificando pasta vigiada…", trabalho, pronto)

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

    @Slot(int, str)
    def salvarObservacoes(self, gid, texto):
        self._alterar("Salvando notas do jogo…", lambda: self.servico.salvar_observacoes(gid, texto))

    @Slot(QUrl)
    def exportarColecao(self, url):
        pasta = url.toLocalFile()
        if not pasta:
            return

        def pronto(_r):
            if not _r.get("ok"):
                raise ValueError(_r.get("erro", "Exportação não concluída."))
            self.aviso.emit("Coleção exportada para a pasta escolhida (pacote ZIP).", False)

        self.executar("Exportando coleção…",
                      lambda: self.servico.exportar_colecao_para(pasta), pronto,
                      lambda erro: self.aviso.emit(f"Exportação falhou: {erro}", True))

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

    @Slot()
    def sincronizarDesejosSteam(self):
        self._alterar("Lendo a wishlist da Steam…", self.servico.sincronizar_desejos_steam)

    @Slot(QUrl)
    def importarWishlist(self, url):
        self._alterar("Importando wishlist…", lambda: self.servico.importar_wishlist(url.toLocalFile()))

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
            def registrada(_r):
                self.atualizar()
                self._auto_backup_sessao(jogo_gid or gid)
            self.executar("Registrando sessão…", lambda: self.servico.registrar_sessao(gid, horas),
                          registrada)
            self.jogoTerminou.emit()
        else:
            self.aviso.emit("Sessão sem rastreio: registre as horas nas ferramentas clássicas.", False)
        self.mudou.emit()

    def _auto_backup_sessao(self, gid):
        """Backup da coleção ao encerrar sessão rastreada (opt-in, default ligado)."""
        if self._fechado or not gid:
            return
        # A configuração pode ter sido alterada pelo serviço/clássico depois
        # da carga da UI. Releia só neste checkpoint, não em cada binding QML.
        self._aparencia = self.servico.aparencia()
        if self.aparencia.get("auto_backup", True) is False:
            return

        def pronto(_r):
            if not self._fechado:
                if not _r.get("ok", True):
                    self.aviso.emit("Backup dos saves não foi concluído: " + _r.get("erro", "falha"), True)
                    return
                saves = _r.get("saves", {})
                self.aviso.emit("Backup pós-sessão criado. " +
                                (f'{saves.get("arquivos", 0)} arquivo(s) de saves guardados.'
                                 if saves.get("ok") and saves.get("arquivos") else
                                 saves.get("aviso") or saves.get("erro") or "Configure os saves deste jogo."), False)

        self.executar("Guardando backup pós-sessão…",
                      lambda: self.servico.backup_pos_sessao(gid), pronto)


__all__ = ["MixJogos"]
