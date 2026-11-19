"""Coleções, catálogo da loja Steam e importação de lojas instaladas via ServicoBiblioteca."""
from __future__ import annotations

from contextlib import closing

from bib_nucleo import banco, scans
from bib_nucleo.banco import colecoes as banco_colecoes


class MixColecoes:
    # -- coleções -------------------------------------------------------------
    def _com_banco(self, operacao, escrever=False):
        if escrever:
            with self._escrita, closing(banco.get_db(self.db_path)) as con:
                return operacao(con)
        with closing(banco.get_db(self.db_path)) as con:
            return operacao(con)

    def colecoes(self):
        return self._com_banco(banco_colecoes.listar_colecoes)

    def criar_colecao(self, nome):
        return self._com_banco(lambda con: banco_colecoes.criar_colecao(con, nome), escrever=True)

    def renomear_colecao(self, cid, nome):
        self._com_banco(lambda con: banco_colecoes.renomear_colecao(con, cid, nome), escrever=True)
        return self.colecoes()

    def apagar_colecao(self, cid):
        self._com_banco(lambda con: banco_colecoes.apagar_colecao(con, cid), escrever=True)
        return self.colecoes()

    def colecoes_do_jogo(self, gid):
        uuid = self.jogo(gid).get("uuid") or ""
        return self._com_banco(lambda con: banco_colecoes.colecoes_do_jogo(con, uuid))

    def definir_colecao_jogo(self, cid, gid, dentro):
        uuid = self.jogo(gid).get("uuid") or ""
        self._com_banco(lambda con: banco_colecoes.definir_membro(con, cid, uuid, dentro), escrever=True)
        return self.colecoes_do_jogo(gid)

    # -- loja Steam (rede; ação do usuário) -------------------------------------
    def _donos(self):
        """appid → id do jogo na biblioteca (pela loja de origem ou pelo App ID dos metadados)."""
        with closing(banco.get_db(self.db_path)) as con:
            donos = {str(r[0]): int(r[1]) for r in con.execute(
                "SELECT object_id, id FROM jogos WHERE shop='steam' AND object_id <> ''")}
            try:
                donos.update({str(r[0]): int(r[1]) for r in con.execute(
                    "SELECT m.steam_appid, j.id FROM jogos_meta m JOIN jogos j ON j.uuid = m.uuid "
                    "WHERE m.steam_appid <> ''") if str(r[0]) not in donos})
            except Exception:
                pass  # banco sem metadados ainda
            desejos = {str(d.get("appid")) for d in banco.listar_desejos(con)}
        return donos, desejos

    def _marcar(self, cartoes):
        donos, desejos = self._donos()
        for c in cartoes:
            c["na_biblioteca"] = donos.get(c["appid"])
            c["nos_desejos"] = c["appid"] in desejos
        return cartoes

    def loja_destaques(self):
        from bib_nucleo.rede import exigir_rede, loja_steam
        exigir_rede("Ver o catálogo da Steam")
        secoes = loja_steam.destaques()
        for s in secoes:
            self._marcar(s["itens"])
        return secoes

    def loja_generos(self):
        from bib_nucleo.rede import loja_steam
        return [{"chave": c, "nome": n} for c, n, _ in loja_steam.GENEROS]

    def loja_genero(self, chave, pagina=0):
        from bib_nucleo.rede import exigir_rede, loja_steam
        exigir_rede("Ver jogos por gênero na Steam")
        r = loja_steam.por_genero(chave, pagina)
        self._marcar(r["itens"])
        return r

    def loja_buscar(self, termo):
        from bib_nucleo.rede import exigir_rede, loja_steam
        exigir_rede("Buscar na Steam")
        return self._marcar(loja_steam.buscar(termo))

    def loja_pagina(self, appid):
        from bib_nucleo.rede import exigir_rede, loja_steam
        exigir_rede("Abrir a página da loja")
        return self._marcar([loja_steam.pagina(appid)])[0]

    def loja_desejar(self, appid, titulo):
        r = self.alterar(lambda con: banco.adicionar_desejo(con, appid, titulo))
        return {"ok": True, "resultado": r}

    # -- lojas instaladas no PC (só leitura do disco) ---------------------------
    def prever_lojas(self):
        """Jogos instalados em Steam/Epic/GOG/Hydra/Riot/Windows que ainda não estão na biblioteca."""
        from bib_nucleo.banco.jogos import chave_dedup
        itens, info = scans.ler_do_disco()
        with closing(banco.get_db(self.db_path)) as con:
            vistos = {chave_dedup(r[0], r[1], r[2])[1:] for r in con.execute(
                "SELECT titulo, executable_path, launch_options FROM jogos")}
        novos = [dict(i) for i in itens
                 if chave_dedup(i.get("titulo") or "", i.get("executable_path") or "",
                                i.get("launch_options") or "")[1:] not in vistos]
        fontes = [f for f in info.get("fontes") or [] if isinstance(f, dict)]
        resumo = ", ".join(f"{f['fonte']}: {f['n']}" for f in fontes if f.get("ok") and f.get("n"))
        return {"itens": novos, "fontes": fontes, "ja_na_biblioteca": len(itens) - len(novos),
                "aviso": (f"{len(novos)} jogo(s) novo(s) nas lojas instaladas ({resumo})." if novos
                          else "Nenhum jogo novo nas lojas instaladas.")}


__all__ = ["MixColecoes"]
