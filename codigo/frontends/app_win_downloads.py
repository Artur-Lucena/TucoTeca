#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TucoTeca classico: MixDownloads de App (verbatim do modulo original)."""
from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import app_win as _W
import bib_core as core
from aparencia import BarraAcoes


class MixDownloads:
    def _recarregar_downloads(self):
        for w in self.grade.winfo_children():
            w.destroy()
        self.cards = []
        self._imgs_cards = []
        self._dl_lista = None
        try:
            q = self.var_q.get().strip()
        except (tk.TclError, AttributeError):
            q = ""
        leitura = self._dl_snapshot
        self.dls = [t for t in leitura.get("torrents") or []
                    if not q or q.lower() in t["nome"].lower()]
        if self.dl_sel is None or self.dl_sel >= len(self.dls):
            self.dl_sel = 0 if self.dls else None
        fr_btn = BarraAcoes(self.grade)
        fr_btn.pack(side="bottom", fill="x", pady=(8, 0))
        fr_btn.adicionar("Atualizar", self.recarregar)
        fr_btn.adicionar("Iniciar cliente", self.iniciar_cliente_dl)
        fr_btn.adicionar("Pausar", lambda: self.controlar_dl("pausar"))
        fr_btn.adicionar("Retomar", lambda: self.controlar_dl("retomar"))
        fr_btn.adicionar("Verificar concluídos", self.verificar_concluidos_ui)
        fr_btn.adicionar("Abrir pasta", self.abrir_pasta_dl)
        lst = _W._nova_grade_tv(self.grade, ("Download", "Progresso"))
        lst.pack(fill="both", expand=True)
        _W._com_rolagem(lst)
        linhas_dl = []
        for t in self.dls:
            try:
                tam = (f"{core.formatar_tamanho(t['feito'])}/"
                       f"{core.formatar_tamanho(t['total'])}")
                marca = "✓ " if t["completo"] else ""
                estimativa = "~" if t.get("fonte_progresso") == "estimativa" else ""
                velocidade = f" · {core.formatar_tamanho(t['velocidade'])}/s" if t.get("velocidade") else ""
                linhas_dl.append((f"{marca}{t['nome']}",
                                  f"{estimativa}{t['pct']}% · {tam}{velocidade}"))
            except Exception:
                continue
        _W._tv_por(lst, linhas_dl)
        _W._tv_marcar(lst, self.dl_sel)
        lst.bind("<<TreeviewSelect>>", self._ao_sel_dl)
        lst.bind("<Double-Button-1>", lambda _e: self.abrir_pasta_dl())
        self._dl_lista = lst
        n = len(self.dls)
        try:
            api = leitura.get("fonte") == "api"
            self.lbl_cont.configure(text=f"{n} torrent(s) · " + (
                "qBittorrent conectado (API local)" if api else "histórico local do qBittorrent"))
        except tk.TclError:
            pass
        if n == 0:
            self.lbl_vazio.configure(
                text="Vazio — baixe um magnet (FitGirl) com o qBittorrent.")
            self.lbl_vazio.pack(anchor="w", padx=14)
        else:
            self.lbl_vazio.pack_forget()
        self.mostrar_detalhe()
    def iniciar_cliente_dl(self):
        self._acao_qbit_ui(lambda: core.qbit_iniciar(), "Iniciar qBittorrent")
    def controlar_dl(self, acao):
        t = self._dl_sel_atual()
        if t is None:
            return
        if t.get("fonte_progresso") != "api":
            _W.messagebox.showinfo("qBittorrent", "Este item pertence ao histórico local, não ao cliente conectado.")
            return
        self._acao_qbit_ui(lambda: core.qbit_controlar(t["hash"], acao), "qBittorrent")
    def _acao_qbit_ui(self, acao, contexto):
        def trabalho():
            try:
                res = acao()
            except Exception as e:
                res = {"ok": False, "erro": str(e)}

            def fim():
                if res.get("ok"):
                    self.recarregar()
                    self._aviso_barra(contexto + " ✓")
                else:
                    _W.messagebox.showwarning(contexto, res.get("erro", "falha"))
            self._depois(fim)
        threading.Thread(target=trabalho, daemon=True).start()
    def _vigiar_downloads(self):
        if self._mus_fechado:
            return
        self._dl_timer = self.root.after(3000, self._vigiar_downloads)
        if self._em_downloads():
            self._consultar_downloads()
    def _consultar_downloads(self):
        if self._dl_ocupado or self._mus_fechado:
            return
        self._dl_ocupado = True

        def trabalho():
            try:
                leitura = core.listar_torrents()
            except Exception as e:
                leitura = {"torrents": [], "erros": [str(e)]}

            def fim():
                self._dl_ocupado = False
                if self._mus_fechado:
                    return
                if leitura.get("erros"):
                    self._aviso_barra(leitura["erros"][0])
                    return
                mudou = leitura != self._dl_snapshot
                self._dl_snapshot = leitura
                if mudou and self._em_downloads():
                    self._recarregar_downloads()
            self._depois(fim)
        threading.Thread(target=trabalho, daemon=True).start()
    def _ao_sel_dl(self, _e=None):
        i = _W._tv_sel(self._dl_lista)
        if i is None:
            return
        self.dl_sel = i
        self.mostrar_detalhe()
    def _dl_sel_atual(self):
        if not self._em_downloads() or self.dl_sel is None \
                or self.dl_sel >= len(self.dls):
            return None
        return self.dls[self.dl_sel]
    def abrir_pasta_dl(self):
        t = self._dl_sel_atual()
        if t is None or not t.get("save_path"):
            _W.messagebox.showinfo("Downloads", "Selecione um download na lista.")
            return
        try:
            alvo = str(Path(t["save_path"]).parent) \
                if Path(t["save_path"]).is_file() \
                else str(Path(t["save_path"]))
        except (TypeError, ValueError):
            _W.messagebox.showwarning("Downloads", "Pasta inválida.")
            return
        if os.name == "nt":
            try:
                os.startfile(alvo)
            except OSError as e:
                _W.messagebox.showwarning("Downloads", f"falha: {e}")
        else:
            _W.messagebox.showinfo("Downloads", alvo)
    def verificar_concluidos_ui(self):
        """Importa p/ o Hub todo torrent 100% (thread, com backup)."""
        prontos = [t for t in self.dls if t.get("completo") and t.get("save_path")]
        if not prontos:
            _W.messagebox.showinfo("Downloads", "Nada 100% ainda.")
            return
        prog = tk.Toplevel(self.root)
        _W._titulo_escuro(prog)
        prog.title("Verificando concluídos…")
        prog.transient(self.root)
        ttk.Label(prog, text=f"Importando {len(prontos)} concluído(s)…").pack(
            padx=24, pady=20)
        try:
            prog.update()
        except tk.TclError:
            return

        def trabalho():
            self._backup_pre_import()
            con = self._con()
            linhas = []
            try:
                for t in prontos:
                    alvo = Path(t["save_path"])
                    try:
                        if not core.dentro_do_destino(alvo):
                            org = core.organizar_no_destino(alvo)
                            if org.get("ok"):
                                alvo = Path(org["path"])
                                linhas.append(f"'{t['nome']}': movido p/ Meus Jogos Locais/")
                            else:
                                linhas.append(f"'{t['nome']}': {org.get('erro')}")
                                continue
                        if alvo.is_file() and alvo.suffix.lower() in (
                                ".rar", ".zip", ".7z", ".iso"):
                            res = core.importar_repack(con, str(alvo))
                            if res.get("ok"):
                                linhas.append(f"'{res['titulo']}' ✓")
                            elif res.get("precisa_instalar"):
                                linhas.append(f"'{res.get('titulo', t['nome'])}': rode o setup")
                            else:
                                linhas.append(f"'{t['nome']}': {res.get('erro')}")
                        elif alvo.is_dir():
                            ach = core.achar_exe(alvo)
                            if ach.get("precisa_instalar"):
                                linhas.append(f"'{t['nome']}': instalador baixado; instale antes de importar")
                                continue
                            _roots_u, itens, _info = core.preview_pasta([str(alvo)])
                            if not itens:
                                linhas.append(f"'{t['nome']}': sem jogo/importável")
                                continue
                            res = core.importar_lista(con, itens)
                            linhas.append(f"'{t['nome']}': +{res.get('novos', 0)}")
                        else:
                            linhas.append(f"'{t['nome']}': sumiu do disco")
                    except Exception as e:
                        linhas.append(f"'{t['nome']}': {e}")
            finally:
                try:
                    con.close()
                except Exception:
                    pass

            def fim(linhas=linhas):
                try:
                    prog.destroy()
                except tk.TclError:
                    pass
                try:
                    self.recarregar()
                except tk.TclError:
                    pass
                _W.messagebox.showinfo("Downloads", "\n".join(linhas[:12]))
            self._depois(fim)

        threading.Thread(target=self._thread_segura(
            trabalho, prog, "Verificar concluídos"), daemon=True).start()
