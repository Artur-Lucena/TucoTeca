"""O app em si via ServicoBiblioteca: histórico de notificações e verificar atualização."""
from __future__ import annotations

from bib_nucleo import notificacoes


class MixApp:
    def avisos_listar(self):
        return notificacoes.listar()

    def avisos_registrar(self, avisos):
        return notificacoes.registrar(avisos)

    def avisos_dispensar(self, ident):
        return notificacoes.dispensar(ident)

    def avisos_limpar(self):
        return notificacoes.limpar()

    def verificar_atualizacao(self):
        from bib_nucleo.rede import versao_nova
        return versao_nova.verificar()

    def baixar_atualizacao(self, instalador, progresso=None, cancelado=None):
        from bib_nucleo.rede import versao_nova
        return versao_nova.baixar_instalador(instalador, progresso, cancelado)


__all__ = ["MixApp"]
