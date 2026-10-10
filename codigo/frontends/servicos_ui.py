"""Contratos da interface desktop, independentes de Qt e de widgets.

Adaptadores retornam dados simples. Cada operação possui sua conexão SQLite;
o frontend escolhe a thread e apresenta erros. Integrações são registradas
explicitamente: instalar um serviço não implica executar plugins arbitrários.
"""
from __future__ import annotations

import threading
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import bib_core as core


@dataclass(frozen=True)
class Integracao:
    chave: str
    nome: str
    descricao: str
    tipo: str
    inicial: str
    cor: str
    buscar: Callable | None = None

    def apresentar(self):
        return {k: v for k, v in asdict(self).items() if k != "buscar"}


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
    ):
        registro.registrar(item)
    return registro


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
    except Exception:
        backup = "backup?"
    try:
        uso = shutil.disk_usage(core.HOME_DIR)
        livre_gb = round(uso.free / 1024 ** 3, 1)
        total_gb = round(uso.total / 1024 ** 3)
    except Exception:
        livre_gb, total_gb = 0, 0
    return {"jogos": len(jogos), "musicas": len(musicas), "desejos": len(desejos),
            "downloads": len(downloads or []), "pendentes": pendentes, "backup": backup,
            "disco_livre_gb": livre_gb, "disco_total_gb": total_gb,
            "recentes": [dict(r) for r in recentes]}


def saude_colecao(jogos, limite=8):
    """QoL 1.0: exe/ROM ausentes por jogo, sem I/O além do diagnóstico local."""
    problemas = []
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
            problemas.append({"id": j["id"], "titulo": j["titulo"], "motivo": ", ".join(motivos)})
            if len(problemas) >= limite:
                break
    return {"total": len(jogos), "problemas": problemas, "ok": len(jogos) - len(problemas)}


def busca_global(jogos, musicas, desejos, downloads, termo, limite=12):
    """Paleta de comandos OS: filtra coleção em memória, sem I/O. Retorna DTOs."""
    palavras = (termo or "").casefold().split()
    if not palavras:
        return []
    def casa(item, campos):
        texto = " ".join(str(item.get(k) or "") for k in campos).casefold()
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

    def snapshot(self):
        with closing(core.get_db(self.db_path)) as con:
            jogos = core.listar_jogos(con)
            musicas = core.listar_musicas(con)
            desejos = core.listar_desejos(con)
        for j in jogos:
            j.update(capa_url=capa_url(j.get("capa")), plataforma=core.plataforma_jogo(j))
        for m in musicas:
            m["capa_url"] = capa_url(m.get("musica_capa"))
        return {"jogos": jogos, "musicas": musicas, "desejos": desejos,
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

    def salvar_jogo(self, gid, dados):
        permitido = {"titulo", "executable_path", "launch_options", "status", "nota",
                     "etiquetas", "favorito", "observacoes"}
        dados = {k: v for k, v in (dados or {}).items() if k in permitido}
        if "nota" in dados and (dados["nota"] == "" or dados["nota"] is None):
            dados["nota"] = None
        return self.alterar(lambda con: core.atualizar_jogo(con, gid, dados) if gid
                            else core.criar_jogo(con, dados))

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
                   "musicas": core.excluir_musica}
        if categoria not in funcoes:
            raise ValueError("Esta categoria não permite exclusão pela biblioteca.")
        return self.alterar(lambda con: funcoes[categoria](con, int(ident)))

    def importar_musicas(self, pasta):
        # Capas remotas não são buscadas implicitamente nesta importação local.
        return self.alterar(lambda con: core.importar_musicas(con, pasta, capa_auto=False))

    def adicionar_desejo(self, appid, titulo):
        return self.alterar(lambda con: core.adicionar_desejo(con, appid, titulo))

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
        if horas > 0:
            with closing(core.get_db(self.db_path)) as con:
                return core.adicionar_horas(con, gid, horas)
        return {"ok": True}
