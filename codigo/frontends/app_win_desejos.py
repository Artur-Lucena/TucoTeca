#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TucoTeca classico: MixDesejos de App (verbatim do modulo original)."""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, ttk

import app_win as _W
import bib_core as core
from aparencia import ACC, TXT, BarraAcoes


class MixDesejos:
    def _recarregar_desejos(self):
        for w in self.grade.winfo_children():
            w.destroy()
        self.cards = []
        self._imgs_cards = []
        self._des_lista = None
        try:
            q = self.var_q.get().strip()
        except (tk.TclError, AttributeError):
            q = ""
        con = self._con()
        try:
            try:
                self.desejos = core.listar_desejos(con, q=q)
            except Exception:
                self.desejos = []
        finally:
            con.close()
        if self.des_sel is None or self.des_sel >= len(self.desejos):
            self.des_sel = 0 if self.desejos else None
        fr_btn = BarraAcoes(self.grade)
        fr_btn.pack(side="bottom", fill="x", pady=(8, 0))
        fr_btn.adicionar("Sincronizar", self.sincronizar_desejos_ui)
        fr_btn.adicionar("Adicionar…", self.adicionar_desejo_ui)
        fr_btn.adicionar("Na Steam", self.abrir_wishlist_json_na_steam)
        fr_btn.adicionar("Arquivo…", self.importar_desejos_arquivo_ui)
        fr_btn.adicionar("Buscar download", self.buscar_desejo_download)
        fr_btn.adicionar("Remover", self.excluir_desejo_selecionado)
        lst = _W._nova_grade_tv(self.grade, ("Desejo", "Steam"))
        lst.pack(fill="both", expand=True)
        _W._com_rolagem(lst)
        _W._tv_por(lst, [(d.get("titulo", "?"), f"appid {d.get('appid', '?')}")
                      for d in self.desejos])
        _W._tv_marcar(lst, self.des_sel)
        lst.bind("<<TreeviewSelect>>", self._ao_sel_desejo)
        lst.bind("<Double-Button-1>",
                 lambda _e: self.buscar_desejo_download())
        self._des_lista = lst
        n = len(self.desejos)
        try:
            conta = core.steam_principal().get("persona") or "Steam"
            self.lbl_cont.configure(text=f"{n} desejo(s) · wishlist {conta}")
        except tk.TclError:
            pass
        if n == 0:
            self.lbl_vazio.configure(
                text="Vazio — ➕ Adicionar… busca o jogo na Steam.")
            self.lbl_vazio.pack(anchor="w", padx=14)
        else:
            self.lbl_vazio.pack_forget()
        self.mostrar_detalhe()
    def _ao_sel_desejo(self, _e=None):
        i = _W._tv_sel(self._des_lista)
        if i is None:
            return
        self.des_sel = i
        self.mostrar_detalhe()
    def _desejo_sel(self):
        if not self._em_desejos() or self.des_sel is None \
                or self.des_sel >= len(self.desejos):
            return None
        return self.desejos[self.des_sel]
    def sincronizar_desejos_ui(self):
        """Lê a wishlist e espelha no Hub (thread, com backup).

        Uma resposta indisponível ou parcial não substitui a lista local.
        """
        prog = tk.Toplevel(self.root)
        _W._titulo_escuro(prog)
        prog.title("Sincronizando desejos…")
        prog.transient(self.root)
        ttk.Label(prog, text="Lendo wishlist Steam…").pack(padx=24, pady=20)
        try:
            prog.update()
        except tk.TclError:
            return

        def trabalho():
            try:
                conta = core.steam_principal()
                if not conta:
                    res = {"novos": 0, "atualizados": 0, "removidos": 0,
                           "erros": ["conta Steam não achada neste PC"]}
                else:
                    leitura = core.ler_wishlist(conta["steamid"])
                    if leitura["erros"]:
                        res = {"novos": 0, "atualizados": 0, "removidos": 0,
                               "erros": leitura["erros"]}
                    else:
                        self._backup_pre_import()
                        con = self._con()
                        try:
                            res = core.sincronizar_desejos(con, leitura["itens"])
                            res["erros"] = leitura["erros"]
                        finally:
                            con.close()
            except Exception as e:
                res = {"novos": 0, "atualizados": 0, "removidos": 0,
                       "erros": [str(e)]}

            def fim(res=res):
                try:
                    prog.destroy()
                except tk.TclError:
                    pass
                if self._em_desejos():
                    try:
                        self.recarregar()
                    except tk.TclError:
                        pass
                detalhe = (f"{res['novos']} novo(s), {res['atualizados']} "
                           f"atualizado(s), {res['removidos']} removido(s)")
                if res["erros"]:
                    _W.messagebox.showwarning("Desejos", "\n".join(res["erros"]))
                else:
                    _W.messagebox.showinfo("Desejos", detalhe)
            self._depois(lambda: fim())

        threading.Thread(target=trabalho, daemon=True).start()
    def adicionar_desejo_ui(self):
        """➕ Adicionar: busca o título na loja pública e grava o escolhido."""
        win = tk.Toplevel(self.root)
        _W._titulo_escuro(win)
        win.title("Adicionar desejo")
        win.transient(self.root)
        fr = ttk.Frame(win, padding=12)
        fr.pack(fill="both", expand=True)
        var = tk.StringVar()
        ent = ttk.Entry(fr, textvariable=var, width=40)
        ent.pack(fill="x")
        lbl = ttk.Label(fr, text="Digite e busque.", style="Mut.TLabel")
        lbl.pack(anchor="w", pady=(4, 6))
        lst = tk.Listbox(fr, selectmode="single", width=52, height=8,
                         bg="#0b0d12", fg=TXT, selectbackground=ACC,
                         font=("Segoe UI", 11))
        lst.pack(fill="both", expand=True)
        _W._com_rolagem(lst)
        achados: list[dict] = []

        def estado(txt):
            self._depois(lambda: lbl.configure(text=txt))

        def buscar():
            termo = var.get().strip()
            if not termo:
                return
            estado(f"Buscando '{termo}'…")

            def trabalho(termo_fx=termo):
                try:
                    res = core.buscar_jogos_steam(termo_fx)
                except Exception as e:
                    res = {"itens": [], "erros": [str(e)]}

                def fim(res=res):
                    if not win.winfo_exists():
                        return
                    achados.clear()
                    achados.extend(res.get("itens") or [])
                    lst.delete(0, "end")
                    for it in achados:
                        lst.insert("end", it["titulo"])
                    if res.get("erros"):
                        estado(f"Falha: {res['erros'][0]}")
                    else:
                        estado(f"{len(achados)} resultado(s).")
                self._depois(fim)
            threading.Thread(target=trabalho, daemon=True).start()

        def adicionar():
            sel = lst.curselection()
            if not sel or sel[0] >= len(achados):
                _W.messagebox.showinfo("Desejos", "Busque e escolha um jogo.")
                return
            it = achados[sel[0]]
            con = self._con()
            try:
                self._backup_pre_import()
                core.adicionar_desejo(con, it["appid"], it["titulo"])
            except (ValueError, LookupError) as e:
                _W.messagebox.showwarning("Desejos", f"falha: {e}")
                return
            except Exception as e:
                core.log_erro("adicionar-desejo", f"{type(e).__name__}: {e}")
                _W.messagebox.showwarning("Desejos", f"falha: {e}")
                return
            finally:
                con.close()
            win.destroy()
            self.recarregar()
            self._aviso_barra(f"Desejo '{it['titulo']}' ✓")

        ent.bind("<Return>", lambda _e: buscar())
        lin = ttk.Frame(fr)
        lin.pack(fill="x", pady=(8, 0))
        ttk.Button(lin, text="🔎 Buscar", command=buscar).pack(side="left")
        ttk.Button(lin, text="➕ Adicionar",
                   command=adicionar).pack(side="left", padx=6)
        ttk.Button(lin, text="Fechar",
                   command=win.destroy).pack(side="right")
    def abrir_wishlist_json_na_steam(self):
        """Abre tua wishlist no navegador (conferir) — importar é por ➕/📄."""
        conta = core.steam_principal()
        if not conta:
            _W.messagebox.showinfo(
                "Desejos", "Conta Steam não achada neste PC.")
            return
        url = ("https://store.steampowered.com/wishlist/profiles/"
               f"{conta['steamid']}/")
        res = core.abrir_url(url)
        if not res.get("ok"):
            _W.messagebox.showwarning(
                "Desejos",
                f"Navegador não abriu ({res.get('erro', 'falha')}).\n"
                f"Cole no navegador logado:\n{url}")
            return
        _W.messagebox.showinfo(
            "Desejos",
            "Confira a lista no navegador.\n"
            "P/ trazer p/ cá: ➕ Adicionar… (busca na loja) ou\n"
            "📄 Arquivo… (JSON do wishlistdata).")
    def importar_desejos_arquivo_ui(self):
        """Espelha wishlist de um wishlistdata/?p=N salvo (Steam pede login)."""
        caminho = filedialog.askopenfilename(
            title="Wishlist salva (JSON)",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")])
        if not caminho:
            return
        leitura = core.ler_wishlist_arquivo(caminho)
        if leitura["erros"] and not leitura["itens"]:
            _W.messagebox.showerror("Desejos", leitura["erros"][0])
            return
        self._backup_pre_import()
        con = self._con()
        try:
            res = core.sincronizar_desejos(con, leitura["itens"])
        except Exception as e:
            _W.messagebox.showerror("Desejos", f"falha: {e}")
            return
        finally:
            con.close()
        self.recarregar()
        _W.messagebox.showinfo(
            "Desejos",
            f"{res['novos']} novo(s), {res['atualizados']} atualizado(s), "
            f"{res['removidos']} removido(s)")
    def excluir_desejo_selecionado(self):
        d = self._desejo_sel()
        if d is None:
            return
        if not _W.messagebox.askokcancel(
                "Desejos", f"Tirar '{d['titulo']}' da lista?"):
            return
        con = self._con()
        try:
            core.remover_desejo(con, d["id"])
        except LookupError as e:
            _W.messagebox.showwarning("Desejos", str(e))
            return
        finally:
            con.close()
        self.des_sel = None
        self.recarregar()
    def buscar_desejo_download(self):
        """Abre os catálogos já buscando o título do desejo."""
        d = self._desejo_sel()
        if d is None:
            _W.messagebox.showinfo("Desejos", "Selecione um desejo na lista.")
            return
        opcoes = tk.Toplevel(self.root)
        _W._titulo_escuro(opcoes)
        opcoes.title(f"Baixar: {d['titulo'][:40]}")
        opcoes.transient(self.root)
        ttk.Label(opcoes, text=f"Buscar '{d['titulo']}' onde?",
                  wraplength=360).pack(padx=20, pady=(16, 8))
        fr = ttk.Frame(opcoes)
        fr.pack(pady=(0, 16))

        def ir(fonte):
            try:
                opcoes.destroy()
            except tk.TclError:
                pass
            self.dlg_catalogo(fonte, termo=d["titulo"])

        ttk.Button(fr, text="SteamRip",
                   command=lambda: ir("steamrip")).pack(side="left", padx=6)
        ttk.Button(fr, text="FitGirl",
                   command=lambda: ir("fitgirl")).pack(side="left", padx=6)
        ttk.Button(fr, text="Steam",
                   command=lambda: (opcoes.destroy(),
                                    core.abrir_url(
                                        f"https://store.steampowered.com/app/"
                                        f"{d['appid']}/"))).pack(side="left",
                                                                  padx=6)
