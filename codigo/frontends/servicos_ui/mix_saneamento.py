"""Saneamento e organizacao via ServicoBiblioteca (reversivel, com plano)."""
from __future__ import annotations

from pathlib import Path

from bib_nucleo import pacotes
from bib_nucleo.rede import repacks


class MixSaneamento:
    def sanear_plano(self, caminho):
        """Plano de saneamento. Só leitura: nada é movido ou apagado.

        Devolve o que a organização faria (pasta resolvida, executável, sobras
        que iriam para .hub-lixo) para a interface mostrar antes de aplicar.
        """
        from bib_nucleo.rede.repacks import achar_exe
        pasta = (caminho or "").strip()
        if not pasta:
            return {"ok": False, "pasta": "", "exe": None, "precisa_instalar": False,
                    "quarentenaveis": 0, "avisos": ["escolha uma pasta."], "erro": ""}
        base = Path(pasta)
        if not base.is_dir():
            return {"ok": False, "pasta": str(base), "exe": None,
                    "precisa_instalar": False, "quarentenaveis": 0,
                    "avisos": [], "erro": "pasta não encontrada."}
        from bib_nucleo.rede.repacks import _pasta_conteudo
        base = _pasta_conteudo(base)
        ach = achar_exe(base)
        if not ach.get("ok"):
            if ach.get("precisa_instalar"):
                return {"ok": True, "pasta": str(base), "exe": None,
                        "precisa_instalar": True, "quarentenaveis": 0,
                        "avisos": ["só há instalador: a pasta fica como está."],
                        "erro": ""}
            return {"ok": False, "pasta": str(base), "exe": None,
                    "precisa_instalar": False, "quarentenaveis": 0, "avisos": [],
                    "erro": ach.get("erro", "sem executável.")}
        sobras = 0
        try:
            sobras = len(sorted(base.glob("setup*.exe")))
        except OSError:
            sobras = 0
        return {"ok": True, "pasta": str(base), "exe": ach.get("exe"),
                "precisa_instalar": False, "quarentenaveis": sobras,
                "avisos": ([f"{sobras} instalador(es) iriam para .hub-lixo (reversível)."]
                           if sobras else []),
                "erro": ""}

    def sanear_pasta(self, caminho):
        """Aplica o saneamento. Reversível (.hub-lixo); depende de sanear_plano."""
        from bib_nucleo.rede.repacks import sanear_pasta as _sanear
        pasta = (caminho or "").strip()
        if not pasta:
            raise ValueError("Escolha uma pasta para sanear.")
        r = _sanear(pasta)
        if not r.get("ok"):
            raise ValueError(r.get("erro", "Não foi possível sanear a pasta."))
        return r

    def organizar_download(self, caminho):
        pacotes.fazer_backup(self.db_path)
        r = repacks.organizar_no_destino(caminho)
        if not r.get("ok"):
            raise ValueError(r.get("erro", "Não foi possível organizar."))
        return r

    def fora_do_destino(self, caminho):
        try:
            return bool(caminho) and not repacks.dentro_do_destino(caminho)
        except (OSError, ValueError):
            return False


__all__ = ["MixSaneamento"]
