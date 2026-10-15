#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ponte Qt: midias, videos, letras, fontes de desejo e YouTube."""
from __future__ import annotations

from PySide6.QtCore import (
    QUrl,
    Slot,
)


class MixMidia:


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

    @Slot(QUrl, result=str)
    def caminhoLocal(self, url):
        return url.toLocalFile()

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

    @Slot(str)
    def baixarMp3Url(self, url):
        def trabalho():
            try:
                return self.servico.baixar_mp3(url, lambda vid, pct: self._progressoVideo.emit(
                    {"rotulo": vid + " · MP3", "pct": pct}))
            finally:
                self._progressoVideo.emit({"rotulo": "", "pct": 0})
        self._alterar("Baixando MP3 para a coleção…", trabalho)

    @Slot(int)
    def prepararVideoInterno(self, ident):
        self.executar("Abrindo vídeo interno…", lambda: self.servico.video_local(ident), self.videoLocalPronto.emit)

    @Slot(str, int)
    def guardarVideoPosicao(self, sha, posicao):
        self.executar("Guardando posição do vídeo…", lambda: self.servico.salvar_posicao_video(sha, posicao))

    @Slot(bool)
    def definirSponsorBlock(self, ativa):
        from bib_nucleo.preferencias_pessoais import atualizar
        self._preferencias = atualizar(sponsorblock=ativa)
        self._sponsor = {"video": "", "segmentos": []}
        self.sponsorMudou.emit()
        self.preferenciasMudou.emit()


    @Slot(str)
    def consultarSponsor(self, url):
        from bib_nucleo.rede.sponsorblock import buscar_segmentos
        from bib_nucleo.rede.videos_youtube import identificar_youtube
        vid = identificar_youtube(url)
        if not vid or not self._preferencias["sponsorblock"] or vid == self._sponsor["video"]:
            return
        self._sponsor = {"video": vid, "segmentos": []}
        def pronto(r):
            if self._sponsor["video"] == vid and self._preferencias["sponsorblock"]:
                self._sponsor = {"video": vid, "segmentos": r}
                self.sponsorMudou.emit()
        self.executar("Consultando patrocínios…", lambda: buscar_segmentos(vid), pronto,
                      lambda erro: self.aviso.emit("SponsorBlock indisponível; vídeo não será interrompido. " + erro, False))

    @Slot()
    def atualizarAudio(self):
        self._alterar("Atualizando ferramentas com SHA-256 fixado…", self.servico.atualizar_audio)


    @Slot(str, result=str)
    def youtubeBuscar(self, termo):
        """Valida e devolve a URL de resultados do YouTube (o QML navega)."""
        import urllib.parse
        termo = (termo or "").strip()
        if len(termo) < 2:
            self.aviso.emit("Digite ao menos 2 caracteres para buscar.", False)
            return ""
        return "https://www.youtube.com/results?search_query=" + urllib.parse.quote(termo)

    @Slot(str, str, result=str)
    def youtubeIr(self, url, termo=""):
        """Normaliza/valida destino antes de navegar (só https/hosts YouTube)."""
        import urllib.parse
        texto = (url or "").strip()
        if not texto and termo:
            return self.youtubeBuscar(termo)
        try:
            alvo = urllib.parse.urlsplit(texto if "://" in texto else "https://" + texto)
            valido = (alvo.scheme == "https" and (alvo.hostname or "").lower() in (
                "www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be")
                and not alvo.username and not alvo.password and alvo.port in (None, 443))
        except ValueError:
            valido = False
        if not valido:
            self.aviso.emit("Só é possível navegar em endereços do YouTube.", False)
            return ""
        return alvo.geturl()

    @Slot(str)
    def youtubeBaixarUrl(self, url):
        """Baixa o vídeo da URL informada (valida no Python, nunca confia no JS)."""
        from bib_nucleo.rede.videos_youtube import identificar_youtube
        vid = identificar_youtube(url or "")
        if not vid:
            self.aviso.emit("Link do YouTube inválido.", False)
            return
        self.baixarVideo(vid)


    @Slot(str, str, str, int)
    def buscarLetras(self, artista, titulo, album, duracao_s):
        self._letras_geracao += 1
        geracao = self._letras_geracao
        self._letras_faixa = (artista, titulo)
        self._letras = {"ok": False, "sincronizadas": False, "linhas": [], "texto": "",
                        "erro": "Buscando letra…"}
        self.letrasMudou.emit()

        def pronto(r):
            if geracao != self._letras_geracao:
                return
            self._letras = r
            self.letrasMudou.emit()

        def falha(erro):
            if geracao != self._letras_geracao:
                return
            self._letras = {"ok": False, "sincronizadas": False, "linhas": [], "texto": "",
                            "erro": erro}
            self.letrasMudou.emit()
        self.executar("Buscando letra…",
                      lambda: self.servico.buscar_letras(artista, titulo, album, duracao_s),
                      pronto, falha)

    @Slot(str)
    def buscarFontesDesejo(self, titulo):
        self._fontes_geracao += 1
        geracao = self._fontes_geracao
        self._fontes_desejo = {"steamrip": [], "fitgirl": [], "erros": ["Buscando nas fontes…"]}
        self.fontesMudou.emit()

        def pronto(r):
            if geracao != self._fontes_geracao:
                return
            self._fontes_desejo = r
            self.fontesMudou.emit()

        def falha(erro):
            if geracao != self._fontes_geracao:
                return
            self._fontes_desejo = {"steamrip": [], "fitgirl": [], "erros": [erro]}
            self.fontesMudou.emit()
        self.executar("Buscando fontes…",
                      lambda: self.servico.buscar_fontes_desejo(titulo), pronto, falha)

    @Slot(str, int)
    def baixarDesejoSteamRip(self, url, did):
        if self.ocupado:
            return
        def pronto(r):
            if r.get("ok"):
                self.aviso.emit("Baixado e importado. Desejo marcado como obtido.", False)
                self.atualizar()
            else:
                self.aviso.emit(r.get("erro") or "Não foi possível importar.", True)
        self.executar("Baixando e importando…",
                      lambda: self.servico.baixar_fonte_steamrip(url, did), pronto)

    @Slot(int)
    def buscarCapaLibretro(self, gid):
        def pronto(_r):
            self.aviso.emit("Capa offline salva.", False)
            self.atualizar()
        self.executar("Buscando capa offline…",
                      lambda: self.servico.buscar_capa_libretro(gid), pronto)


__all__ = ["MixMidia"]
