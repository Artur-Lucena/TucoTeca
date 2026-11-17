"""Página do jogo e metadados dos provedores via ServicoBiblioteca."""
from __future__ import annotations

from contextlib import closing
from pathlib import Path

import bib_core as core
from bib_nucleo.banco import meta as banco_meta

from .sistema import capa_url

TIPOS_ARTE = ("hero", "logo", "icone")


def _uri(caminho) -> str:
    try:
        alvo = Path(str(caminho or ""))
        return alvo.resolve().as_uri() if str(caminho or "") and alvo.is_file() else ""
    except (OSError, ValueError):
        return ""


def _publico(meta: dict) -> dict:
    """Meta para o renderer: caminhos locais de arte viram file:// (via tucoteca-img)."""
    saida = {k: v for k, v in meta.items() if k not in ("hero", "logo", "icone", "screenshots")}
    for tipo in TIPOS_ARTE:
        saida[f"{tipo}_url"] = _uri(meta.get(tipo))
    saida["screenshots_urls"] = [u for u in (_uri(c) for c in meta.get("screenshots") or []) if u]
    return saida


class MixMeta:
    def _meta_de(self, uuid):
        with closing(core.get_db(self.db_path)) as con:
            return banco_meta.ler_meta(con, uuid)

    def _gravar_meta(self, uuid, novos, **opcoes):
        with self._escrita, closing(core.get_db(self.db_path)) as con:
            return banco_meta.gravar_meta(con, uuid, novos, **opcoes)

    def pagina_jogo(self, gid):
        """Tudo da página do jogo sem rede: jogo (no perfil ativo), metadados e provedores."""
        from bib_nucleo.preferencias_pessoais import aplicar_perfil
        from bib_nucleo.rede import provedores
        jogo = aplicar_perfil([self.jogo(gid)])[0]
        jogo.update(capa_url=capa_url(jogo.get("capa")), plataforma=core.plataforma_jogo(jogo))
        meta = self._meta_de(jogo.get("uuid") or "")
        return {"jogo": jogo, "meta": _publico(meta), "provedores": provedores.estado(),
                "enriquecido": bool(meta.get("fontes"))}

    def enriquecer_jogo(self, gid, chaves=None, progresso=None, cancelado=None):
        """Busca descrição/arte/conquistas nos provedores e guarda (rede; rodar como trabalho)."""
        from bib_nucleo.rede import provedores
        cancelado = cancelado or (lambda: False)
        jogo = self.jogo(gid)
        uuid = jogo.get("uuid") or ""
        meta = self._meta_de(uuid)
        campos, artes, erros = provedores.enriquecer(jogo, meta, chaves, cancelado)
        if progresso:
            progresso(50)
        locais, erros_arte = provedores.baixar_artes(uuid, artes, meta.get("travado") or (), cancelado)
        self._gravar_meta(uuid, {**campos, **locais})
        achados = sorted(k for k in {**campos, **locais} if k != "fontes")
        fontes = [p.nome for p in provedores.PROVEDORES if p.chave in (campos.get("fontes") or {})]
        if achados:
            aviso = f"{jogo['titulo']}: dados de {', '.join(fontes)}."
        else:
            aviso = f"{jogo['titulo']}: nenhum provedor encontrou dados."
        todos_erros = erros + erros_arte
        if todos_erros:
            aviso += " " + " ".join(todos_erros[:2])
        return {"id": int(gid), "campos": achados, "erros": todos_erros, "aviso": aviso}

    def enriquecer_lote(self, progresso=None, cancelado=None):
        """Jogos que nunca passaram pelos provedores, um por vez (cancelável)."""
        from bib_nucleo.rede import exigir_rede
        exigir_rede("Buscar dados dos jogos")
        cancelado = cancelado or (lambda: False)
        with closing(core.get_db(self.db_path)) as con:
            pendentes = banco_meta.uuids_sem_meta(con)
        com_dados = sem_dados = 0
        for i, (gid, _uuid) in enumerate(pendentes):
            if cancelado():
                break
            try:
                r = self.enriquecer_jogo(gid, cancelado=cancelado)
                com_dados += bool(r["campos"])
                sem_dados += not r["campos"]
            except (ValueError, LookupError):
                sem_dados += 1
            if progresso:
                progresso((i + 1) * 100 / max(1, len(pendentes)))
        if not pendentes:
            return {"aviso": "Todos os jogos já têm dados dos provedores."}
        return {"aviso": f"Dados atualizados: {com_dados} jogo(s); sem resultado: {sem_dados}.",
                "com_dados": com_dados, "sem_dados": sem_dados}

    def salvar_meta(self, gid, campos):
        jogo = self.jogo(gid)
        with self._escrita, closing(core.get_db(self.db_path)) as con:
            return _publico(banco_meta.salvar_edicao(con, jogo.get("uuid") or "", campos))

    def buscar_artes(self, gid, tipo):
        """Candidatos de hero/logo/ícone: CDN da Steam e SteamGridDB (rede, ação do usuário)."""
        from bib_nucleo.rede import exigir_rede, online
        from bib_nucleo.rede.provedores import sgdb, steam
        if tipo not in TIPOS_ARTE:
            raise ValueError("tipo deve ser hero, logo ou icone")
        exigir_rede("Buscar arte")
        jogo = self.jogo(gid)
        meta = self._meta_de(jogo.get("uuid") or "")
        itens, erros = [], []
        appid = steam.resolver_appid(jogo, meta)
        itens += [{"url": u, "preview": u, "fonte": "Steam"} for u in steam.candidatos_arte(appid, tipo)]
        if online.chave_provedor("steamgriddb_key"):
            try:
                ident = sgdb.resolver_id(jogo, {**meta, "steam_appid": appid or meta.get("steam_appid")})
                itens += [{**a, "fonte": "SteamGridDB"} for a in sgdb.artes(ident, tipo)]
            except ValueError as e:
                erros.append(f"SteamGridDB: {e}")
        else:
            erros.append("SteamGridDB: configure a chave para ver mais opções.")
        return {"itens": itens, "erros": erros}

    def aplicar_arte(self, gid, tipo, url):
        from bib_nucleo.rede import provedores
        if tipo not in TIPOS_ARTE:
            raise ValueError("tipo deve ser hero, logo ou icone")
        jogo = self.jogo(gid)
        uuid = jogo.get("uuid") or ""
        caminho = provedores.baixar_uma(uuid, tipo, url)
        meta = self._gravar_meta(uuid, {tipo: caminho}, respeitar_trava=False, travar=(tipo,))
        return _publico(meta)

    def provedores_metadados(self):
        from bib_nucleo.rede import online, provedores
        return {"provedores": provedores.estado(),
                "retro_user": online.chave_provedor("retro_user"),
                "retro_key": bool(online.chave_provedor("retro_key"))}

    def configurar_metadados(self, ligados=None, retro_user="", retro_key=""):
        from bib_nucleo.rede import online, provedores
        if ligados:
            provedores.definir_ligados(ligados)
        if retro_user or retro_key:
            online.configurar_provedores({"retro_user": retro_user, "retro_key": retro_key})
        return self.provedores_metadados()


__all__ = ["MixMeta"]
