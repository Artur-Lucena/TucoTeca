"""Torrents e repacks via ServicoBiblioteca: prontos, importar e local."""
from __future__ import annotations

from pathlib import Path

from bib_nucleo import scans
from bib_nucleo.rede import repacks, torrents


class MixTorrents:
    def importar_torrent(self, save_path):
        """Importa UM torrent concluído, com backup. Preserva a origem."""
        caminho = (save_path or "").strip()
        if not caminho:
            raise ValueError("Informe o caminho do download concluído.")
        alvo = Path(caminho)
        if not alvo.exists():
            raise ValueError("O arquivo/pasta não está mais no disco.")

        def trabalho(con):
            if not repacks.dentro_do_destino(alvo):
                org = repacks.organizar_no_destino(alvo)
                if not org.get("ok"):
                    raise ValueError(org.get("erro", "Não foi possível organizar o download."))
                alvo_local = Path(org["path"])
            else:
                alvo_local = alvo
            if alvo_local.is_file():
                from bib_nucleo.rede.repacks import ARQUIVO_EXTS
                if alvo_local.suffix.lower() not in ARQUIVO_EXTS:
                    raise ValueError("Formato não suportado para importar.")
                res = repacks.importar_repack(con, str(alvo_local))
                if res.get("precisa_instalar"):
                    return {"ok": True, "titulo": res.get("titulo"),
                            "avisos": ["instalador baixado: rode o setup e importe a pasta."]}
                return res
            _roots, itens, _info = scans.preview_pasta([str(alvo_local)])
            if not itens:
                raise ValueError("Nada importável nesta pasta.")
            return scans.importar_lista(con, itens)
        return self.alterar(trabalho)

    def listar_torrents(self):
        return torrents.listar_torrents()

    def torrent_controlar(self, ident, acao):
        from bib_nucleo import qbit
        acao = str(acao or "").strip()
        ident = str(ident or "").strip()
        r = qbit.qbit_controlar(ident, acao)
        if not r.get("ok"):
            raise ValueError(r.get("erro", "Não foi possível controlar o torrent."))
        return {"ok": True}

__all__ = ["MixTorrents"]
