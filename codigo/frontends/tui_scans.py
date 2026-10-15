#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TucoTeca terminal: MixScans de Tui (verbatim do modulo original)."""
from __future__ import annotations

import json
from pathlib import Path

import bib_core as core
from late import ModuloTardio

_T = ModuloTardio("app_tui")


class MixScans:
    def tela_prev(self, titulo: str, itens: list[dict]):
        if not itens:
            self.msg = "Nada encontrado."
            return
        s = self.stdscr
        marcados = {i for i, it in enumerate(itens) if it.get("score", 0) >= 0.3}
        cur = 0
        while True:
            s.erase()
            rows, cols = s.getmaxyx()
            if rows < 4 or cols < 10:
                try:
                    s.addnstr(0, 0, "Terminal pequeno demais (min 10x4).", max(1, cols - 1))
                    s.refresh()
                    s.getch()
                except Exception:
                    pass
                return
            larg = max(1, cols - 1)
            s.addnstr(0, 0, f"{titulo} — Espaço marca · i importa · q volta"[:larg],
                      larg, self.cor["head"] | self.abold)
            area = rows - 2
            top = max(0, min(cur - area + 1, max(0, len(itens) - area)))
            if cur < top:
                top = cur
            for i in range(area):
                idx = top + i
                if idx >= len(itens):
                    break
                it = itens[idx]
                chk = "[x]" if idx in marcados else "[ ]"
                bola = "●" if it.get("exe_existe") else "○"
                tag = f" [{it['regiao']}]" if it.get("regiao") else ""
                shop = f" · {it['shop']}" if it.get("shop") else ""
                linha = f"{chk} {bola} [{it.get('score', 0):.2f}] {it['titulo']}{tag}{shop} ({it.get('fonte') or it['origem']})"
                linha = linha.ljust(larg)[:larg]
                if idx == cur:
                    attr = self.cor["acc"] | self.abold
                elif it.get("score", 0) >= 0.7:
                    attr = self.cor["ok"]
                elif it.get("score", 0) >= 0.3:
                    attr = self.cor["txt"]
                else:
                    attr = self.cor["ruim"]
                s.addnstr(1 + i, 0, linha, larg, attr)
            s.addnstr(rows - 1, 0, f"{len(marcados)} marcado(s) de {len(itens)}"[:larg],
                      larg, self.cor["mut"] | self.adim)
            s.refresh()
            ch = s.getch()
            if ch in (ord("q"), 27):
                return
            elif ch in (_T.curses.KEY_UP, ord("k")):
                cur = max(0, cur - 1)
            elif ch in (_T.curses.KEY_DOWN, ord("j")):
                cur = min(len(itens) - 1, cur + 1)
            elif ch == _T.curses.KEY_PPAGE:
                cur = max(0, cur - 10)
            elif ch == _T.curses.KEY_NPAGE:
                cur = min(len(itens) - 1, cur + 10)
            elif ch == ord(" "):
                if cur in marcados:
                    marcados.discard(cur)
                else:
                    marcados.add(cur)
            elif ch == ord("i"):
                if not marcados:
                    continue
                sel = [itens[i] for i in sorted(marcados)]
                self._backup_pre_import()
                con = self._con()
                try:
                    res = core.importar_lista(con, sel)
                finally:
                    con.close()
                self.msg = core.resumo_importacao(res).replace("\n", " · ")
                self.recarregar()
                return
    def _prev_disco(self):
        self.msg = "Lendo Hydra, lojas e programas (só leitura)..."
        self.desenhar()
        try:
            itens, info = core.ler_do_disco()
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        partes = [f"{f['fonte']}: {f['n']}" for f in info["fontes"]
                  if f["ok"] and f["n"]]
        falhas = [f"{f['fonte']}: {f.get('detalhe') or 'falha'}" for f in info["fontes"]
                  if not f["ok"]]
        sub = f"Disco: {len(itens)} achado(s) ({'; '.join(partes) or 'nada'})"
        if falhas:
            sub += f" [falhas: {'; '.join(falhas)}]"
        self.tela_prev(sub, itens)
    def _prev_pasta(self, roots):
        self.msg = "Varrendo (só leitura)..."
        self.desenhar()
        try:
            _ru, itens, info = core.preview_pasta(roots)
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        sub = f"Pasta: {len(itens)} achado(s)"
        if info.get("truncado"):
            sub += f" (PARCIAL: {info.get('vistos', 0)} vistos — refine a pasta)"
        if not info.get("emu"):
            sub += " [Azahar ausente: ROMs importam; instale com A]"
        self.tela_prev(sub, itens)
    def _importar_arquivo(self, arq: str):
        ana = core.analisar_arquivo(arq)
        tipo = ana["tipo"]
        if tipo == "pasta":
            self._prev_pasta([arq])
        elif tipo == "json":
            self.importar_json(arq)
        elif tipo == "pacote":
            self.importar_pacote(arq)
        elif tipo == "arquivo-jogo":
            self._backup_pre_import()
            con = self._con()
            try:
                res = core.importar_repack(con, arq)
            except Exception as e:
                res = {"ok": False, "erro": f"{type(e).__name__}: {e}"}
            finally:
                con.close()
            if not res.get("ok"):
                detalhe = res["erro"]
                if res.get("precisa_instalar"):
                    detalhe += " (rode o setup na pasta e importe a pasta.)"
                self.msg = detalhe
            elif res.get("novos"):
                self.msg = f"'{res['titulo']}' ✓ em {res['pasta']}"
                if res.get("capa_auto"):
                    self.msg += " + capa ✓"
                if res.get("capa_pendente"):
                    self.msg += " (sem capa: ajuste na GUI)."
            else:
                self.msg = "Já estava na biblioteca (nada novo)."
            self.recarregar()
        elif tipo in ("rom", "jogo"):
            if ana.get("aviso") and not self.confirmar(f"{ana['aviso']} Importar?"):
                return
            self._backup_pre_import()
            con = self._con()
            try:
                res = core.importar_lista(con, [ana["item"]])
            finally:
                con.close()
            if res["novos"]:
                self.msg = f"{ana['detalhe']} ✓"
            else:
                self.msg = "Já estava na biblioteca (nada novo)."
            self.recarregar()
        else:
            self.msg = ana["detalhe"] or "não suportado."
    def backup(self):
        try:
            res = core.fazer_backup(self.db_path)
            self.msg = f"Backup ok: {res['jogos']} jogo(s)"
        except Exception as e:
            self.msg = f"Backup falhou: {e}"
    def backup_saves(self):
        try:
            res = core.backup_saves_azahar()
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        if res.get("ok"):
            self.msg = f"Saves ok: {res['arquivos']} arquivo(s)"
        else:
            self.msg = f"Saves: {res.get('erro')}"
    def exportar_json(self):
        dest = self.perguntar("Exportar para (caminho .json): ")
        if not dest:
            return
        dest = dest.strip()
        try:
            res = core.exportar_json(dest, db_path=self.db_path)
        except Exception as e:
            self.msg = f"Falha ao gravar: {e}"
            return
        if not res.get("ok"):
            self.msg = f"Falha ao gravar: {res.get('erro')}"
            return
        self.msg = f"Exportados {res['jogos']} jogo(s)."
    def importar_json(self, arq: str | None = None):
        if not arq:
            arq = self.perguntar("Importar de (JSON ou pacote .zip): ")
            if not arq:
                return
            arq = arq.strip()
        if arq.lower().endswith(".zip") and core.eh_pacote_hub(arq):
            self.importar_pacote(arq)
            return
        if arq.lower().endswith(".zip"):
            self._importar_arquivo(arq)
            return
        try:
            dados = json.loads(Path(arq).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            self.msg = f"JSON inválido: {e}"
            return
        lista = dados if isinstance(dados, list) else dados.get("jogos") if isinstance(dados, dict) else None
        if not isinstance(lista, list):
            self.msg = "JSON deve ser lista ou {jogos:[...]}."
            return
        self._backup_pre_import()
        con = self._con()
        try:
            res = core.importar_lista(con, lista)
        finally:
            con.close()
        self.msg = core.resumo_importacao(res).replace("\n", " · ")
        self.recarregar()
    def exportar_pacote(self):
        dest = self.perguntar("Pacote (.zip) destino: ",
                              str(core.BACKUP_DIR / "biblioteca-pacote.zip"))
        if not dest:
            return
        try:
            res = core.exportar_pacote(dest.strip(), db_path=self.db_path,
                                       incluir_saves=True)
        except Exception as e:
            self.msg = f"Pacote falhou: {e}"
            return
        if not res.get("ok"):
            self.msg = f"Pacote: {res.get('erro')}"
            return
        kb = res["bytes"] // 1024
        self.msg = (f"Pacote: {res['jogos']} jogo(s), {res['arquivos']} arq, "
                    f"{kb} KB{' +saves' if res['inclui_saves'] else ''}.")
    def importar_pacote(self, arq: str):
        try:
            res = core.importar_pacote(
                arq, db_path=self.db_path,
                restaurar_saves=self.confirmar("Restaurar os saves do pacote?"))
        except Exception as e:
            self.msg = f"Pacote falhou: {e}"
            return
        if not res.get("ok"):
            self.msg = f"Pacote: {res.get('erro')}"
            return
        self.msg = (core.resumo_importacao(res).replace("\n", " · ") + " · " +
                    f"capas {res['capas']} · presets {res['presets']} · "
                    f"saves {res['saves']}")
        self.recarregar()
    def atualizar_azahar(self):
        self.atualizar_emu("azahar")
    def atualizar_desmume(self):
        self.atualizar_emu("desmume")
    def atualizar_emu(self, chave: str):
        try:
            prov = core.provedores()[chave]
        except KeyError:
            self.msg = f"Provider '{chave}' desconhecido."
            return
        nome = prov["nome"]
        self.msg = "Consultando releases..."
        self.desenhar()
        try:
            info = prov["release_info"]()
        except Exception as e:
            self.msg = f"{nome}: falha de rede ({type(e).__name__}: {e})"
            return
        if info.get("erro"):
            self.msg = f"{nome}: {info['erro']}"
            return
        local, tag = prov["versao_local"](), info.get("tag") or "?"
        if local and local == tag:
            self.msg = f"{nome} já está na {tag} ✓"
            return
        mb = round((info.get("size") or 0) / 1048576)
        if not self.confirmar(f"{nome} {local or '?'} -> {tag} (~{mb} MB). Baixar?"):
            return
        self.msg = "Baixando e instalando (aguarde)..."
        self.desenhar()
        try:
            res = prov["instalar"](info, progresso=self._prog_azahar)
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        if res.get("ok"):
            self.msg = f"{res.get('tag')} instalado ✓"
        else:
            self.msg = f"Falha: {res.get('erro')}"
        self.recarregar()
    def _prog_azahar(self, feito, total):
        self.msg = f"Baixando... {feito // 1048576} MB"
        if total:
            self.msg += f" / {total // 1048576} MB"
        try:
            self.desenhar()
        except Exception:
            pass
    def rodar(self):
        s = self.stdscr
        try:
            s.timeout(500)  # getch não-bloqueante: sessões aplicam sem tecla
        except Exception:
            pass
        self._verificar_pendencias_inicio()
        while True:
            self._vigiar_player()
            self._aplicar_sessoes()
            self.desenhar()
            try:
                ch = s.getch()
            except Exception:
                ch = -1
            if ch == -1:
                continue  # timeout: só drenou sessões e redesenhou
            if ch in (ord("q"),):
                antes = self.msg  # desenhar consome; guarda p/ exibir após sair
                self._aplicar_sessoes()  # vigia pode ter encerrado no último instante
                self.msg_final = self.msg or antes
                return
            elif ch in (_T.curses.KEY_DOWN, ord("j")):
                self.cur = min(len(self.jogos) - 1, self.cur + 1) if self.jogos else 0
            elif ch in (_T.curses.KEY_UP, ord("k")):
                self.cur = max(0, self.cur - 1)
            elif ch == _T.curses.KEY_NPAGE:
                self.cur = min(len(self.jogos) - 1, self.cur + 10) if self.jogos else 0
            elif ch == _T.curses.KEY_PPAGE:
                self.cur = max(0, self.cur - 10)
            elif ch == 27:
                if self.menu_principal():
                    antes = self.msg
                    self._aplicar_sessoes()
                    self.msg_final = self.msg or antes
                    return
            elif ch in (_T.curses.KEY_ENTER, 10, 13):
                self.menu_jogo()

