#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TucoTeca classico: MixSistema de App (verbatim do modulo original)."""
from __future__ import annotations

import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, simpledialog, ttk

import app_win as _W
import bib_core as core
from aparencia import ACC, BG, TXT


class MixSistema:
    def abrir_configuracoes(self):
        """Técnico fora da tela inicial: backup, sessão, emuladores, JSON."""
        dlg = tk.Toplevel(self.root)
        _W._titulo_escuro(dlg)
        dlg.title("⚙ Configurações")
        dlg.configure(bg=BG)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.minsize(420, 0)
        ttk.Label(dlg, text="Coisas técnicas — a biblioteca mora na tela inicial.",
                  style="Sec.TLabel",
                  font=("Segoe UI", 11, "italic")).pack(anchor="w", padx=14, pady=(12, 2))

        def secao(titulo):
            fr = ttk.LabelFrame(dlg, text=f"  {titulo}  ", style="Sec.TLabelframe")
            fr.pack(fill="x", padx=12, pady=(10, 0))
            fr.columnconfigure(0, weight=1)
            return fr

        fr_banco = secao("Banco")
        for rotulo, cmd in (("💾 Backup agora", self.backup),
                            ("💾 Saves 3DS", self.backup_saves),
                            ("⏱ Registrar sessão", self.registrar_sessao_manual),
                            ("💾 Exportar JSON…", self.exportar_json),
                            ("📦 Pacote…", self.exportar_pacote)):
            ttk.Button(fr_banco, text=rotulo, command=cmd).pack(
                fill="x", padx=4, pady=3)
        fr_emu = secao("Emuladores")
        for rotulo, cmd in (("⬇ Atualizar Azahar", self.atualizar_azahar),
                            ("⬇ Atualizar DeSmuME", self.atualizar_desmume)):
            ttk.Button(fr_emu, text=rotulo, command=cmd).pack(
                fill="x", padx=4, pady=3)
        try:
            ff_ok = "✓" if core.ffmpeg_pronto() else "✗"
            yt_ok = "✓" if core.ytdlp_pronto() else "✗"
        except Exception:
            ff_ok = yt_ok = "?"
        ttk.Label(fr_emu, text=f"áudio: ffmpeg {ff_ok} · yt-dlp {yt_ok}",
                  style="Sec.TLabel").pack(anchor="w", padx=4)
        ttk.Button(fr_emu, text="⬇ Dependências de áudio",
                   command=lambda: self.instalar_deps_audio()).pack(
                       fill="x", padx=4, pady=3)
        fr_mus = secao("Músicas")
        auto_capa = ("ligada" if core.capa_musica_auto() else "desligada")
        ttk.Label(fr_mus, text=f"capa automática: {auto_capa}"
                               " (BIBLIOTECA_CAPA_MUSICA_AUTO)",
                  style="Sec.TLabel").pack(anchor="w", padx=4)
        for rotulo, cmd in (("🎵 Músicas…", lambda: self._ir_aba_config(dlg)),
                            ("📥 Importar músicas…", self.importar_musicas),
                            ("⬇ Baixar capas faltantes",
                             self.baixar_capas_ui)):
            ttk.Button(fr_mus, text=rotulo, command=cmd).pack(
                fill="x", padx=4, pady=3)
        fr_ctl = secao("Controles")
        for rotulo, cmd in (("🎮 Controles…", self._janela_controles),):
            ttk.Button(fr_ctl, text=rotulo, command=cmd).pack(
                fill="x", padx=4, pady=3)
        ttk.Button(dlg, text="Fechar", command=dlg.destroy).pack(pady=14)
    def _ir_aba_config(self, dlg):
        """Config → aba 🎵 (a janela modal antiga virou a aba)."""
        try:
            dlg.destroy()
        except tk.TclError:
            pass
        for i, (rot, _s, _f) in enumerate(_W.NAV):
            if rot.startswith("🎵"):
                self._ir_nav(i)
                return
    def baixar_capas_ui(self):
        """Arte dos álbuns faltantes em thread (rede falhou = pendente)."""
        prog = tk.Toplevel(self.root)
        _W._titulo_escuro(prog)
        prog.title("Baixando capas…")
        prog.transient(self.root)
        ttk.Label(prog, text="Consultando iTunes…").pack(padx=24, pady=20)
        try:
            prog.update()
        except tk.TclError:
            return

        def trabalho():
            con = None
            try:
                con = self._con()
                res = core.baixar_capas_faltantes(con)
            except Exception as e:
                res = {"novas": 0, "pendentes": 0, "erros": [str(e)]}
            finally:
                try:
                    if con is not None:
                        con.close()
                except Exception:
                    pass

            def fim(res=res):
                try:
                    prog.destroy()
                except tk.TclError:
                    pass
                if self._em_musicas():
                    try:
                        self.recarregar()
                    except tk.TclError:
                        pass
                detalhe = (f"{res['novas']} capa(s), "
                           f"{res['pendentes']} pendente(s)")
                if res["erros"]:
                    detalhe += f"\n{res['erros'][0]}"
                _W.messagebox.showinfo("Capas", detalhe)
            self._depois(fim)
        threading.Thread(target=trabalho, daemon=True).start()
    def _janela_controles(self):
        win_ant = getattr(self, "_win_controles", None)
        try:
            if win_ant is not None and win_ant.winfo_exists():
                win_ant.lift()
                win_ant.focus_force()
                return
        except tk.TclError:
            pass
        win = tk.Toplevel(self.root)
        self._win_controles = win
        _W._titulo_escuro(win)
        win.title("Controles (feche o Azahar p/ aplicar)")
        win.transient(self.root)
        win.minsize(460, 360)
        filhas = []

        def fechar_tudo():
            for vw in list(filhas):
                try:
                    vw.destroy()
                except tk.TclError:
                    pass
            filhas.clear()
            try:
                win.destroy()
            except tk.TclError:
                pass
            self._win_controles = None
        win.protocol("WM_DELETE_WINDOW", fechar_tudo)
        fr = ttk.Frame(win, padding=12)
        fr.pack(fill="both", expand=True)
        try:
            pads = core.listar_controles()
        except Exception:
            pads = []
        txt_pads = "; ".join(
            f"{p.get('nome') or '?'}"
            f"{' [' + p['familia'] + ']' if p.get('familia') else ''}"
            for p in pads) or "nenhum controle"
        ttk.Label(fr, text=f"Pads: {txt_pads}", wraplength=460,
                  justify="left",
                  font=("Segoe UI", 11)).pack(anchor="w")
        lst = tk.Listbox(fr, selectmode="single", width=52, height=8,
                         bg="#0b0d12", fg=TXT, selectbackground=ACC,
                         font=("Segoe UI", 11))
        lst.pack(fill="both", expand=True, pady=(8, 0))
        _W._com_rolagem(lst)

        def redesenhar():
            try:
                nomes = core.listar_presets_controle()
            except Exception:
                nomes = []
            lst.delete(0, "end")
            for nome in nomes:
                lst.insert("end", nome)
            return nomes

        def selecionado():
            sel = lst.curselection()
            nomes = redesenhar()
            if not sel or sel[0] >= len(nomes):
                return ""
            return nomes[sel[0]]

        def fotografar():
            nome = simpledialog.askstring("Controles", "Nome do preset:",
                                          parent=win)
            if not nome:
                return
            try:
                r = core.fotografar_perfil(nome.strip())
            except Exception as e:
                _W.messagebox.showwarning("Controles", f"falha: {e}")
                return
            if not r.get("ok"):
                _W.messagebox.showwarning("Controles", r.get("erro", "falha"))
                return
            redesenhar()

        def aplicar():
            nome = selecionado()
            if not nome:
                return
            try:
                r = core.aplicar_preset_controle(nome)
            except Exception as e:
                _W.messagebox.showwarning("Controles", f"falha: {e}")
                return
            if not r.get("ok"):
                _W.messagebox.showwarning("Controles", r.get("erro", "falha"))
                return
            _W.messagebox.showinfo(
                "Controles",
                f"{r.get('chaves', 0)} binds no Azahar ✓")

        def gerar():
            tipos = sorted(core.NOMES_TIPO)
            win2 = tk.Toplevel(win)
            _W._titulo_escuro(win2)
            win2.title("Gerar mapa padrão")
            win2.transient(win)
            win2.grab_set()
            lb = tk.Listbox(win2, selectmode="single", width=40, height=6,
                            bg="#0b0d12", fg=TXT, selectbackground=ACC,
                            font=("Segoe UI", 11))
            lb.pack(fill="both", expand=True, padx=12, pady=12)
            _W._com_rolagem(lb)
            for t in tipos:
                lb.insert("end", f"{t} — {core.NOMES_TIPO[t]}")

            def ok():
                sel = lb.curselection()
                if not sel:
                    return
                tipo = tipos[sel[0]]
                guid, port, rot = "", 0, {}
                try:
                    det = core.detectar_sdl()
                    if det:
                        guid, port = det[0]["guid"], det[0]["port"]
                    rot = core.nomes_sdl()
                except Exception:
                    pass
                try:
                    r = core.salvar_mapa_gerado(
                        tipo, guid=guid, port=port, nome=f"{tipo}-hub",
                        rotulos=rot)
                except ValueError as e:
                    _W.messagebox.showwarning("Controles", str(e))
                    return
                if not r.get("ok"):
                    _W.messagebox.showwarning(
                        "Controles", r.get("erro", "falha"))
                    return
                win2.destroy()
                redesenhar()
                _W.messagebox.showinfo(
                    "Controles",
                    f"Preset {r['preset']} ✓ — aplique p/ usar.")

            ttk.Button(win2, text="Gerar",
                       command=ok).pack(pady=(0, 12))

        def testar():
            vw = tk.Toplevel(win)
            _W._titulo_escuro(vw)
            vw.title("Testar (aperte botões/mexa sticks)")
            vw.transient(win)
            filhas.append(vw)
            lbl = ttk.Label(vw, text="—", font=("Consolas", 14))
            lbl.pack(padx=20, pady=20)
            vivo = {"ok": True}

            def ciclo():
                if not vivo["ok"]:
                    return
                try:
                    est = core.ler_estado_xinput(0)
                    lbl.configure(text=core.resumir_estado(est))
                except tk.TclError:
                    vivo["ok"] = False
                    return
                except Exception:
                    pass
                try:
                    vw.after(120, ciclo)
                except tk.TclError:
                    vivo["ok"] = False

            def fechar():
                vivo["ok"] = False
                try:
                    filhas.remove(vw)
                except ValueError:
                    pass
                try:
                    vw.destroy()
                except tk.TclError:
                    pass
            vw.protocol("WM_DELETE_WINDOW", fechar)
            ciclo()

        redesenhar()
        fr_btn = ttk.Frame(fr)
        fr_btn.pack(fill="x", pady=(10, 0))
        ttk.Button(fr_btn, text="Fotografar…",
                   command=fotografar).pack(side="left")
        ttk.Button(fr_btn, text="Aplicar",
                   command=aplicar).pack(side="left", padx=6)
        ttk.Button(fr_btn, text="Gerar…",
                   command=gerar).pack(side="left")
        ttk.Button(fr_btn, text="Testar…",
                   command=testar).pack(side="left", padx=6)
        ttk.Button(fr_btn, text="Fechar",
                   command=fechar_tudo).pack(side="right")
    def atualizar_azahar(self):
        self.atualizar_emu("azahar")
    def atualizar_desmume(self):
        self.atualizar_emu("desmume")
    def atualizar_emu(self, chave: str):
        prov = core.provedores()[chave]
        nome = prov["nome"]
        prog = tk.Toplevel(self.root)
        _W._titulo_escuro(prog)
        prog.title(nome)
        prog.transient(self.root)
        lbl = ttk.Label(prog, text="Consultando releases...")
        lbl.pack(padx=24, pady=(20, 8))
        bar = ttk.Progressbar(prog, mode="indeterminate", length=260)
        bar.pack(padx=24, pady=(0, 20))
        bar.start()
        try:
            prog.update()
        except tk.TclError:
            return

        def trabalho():
            info = prov["release_info"]()
            if info.get("erro"):
                msg_erro = info["erro"]  # captura já-string (padrão Fase A)

                def mostra_erro(msg=msg_erro):
                    try:
                        prog.destroy()
                    except tk.TclError:
                        pass
                    _W.messagebox.showerror(nome, msg)

                return self._depois(mostra_erro)
            local = prov["versao_local"]()
            tag = info.get("tag") or "?"

            def decidir():
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                if local and local == tag:
                    _W.messagebox.showinfo(nome, f"Já está na {tag} ✓")
                    return
                mb = round((info.get("size") or 0) / 1048576)
                if not _W.messagebox.askyesno(
                        nome,
                        f"Instalada: {local or '?'} → remota: {tag} (~{mb} MB).\n"
                        "Baixar e instalar agora? (demora alguns minutos)"):
                    return
                self._baixar_emu(chave, info)

            self._depois(decidir)

        threading.Thread(target=self._thread_segura(trabalho, prog, "Atualizar emulador"), daemon=True).start()
    def _baixar_emu(self, chave: str, info):
        prov = core.provedores()[chave]
        nome = prov["nome"]
        prog = tk.Toplevel(self.root)
        _W._titulo_escuro(prog)
        prog.title(nome)
        prog.transient(self.root)
        lbl = ttk.Label(prog, text="Baixando...")
        lbl.pack(padx=24, pady=20)
        try:
            prog.update()
        except tk.TclError:
            return

        def trabalho():
            def andamento(feito, total):
                txt = f"Baixando... {feito // 1048576} MB"
                if total:
                    txt += f" / {total // 1048576} MB"

                def aplica(texto=txt):
                    try:
                        lbl.configure(text=texto)
                    except tk.TclError:
                        pass  # janela fechada no meio do download

                self._depois(aplica)

            res = prov["instalar"](info, progresso=andamento)

            def fim():
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                if res.get("ok"):
                    _W.messagebox.showinfo(nome, f"{res.get('tag')} instalado ✓")
                else:
                    _W.messagebox.showerror(nome, res.get("erro", "falha"))
                self.recarregar()

            self._depois(fim)

        threading.Thread(target=self._thread_segura(trabalho, prog, "Baixar emulador"), daemon=True).start()
    def backup(self):
        try:
            res = core.fazer_backup(self.db_path)
        except Exception as e:
            _W.messagebox.showerror("Backup", f"backup falhou: {e}")
            return
        _W.messagebox.showinfo("Backup", f"Backup ok: {res['jogos']} jogo(s)\n{res['db']}")
    def exportar_json(self):
        dest = filedialog.asksaveasfilename(
            title="Exportar biblioteca", defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="biblioteca.json")
        if not dest:
            return
        try:
            res = core.exportar_json(dest, db_path=self.db_path)
        except Exception as e:
            _W.messagebox.showerror("Exportar", f"falha ao gravar: {e}")
            core.log_erro("exportar-json", str(e))
            return
        if not res.get("ok"):
            _W.messagebox.showerror("Exportar", res.get("erro", "falha"))
            return
        _W.messagebox.showinfo("Exportar", f"Exportados {res['jogos']} jogo(s).")
    def importar_json(self, arq: str | None = None):
        if not arq:
            arq = filedialog.askopenfilename(
                title="Importar JSON", filetypes=[("JSON", "*.json")])
            if not arq:
                return
        try:
            dados = json.loads(Path(arq).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            _W.messagebox.showerror("Importar", f"JSON inválido: {e}")
            return
        lista = dados if isinstance(dados, list) else dados.get("jogos") if isinstance(dados, dict) else None
        if not isinstance(lista, list):
            _W.messagebox.showerror("Importar", "JSON deve ser lista ou {jogos:[...]}.")
            return
        self._backup_pre_import()
        con = self._con()
        try:
            res = core.importar_lista(con, lista)
        finally:
            con.close()
        self.sel = None
        self.recarregar()
        _W.messagebox.showinfo("Importar", core.resumo_importacao(res))
    def exportar_pacote(self):
        dest = filedialog.asksaveasfilename(
            title="Pacote portátil (banco + capas + presets + saves)",
            defaultextension=".zip", filetypes=[("ZIP", "*.zip")],
            initialfile="biblioteca-pacote.zip")
        if not dest:
            return
        prog = tk.Toplevel(self.root)
        _W._titulo_escuro(prog)
        prog.title("Pacote")
        prog.transient(self.root)
        ttk.Label(prog, text="Empacotando (só leitura)...").pack(padx=24, pady=24)
        try:
            prog.update()
        except tk.TclError:
            return

        def trabalho():
            def na_ui(fn):
                self._depois(fn)

            def _falhou(msg):
                core.log_erro("pacote", msg)
                try:
                    prog.destroy()
                except tk.TclError:
                    pass
                _W.messagebox.showerror("Pacote", f"falha: {msg}")

            try:
                res = core.exportar_pacote(dest, db_path=self.db_path, incluir_saves=True)
            except Exception as e:
                msg_erro = f"{type(e).__name__}: {e}"
                return na_ui(lambda m=msg_erro: _falhou(m))

            def pronto():
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                if not res.get("ok"):
                    _W.messagebox.showerror("Pacote", res.get("erro", "falha"))
                    return
                kb = res["bytes"] // 1024
                _W.messagebox.showinfo("Pacote",
                                    f"{res['jogos']} jogo(s) · {res['arquivos']} arquivo(s) · "
                                    f"{kb} KB{' · +saves' if res['inclui_saves'] else ''}\n"
                                    f"{res['destino']}")

            na_ui(pronto)

        threading.Thread(target=self._thread_segura(trabalho, prog, "Pacote"), daemon=True).start()
    def importar_pacote(self, arq: str | None = None):
        if not arq:
            arq = filedialog.askopenfilename(
                title="Pacote portátil", filetypes=[("ZIP", "*.zip")])
            if not arq:
                return
        quer_saves = _W.messagebox.askyesno("Pacote", "Restaurar os saves do pacote?")
        prog = tk.Toplevel(self.root)
        _W._titulo_escuro(prog)
        prog.title("Pacote")
        prog.transient(self.root)
        ttk.Label(prog, text="Restaurando pacote...").pack(padx=24, pady=24)
        try:
            prog.update()
        except tk.TclError:
            return

        def trabalho():
            def na_ui(fn):
                self._depois(fn)

            def _falhou(msg):
                core.log_erro("pacote", msg)
                try:
                    prog.destroy()
                except tk.TclError:
                    pass
                _W.messagebox.showerror("Pacote", f"falha: {msg}")

            try:
                res = core.importar_pacote(arq, db_path=self.db_path,
                                           restaurar_saves=quer_saves)
            except Exception as e:
                msg_erro = f"{type(e).__name__}: {e}"
                return na_ui(lambda m=msg_erro: _falhou(m))

            def pronto():
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                if not res.get("ok"):
                    _W.messagebox.showerror("Pacote", res.get("erro", "falha"))
                    return
                self.sel = None
                self.recarregar()
                _W.messagebox.showinfo("Pacote",
                                    core.resumo_importacao(res) + "\n" +
                                    f"capas {res['capas']} · presets {res['presets']} · "
                                    f"saves {res['saves']}")

            na_ui(pronto)

        threading.Thread(target=self._thread_segura(trabalho, prog, "Pacote"), daemon=True).start()
