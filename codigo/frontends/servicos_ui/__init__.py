#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contratos da interface desktop, independentes de Qt e de widgets.

Pacote por contrato (F3 do O2): `integracoes`, `sistema` e mixins por
dominio (`mix_*`). Compat total: `from servicos_ui import ServicoBiblioteca`
(único patch em testes é `ServicoBiblioteca.jogo`, que continua valendo —
classe definida uma vez aqui) e todos os nomes de módulo continuam iguais.
"""
from __future__ import annotations

from .integracoes import (
    _CORES,
    CHAVES_PADRAO,
    INTEGRACAO_TIPOS,
    Integracao,
    RegistroIntegracoes,
    _arquivo_personalizadas,
    _validar_personalizada,
    carregar_personalizadas,
    integracoes_padrao,
    remover_personalizada,
    salvar_personalizada,
)
from .integracoes import (
    url_integracao as _url_integracao,
)
from .mix_conquistas import MixConquistas
from .mix_desejos import MixDesejos
from .mix_emulacao import MixEmulacao
from .mix_meta import MixMeta
from .mix_midia import MixMidia
from .mix_nucleo import MixNucleo
from .mix_saneamento import MixSaneamento
from .mix_scans import MixScans
from .mix_sessoes import MixSessoes
from .mix_torrents import MixTorrents
from .modulos import Modulo, modulos_padrao
from .sistema import _sem_acento, busca_global, capa_url, resumo_sistema, saude_colecao


class ServicoBiblioteca(MixNucleo, MixScans, MixSaneamento, MixSessoes,
                        MixMidia, MixTorrents, MixEmulacao, MixDesejos,
                        MixConquistas, MixMeta):
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


__all__ = ["ServicoBiblioteca", "Integracao", "RegistroIntegracoes",
           "INTEGRACAO_TIPOS", "CHAVES_PADRAO", "_CORES",
           "Modulo", "modulos_padrao",
           "_arquivo_personalizadas", "carregar_personalizadas",
           "_validar_personalizada", "salvar_personalizada",
           "remover_personalizada", "integracoes_padrao", "url_integracao",
           "capa_url", "resumo_sistema", "saude_colecao", "_sem_acento",
           "busca_global"]

# Reexport com o nome historico p/ `from servicos_ui import url_integracao`.
url_integracao = _url_integracao
