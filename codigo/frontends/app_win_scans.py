#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TucoTeca classico: MixScans de App (verbatim do modulo original)."""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

import app_win as _W
import bib_core as core
from aparencia import ACC, BG, TXT


class MixScans:
    def importar_unificado(self):
        dlg = tk.Toplevel(self.root)
        _W._titulo_escuro(dlg)
        dlg.title("Importar")
        dlg.configure(bg=BG)
        dlg.transient(self.root)
        dlg.grab_set()
        ttk.Label(dlg, wraplength=420, justify="left", text=(
            "Escolha uma PASTA (varre jogos de PC + ROMs de uma vez), um "
            "ARQUIVO (exe, ROM, JSON, pacote .zip ou repack .rar/.7z/.iso) ou LEIA DO DISCO "
            "(Hydra + Steam + Epic + GOG + Riot + programas instalados).\n"
            "Repack extrai p/ Meus Jogos Locais, organiza, acha o exe e importa sozinho; "
            "ROMs são ligadas no emulador sozinhas; sem emulador, importam "
            "mesmo assim e o play orienta.")).pack(anchor="w", padx=14, pady=12)

        def de_pasta():
            pasta = filedialog.askdirectory(title="Pasta para varrer", parent=dlg)
            if not pasta:
                return
            dlg.destroy()
            self._importar_pasta(pasta)

        def de_arquivo():
            arq = filedialog.askopenfilename(
                title="Arquivo para importar", parent=dlg,
                filetypes=[("Suportados",
                            "*.exe *.lnk *.bat *.cmd *.3ds *.3dsx *.cci *.cxi "
                            "*.elf *.app *.axf *.nds *.dsi *.json *.zip *.rar *.7z *.iso"),
                           ("Repacks", "*.zip *.rar *.7z *.iso"),
                           ("Executáveis", "*.exe *.lnk *.bat *.cmd"),
                           ("ROMs 3DS", "*.3ds *.3dsx *.cci *.cxi *.elf *.app *.axf"),
                           ("ROMs NDS", "*.nds *.dsi"),
                           ("JSON", "*.json"), ("Pacote", "*.zip"),
                           ("Todos", "*.*")])
            if not arq:
                return
            dlg.destroy()
            self._importar_arquivo(arq)

        def do_disco():
            dlg.destroy()
            self._ler_do_disco()

        for rotulo, cmd in (("📁 Escolher pasta…", de_pasta),
                            ("📄 Escolher arquivo…", de_arquivo),
                            ("💽 Ler do disco", do_disco)):
            ttk.Button(dlg, text=rotulo, command=cmd).pack(fill="x", padx=14, pady=3)
        ttk.Button(dlg, text="Cancelar", command=dlg.destroy).pack(pady=(3, 12))
    def sanear_pasta_ui(self):
        """Acha a pasta do jogo, limpa installers/sobras e oferece importar."""
        pasta = filedialog.askdirectory(title="Pasta do jogo p/ sanear")
        if not pasta:
            return
        prog = tk.Toplevel(self.root)
        prog.title("Organizando pasta…")
        prog.transient(self.root)
        ttk.Label(prog, text="Localizando o jogo e verificando sobras…").pack(padx=24, pady=20)

        def trabalho():
            self._backup_pre_import()
            res = core.sanear_pasta(pasta)

            def fim():
                if not prog.winfo_exists():
                    return
                prog.destroy()
                if not res.get("ok"):
                    _W.messagebox.showwarning("Sanear", res.get("erro", "falha"))
                    return
                detalhe = f"Pasta: {res['pasta']}"
                if res.get("avisos"):
                    detalhe += "\n" + "\n".join(res["avisos"][:6])
                if res.get("precisa_instalar"):
                    _W.messagebox.showinfo("Sanear", detalhe + "\nSó há instalador — rode o setup antes.")
                    return
                detalhe += f"\nExe: {Path(res['exe']).name}"
                if _W.messagebox.askyesno("Sanear", detalhe + "\n\nImportar para o Hub?"):
                    self._importar_pasta(res["pasta"])
            self._depois(fim)
        threading.Thread(target=self._thread_segura(trabalho, prog, "Sanear"), daemon=True).start()
    def _importar_pasta(self, pasta: str):
        prog = tk.Toplevel(self.root)
        _W._titulo_escuro(prog)
        prog.title("Importar pasta")
        prog.transient(self.root)
        ttk.Label(prog, text="Varrendo pasta (só leitura)...").pack(padx=24, pady=24)
        try:
            prog.update()
        except tk.TclError:
            return

        def trabalho():
            def na_ui(fn):
                self._depois(fn)

            def falhou(e):
                core.log_erro("importar-pasta", str(e))
                try:
                    prog.destroy()
                except tk.TclError:
                    pass
                _W.messagebox.showerror("Importar pasta", f"falha na varredura: {e}")

            try:
                _roots_u, itens, info = core.preview_pasta([pasta])
            except Exception as e:
                msg_erro = f"{type(e).__name__}: {e}"  # e morre no fim do except; string não
                na_ui(lambda m=msg_erro: falhou(m))
                return

            def pronto():
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                sub = f"{len(itens)} achado(s)."
                if info.get("truncado"):
                    sub += " LISTA PARCIAL (teto de varredura — refine a pasta)."
                if not info.get("emu"):
                    sub += (" ROMs importam sem executável (Azahar ausente) — "
                            "instale com 'Atualizar Azahar'.")
                self._dlg_prev("Preview — Pasta",
                               sub + " Pré-marcados: score ≥ 0.3.", itens)
                if info.get("truncado"):
                    try:
                        _W.messagebox.showwarning(
                            "Importar pasta",
                            f"Lista parcial: {info.get('vistos', 0)} arquivos vistos, "
                            "teto estourou. Refine a pasta ou defina BIBLIOTECA_SCAN_ROOTS.")
                    except Exception:
                        pass
            na_ui(pronto)

        threading.Thread(target=self._thread_segura(trabalho, prog, "Importar pasta"), daemon=True).start()
    def _importar_arquivo(self, arq: str):
        ana = core.analisar_arquivo(arq)
        tipo = ana["tipo"]
        if tipo == "pasta":
            self._importar_pasta(arq)
        elif tipo == "json":
            self.importar_json(arq)
        elif tipo == "pacote":
            self.importar_pacote(arq)
        elif tipo == "arquivo-jogo":
            self._importar_repack(arq)
        elif tipo in ("rom", "jogo"):
            if ana.get("aviso") and not _W.messagebox.askyesno("Importar", f"{ana['aviso']}\n\nImportar mesmo assim?"):
                return
            self._backup_pre_import()
            con = self._con()
            try:
                res = core.importar_lista(con, [ana["item"]])
            finally:
                con.close()
            self.sel = None
            self.recarregar()
            if res["novos"]:
                _W.messagebox.showinfo("Importar", f"{ana['detalhe']} ✓")
            else:
                _W.messagebox.showinfo("Importar", "Já estava na biblioteca (nada novo).")
        else:
            _W.messagebox.showwarning("Importar", ana["detalhe"] or "não suportado.")
    def _importar_repack(self, arq: str):
        prog = tk.Toplevel(self.root)
        _W._titulo_escuro(prog)
        prog.title("Importar repack")
        prog.transient(self.root)
        ttk.Label(prog, text="Extraindo p/ Meus Jogos Locais e importando...").pack(
            padx=24, pady=24)
        try:
            prog.update()
        except tk.TclError:
            return

        def trabalho():
            def na_ui(fn):
                self._depois(fn)

            def falhou(msg):
                core.log_erro("importar-repack", msg)
                try:
                    prog.destroy()
                except tk.TclError:
                    pass
                _W.messagebox.showerror("Importar repack", msg)

            con = None
            try:
                con = self._con()
                self._backup_pre_import()
                res = core.importar_repack(con, arq)
            except Exception as e:
                msg_erro = f"{type(e).__name__}: {e}"
                na_ui(lambda m=msg_erro: falhou(m))
                return
            finally:
                try:
                    if con is not None:
                        con.close()
                except Exception:
                    pass

            def pronto(res=res):
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                if not res.get("ok"):
                    detalhe = res["erro"]
                    if res.get("precisa_instalar"):
                        detalhe += "\n(rode o setup dentro da pasta e importe a pasta.)"
                    _W.messagebox.showwarning("Importar repack", detalhe)
                    return
                self.sel = None
                self.recarregar()
                detalhe = f"'{res['titulo']}' ✓\n{res['exe']}"
                if res.get("avisos"):
                    detalhe += "\n" + " ".join(res["avisos"])
                if res.get("capa_pendente"):
                    detalhe += "\nSem capa: ajuste no diálogo do jogo."
                if not res.get("apagou_arquivo"):
                    detalhe += "\n(archive original mantido — apague à mão.)"
                _W.messagebox.showinfo("Importar repack", detalhe)
            na_ui(pronto)
        threading.Thread(target=self._thread_segura(trabalho, prog, "Importar repack"), daemon=True).start()
    def _dlg_prev(self, titulo: str, sub: str, itens: list[dict]):
        dlg = tk.Toplevel(self.root)
        _W._titulo_escuro(dlg)
        dlg.title(titulo)
        dlg.configure(bg=BG)
        dlg.geometry("700x480")
        dlg.transient(self.root)
        dlg.grab_set()
        ttk.Label(dlg, text=sub, wraplength=660).pack(anchor="w", padx=10, pady=6)
        lb = tk.Listbox(dlg, selectmode="multiple", bg="#0b0d12", fg=TXT,
                        selectbackground=ACC, font=("Segoe UI", 10))
        lb.pack(fill="both", expand=True, padx=10)
        _W._com_rolagem(lb)
        for i, it in enumerate(itens):
            bola = "●" if it.get("exe_existe") else "○"
            tag = f" [{it['regiao']}]" if it.get("regiao") else ""
            linha = (f"{bola} [{it.get('score', 0):.2f}] {it['titulo']}{tag} — {it.get('fonte') or it['origem']}"
                     + (f" · {it['shop']}" if it.get("shop") else ""))
            if len(linha) > 120:
                linha = linha[:119] + "…"
            lb.insert("end", linha)
            if it.get("score", 0) >= 0.3:
                lb.selection_set(i)

        def importar():
            idx = list(lb.curselection())
            if not idx:
                _W.messagebox.showinfo(titulo, "Nada selecionado.")
                return
            sel = [itens[i] for i in idx]
            self._backup_pre_import()
            con = self._con()
            try:
                res = core.importar_lista(con, sel)
            finally:
                con.close()
            dlg.destroy()
            self.sel = None
            self.recarregar()
            _W.messagebox.showinfo(titulo, core.resumo_importacao(res))

        ttk.Button(dlg, text="Importar selecionados", command=importar,
                   style="Accent.TButton").pack(pady=8)
    def _backup_pre_import(self):
        """Backup silencioso antes de importar (nunca bloqueia o import)."""
        core.backup_pre_import(self.db_path)
    def _ler_do_disco(self):
        prog = tk.Toplevel(self.root)
        _W._titulo_escuro(prog)
        prog.title("Ler do disco")
        prog.transient(self.root)
        ttk.Label(prog, text="Lendo Hydra, lojas e programas (só leitura)...").pack(
            padx=24, pady=24)
        try:
            prog.update()
        except tk.TclError:
            return

        def trabalho():
            def na_ui(fn):
                self._depois(fn)

            def falhou(e):
                core.log_erro("ler-do-disco", str(e))
                try:
                    prog.destroy()
                except tk.TclError:
                    pass
                _W.messagebox.showerror("Ler do disco", f"falha na leitura: {e}")

            try:
                itens, info = core.ler_do_disco()
            except Exception as e:
                msg_erro = f"{type(e).__name__}: {e}"  # e morre no fim do except; string não
                na_ui(lambda m=msg_erro: falhou(m))
                return

            def pronto():
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                partes = []
                for f in info["fontes"]:
                    if f["ok"] and f["n"]:
                        partes.append(f"{f['fonte']}: {f['n']}")
                    elif not f["ok"]:
                        partes.append(f"{f['fonte']}: falha")
                sub = f"{len(itens)} achado(s) ({'; '.join(partes) or 'nada'})."
                self._dlg_prev("Preview — Disco",
                               sub + " Pré-marcados: score ≥ 0.3.", itens)
            na_ui(pronto)

        threading.Thread(target=self._thread_segura(trabalho, prog, "Ler do disco"), daemon=True).start()
    def backup_saves(self):
        try:
            res = core.backup_saves_azahar()
        except Exception as e:
            _W.messagebox.showerror("Saves 3DS", f"falha: {e}")
            return
        if res.get("ok"):
            _W.messagebox.showinfo("Saves 3DS",
                                f"{res['arquivos']} arquivo(s)\n{res['arquivo']}")
        else:
            _W.messagebox.showwarning("Saves 3DS", res.get("erro", "falha"))
