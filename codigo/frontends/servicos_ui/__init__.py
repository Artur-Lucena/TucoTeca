#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Casos de uso do desktop: `ServicoBiblioteca` composto de mixins por domínio.

Consumidores usam `from servicos_ui import ServicoBiblioteca`; o resto
(`integracoes`, `sistema`, `modulos`, `mix_*`) é importado do módulo dono.
"""
from __future__ import annotations

from .integracoes import (
    _arquivo_personalizadas,
    integracoes_padrao,
    remover_personalizada,
    salvar_personalizada,
)
from .integracoes import (
    url_integracao as _url_integracao,
)
from .mix_colecoes import MixColecoes
from .mix_conquistas import MixConquistas
from .mix_desejos import MixDesejos
from .mix_emulacao import MixEmulacao
from .mix_filmes import MixFilmes
from .mix_fontes import MixFontes
from .mix_meta import MixMeta
from .mix_midia import MixMidia
from .mix_nucleo import MixNucleo
from .mix_saneamento import MixSaneamento
from .mix_scans import MixScans
from .mix_sessoes import MixSessoes
from .mix_torrents import MixTorrents


class ServicoBiblioteca(MixNucleo, MixScans, MixSaneamento, MixSessoes,
                        MixMidia, MixTorrents, MixEmulacao, MixDesejos,
                        MixConquistas, MixMeta, MixColecoes, MixFilmes, MixFontes):
    """Fachada da biblioteca: contratos por dominio via mixins."""

    def adicionar_integracao(self, dados):
        """Registra integracao personalizada e recarrega o registro."""
        item = salvar_personalizada(dados)
        self.integracoes = integracoes_padrao()
        return item

    def remover_integracao(self, chave):
        """Remove integracao personalizada e recarrega o registro."""
        remover_personalizada(chave)
        self.integracoes = integracoes_padrao()
        return {"ok": True}

    def url_integracao(self, chave, termo=""):
        """URL da integracao com o termo aplicado."""
        return _url_integracao(self.integracoes, chave, termo)


__all__ = ["ServicoBiblioteca", "_arquivo_personalizadas"]
