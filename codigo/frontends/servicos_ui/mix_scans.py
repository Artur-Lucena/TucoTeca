"""Scans e pacotes via ServicoBiblioteca: preview, importacao e pacotes."""
from __future__ import annotations

from bib_nucleo import pacotes, scans
from bib_nucleo.rede import repacks


class MixScans:
    def importar_jogos(self, pasta):
        roots, itens, info = scans.preview_scan([pasta])
        return self.alterar(lambda con: scans.importar_lista(con, itens))

    def prever_pasta(self, pasta):
        """Preview só-leitura de pasta (PC + ROMs). Sem backup, sem escrita."""
        pasta = (pasta or "").strip()
        if not pasta:
            return {"ok": False, "raizes": [], "itens": [], "info": {},
                    "erro": "Escolha uma pasta para varrer."}
        try:
            raizes, itens, info = scans.preview_pasta([pasta])
        except Exception as e:
            return {"ok": False, "raizes": [], "itens": [], "info": {},
                    "erro": f"falha na varredura: {e}"}
        return {"ok": True, "raizes": list(raizes or []),
                "itens": [dict(it) for it in (itens or [])],
                "info": dict(info or {}), "erro": ""}

    def analisar_arquivo(self, caminho):
        """Classifica um caminho sem importar. Só leitura."""
        caminho = (caminho or "").strip()
        if not caminho:
            return {"ok": False, "tipo": "desconhecido", "item": None,
                    "provedor": None, "detalhe": "caminho vazio.", "aviso": None}
        try:
            ana = scans.analisar_arquivo(caminho)
        except Exception as e:
            return {"ok": False, "tipo": "desconhecido", "item": None,
                    "provedor": None, "detalhe": f"falha na análise: {e}",
                    "aviso": None}
        return {"ok": True, "tipo": ana.get("tipo"), "item": ana.get("item"),
                "provedor": ana.get("provedor"), "detalhe": ana.get("detalhe", ""),
                "aviso": ana.get("aviso")}

    def importar_selecionados(self, itens):
        """Importa a seleção do preview, com backup. Nada antes da seleção."""
        sel = [dict(it) for it in (itens or [])
               if isinstance(it, dict) and (it.get("titulo") or it.get("executable_path"))]
        if not sel:
            raise ValueError("Nada selecionado para importar.")
        return self.alterar(lambda con: scans.importar_lista(con, sel))

    def importar_colecao(self, caminho, restaurar_saves=False):
        with self._escrita:
            return pacotes.importar_pacote(caminho, self.db_path, restaurar_saves)

    def preparar_pacote(self, arquivo):
        pacotes.fazer_backup(self.db_path)
        r = repacks.preparar_pacote(arquivo)
        if not r.get("ok"):
            raise ValueError(r.get("erro", "Não foi possível preparar o pacote."))
        return r

    def abrir_instalador_pacote(self, exe):
        r = repacks.abrir_instalador(exe)
        if not r.get("ok"):
            raise ValueError(r.get("erro", "Não foi possível abrir o instalador."))
        return r

    def importar_pacote(self, pasta, exe=""):
        def importar(con):
            r = repacks.importar_pasta(con, pasta, exe)
            if not r.get("ok"):
                raise ValueError(r.get("erro", "Não foi possível importar o pacote."))
            return r
        return self.alterar(importar)


__all__ = ["MixScans"]
