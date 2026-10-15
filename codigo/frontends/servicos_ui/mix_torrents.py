"""Torrents e repacks via ServicoBiblioteca: prontos, importar e local."""
from __future__ import annotations

from pathlib import Path

import bib_core as core


class MixTorrents:
    def baixar_torrent_hub(self, url):
        from bib_nucleo.rede import exigir_rede
        exigir_rede("Adicionar torrent")
        r = core.qbit_adicionar(url)
        if not r.get("ok"):
            raise ValueError(r.get("erro", "Não foi possível adicionar o torrent."))
        return r

    def torrents_prontos(self):
        """Torrents 100% com caminho conhecido. Só leitura.

        Download incompleto não entra na lista: nada de importar pela metade.
        Devolve {"itens": [...], "erros": [...]} com o estado de cada alvo.
        """
        from bib_nucleo.rede.repacks import ARQUIVO_EXTS
        leitura = core.listar_torrents()
        erro = leitura.get("erro") if isinstance(leitura, dict) else None
        torrents = leitura.get("torrents") if isinstance(leitura, dict) else []
        prontos: list[dict] = []
        for t in torrents or []:
            if not isinstance(t, dict) or not (t.get("completo") and t.get("save_path")):
                continue
            alvo = Path(str(t["save_path"]))
            if alvo.is_file():
                if alvo.suffix.lower() in ARQUIVO_EXTS:
                    estado = "arquivo"
                else:
                    estado = "nao-suportado"
            elif alvo.is_dir():
                estado = "pasta"
            else:
                estado = "sumiu"
            prontos.append({"hash": t.get("hash", ""), "nome": t.get("nome") or alvo.name,
                            "save_path": str(alvo), "estado": estado,
                            "progresso": t.get("progresso", 1.0)})
        return {"itens": prontos, "erros": [erro] if erro else list(leitura.get("erros") or [])}

    def importar_torrent(self, save_path):
        """Importa UM torrent concluído, com backup. Preserva a origem."""
        caminho = (save_path or "").strip()
        if not caminho:
            raise ValueError("Informe o caminho do download concluído.")
        alvo = Path(caminho)
        if not alvo.exists():
            raise ValueError("O arquivo/pasta não está mais no disco.")

        def trabalho(con):
            if not core.dentro_do_destino(alvo):
                org = core.organizar_no_destino(alvo)
                if not org.get("ok"):
                    raise ValueError(org.get("erro", "Não foi possível organizar o download."))
                alvo_local = Path(org["path"])
            else:
                alvo_local = alvo
            if alvo_local.is_file():
                from bib_nucleo.rede.repacks import ARQUIVO_EXTS
                if alvo_local.suffix.lower() not in ARQUIVO_EXTS:
                    raise ValueError("Formato não suportado para importar.")
                res = core.importar_repack(con, str(alvo_local))
                if res.get("precisa_instalar"):
                    return {"ok": True, "titulo": res.get("titulo"),
                            "avisos": ["instalador baixado: rode o setup e importe a pasta."]}
                return res
            _roots, itens, _info = core.preview_pasta([str(alvo_local)])
            if not itens:
                raise ValueError("Nada importável nesta pasta.")
            return core.importar_lista(con, itens)
        return self.alterar(trabalho)

    def importar_repack_local(self, caminho):
        return self.alterar(lambda con: core.importar_repack(con, caminho))


__all__ = ["MixTorrents"]
