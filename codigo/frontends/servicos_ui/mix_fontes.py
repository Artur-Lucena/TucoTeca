"""Fontes de download (formato do Hydra) via ServicoBiblioteca: cadastro, busca e baixar dentro do app."""
from __future__ import annotations

from bib_nucleo.rede import fontes_download


class MixFontes:
    def fontes_listar(self):
        return fontes_download.listar()

    def fontes_adicionar(self, url):
        return fontes_download.adicionar(url)

    def fontes_atualizar(self, ident=""):
        return fontes_download.atualizar(ident)

    def fontes_remover(self, ident):
        return fontes_download.remover(ident)

    def fontes_buscar(self, titulo):
        return fontes_download.buscar(titulo)

    def baixar_da_fonte(self, uri, titulo, progresso=None, cancelado=None):
        """magnet → qBittorrent integrado (pasta de jogos); https → o app baixa para a pasta de jogos."""
        from bib_nucleo.rede.repacks import pasta_jogos
        uri = str(uri or "").strip()
        if uri.startswith("magnet:?"):
            from bib_nucleo import qbit
            if qbit.qbit_api_url():
                try:
                    qbit.qbit_request("torrents/add", {"urls": uri, "category": "tucoteca",
                                                      "savepath": str(pasta_jogos().resolve())}, timeout=10)
                    return {"ok": True, "modo": "torrent", "aviso": f"{titulo} foi para o qBittorrent (Downloads)."}
                except Exception:
                    pass  # API fora do ar: abre/encaminha pelo executável
            r = qbit.qbit_iniciar(uri)
            if not r.get("ok"):
                raise ValueError(r.get("erro") or "Não consegui entregar o torrent ao qBittorrent.")
            return {"ok": True, "modo": "torrent", "aviso": f"{titulo} foi para o qBittorrent (Downloads)."}
        r = fontes_download.baixar_direto(uri, titulo, pasta_jogos(), progresso, cancelado)
        return {**r, "modo": "direto", "aviso": f"{titulo} baixado em Meus Jogos Locais. Importe em Downloads."}


__all__ = ["MixFontes"]
