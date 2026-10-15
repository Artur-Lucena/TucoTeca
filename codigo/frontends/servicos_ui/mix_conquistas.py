"""Conquistas, provedores e aparencia via ServicoBiblioteca."""
from __future__ import annotations

from bib_nucleo import conquistas, online


class MixConquistas:
    def sincronizar_conquistas(self, gid, appid="", save=""):
        return conquistas.sincronizar_catalogo(self.jogo(gid), appid, save)

    def avaliar_conquistas(self, gid):
        return conquistas.avaliar_save(self.jogo(gid))

    def regras_conquistas(self, gid, texto):
        return conquistas.salvar_regras(self.jogo(gid), texto)

    def configurar_provedores(self, steam, steamgrid, spotify_id, spotify_secret=""):
        return online.configurar_provedores({"steam_key": steam, "steamgriddb_key": steamgrid,
                                            "spotify_client_id": spotify_id,
                                            "spotify_client_secret": spotify_secret})

    def aparencia(self):
        from bib_nucleo import aparencia_usuario
        return aparencia_usuario.ler_aparencia()

    def definir_aparencia(self, tema="", densidade="", auto_backup=None, modo_simples=None):
        from bib_nucleo import aparencia_usuario
        return aparencia_usuario.salvar_aparencia(tema, densidade, auto_backup, modo_simples)


__all__ = ["MixConquistas"]
