"""Midias via ServicoBiblioteca: capas, musicas, videos e ferramentas."""
from __future__ import annotations

from contextlib import closing
from pathlib import Path

from bib_nucleo import (
    apps_externos,
    baixar,
    banco,
    base,
    capas,
    musicas,
    online,
    pacotes,
    spotify,
    videos,
)
from bib_nucleo.rede import videos_youtube


class MixMidia:
    def buscar_capas(self, categoria, ident, provedor, atualizar=False):
        from bib_nucleo.rede import exigir_rede
        exigir_rede("Buscar capas")
        return capas.buscar_capas(categoria, self.item_capa(categoria, ident), provedor, atualizar)

    def aplicar_capa(self, categoria, ident, candidato):
        return self.alterar(lambda con: capas.salvar_capa_provedor(con, categoria, ident, candidato))

    def buscar_capa_libretro(self, gid):
        from bib_nucleo.rede import capas_libretro
        jogo = self.jogo(gid)
        r = capas_libretro.buscar_capa_libretro(
            jogo.get("plataforma") or banco.plataforma_jogo(jogo), jogo.get("titulo"))
        return self.alterar(lambda con: banco.salvar_capa_bytes(
            con, gid, f"libretro-{gid}{r['ext']}", r["raw"]))

    def buscar_musicas_online(self, termo, fonte="todas", atualizar=False):
        from bib_nucleo.rede import exigir_rede
        exigir_rede("Buscar músicas online")
        from bib_nucleo import musica_online
        if fonte == "spotify":
            link = spotify.identificar_spotify(termo)
            modo = {"track": "faixa", "album": "album", "playlist": "playlist"}[link[0]] if link else "busca"
            r = self.spotify.consultar(modo, link[1] if link else termo)
            itens = []
            for f in r.get("itens", []):
                f = dict(f)
                f["fonte"], f["nome_fonte"] = "spotify", "Spotify"
                itens.append(f)
            return {"itens": itens, "erros": [], "cache": bool(r.get("cache")),
                    "aviso": r.get("aviso", "")}
        return musica_online.buscar_musicas(termo, fonte, atualizar)

    def buscar_letras(self, artista, titulo, album="", duracao_s=0):
        from bib_nucleo.rede import letras
        return letras.buscar_letras(artista, titulo, album, duracao_s)

    def enfileirar_musicas(self, itens):
        metas = online.ler_json(base.DADOS_DIR / "musicas-online/faixas.json", {})
        metas = metas if isinstance(metas, dict) else {}
        metas.update({i["uri"]: i for i in itens if i.get("uri") and i.get("capa_url")})
        if metas:
            online.gravar_json(base.DADOS_DIR / "musicas-online/faixas.json", metas)
        return self.alterar(lambda con: banco.enfileirar_downloads(con, itens))

    def instalar_audio(self):
        resultados = []
        if not baixar.ffmpeg_pronto():
            resultados.append(baixar.instalar_ffmpeg())
        if not baixar.ytdlp_pronto():
            resultados.append(baixar.instalar_ytdlp())
        erros = [r.get("erro", "Falha na instalação.") for r in resultados if not r.get("ok")]
        return {"ok": not erros, "erros": erros}

    def baixar_musicas(self, cancelar, progresso=None):
        pacotes.fazer_backup(self.db_path)
        novas = 0
        erros = []
        with closing(banco.get_db(self.db_path)) as con:
            fila = [d for d in banco.listar_downloads(con) if d["estado"] in ("pendente", "falha", "baixando", "baixado")]
            def staging_pronto(d):
                return d["estado"] == "falha" and bool(d.get("video_id")) and Path(d.get("musica_path") or "").is_file()
            if any(d["estado"] != "baixado" and not staging_pronto(d) for d in fila) and not baixar.localizar_ytdlp():
                raise ValueError("Instale yt-dlp em Dependências de áudio antes de baixar a fila.")
            metas = online.ler_json(base.DADOS_DIR / "spotify/faixas.json", {})
            publicas = online.ler_json(base.DADOS_DIR / "musicas-online/faixas.json", {})
            metas = {**(metas if isinstance(metas, dict) else {}),
                     **(publicas if isinstance(publicas, dict) else {})}
            for n, d in enumerate(fila):
                if cancelar.is_set():
                    break
                # n/d fixados na definição: o callback pertence a ESTA faixa
                def pct(did, valor, n=n, d=d):
                    if progresso:
                        progresso({"id": did, "rotulo": f'{n + 1}/{len(fila)} · {d["artista"]} — {d["titulo"]}', "pct": valor})
                pct(d["id"], 0)
                retomar_conversao = staging_pronto(d)
                if retomar_conversao:
                    banco.marcar_download(con, d["id"], "baixado", video_id=d["video_id"], musica_path=d["musica_path"])
                if d["estado"] != "baixado" and not retomar_conversao:
                    baixou = baixar.baixar_faixa(con, d["id"], progresso=pct)
                    if not baixou.get("ok"):
                        erros.append(f'{d["titulo"]}: {baixou.get("erro")}')
                        continue
                r = baixar.converter_faixa(con, d["id"], capa_auto=False)
                if not r.get("ok"):
                    erros.append(f'{d["titulo"]}: {r.get("erro")}')
                    continue
                novas += 1
                row = con.execute("SELECT id FROM musicas WHERE musica_sha=?", (r["sha"],)).fetchone()
                meta = metas.get(d.get("uri"), {}) if isinstance(metas, dict) else {}
                if row:
                    try:
                        if online.url_https(meta.get("capa_url") or ""):
                            raw, ext, _ = online.baixar_imagem(meta["capa_url"])
                            banco.salvar_capa_musica_bytes(con, row["id"], "spotify-album" + ext, raw)
                        else:
                            musicas.baixar_capa_album(con, row["id"])
                    except (ValueError, OSError):
                        pass
        return {"novas": novas, "erros": erros, "cancelado": cancelar.is_set()}

    def buscar_videos_online(self, termo, limite=10, atualizar=False):
        from bib_nucleo.rede import exigir_rede
        exigir_rede("Buscar vídeos no YouTube")
        return videos_youtube.buscar_youtube(termo, limite=limite, atualizar=atualizar)

    def baixar_video_online(self, video_id, progresso=None):
        pacotes.fazer_backup(self.db_path)
        with closing(banco.get_db(self.db_path)) as con:
            return videos_youtube.baixar_video_youtube(con, video_id, progresso=progresso)

    def listar_videos(self, q=""):
        with closing(banco.get_db(self.db_path)) as con:
            return banco.listar_videos(con, q)

    def importar_videos(self, pasta):
        return self.alterar(lambda con: videos.importar_videos(con, pasta))

    def importar_musicas(self, pasta):
        # Capas remotas não são buscadas implicitamente nesta importação local.
        return self.alterar(lambda con: musicas.importar_musicas(con, pasta, capa_auto=False))

    def aplicar_eq_musica(self, caminho, preset="bass"):
        from bib_nucleo.musicas import ler_tags, sha_arquivo
        with self._escrita:
            pacotes.fazer_backup(self.db_path)
            r = apps_externos.aplicar_eq(caminho, preset)
            if not r.get("ok"):
                raise ValueError(r.get("erro", "Falha na equalização."))
            tags = ler_tags(caminho)
            with closing(banco.get_db(self.db_path)) as con:
                banco.criar_musica(con, {**tags, "titulo": tags["titulo"] + " [EQ: " + preset + "]",
                                       "musica_path": r["path"], "musica_sha": sha_arquivo(Path(r["path"])),
                                       "origem": "equalizacao"})
            return r

    def reproduzir_video(self, ident, reprodutor="auto"):
        with closing(banco.get_db(self.db_path)) as con:
            row = con.execute("SELECT video_path FROM videos WHERE id=?", (int(ident),)).fetchone()
        if row is None:
            raise LookupError("Vídeo não encontrado na videoteca.")
        r = apps_externos.reproduzir_video(row["video_path"], reprodutor)
        if not r.get("ok"):
            raise ValueError(r.get("erro", "Não foi possível abrir o vídeo."))
        return r

    def abrir_ferramenta_midia(self, tipo, nome, caminho=""):
        import subprocess
        grupos = {"imagens": (apps_externos.PROVEDORES_IMAGEM, apps_externos.localizar_editor),
                  "equalizadores": (apps_externos.PROVEDORES_EQUALIZADOR, apps_externos.localizar_equalizador),
                  "videos": (apps_externos.PROVEDORES_VIDEO, apps_externos.localizar_reprodutor)}
        if tipo not in grupos or nome not in grupos[tipo][0]:
            raise ValueError("Ferramenta de mídia inválida.")
        exe = grupos[tipo][1](nome)
        if not exe:
            raise ValueError("Ferramenta não instalada; informe o executável no ambiente/runtime ou abra o site oficial.")
        if caminho and tipo == "imagens":
            r = apps_externos.abrir_no_editor(nome, caminho)
        elif caminho and tipo == "videos":
            r = apps_externos.reproduzir_video(caminho, nome)
        elif caminho and nome == "audacity":
            r = apps_externos.abrir_no_editor_audio(nome, caminho)
        else:
            subprocess.Popen([exe])
            r = {"ok": True}
        if not r.get("ok"):
            raise ValueError(r.get("erro", "Falha ao abrir a ferramenta."))
        return r

    def baixar_mp3(self, video, progresso=None, musica=None):
        """MP3 do vídeo; com `musica` (faixa do Spotify), entra com os dados e a capa dela."""
        r = self.alterar(lambda con: videos_youtube.baixar_audio_youtube(con, video, progresso, musica))
        capa = str((musica or {}).get("capa_url") or "") if isinstance(musica, dict) else ""
        if r.get("ok") and r.get("id") and online.url_https(capa):
            try:
                self.aplicar_capa("musicas", r["id"], {"url": capa, "provedor": "spotify"})
            except (OSError, ValueError) as erro:
                r["aviso"] = f"MP3 baixado; a capa do Spotify não veio ({erro})."
        return r

    def versao_musica(self, video):
        """A mesma música no Spotify para o vídeo (para oferecer MP3 com os dados dela)."""
        from bib_nucleo.rede import exigir_rede, musica_video
        exigir_rede("Procurar a música no Spotify")
        return musica_video.versao_spotify(self.spotify, video)

    def limpar_fila_musicas(self):
        """Tira da fila de downloads as faixas já baixadas."""
        return {"removidas": self.alterar(lambda con: banco.limpar_downloads(con, ("pronta",)))}

    def video_local(self, ident):
        from bib_nucleo.apps_externos import resolver_video
        with closing(banco.get_db(self.db_path)) as con:
            row = con.execute("SELECT * FROM videos WHERE id=?", (int(ident),)).fetchone()
        if row is None:
            raise ValueError("Vídeo não encontrado.")
        path = resolver_video(row["video_path"])
        if not path:
            raise ValueError("Arquivo de vídeo ausente.")
        posicoes = online.ler_json(base.DADOS_DIR / "videos-posicoes.json", {})
        posicoes = posicoes if isinstance(posicoes, dict) else {}
        try:
            posicao = max(0, int(posicoes.get(row["video_sha"], 0)))
        except (TypeError, ValueError):
            posicao = 0
        return {"id": ident, "url": Path(path).resolve().as_uri(), "titulo": row["titulo"],
                "posicao": posicao, "sha": row["video_sha"]}

    def salvar_posicao_video(self, sha, posicao):
        import re
        if not re.fullmatch(r"[0-9a-f]{64}", sha):
            return
        with self._escrita:
            alvo = base.DADOS_DIR / "videos-posicoes.json"
            posicoes = online.ler_json(alvo, {})
            posicoes = posicoes if isinstance(posicoes, dict) else {}
            posicoes[sha] = max(0, int(posicao))
            online.gravar_json(alvo, posicoes)

__all__ = ["MixMidia"]
