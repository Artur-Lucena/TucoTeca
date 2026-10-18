"""Nucleo do ServicoBiblioteca: ciclo de vida, biblioteca e colecao."""
from __future__ import annotations

import threading
from contextlib import closing
from pathlib import Path

import bib_core as core
from bib_nucleo import conquistas, spotify

from .integracoes import integracoes_padrao
from .sistema import busca_global, capa_url, resumo_sistema, saude_colecao


class MixNucleo:
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
        from bib_nucleo.preferencias_pessoais import aplicar_perfil
        jogos = aplicar_perfil(jogos)
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

    def salvar_observacoes(self, gid, texto):
        """Notas/diário do jogo (campo `observacoes`, sem migração)."""
        texto = str(texto or "")[:4000]
        return self.alterar(lambda con: core.atualizar_jogo(con, gid, {"observacoes": texto}))

    def excluir(self, categoria, ident):
        funcoes = {"jogos": core.excluir_jogo, "desejos": core.remover_desejo,
                   "musicas": core.excluir_musica,
                   "videos": core.excluir_video}
        if categoria not in funcoes:
            raise ValueError("Esta categoria não permite exclusão pela biblioteca.")
        if categoria == "musicas":
            # O arquivo de áudio é apagado junto; fica fora da lixeira (por design).
            return self.alterar(lambda con: funcoes["musicas"](con, int(ident)))

        def operacao(con):
            from bib_nucleo import lixeira
            recibo = lixeira.arquivar(con, categoria, int(ident))
            funcoes[categoria](con, int(ident))
            return {"ok": True, "desfazer": recibo}

        return self.alterar(operacao)

    def desfazer_exclusao(self):
        """Recria a última remoção arquivada na lixeira local."""
        from bib_nucleo import lixeira
        return self.alterar(lambda con: lixeira.restaurar_ultimo(con))

    def favorito(self, gid):
        with self._escrita:
            from bib_nucleo.preferencias_pessoais import (
                aplicar_perfil,
                ler_preferencias,
                salvar_favorito,
            )
            jogo = self.jogo(gid)
            novo = not aplicar_perfil([jogo])[0]["favorito"]
            if ler_preferencias()["ativo"] == "Tuco":
                self.salvar_jogo(gid, {"favorito": novo})
            salvar_favorito(jogo, novo)
            return {"ok": True}

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

    def exportar_colecao_para(self, pasta):
        """Pacote ZIP da coleção numa pasta escolhida (pendrive, nuvem, etc.)."""
        from datetime import datetime
        from pathlib import Path
        destino = Path(pasta) / f"tucoteca-{datetime.now():%Y%m%d-%H%M%S-%f}.zip"
        return core.exportar_pacote(destino, self.db_path)

    def estatisticas(self):
        from bib_nucleo.estatisticas import resumo_ano
        from bib_nucleo.preferencias_pessoais import ler_preferencias
        with closing(core.get_db(self.db_path)) as con:
            return resumo_ano(con, perfil=ler_preferencias()["ativo"])

    def disco_jogo(self, gid):
        from bib_nucleo.estatisticas import tamanho_pasta
        jogo = self.jogo(gid)
        exe = Path(core.traduzir_para_atual(jogo.get("executable_path", "")))
        if not exe.is_file():
            raise ValueError("Executável local não encontrado.")
        return tamanho_pasta(exe.parent)

    def buscar(self, termo, limite=12):
        snap = self.snapshot()
        return busca_global(snap["jogos"], snap["musicas"], snap["desejos"], [],
                            str(termo or ""), int(limite))

    def preferencias(self):
        from bib_nucleo.preferencias_pessoais import PERFIS, ler_preferencias
        dados = ler_preferencias()
        return {"ativo": dados["ativo"], "perfis": list(PERFIS), "atalhos": dados["atalhos"]}

    def trocar_perfil(self, nome):
        from bib_nucleo import preferencias_pessoais as prefs
        prefs.trocar_perfil(nome)
        return self.preferencias()

    _FILTROS = ("todos", "favoritos", "jogando", "PC", "3DS", "NDS", "pendencias")
    _ORDENS = ("titulo", "recentes", "horas")

    def filtro(self):
        """Filtro/ordenação da tela Jogos do perfil ativo (com default seguro)."""
        from bib_nucleo.preferencias_pessoais import ler_preferencias
        dados = ler_preferencias()
        perfil = dados["perfis"][dados["ativo"]]
        filtro = perfil.get("filtro") if perfil.get("filtro") in self._FILTROS else "todos"
        ordem = perfil.get("ordem") if perfil.get("ordem") in self._ORDENS else "titulo"
        return {"filtro": filtro, "ordem": ordem}

    def salvar_filtro(self, filtro, ordem):
        from bib_nucleo import preferencias_pessoais as prefs
        prefs.salvar_filtro(filtro, ordem)
        return self.filtro()

    def lixeira(self):
        """Estado do desfazer: recibo mais recente ainda restaurável."""
        from bib_nucleo import lixeira as lixeira_nucleo
        recibo = lixeira_nucleo.ultima()
        if not recibo:
            return {"disponivel": False, "titulo": "", "tipo": ""}
        return {"disponivel": True, "titulo": recibo.get("titulo", ""),
                "tipo": recibo.get("tipo", "")}


__all__ = ["MixNucleo"]
