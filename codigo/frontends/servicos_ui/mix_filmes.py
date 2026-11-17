"""Filmes e Séries via ServicoBiblioteca: pastas, índice, Cinemeta, progresso e player."""
from __future__ import annotations

import json
import time
from contextlib import closing

import bib_core as core
from bib_nucleo.midia import banco as mb

INTERVALO_SEGUIDAS = 12 * 3600


def pasta_posters():
    return core.DADOS_DIR / "posters"


def poster_dto(imdb, remoto) -> str:
    """Pôster salvo no disco (file://) ou, se ainda não há cópia, o endereço do Cinemeta."""
    for arq in pasta_posters().glob(f"{imdb}.*") if imdb else ():
        return arq.resolve().as_uri()
    return str(remoto or "")


class MixFilmes:
    def _salvar_posters(self, cancelado=lambda: False, so=None):
        """Copia os pôsteres que faltam (títulos com arquivo no disco ou na lista, ou só os de `so`) — rede,
        ação do usuário."""
        from bib_nucleo.arquivos import gravar_atomico
        from bib_nucleo.rede import online, rede_ativa
        if not rede_ativa():
            return 0
        if so:
            sql = f"SELECT imdb_id, poster FROM midia_titulos WHERE poster <> '' AND imdb_id IN ({','.join('?' * len(so))})"
            params = list(so)
        else:
            sql = ("SELECT imdb_id, poster FROM midia_titulos WHERE poster <> '' AND (na_lista=1 OR imdb_id IN "
                   "(SELECT imdb_id FROM midia_arquivos WHERE ausente=0))")
            params = []
        faltam = self._midia(lambda con: [(r[0], r[1]) for r in con.execute(sql, params)])
        n = 0
        for imdb, url in faltam:
            if cancelado() or any(pasta_posters().glob(f"{imdb}.*")):
                continue
            try:
                raw, ext, _ = online.baixar_imagem(url, limite=3_000_000)
            except ValueError:
                continue
            pasta_posters().mkdir(parents=True, exist_ok=True)
            gravar_atomico(pasta_posters() / f"{imdb}{ext}", raw)
            n += 1
        return n

    def _midia(self, operacao, escrever=False):
        if escrever:
            with self._escrita, closing(core.get_db(self.db_path)) as con:
                mb.garantir_tabelas_midia(con)
                return operacao(con)
        with closing(core.get_db(self.db_path)) as con:
            mb.garantir_tabelas_midia(con)
            return operacao(con)

    # -- pastas e índice ------------------------------------------------------
    def midia_pastas(self):
        return {"pastas": self._midia(mb.listar_pastas)}

    def midia_pasta_adicionar(self, caminho):
        self._midia(lambda con: mb.adicionar_pasta(con, caminho), escrever=True)
        return self.midia_pastas()

    def midia_pasta_remover(self, pid):
        self._midia(lambda con: mb.remover_pasta(con, pid), escrever=True)
        return self.midia_pastas()

    def midia_varrer(self, progresso=None, cancelado=None):
        """Indexa todas as pastas e, com rede, casa o que é novo no Cinemeta (trabalho)."""
        from bib_nucleo.midia.casar import casar_pendentes
        from bib_nucleo.midia.indexar import indexar_pasta
        from bib_nucleo.rede import cinemeta, rede_ativa
        cancelado = cancelado or (lambda: False)
        pastas = self._midia(mb.listar_pastas)
        if not pastas:
            raise ValueError("Adicione uma pasta de filmes ou séries primeiro.")
        tot = {"novos": 0, "alterados": 0, "ausentes": 0}
        avisos = []
        for i, p in enumerate(pastas):
            r = self._midia(lambda con, p=p: indexar_pasta(con, p["id"], p["caminho"], cancelado), escrever=True)
            for k in tot:
                tot[k] += max(0, r.get(k, 0))
            if r.get("aviso"):
                avisos.append(r["aviso"])
            if progresso:
                progresso((i + 1) * 50 / len(pastas))
        casados = revisar = 0
        if rede_ativa() and not cancelado():
            c = self._midia(lambda con: casar_pendentes(con, cinemeta.buscar, cinemeta.meta, cancelado=cancelado),
                            escrever=True)
            casados, revisar = c["casados"], c["revisar"]
            avisos += c["erros"][:2]
            self._salvar_posters(cancelado)
        elif not rede_ativa():
            avisos.append("Sem rede: os arquivos foram indexados, mas a identificação no catálogo fica para depois.")
        if progresso:
            progresso(100)
        partes = [f"{tot['novos']} novo(s)", f"{casados} identificado(s)"]
        if revisar:
            partes.append(f"{revisar} para revisar")
        if tot["ausentes"]:
            partes.append(f"{tot['ausentes']} sumiram do disco")
        return {"aviso": "Filmes e Séries: " + ", ".join(partes) + "." + (" " + " ".join(avisos) if avisos else ""),
                **tot, "casados": casados, "revisar": revisar}

    # -- leituras locais -------------------------------------------------------
    def midia_biblioteca(self):
        """Títulos com arquivos no disco + arquivos sem correspondência (para revisar)."""
        def ler(con):
            titulos = []
            for r in con.execute(
                    "SELECT t.imdb_id, t.tipo, t.nome, t.ano, t.poster, COUNT(a.id) AS n, MAX(a.indexado_em) AS quando "
                    "FROM midia_arquivos a JOIN midia_titulos t ON t.imdb_id = a.imdb_id "
                    "WHERE a.ausente=0 GROUP BY t.imdb_id ORDER BY t.nome COLLATE NOCASE"):
                titulos.append({"imdb_id": r["imdb_id"], "tipo": r["tipo"], "nome": r["nome"], "ano": r["ano"],
                                "poster": poster_dto(r["imdb_id"], r["poster"]), "arquivos": int(r["n"]),
                                "adicionado": r["quando"]})
            vistos = mb.progresso(con)
            for t in titulos:
                prefixo = t["imdb_id"]
                if t["tipo"] == "movie":
                    t["assistido"] = bool(vistos.get(prefixo, {}).get("assistido"))
                else:
                    t["assistidos"] = sum(1 for k, v in vistos.items() if k.startswith(prefixo + ":") and v["assistido"])
            revisar = [{"id": int(r["id"]), "caminho": r["caminho"], "nome_lido": r["nome_lido"],
                        "ano_lido": r["ano_lido"], "tipo": r["tipo_lido"], "temporada": r["temporada"],
                        "episodio": r["episodio"], "sugestao": r["sugestao"], "confianca": float(r["confianca"] or 0)}
                       for r in con.execute("SELECT * FROM midia_arquivos WHERE imdb_id IS NULL AND ausente=0 "
                                            "ORDER BY caminho")]
            return {"titulos": titulos, "revisar": revisar, "pastas": mb.listar_pastas(con)}
        return self._midia(ler)

    def _arquivos_do_titulo(self, con, imdb):
        return [dict(r) for r in con.execute(
            "SELECT id, caminho, temporada, episodio, hash, legendas, imdb_id FROM midia_arquivos "
            "WHERE imdb_id=? AND ausente=0 ORDER BY temporada, episodio, caminho", (imdb,))]

    def midia_titulo(self, imdb, tipo=""):
        """Página do título: ficha, temporadas/episódios com arquivo local e progresso."""
        from bib_nucleo.rede import cinemeta, rede_ativa
        salvo = self._midia(lambda con: mb.ler_titulo(con, imdb))
        if salvo is None:
            if not rede_ativa():
                raise ValueError("Este título não está na sua biblioteca e a rede está desligada.")
            m = cinemeta.meta(tipo or "movie", imdb)
            salvo = {"imdb_id": imdb, "tipo": "series" if m.get("type") == "series" else "movie",
                     "nome": m.get("name") or imdb, "ano": str(m.get("releaseInfo") or ""),
                     "poster": m.get("poster") or "", "fundo": m.get("background") or "", "logo": m.get("logo") or "",
                     "descricao": m.get("description") or "", "generos": list(m.get("genres") or [])[:8],
                     "meta": {k: m[k] for k in ("videos", "runtime", "imdbRating", "director", "cast") if k in m},
                     "na_lista": False, "seguindo": False}

        def montar(con):
            arquivos = self._arquivos_do_titulo(con, imdb)
            vistos = mb.progresso(con, [imdb] + [f"{imdb}:{a['temporada']}:{a['episodio']}" for a in arquivos
                                                if a["temporada"] is not None] +
                                  [f"{imdb}:{int(v.get('season') or 0)}:{int(v.get('episode') or 0)}"
                                   for v in salvo["meta"].get("videos") or [] if isinstance(v, dict)])
            dto = {k: salvo[k] for k in ("imdb_id", "tipo", "nome", "ano", "poster", "fundo", "logo", "descricao",
                                         "generos", "na_lista", "seguindo")}
            dto["poster"] = poster_dto(imdb, salvo["poster"])
            dto["nota"] = str(salvo["meta"].get("imdbRating") or "")
            dto["duracao"] = str(salvo["meta"].get("runtime") or "")
            if salvo["tipo"] == "movie":
                dto["arquivos"] = [{"id": a["id"], "caminho": a["caminho"]} for a in arquivos]
                dto["progresso"] = vistos.get(imdb)
                return dto
            locais = {(a["temporada"], a["episodio"]): a["id"] for a in arquivos}
            temporadas: dict[int, list] = {}
            for v in salvo["meta"].get("videos") or []:
                if not isinstance(v, dict) or v.get("season") is None:
                    continue
                s, e = int(v.get("season") or 0), int(v.get("episode") or 0)
                chave = f"{imdb}:{s}:{e}"
                temporadas.setdefault(s, []).append({
                    "chave": chave, "temporada": s, "episodio": e, "nome": str(v.get("name") or v.get("title") or ""),
                    "estreia": str(v.get("released") or "")[:10], "resumo": str(v.get("overview") or v.get("description") or ""),
                    "miniatura": str(v.get("thumbnail") or ""), "arquivo": locais.pop((s, e), None),
                    "progresso": vistos.get(chave)})
            for (s, e), aid in locais.items():  # arquivo de episódio que o catálogo não lista
                if s is not None:
                    temporadas.setdefault(int(s), []).append({
                        "chave": f"{imdb}:{s}:{e}", "temporada": int(s), "episodio": int(e or 0), "nome": "",
                        "estreia": "", "resumo": "", "miniatura": "", "arquivo": aid,
                        "progresso": vistos.get(f"{imdb}:{s}:{e}")})
            # temporadas em ordem; a 0 (especiais) vai para o fim
            ordem = sorted(temporadas, key=lambda s: (s == 0, s))
            dto["temporadas"] = [{"numero": s, "episodios": sorted(temporadas[s], key=lambda x: x["episodio"])}
                                 for s in ordem]
            return dto
        return self._midia(montar)

    def midia_continuar(self, limite=12):
        """Em andamento (5 %–92 %) e o próximo episódio das séries que você está vendo."""
        def ler(con):
            arquivos = [dict(r) for r in con.execute(
                "SELECT a.id, a.imdb_id, a.temporada, a.episodio, a.hash, a.nome_lido, t.nome, t.poster, t.fundo, "
                "t.tipo, t.meta_json FROM midia_arquivos a LEFT JOIN midia_titulos t ON t.imdb_id=a.imdb_id "
                "WHERE a.ausente=0")]
            por_chave = {mb.chave_do_arquivo(a): a for a in arquivos}
            vistos = mb.progresso(con)
            ordenados = sorted(vistos.items(), key=lambda kv: kv[1]["atualizado_em"] or "", reverse=True)
            saida, series_feitas = [], set()
            # 1º: o que está pela metade (de 5 % a 92 %)
            for chave, p in ordenados:
                a = por_chave.get(chave)
                frac = p["posicao"] / p["duracao"] if p["duracao"] else 0
                if a is not None and not p["assistido"] and 0.05 <= frac < mb.LIMIAR_ASSISTIDO:
                    saida.append(self._cartao_continuar(a, chave, p, "em andamento"))
                    if a["tipo"] == "series":
                        series_feitas.add(a["imdb_id"])
            # 2º: próximo episódio das séries cujo último visto terminou
            for chave, p in ordenados:
                a = por_chave.get(chave)
                if a is None or not p["assistido"] or a["tipo"] != "series" or a["imdb_id"] in series_feitas:
                    continue
                series_feitas.add(a["imdb_id"])
                prox = self._proximo_episodio(a, por_chave, vistos)
                if prox is not None:
                    saida.append(self._cartao_continuar(prox, mb.chave_do_arquivo(prox), None, "próximo episódio"))
            return saida[:limite]
        return self._midia(ler)

    @staticmethod
    def _proximo_episodio(a, por_chave, vistos):
        try:
            videos = json.loads(a.get("meta_json") or "{}").get("videos") or []
        except ValueError:
            videos = []
        ordem = sorted({(int(v.get("season") or 0), int(v.get("episode") or 0)) for v in videos
                        if isinstance(v, dict) and v.get("season")})
        if not ordem:
            ordem = sorted((x["temporada"], x["episodio"]) for x in por_chave.values()
                           if x["imdb_id"] == a["imdb_id"] and x["temporada"] is not None)
        atual = (a["temporada"], a["episodio"])
        for s, e in ordem:
            if (s, e) <= atual:
                continue
            chave = f"{a['imdb_id']}:{s}:{e}"
            if chave in por_chave and not vistos.get(chave, {}).get("assistido"):
                return por_chave[chave]
            return None  # o próximo não está no disco
        return None

    @staticmethod
    def _cartao_continuar(a, chave, p, motivo):
        rotulo = a.get("nome") or a.get("nome_lido") or ""
        if a.get("temporada") is not None:
            rotulo += f" · T{a['temporada']}E{a['episodio']}"
        return {"arquivo": int(a["id"]), "chave": chave, "imdb_id": a.get("imdb_id") or "", "titulo": rotulo,
                "poster": poster_dto(a.get("imdb_id"), a.get("poster")), "fundo": a.get("fundo") or "", "motivo": motivo,
                "fracao": round(p["posicao"] / p["duracao"], 3) if p and p["duracao"] else 0}

    def midia_lista(self):
        def ler(con):
            return [{"imdb_id": r["imdb_id"], "tipo": r["tipo"], "nome": r["nome"], "ano": r["ano"],
                     "poster": poster_dto(r["imdb_id"], r["poster"]), "seguindo": bool(r["seguindo"])}
                    for r in con.execute("SELECT * FROM midia_titulos WHERE na_lista=1 ORDER BY nome COLLATE NOCASE")]
        return self._midia(ler)

    def midia_calendario(self):
        from bib_nucleo.midia.calendario import calendario
        return self._midia(calendario)

    # -- com rede (ação do usuário ou abrir a aba Calendário) -------------------
    def _garantir_titulo(self, imdb, tipo):
        from bib_nucleo.rede import cinemeta, exigir_rede
        if self._midia(lambda con: mb.ler_titulo(con, imdb)) is None:
            exigir_rede("Buscar o título no catálogo")
            m = cinemeta.meta(tipo, imdb)
            self._midia(lambda con: mb.gravar_titulo(con, m), escrever=True)
            self._salvar_posters(so=[imdb])  # só o pôster do título que acabou de entrar

    def midia_lista_alternar(self, imdb, tipo):
        self._garantir_titulo(imdb, tipo)
        atual = self._midia(lambda con: mb.ler_titulo(con, imdb))
        self._midia(lambda con: mb.marcar_titulo(con, imdb, na_lista=not atual["na_lista"]), escrever=True)
        return {"na_lista": not atual["na_lista"]}

    def midia_seguir(self, imdb, seguir):
        self._garantir_titulo(imdb, "series")
        self._midia(lambda con: mb.marcar_titulo(con, imdb, seguindo=seguir), escrever=True)
        return {"seguindo": bool(seguir)}

    def midia_descobrir(self, tipo="movie", genero="", pular=0, termo=""):
        from bib_nucleo.rede import cinemeta, exigir_rede
        exigir_rede("Ver o catálogo de filmes e séries")
        metas = cinemeta.buscar(tipo, termo) if termo.strip() else cinemeta.catalogo(tipo, genero, pular)
        def marcar(con):
            locais = {r[0] for r in con.execute("SELECT DISTINCT imdb_id FROM midia_arquivos WHERE ausente=0 "
                                                "AND imdb_id IS NOT NULL")}
            lista = {r[0] for r in con.execute("SELECT imdb_id FROM midia_titulos WHERE na_lista=1")}
            return [{**cinemeta.resumo(m), "no_disco": str(m.get("id")) in locais, "na_lista": str(m.get("id")) in lista}
                    for m in metas]
        return self._midia(marcar)

    def midia_atualizar_seguidas(self, forcar=False):
        """Renova episódios das séries seguidas; ao abrir o Calendário, no máximo a cada 12 h."""
        from bib_nucleo.arquivos import gravar_json, ler_json
        from bib_nucleo.rede import cinemeta, rede_ativa
        marca = core.DADOS_DIR / "midia-seguidas.json"
        ultima = ler_json(marca, {}) if marca.is_file() else {}
        if not rede_ativa():
            return {"atualizado": False, "motivo": "sem rede"}
        if not forcar and time.time() - float((ultima or {}).get("em") or 0) < INTERVALO_SEGUIDAS:
            return {"atualizado": False, "motivo": "recente"}
        seguidas = self._midia(lambda con: [r[0] for r in con.execute(
            "SELECT imdb_id FROM midia_titulos WHERE seguindo=1")])
        erros = []
        for imdb in seguidas:
            try:
                m = cinemeta.meta("series", imdb, validade_s=INTERVALO_SEGUIDAS)
                self._midia(lambda con, m=m: mb.gravar_titulo(con, m), escrever=True)
            except ValueError as e:
                erros.append(f"{imdb}: {e}")
        gravar_json(marca, {"em": time.time()})
        return {"atualizado": True, "series": len(seguidas), "erros": erros}

    def midia_corrigir(self, arquivo_id, imdb, tipo, temporada=None, episodio=None):
        from bib_nucleo.midia.casar import corrigir
        self._garantir_titulo(imdb, tipo)
        self._midia(lambda con: corrigir(con, arquivo_id, imdb, tipo, temporada, episodio), escrever=True)
        return {"ok": True}

    # -- reprodução -------------------------------------------------------------
    def _arquivo(self, con, arquivo_id):
        r = con.execute("SELECT * FROM midia_arquivos WHERE id=? AND ausente=0", (int(arquivo_id),)).fetchone()
        if r is None:
            raise LookupError("Arquivo não encontrado (foi movido ou apagado?). Varra as pastas de novo.")
        return dict(r)

    def midia_reproduzir(self, arquivo_id):
        def ler(con):
            a = self._arquivo(con, arquivo_id)
            chave = mb.chave_do_arquivo(a)
            p = mb.progresso(con, [chave]).get(chave) or {}
            t = mb.ler_titulo(con, a["imdb_id"]) if a["imdb_id"] else None
            titulo = (t or {}).get("nome") or a["nome_lido"]
            if a["temporada"] is not None:
                titulo += f" · T{a['temporada']}E{a['episodio']}"
            legendas = json.loads(a["legendas"] or "[]")
            return {"arquivo": int(a["id"]), "caminho": a["caminho"], "chave": chave, "titulo": titulo,
                    "posicao": 0.0 if p.get("assistido") else float(p.get("posicao") or 0),
                    "legendas": [{"indice": i, "idioma": leg.get("idioma") or f"Legenda {i + 1}"}
                                 for i, leg in enumerate(legendas)]}
        return self._midia(ler)

    def midia_externo(self, arquivo_id, reprodutor="auto"):
        caminho = self._midia(lambda con: self._arquivo(con, arquivo_id))["caminho"]
        r = core.reproduzir_video(caminho, reprodutor)
        if not r.get("ok"):
            raise ValueError(r.get("erro", "Não foi possível abrir o vídeo."))
        return {"reprodutor": r.get("reprodutor", "")}

    def midia_salvar_posicao(self, chave, posicao, duracao):
        return self._midia(lambda con: mb.salvar_progresso(con, chave, posicao, duracao), escrever=True)

    def midia_marcar(self, chaves, assistido):
        self._midia(lambda con: mb.marcar_assistido(con, chaves, assistido), escrever=True)
        return {"ok": True, "chaves": len(chaves)}

    def midia_legenda(self, arquivo_id, indice):
        from bib_nucleo.midia.legendas import legenda_vtt
        a = self._midia(lambda con: self._arquivo(con, arquivo_id))
        legendas = json.loads(a["legendas"] or "[]")
        if not 0 <= int(indice) < len(legendas):
            raise ValueError("Legenda não encontrada.")
        return {"vtt": legenda_vtt(legendas[int(indice)]["arquivo"])}


__all__ = ["MixFilmes"]
