"""Desejos e fontes de download via ServicoBiblioteca."""
from __future__ import annotations

from contextlib import closing

from bib_nucleo import banco, config


class MixDesejos:
    def sincronizar_desejos_steam(self):
        from bib_nucleo.rede import fontes
        conta = fontes.steam_principal()
        if not conta.get("steamid"):
            raise ValueError("Conta Steam não encontrada neste PC. Defina BIBLIOTECA_STEAM_ID ou importe o JSON da wishlist.")
        return self._aplicar_wishlist(fontes.ler_wishlist(conta["steamid"]), "Steam")

    def importar_wishlist(self, caminho):
        from bib_nucleo.rede import fontes
        return self._aplicar_wishlist(fontes.ler_wishlist_arquivo(caminho), "arquivo")

    def _aplicar_wishlist(self, leitura, origem):
        if not leitura.get("itens"):
            raise ValueError((leitura.get("erros") or ["Nenhum jogo encontrado na wishlist."])[0])
        r = self.alterar(lambda con: banco.sincronizar_desejos(con, leitura["itens"]))
        aviso = f"Wishlist ({origem}): {r['novos']} novos, {r['atualizados']} atualizados, {r['removidos']} removidos."
        return {"ok": True, "erros": [], "avisos": [aviso, *leitura.get("erros", [])]}

    def adicionar_desejo(self, appid, titulo):
        return self.alterar(lambda con: banco.adicionar_desejo(con, appid, titulo))

    def precos_desejos(self, regiao=""):
        """Preço dos desejos ainda não obtidos (cache local; consulta sob demanda)."""
        from bib_nucleo.rede import metadados
        regiao = (regiao or config.cfg.preco_regiao or "br")
        with closing(banco.get_db(self.db_path)) as con:
            appids = [r["appid"] for r in con.execute(
                "SELECT appid FROM desejos WHERE obtido_em IS NULL").fetchall()]
        return metadados.precos_steam(appids, regiao)

    def buscar_fontes_desejo(self, titulo):
        """Procura o título nas fontes de download (SteamRip e FitGirl)."""
        from bib_nucleo.rede import exigir_rede, fontes
        exigir_rede("Buscar fontes de download")
        saida = {"steamrip": [], "fitgirl": [], "erros": []}
        for chave, buscar in (("steamrip", fontes.buscar_steamrip),
                              ("fitgirl", fontes.buscar_fitgirl)):
            try:
                r = buscar(titulo)
            except Exception as e:
                saida["erros"].append(f"{chave}: {e}")
                continue
            saida[chave] = [{"titulo": i.get("titulo", ""), "url": i.get("url", "")}
                            for i in (r.get("itens") or [])]
            saida["erros"].extend(str(e) for e in (r.get("erros") or []))
        return saida


__all__ = ["MixDesejos"]
