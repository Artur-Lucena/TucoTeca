"""Contratos da interface desktop, independentes de Qt e de widgets.

Adaptadores retornam dados simples. Cada operação possui sua conexão SQLite;
o frontend escolhe a thread e apresenta erros. Integrações são registradas
explicitamente: instalar um serviço não implica executar plugins arbitrários.
"""
from __future__ import annotations

import math
import threading
import urllib.parse
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import bib_core as core
from bib_nucleo import capas, conquistas, online, spotify
from bib_nucleo.arquivos import gravar_atomico


@dataclass(frozen=True)
class Integracao:
    chave: str
    nome: str
    descricao: str
    tipo: str
    inicial: str
    cor: str
    buscar: Callable | None = None
    url: str = ""
    personalizada: bool = False

    def apresentar(self):
        return {k: v for k, v in asdict(self).items() if k != "buscar"}


INTEGRACAO_TIPOS = ("catalogo", "emulador", "download", "musicas_online",
                    "provedores", "link")
_CORES = ("#62d4ad", "#b5a0ff", "#f0bb77", "#7eaaff", "#67cff1", "#7ce3b8", "#6cd5f5")


def _arquivo_personalizadas():
    return core.DADOS_DIR / "integracoes-usuario.json"


def carregar_personalizadas() -> list[dict]:
    dados = online.ler_json(_arquivo_personalizadas(), [])
    return [d for d in dados] if isinstance(dados, list) else []


def _validar_personalizada(dados: dict) -> dict:
    import re
    chave = str(dados.get("chave") or "").strip().lower()
    nome = str(dados.get("nome") or "").strip()
    descricao = str(dados.get("descricao") or "").strip()
    tipo = str(dados.get("tipo") or "link").strip()
    url = str(dados.get("url") or "").strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,30}[a-z0-9]", chave):
        raise ValueError("Chave inválida: use 2–32 letras/números/hífens.")
    if not 2 <= len(nome) <= 60:
        raise ValueError("Nome precisa de 2–60 caracteres.")
    if len(descricao) > 200:
        raise ValueError("Descrição de até 200 caracteres.")
    if tipo not in INTEGRACAO_TIPOS:
        raise ValueError("Tipo inválido.")
    if url:
        if not online.url_https(url) or len(url) > 500:
            raise ValueError("URL precisa ser https válida.")
    elif tipo in ("catalogo", "link"):
        raise ValueError("Catálogo/link personalizado precisa da URL (use {q} p/ busca).")
    inicial = "".join(w[0] for w in nome.split()[:2]).upper() or "•"
    cor = _CORES[abs(hash(chave)) % len(_CORES)]
    return {"chave": chave, "nome": nome, "descricao": descricao or "Atalho personalizado.",
            "tipo": tipo, "inicial": inicial, "cor": cor, "url": url}


CHAVES_PADRAO = frozenset({"steamrip", "fitgirl", "azahar", "desmume",
                             "qbittorrent", "spotify", "capas"})


def salvar_personalizada(dados: dict) -> dict:
    item = _validar_personalizada(dados)
    if item["chave"] in CHAVES_PADRAO:
        raise ValueError("Esta chave já é de uma integração do Hub.")
    atual = carregar_personalizadas()
    if any(d.get("chave") == item["chave"] for d in atual):
        raise ValueError("Já existe uma integração com esta chave.")
    atual.append(item)
    online.gravar_json(_arquivo_personalizadas(), atual, backup=True)
    return item


def remover_personalizada(chave: str) -> None:
    atual = carregar_personalizadas()
    nova = [d for d in atual if d.get("chave") != chave]
    if len(nova) == len(atual):
        raise ValueError("Integração padrão não pode ser removida (ou já saiu).")
    online.gravar_json(_arquivo_personalizadas(), nova, backup=True)


class RegistroIntegracoes:
    def __init__(self):
        self._itens: dict[str, Integracao] = {}

    def registrar(self, item: Integracao):
        if not item.chave or item.chave in self._itens:
            raise ValueError(f"Integração duplicada/inválida: {item.chave}")
        self._itens[item.chave] = item

    def listar(self):
        return [i.apresentar() for i in self._itens.values()]

    def buscar(self, chave: str, termo: str):
        item = self._itens.get(chave)
        if item is None or item.buscar is None:
            raise ValueError("Esta integração não oferece pesquisa de catálogo.")
        termo = termo.strip()
        if len(termo) < 2:
            raise ValueError("Digite pelo menos dois caracteres.")
        return item.buscar(termo)


def integracoes_padrao():
    registro = RegistroIntegracoes()
    for item in (
        Integracao("steamrip", "SteamRip", "Pesquise o catálogo e abra a página do jogo.",
                   "catalogo", "SR", "#62d4ad", core.buscar_steamrip),
        Integracao("fitgirl", "FitGirl", "Descubra títulos no catálogo conectado.",
                   "catalogo", "FG", "#b5a0ff", core.buscar_fitgirl),
        Integracao("azahar", "Azahar", "Emulação 3DS, presets, mods e texturas.",
                   "emulador", "3D", "#f0bb77"),
        Integracao("desmume", "DeSmuME", "Sua coleção Nintendo DS, no mesmo lugar.",
                   "emulador", "DS", "#7eaaff"),
        Integracao("qbittorrent", "qBittorrent", "Cliente local com progresso, pausa e retomada.",
                    "download", "qb", "#67cff1"),
        Integracao("spotify", "Spotify", "Escolha faixas/playlists e envie à fila de música local.",
                   "musicas_online", "SP", "#7ce3b8"),
        Integracao("capas", "Capas online", "Steam, SteamGridDB, Wikipedia, iTunes, MusicBrainz e Deezer.",
                   "provedores", "AR", "#6cd5f5"),
    ):
        registro.registrar(item)
    for d in carregar_personalizadas():
        try:
            item = _validar_personalizada(d)
        except ValueError:
            continue
        try:
            registro.registrar(Integracao(url=item.pop("url"), personalizada=True, **item))
        except ValueError:
            continue
    return registro


def url_integracao(registro: RegistroIntegracoes, chave: str, termo="") -> str:
    item = registro._itens.get(chave)
    if item is None or not item.url:
        raise ValueError("Esta integração não tem URL configurada.")
    url = item.url.replace("{q}", urllib.parse.quote_plus((termo or "").strip()))
    if not online.url_https(url):
        raise ValueError("URL da integração inválida.")
    return url


def capa_url(nome):
    if not nome:
        return ""
    alvo = core.caminho_capa(nome)
    return alvo.resolve().as_uri() if alvo is not None and alvo.is_file() else ""


def resumo_sistema(jogos, musicas, desejos, downloads=None):
    """Dashboard local OS: só conta estado já em memória + disco/backup. Sem rede."""
    import shutil
    recentes = sorted((j for j in jogos if j.get("ultima_execucao")),
                      key=lambda j: j.get("ultima_execucao") or "", reverse=True)[:4]
    if len(recentes) < 4:
        vistos = {id(j) for j in recentes}
        extra = sorted((j for j in jogos if id(j) not in vistos),
                       key=lambda j: float(j.get("horas") or 0), reverse=True)
        recentes = [*recentes, *extra][:4]
    try:
        pendentes = len(core.listar_sessoes_pendentes())
    except Exception:
        pendentes = 0
    try:
        idade = core.idade_ultimo_backup_dias()
        backup = "sem backup" if idade is None else (
            "backup hoje" if idade < 1 else f"backup há {int(idade)}d")
        backup_estado = "ausente" if idade is None else "antigo" if idade >= 7 else "recente"
    except Exception:
        idade, backup, backup_estado = None, "backup indisponível", "indisponivel"
    try:
        uso = shutil.disk_usage(core.HOME_DIR)
        livre_gb = round(uso.free / 1024 ** 3, 1)
        total_gb = round(uso.total / 1024 ** 3)
    except Exception:
        livre_gb, total_gb = 0, 0
    return {"jogos": len(jogos), "musicas": len(musicas), "desejos": len(desejos),
            "downloads": len(downloads or []), "pendentes": pendentes, "backup": backup,
            "backup_idade_dias": idade, "backup_estado": backup_estado,
            "disco_livre_gb": livre_gb, "disco_total_gb": total_gb,
            "recentes": [dict(r) for r in recentes]}


def saude_colecao(jogos, limite=8):
    """Diagnostica todos os jogos; o limite afeta só o resumo de problemas."""
    problemas = []
    ids_pendentes = []
    for j in jogos:
        try:
            exe = core.diagnosticar_exe(j)["estado"]
        except Exception:
            exe = "?"
        try:
            rom = core.diagnosticar_rom(j)["estado"]
        except Exception:
            rom = "?"
        motivos = []
        if exe not in ("ok",):
            motivos.append("exe " + exe)
        if rom == "rom-ausente":
            motivos.append("rom ausente")
        if motivos:
            ids_pendentes.append(j["id"])
            if len(problemas) < limite:
                problemas.append({"id": j["id"], "titulo": j["titulo"], "motivo": ", ".join(motivos)})
    return {"total": len(jogos), "problemas": problemas, "pendentes": len(ids_pendentes),
            "ids_pendentes": ids_pendentes, "ok": len(jogos) - len(ids_pendentes)}


def _sem_acento(s: str) -> str:
    """Minúsculas sem diacriticos (para busca tolerante, sem depender de ICU)."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(s or "").casefold())
                   if unicodedata.category(c) != "Mn")


def busca_global(jogos, musicas, desejos, downloads, termo, limite=12):
    """Paleta de comandos OS: filtra coleção em memória, sem I/O. Retorna DTOs.

    Busca tolerante a acentos e sem ordem obrigatória das palavras.
    """
    palavras = _sem_acento(termo).split()
    if not palavras:
        return []
    def casa(item, campos):
        texto = _sem_acento(" ".join(str(item.get(k) or "") for k in campos))
        return all(p in texto for p in palavras)
    out = []
    for j in jogos:
        if casa(j, ("titulo", "etiquetas", "plataforma")):
            out.append({"tipo": "jogo", "id": j["id"], "titulo": j["titulo"],
                        "sub": f"{j.get('plataforma') or 'PC'} · {j.get('status') or 'backlog'}",
                        "capa_url": j.get("capa_url", "")})
    for m in musicas:
        if casa(m, ("titulo", "artista", "album")):
            out.append({"tipo": "musica", "id": m["id"], "titulo": m["titulo"],
                        "sub": str(m.get("artista") or "Artista desconhecido"),
                        "capa_url": m.get("capa_url", "")})
    for d in desejos:
        if casa(d, ("titulo",)):
            out.append({"tipo": "desejo", "id": d["id"], "titulo": d["titulo"],
                        "sub": "Desejo · Steam " + str(d.get("appid") or ""), "capa_url": ""})
    for t in downloads or []:
        if casa(t, ("nome",)):
            out.append({"tipo": "download", "id": t.get("hash", ""), "titulo": t.get("nome", ""),
                        "sub": f"{t.get('pct', 0)}% · {t.get('estado') or 'histórico'}",
                        "capa_url": ""})
    return out[:limite]


class ServicoBiblioteca:
    def __init__(self, db_path, registro=None):
        self.db_path = Path(db_path)
        self.integracoes = registro or integracoes_padrao()
        self._escrita = threading.RLock()
        self.spotify = spotify.ClienteSpotify()

    def snapshot(self):
        with closing(core.get_db(self.db_path)) as con:
            jogos = core.listar_jogos(con)
            musicas = core.listar_musicas(con)
            desejos = core.listar_desejos(con)
            fila_musicas = core.listar_downloads(con)
            videos = core.listar_videos(con)
        for j in jogos:
            j.update(capa_url=capa_url(j.get("capa")), plataforma=core.plataforma_jogo(j))
        for m in musicas:
            m["capa_url"] = capa_url(m.get("musica_capa"))
        return {"jogos": jogos, "musicas": musicas, "desejos": desejos, "videos": videos,
                "fila_musicas": fila_musicas,
                "sistema": resumo_sistema(jogos, musicas, desejos)}

    def panorama(self, termo=""):
        snap = self.snapshot()
        return {"sistema": snap["sistema"],
                "global": busca_global(snap["jogos"], snap["musicas"],
                                       snap["desejos"], [], termo) if termo.strip() else []}

    def jogo(self, gid):
        with closing(core.get_db(self.db_path)) as con:
            row = con.execute("SELECT * FROM jogos WHERE id=?", (int(gid),)).fetchone()
            if row is None:
                raise LookupError("O jogo não está mais na biblioteca.")
            return core.row_to_dict(row)

    def alterar(self, operacao):
        with self._escrita:
            core.fazer_backup(self.db_path)
            with closing(core.get_db(self.db_path)) as con:
                return operacao(con)

    def salvar_jogo(self, gid, dados, sincronizar=False):
        permitido = {"titulo", "executable_path", "launch_options", "status", "nota",
                     "etiquetas", "favorito", "observacoes"}
        dados = {k: v for k, v in (dados or {}).items() if k in permitido}
        if "nota" in dados and (dados["nota"] == "" or dados["nota"] is None):
            dados["nota"] = None
        resultado = self.alterar(lambda con: core.atualizar_jogo(con, gid, dados) if gid
                                 else core.criar_jogo(con, dados))
        if sincronizar and not gid:
            novo_id = resultado.get("id") if isinstance(resultado, dict) else None
            if novo_id:
                try:
                    conquistas.sincronizar_catalogo(self.jogo(novo_id))
                except (ValueError, OSError) as e:
                    resultado["avisos"] = ["Jogo salvo. Referência de conquistas pendente: " + str(e)]
        return resultado

    def item_capa(self, categoria, ident):
        if categoria == "jogos":
            return self.jogo(ident)
        if categoria != "musicas":
            raise ValueError("Categoria de capas inválida.")
        with closing(core.get_db(self.db_path)) as con:
            row = con.execute("SELECT * FROM musicas WHERE id=?", (int(ident),)).fetchone()
        if row is None:
            raise LookupError("Música não encontrada.")
        return dict(row)

    def buscar_capas(self, categoria, ident, provedor, atualizar=False):
        from bib_nucleo.rede import exigir_rede
        exigir_rede("Buscar capas")
        return capas.buscar_capas(categoria, self.item_capa(categoria, ident), provedor, atualizar)

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

    def aplicar_capa(self, categoria, ident, candidato):
        return self.alterar(lambda con: capas.salvar_capa_provedor(con, categoria, ident, candidato))

    def sincronizar_conquistas(self, gid, appid="", save=""):
        return conquistas.sincronizar_catalogo(self.jogo(gid), appid, save)

    def avaliar_conquistas(self, gid):
        return conquistas.avaliar_save(self.jogo(gid))

    def regras_conquistas(self, gid, texto):
        return conquistas.salvar_regras(self.jogo(gid), texto)

    def configurar_provedores(self, steam, steamgrid, spotify_id, spotify_secret=""):
        return online.configurar_provedores({"steam_key": steam, "steamgriddb_key": steamgrid,
                                            "spotify_client_id": spotify_id,
                                            "spotify_client_secret": spotify_secret})

    def aparencia(self):
        from bib_nucleo import aparencia_usuario
        return aparencia_usuario.ler_aparencia()

    def definir_aparencia(self, tema="", densidade="", auto_backup=None, modo_simples=None):
        from bib_nucleo import aparencia_usuario
        return aparencia_usuario.salvar_aparencia(tema, densidade, auto_backup, modo_simples)

    def salvar_observacoes(self, gid, texto):
        """Notas/diário do jogo (campo `observacoes`, sem migração)."""
        texto = str(texto or "")[:4000]
        return self.alterar(lambda con: core.atualizar_jogo(con, gid, {"observacoes": texto}))

    def exportar_colecao_para(self, pasta):
        """Pacote ZIP da coleção numa pasta escolhida (pendrive, nuvem, etc.)."""
        from datetime import datetime
        from pathlib import Path
        destino = Path(pasta) / f"tucoteca-{datetime.now():%Y%m%d-%H%M}.zip"
        return core.exportar_pacote(destino, self.db_path)

    def enfileirar_musicas(self, itens):
        metas = online.ler_json(core.DADOS_DIR / "musicas-online/faixas.json", {})
        metas = metas if isinstance(metas, dict) else {}
        metas.update({i["uri"]: i for i in itens if i.get("uri") and i.get("capa_url")})
        if metas:
            online.gravar_json(core.DADOS_DIR / "musicas-online/faixas.json", metas)
        return self.alterar(lambda con: core.enfileirar_downloads(con, itens))

    def instalar_audio(self):
        resultados = []
        if not core.ffmpeg_pronto():
            resultados.append(core.instalar_ffmpeg())
        if not core.ytdlp_pronto():
            resultados.append(core.instalar_ytdlp())
        erros = [r.get("erro", "Falha na instalação.") for r in resultados if not r.get("ok")]
        return {"ok": not erros, "erros": erros}

    def baixar_musicas(self, cancelar, progresso=None):
        core.fazer_backup(self.db_path)
        novas = 0
        erros = []
        with closing(core.get_db(self.db_path)) as con:
            fila = [d for d in core.listar_downloads(con) if d["estado"] in ("pendente", "falha", "baixando", "baixado")]
            def staging_pronto(d):
                return d["estado"] == "falha" and bool(d.get("video_id")) and Path(d.get("musica_path") or "").is_file()
            if any(d["estado"] != "baixado" and not staging_pronto(d) for d in fila) and not core.localizar_ytdlp():
                raise ValueError("Instale yt-dlp em Dependências de áudio antes de baixar a fila.")
            metas = online.ler_json(core.DADOS_DIR / "spotify/faixas.json", {})
            publicas = online.ler_json(core.DADOS_DIR / "musicas-online/faixas.json", {})
            metas = {**(metas if isinstance(metas, dict) else {}),
                     **(publicas if isinstance(publicas, dict) else {})}
            for n, d in enumerate(fila):
                if cancelar.is_set():
                    break
                def pct(did, valor):
                    if progresso:
                        progresso({"id": did, "rotulo": f'{n + 1}/{len(fila)} · {d["artista"]} — {d["titulo"]}', "pct": valor})
                pct(d["id"], 0)
                retomar_conversao = staging_pronto(d)
                if retomar_conversao:
                    core.marcar_download(con, d["id"], "baixado", video_id=d["video_id"], musica_path=d["musica_path"])
                if d["estado"] != "baixado" and not retomar_conversao:
                    baixou = core.baixar_faixa(con, d["id"], progresso=pct)
                    if not baixou.get("ok"):
                        erros.append(f'{d["titulo"]}: {baixou.get("erro")}')
                        continue
                r = core.converter_faixa(con, d["id"], capa_auto=False)
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
                            core.salvar_capa_musica_bytes(con, row["id"], "spotify-album" + ext, raw)
                        else:
                            core.baixar_capa_album(con, row["id"])
                    except (ValueError, OSError):
                        pass
        return {"novas": novas, "erros": erros, "cancelado": cancelar.is_set()}

    def saude(self):
        with closing(core.get_db(self.db_path)) as con:
            jogos = core.listar_jogos(con)
        return saude_colecao(jogos)

    def backups(self, manter=10):
        arqs = sorted(core.BACKUP_DIR.glob("biblioteca-*.db"),
                      key=lambda p: p.name, reverse=True)[:manter]
        return [{"nome": p.name, "bytes": p.stat().st_size if p.is_file() else 0}
                for p in arqs]

    def sessoes(self):
        try:
            return core.listar_sessoes_pendentes()
        except Exception:
            return []

    def log_cauda(self, linhas=30):
        try:
            alvo = core.DADOS_DIR / "erros.log"
            texto = alvo.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(texto[-linhas:]) if texto else "Sem erros registrados."
        except Exception as e:
            return f"Log indisponível: {e}"

    def favorito(self, gid):
        with self._escrita:
            jogo = self.jogo(gid)
            return self.salvar_jogo(gid, {"favorito": not jogo["favorito"]})

    def excluir(self, categoria, ident):
        funcoes = {"jogos": core.excluir_jogo, "desejos": core.remover_desejo,
                   "musicas": core.excluir_musica,
                   "videos": core.excluir_video}
        if categoria not in funcoes:
            raise ValueError("Esta categoria não permite exclusão pela biblioteca.")
        return self.alterar(lambda con: funcoes[categoria](con, int(ident)))

    def importar_musicas(self, pasta):
        # Capas remotas não são buscadas implicitamente nesta importação local.
        return self.alterar(lambda con: core.importar_musicas(con, pasta, capa_auto=False))

    def adicionar_desejo(self, appid, titulo):
        return self.alterar(lambda con: core.adicionar_desejo(con, appid, titulo))

    # 2.0 — mídias open source (backend pronto p/ a UI/QML ligar; outro chat
    # organiza as abas; aqui só o contrato, sem tocar no QML existente).
    def midias_status(self):
        return {"imagens": core.status_editores(),
                "equalizadores": core.status_equalizadores(),
                "videos": core.status_reprodutores(),
                "eq_presets": sorted(core.PRESETS_EQ)}

    def buscar_videos_online(self, termo, limite=10, atualizar=False):
        from bib_nucleo.rede import exigir_rede
        exigir_rede("Buscar vídeos no YouTube")
        return core.buscar_youtube(termo, limite=limite, atualizar=atualizar)

    def baixar_video_online(self, video_id, progresso=None):
        core.fazer_backup(self.db_path)
        with closing(core.get_db(self.db_path)) as con:
            return core.baixar_video_youtube(con, video_id, progresso=progresso)

    def listar_videos(self, q=""):
        with closing(core.get_db(self.db_path)) as con:
            return core.listar_videos(con, q)

    def importar_videos(self, pasta):
        return self.alterar(lambda con: core.importar_videos(con, pasta))

    def aplicar_eq_musica(self, caminho, preset="bass"):
        from bib_nucleo.musicas import ler_tags, sha_arquivo
        with self._escrita:
            core.fazer_backup(self.db_path)
            r = core.aplicar_eq(caminho, preset)
            if not r.get("ok"):
                raise ValueError(r.get("erro", "Falha na equalização."))
            tags = ler_tags(caminho)
            with closing(core.get_db(self.db_path)) as con:
                core.criar_musica(con, {**tags, "titulo": tags["titulo"] + " [EQ: " + preset + "]",
                                       "musica_path": r["path"], "musica_sha": sha_arquivo(Path(r["path"])),
                                       "origem": "equalizacao"})
            return r

    def reproduzir_video(self, ident, reprodutor="auto"):
        with closing(core.get_db(self.db_path)) as con:
            row = con.execute("SELECT video_path FROM videos WHERE id=?", (int(ident),)).fetchone()
        if row is None:
            raise LookupError("Vídeo não encontrado na videoteca.")
        r = core.reproduzir_video(row["video_path"], reprodutor)
        if not r.get("ok"):
            raise ValueError(r.get("erro", "Não foi possível abrir o vídeo."))
        return r

    def abrir_ferramenta_midia(self, tipo, nome, caminho=""):
        import subprocess
        grupos = {"imagens": (core.PROVEDORES_IMAGEM, core.localizar_editor),
                  "equalizadores": (core.PROVEDORES_EQUALIZADOR, core.localizar_equalizador),
                  "videos": (core.PROVEDORES_VIDEO, core.localizar_reprodutor)}
        if tipo not in grupos or nome not in grupos[tipo][0]:
            raise ValueError("Ferramenta de mídia inválida.")
        exe = grupos[tipo][1](nome)
        if not exe:
            raise ValueError("Ferramenta não instalada; informe o executável no ambiente/runtime ou abra o site oficial.")
        if caminho and tipo == "imagens":
            r = core.abrir_no_editor(nome, caminho)
        elif caminho and tipo == "videos":
            r = core.reproduzir_video(caminho, nome)
        elif caminho and nome == "audacity":
            r = core.abrir_no_editor_audio(nome, caminho)
        else:
            subprocess.Popen([exe])
            r = {"ok": True}
        if not r.get("ok"):
            raise ValueError(r.get("erro", "Falha ao abrir a ferramenta."))
        return r

    def baixar_torrent_hub(self, url):
        r = core.qbit_adicionar(url)
        if not r.get("ok"):
            raise ValueError(r.get("erro", "Não foi possível adicionar o torrent."))
        return r

    def organizar_download(self, caminho):
        core.fazer_backup(self.db_path)
        r = core.organizar_no_destino(caminho)
        if not r.get("ok"):
            raise ValueError(r.get("erro", "Não foi possível organizar."))
        return r

    def fora_do_destino(self, caminho):
        try:
            return bool(caminho) and not core.dentro_do_destino(caminho)
        except (OSError, ValueError):
            return False

    def adicionar_integracao(self, dados):
        item = salvar_personalizada(dados)
        self.integracoes = integracoes_padrao()
        return item

    def remover_integracao(self, chave):
        remover_personalizada(chave)
        self.integracoes = integracoes_padrao()
        return {"ok": True}

    def url_integracao(self, chave, termo=""):
        return url_integracao(self.integracoes, chave, termo)

    def iniciar_jogo(self, gid, ao_fim):
        jogo = self.jogo(gid)
        if core.diagnosticar_rom(jogo)["estado"] == "rom-ausente":
            raise ValueError("ROM não encontrada. Atualize o caminho em Editar jogo.")
        preparo = core.preparar_lancamento(jogo)
        resultado = core.executar_monitorado(jogo, ao_fim=ao_fim)
        if not resultado.get("ok"):
            raise ValueError(resultado.get("erro", "Não foi possível iniciar o jogo."))
        with closing(core.get_db(self.db_path)) as con:
            core.marcar_execucao(con, gid)
        resultado["aviso"] = preparo.get("aviso", "")
        return resultado

    def registrar_sessao(self, gid, horas):
        horas = float(horas)
        if not math.isfinite(horas) or horas < 0:
            raise ValueError("Informe um número de horas finito e não negativo.")
        if horas > 0:
            return self.alterar(lambda con: core.adicionar_horas(con, gid, horas))
        return {"ok": True}

    def encerrar_sessao(self, arquivo, horas):
        horas = float(horas)
        if not math.isfinite(horas) or horas <= 0:
            raise ValueError("Informe quantas horas você jogou (maior que zero).")
        with self._escrita:
            sessao = next((s for s in self.sessoes() if s.get("_arquivo") == arquivo), None)
            if sessao is None:
                raise ValueError("Esta sessão já foi encerrada ou não está mais disponível.")
            core.fazer_backup(self.db_path)
            marcador = Path(sessao["_arquivo"])
            gravar_atomico(core.BACKUP_DIR / "sessoes" / marcador.name, marcador.read_bytes())
            return core.encerrar_sessao_manual(str(marcador), horas, db_path=self.db_path)
