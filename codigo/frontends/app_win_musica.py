#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TucoTeca classico: MixMusica de App (verbatim do modulo original)."""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from queue import Empty
from tkinter import filedialog, simpledialog, ttk

import bib_core as core
from aparencia import ACC, BG, TXT, BarraAcoes
from late import ModuloTardio

_W = ModuloTardio("app_win")


class MixMusica:
    def _mod_jogador(self):
        """Importa o motor de nomes de jogador (ou None se ausente)."""
        try:
            import importlib.util
            p = Path(core.WIN_ROOT) / "Games" / "trocar-nome-jogador.py"
            if not p.is_file():
                return None
            spec = importlib.util.spec_from_file_location(
                "trocar_nome_jogador", str(p))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        except Exception:
            return None
    def _estado_jogador(self) -> dict:
        mod = self._mod_jogador()
        if mod is None:
            return {"usuarios": [], "atual": "", "jogos": {}}
        try:
            from pathlib import Path as _P
            return mod.carregar_estado(
                _P(str(Path(core.WIN_ROOT) / "Games" / "trocar-nome-jogador.json")))
        except Exception:
            return {"usuarios": [], "atual": "", "jogos": {}}
    def _atualizar_chip_usuario(self):
        try:
            atual = (self._estado_jogador().get("atual") or "").strip()
        except Exception:
            atual = ""
        try:
            self.btn_usuario.configure(text=f"👤 {atual}" if atual else "👤 —")
        except (tk.TclError, AttributeError):
            pass
    def dlg_usuario(self):
        """Mostra quem é o jogador atual e troca entre os salvos."""
        mod = self._mod_jogador()
        if mod is None:
            _W.messagebox.showinfo(
                "Usuário jogador",
                "Perfis indisponíveis: D:\\Games\\trocar-nome-jogador.py não encontrado.")
            return
        est = self._estado_jogador()
        dlg = tk.Toplevel(self.root)
        _W._titulo_escuro(dlg)
        dlg.title("👤 Usuário jogador")
        dlg.configure(bg=BG)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.minsize(380, 0)
        ttk.Label(dlg, wraplength=360, justify="left",
                  text=("Nome gravado nos saves dos repacks (UserName=…). "
                        "Trocar aqui reaplica o nome em todos os jogos.")).pack(
                            anchor="w", padx=14, pady=(12, 6))
        lb = tk.Listbox(dlg, bg="#0b0d12", fg=TXT, selectbackground=ACC,
                        font=("Segoe UI", 12), height=4)
        lb.pack(fill="x", padx=14)
        _W._com_rolagem(lb)
        usuarios = list(est.get("usuarios") or [])
        atual = (est.get("atual") or "").strip()
        for u in usuarios:
            lb.insert("end", f"● {u}" if u == atual else f"○ {u}")
        if usuarios:
            lb.selection_set(usuarios.index(atual) if atual in usuarios else 0)

        def usar():
            idx = lb.curselection()
            if not idx and usuarios:
                _W.messagebox.showinfo("Usuário", "Selecione um usuário na lista.")
                return
            nome = usuarios[idx[0]] if idx else None
            if nome is None:
                return
            dlg.destroy()
            self._aplicar_usuario(nome)

        def novo():
            nome = simpledialog.askstring("Usuário jogador",
                                          "Nome novo (máx 3 salvos):",
                                          parent=dlg)
            if not nome:
                return
            dlg.destroy()
            self._aplicar_usuario(nome.strip())

        lin = ttk.Frame(dlg)
        lin.pack(fill="x", padx=14, pady=12)
        ttk.Button(lin, text="Usar selecionado", style="Accent.TButton",
                   command=usar).pack(side="left", expand=True, fill="x",
                                      padx=(0, 3))
        ttk.Button(lin, text="Novo…", command=novo).pack(
            side="left", expand=True, fill="x", padx=(3, 0))
    def sincronizar_nomes_boot(self):
        """1,5s após abrir: aplica o usuário atual aos jogos novos (só nomes).

        Roda em thread, silencioso; só avisa se algo mudou. Saves não
        são tocados aqui (vão na troca manual de usuário).
        """
        def trabalho():
            try:
                mod = self._mod_jogador()
                if mod is None or not hasattr(mod, "sincronizar_nomes"):
                    return
                res = mod.sincronizar_nomes()
            except Exception as e:
                try:
                    core.log_erro("auto-nomes", f"{type(e).__name__}: {e}")
                except Exception:
                    pass
                return
            try:
                aplicadas = int(res.get("aplicadas") or 0)
            except Exception:
                aplicadas = 0
            if aplicadas > 0:
                nome = res.get("nome") or ""

                def fim():
                    try:
                        self._atualizar_chip_usuario()
                        _W.messagebox.showinfo(
                            "Usuário jogador",
                            f"'{nome}' aplicado a {aplicadas} jogo(s) novo(s) ✓")
                    except Exception:
                        pass

                self._depois(fim)

        import threading
        threading.Thread(target=trabalho, daemon=True).start()
    def _aplicar_usuario(self, nome: str):
        mod = self._mod_jogador()
        if mod is None:
            return
        prog = tk.Toplevel(self.root)
        _W._titulo_escuro(prog)
        prog.title("Usuário jogador")
        prog.transient(self.root)
        ttk.Label(prog, text=f"Aplicando '{nome}' aos jogos...").pack(
            padx=24, pady=24)
        try:
            prog.update()
        except tk.TclError:
            return

        def trabalho():
            rc = mod.main([nome, "--aplicar"])

            def fim(rc=rc):
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                self._atualizar_chip_usuario()
                if rc == 0:
                    _W.messagebox.showinfo("Usuário jogador",
                                        f"'{nome}' aplicado aos jogos ✓")
                else:
                    _W.messagebox.showerror("Usuário jogador",
                                         "Falhou em algum jogo (backups .bak intactos).")

            self._depois(fim)

        import threading
        threading.Thread(target=self._thread_segura(
            trabalho, prog, "Usuário jogador"), daemon=True).start()
    def _em_musicas(self) -> bool:
        """Aba Músicas ativa? (mesma janela e banco dos jogos)."""
        try:
            return _W.NAV[self.nav_idx][0].startswith("🎵")
        except (IndexError, AttributeError):
            return False
    def _em_desejos(self) -> bool:
        """Aba Desejos ativa? (wishlist Steam espelhada)."""
        try:
            return _W.NAV[self.nav_idx][0].startswith("☆")
        except (IndexError, AttributeError):
            return False
    def _em_downloads(self) -> bool:
        """Aba Downloads ativa? (% dos torrents do qBittorrent)."""
        try:
            return _W.NAV[self.nav_idx][0].startswith("⬇ D")
        except (IndexError, AttributeError):
            return False
    def _recarregar_musicas(self):
        if self.mus_modo == "fila":
            return self._recarregar_fila()
        for w in self.grade.winfo_children():
            w.destroy()
        self.cards = []
        self._imgs_cards = []
        self._mus_lista = None
        try:
            q = self.var_q.get().strip()
        except (tk.TclError, AttributeError):
            q = ""
        con = self._con()
        try:
            try:
                self.musicas = core.listar_musicas(con, q=q)
            except Exception:
                self.musicas = []
        finally:
            con.close()
        self.mus_ids = [m["id"] for m in self.musicas]
        if self.mus_sel is None or self.mus_sel >= len(self.musicas):
            self.mus_sel = 0 if self.musicas else None
        fr_btn = BarraAcoes(self.grade)
        fr_btn.pack(side="bottom", fill="x", pady=(8, 0))
        fr_btn.adicionar("Tocar", self.tocar_musica_selecionada)
        fr_btn.adicionar("Importar…", self.importar_musicas)
        fr_btn.adicionar("Excluir", self.excluir_musica_selecionada)
        fr_btn.adicionar("CSV…", self.baixar_csv)
        try:
            con2 = self._con()
            try:
                n_pend = len(core.listar_downloads(con2, estado="pendente"))
            finally:
                con2.close()
        except Exception:
            n_pend = 0
        fr_btn.adicionar(f"Fila ({n_pend})", self._ir_fila)
        fr_trans = ttk.Frame(self.grade)
        fr_trans.pack(side="bottom", fill="x", pady=(6, 0))
        ttk.Button(fr_trans, text="⏮", width=4,
                   command=self.mus_anterior).pack(side="left")
        self._btn_play = ttk.Button(fr_trans, text="▶", width=4,
                                    command=self.mus_alternar)
        self._btn_play.pack(side="left", padx=3)
        ttk.Button(fr_trans, text="⏹", width=4,
                   command=self.mus_parar).pack(side="left")
        ttk.Button(fr_trans, text="⏭", width=4,
                   command=self.mus_proxima).pack(side="left", padx=(3, 0))
        ttk.Button(fr_trans, text="Externo…",
                   command=self.abrir_externo_musica).pack(side="left", padx=6)
        self.lbl_agora = ttk.Label(fr_trans, text="♪ parado",
                                   style="Mut.TLabel")
        self.lbl_agora.pack(side="left", padx=6)
        lst = _W._nova_grade_tv(self.grade, ("Música", "Artista · Álbum"))
        lst.pack(fill="both", expand=True)
        _W._com_rolagem(lst)
        linhas_mus = []
        for m in self.musicas:
            try:
                linhas_mus.append((core.texto_musica(m), " · ".join(
                    x for x in (m.get("artista"), m.get("album")) if x)))
            except Exception:
                continue
        _W._tv_por(lst, linhas_mus)
        _W._tv_marcar(lst, self.mus_sel)
        lst.bind("<<TreeviewSelect>>", self._ao_sel_musica)
        lst.bind("<Double-Button-1>",
                 lambda _e: self.tocar_musica_selecionada())
        self._mus_lista = lst
        n = len(self.musicas)
        try:
            self.lbl_cont.configure(
                text=f"{n} música(s) · player interno (segue com o jogo aberto)")
        except tk.TclError:
            pass
        if n == 0:
            try:
                sugest = core.sugestao_harmoni_dir()
            except Exception:
                sugest = ""
            dica = (f"Nada aqui — use 📥 Importar… (Harmoni: {sugest})"
                    if sugest else "Nada aqui — use 📥 Importar…")
            self.lbl_vazio.configure(text=dica)
            self.lbl_vazio.pack(anchor="w", padx=14)
        else:
            self.lbl_vazio.pack_forget()
        self.mostrar_detalhe()
        self._atualizar_transporte()
    def _ao_sel_musica(self, _e=None):
        i = _W._tv_sel(self._mus_lista)
        if i is None:
            return
        self.mus_sel = i
        self.mostrar_detalhe()
    def tocar_musica_selecionada(self, oferecer=True):
        """Toca no player interno (segue com o jogo; externo em Externo…).

        Decode+hash rodam em thread (a troca não congela a UI); token
        descarta thread velha se trocar de novo antes de terminar.
        """
        if self.mus_modo == "fila":
            _W.messagebox.showinfo("Fila", "Aqui é a fila de downloads (Fase B).")
            return
        if self.mus_sel is None or self.mus_sel >= len(self.musicas):
            _W.messagebox.showinfo("Músicas", "Selecione uma música na lista.")
            return
        self._tocar_faixa_async(self.mus_sel, oferecer=oferecer)
    def _tocar_faixa_async(self, idx: int, oferecer=True, avisar=True,
                         faixas=None):
        if self._mus_fechado:
            return
        if faixas is None:
            faixas = [{"id": m.get("id"), "path": m.get("musica_path") or "",
                       "titulo": core.texto_musica(m)} for m in self.musicas]
        faixas = [dict(f) for f in faixas]
        if not (0 <= idx < len(faixas)) or not faixas[idx]["path"]:
            _W.messagebox.showinfo("Músicas", "Selecione uma música na lista.")
            return
        self._mus_token += 1
        meu = self._mus_token
        player = self.player
        player.carregar(faixas, inicio=idx)  # controles MCI sempre na thread Tk
        player.backend.close()
        rotulo = faixas[idx]["titulo"]
        self._mus_carregando = rotulo
        self._aviso_barra(f"Carregando: {rotulo}…")
        self._selecionar_faixa_player()
        self._atualizar_transporte()

        def trabalho():
            # Só hash/conversão aqui: nenhum comando MCI ou chamada Tk.
            with self._mus_preparo_lock:
                if meu != self._mus_token or self._mus_fechado:
                    return
                try:
                    r = player.preparar(faixas[idx]["path"])
                except Exception as e:
                    r = {"ok": False, "erro": str(e)}
            self._mus_resultados.put((meu, idx, r, oferecer, avisar))

        threading.Thread(target=trabalho, daemon=True).start()
    def _processar_mus_resultados(self):
        """Entrega preparação à thread Tk, dona do dispositivo MCI."""
        if self._mus_fechado:
            return
        for _ in range(100):
            try:
                resultado = self._mus_resultados.get_nowait()
            except Empty:
                break
            self._pos_tocar(*resultado)
        if not self._mus_fechado:
            self._mus_poll = self.root.after(50, self._processar_mus_resultados)
    def _pos_tocar(self, meu: int, idx: int, r: dict,
                   oferecer: bool, avisar: bool):
        if meu != self._mus_token or self._mus_fechado:
            return  # descarta o resultado, sem parar a faixa mais nova
        self._mus_carregando = ""
        if r.get("ok"):
            try:
                r = self.player.tocar_preparado(idx, r)
            except Exception as e:
                r = {"ok": False, "erro": str(e)}
        if r.get("ok"):
            at = self.player.atual() or {}
            self._aviso_barra(f"Tocando: {at.get('titulo') or ''}")
        elif oferecer and "ffmpeg" in (r.get("erro") or "") \
                and not core.ffmpeg_pronto():
            faixas = [dict(f) for f in self.player.fila]

            def repetir():
                if meu == self._mus_token and not self._mus_fechado:
                    self._tocar_faixa_async(idx, oferecer=False, faixas=faixas)

            self.instalar_deps_audio(
                ("ffmpeg",), ao_fim=repetir)
        elif avisar:
            try:
                _W.messagebox.showwarning("Músicas", r.get("erro", "falha"))
            except tk.TclError:
                pass
        else:
            self._aviso_barra(f"Falha: {r.get('erro', 'falha')}"[:120])
        self._atualizar_transporte()
    def instalar_deps_audio(self, so_falta=("ffmpeg", "ytdlp"), ao_fim=None):
        """Baixa ffmpeg/yt-dlp oficiais em thread (molde ⬇ emuladores)."""
        pend = []
        if "ffmpeg" in so_falta and not core.ffmpeg_pronto():
            pend.append(("ffmpeg", "ffmpeg (~80MB)"))
        if "ytdlp" in so_falta and not core.ytdlp_pronto():
            pend.append(("ytdlp", "yt-dlp (~30MB)"))
        if not pend:
            if ao_fim:
                try:
                    ao_fim()
                except tk.TclError:
                    pass
            return
        if not _W.messagebox.askyesno(
                "Dependências de áudio",
                "Falta: " + ", ".join(p[1] for p in pend)
                + ".\nBaixar do oficial agora?"):
            return
        prog = tk.Toplevel(self.root)
        _W._titulo_escuro(prog)
        prog.title("Baixando dependências…")
        prog.transient(self.root)
        lbl = ttk.Label(prog, text="Preparando…")
        lbl.pack(padx=24, pady=20)
        try:
            prog.update()
        except tk.TclError:
            return

        def located(txt):
            def _cb(feito, total):
                try:
                    mb = f"{feito/1048576:.0f}/{total/1048576:.0f}MB" \
                        if total else f"{feito/1048576:.0f}MB"
                    self._depois(lambda: lbl.configure(text=f"{txt}: {mb}"))
                except tk.TclError:
                    pass
            return _cb

        def trabalho(pend_fx=pend):
            erros = []
            for chave, _rot in pend_fx:
                try:
                    if chave == "ffmpeg":
                        r = core.instalar_ffmpeg(progresso=located("ffmpeg"))
                    else:
                        r = core.instalar_ytdlp(progresso=located("yt-dlp"))
                except Exception as e:
                    r = {"ok": False, "erro": str(e)}
                if not r.get("ok"):
                    erros.append(f"{chave}: {r.get('erro')}")
            self._depois(lambda: fim(erros))

        def fim(erros):
            try:
                prog.destroy()
            except tk.TclError:
                pass
            if erros:
                _W.messagebox.showwarning("Dependências de áudio",
                                       "\n".join(erros[:3]))
                return
            if ao_fim:
                try:
                    ao_fim()
                except tk.TclError:
                    pass
            else:
                try:
                    self._aviso_barra("Dependências de áudio ok ✓")
                except tk.TclError:
                    pass
        threading.Thread(target=trabalho, daemon=True).start()
    def abrir_externo_musica(self):
        """Fallback: abre no player do SO (como era antes do interno)."""
        if self.mus_modo == "fila" or self.mus_sel is None \
                or self.mus_sel >= len(self.musicas):
            return
        m = self.musicas[self.mus_sel]
        self.mus_parar()
        r = core.tocar_musica(m.get("musica_path") or "")
        if r.get("ok"):
            self._aviso_barra(f"Tocando (externo): {core.texto_musica(m)}")
        else:
            _W.messagebox.showwarning("Músicas", r.get("erro", "falha"))
    def mus_alternar(self):
        if self._mus_carregando:
            return
        if self.player.estado == "parado":
            self.tocar_musica_selecionada()
            return
        r = self.player.alternar()
        if not r.get("ok"):
            _W.messagebox.showwarning("Músicas", r.get("erro", "falha"))
        self._atualizar_transporte()
    def mus_parar(self):
        self._mus_token += 1  # cancela também preparações ainda em andamento
        self._mus_carregando = ""
        self.player.parar()
        self.player.backend.close()
        self._atualizar_transporte()
    def mus_proxima(self):
        faixas = self.player.fila or [
            {"id": m.get("id"), "path": m.get("musica_path") or "",
             "titulo": core.texto_musica(m)} for m in self.musicas]
        base = self.player.idx if self.player.fila else None
        if base is None:
            base = self.mus_sel if self.mus_sel is not None else -1
        idx = base + 1
        if idx >= len(faixas):
            self.mus_parar()
            return
        self._tocar_faixa_async(idx, oferecer=False, avisar=False, faixas=faixas)
    def mus_anterior(self):
        if not self.player.fila:
            if self.musicas:
                self._tocar_faixa_async(max(0, (self.mus_sel or 0) - 1),
                                        oferecer=False, avisar=False)
            return
        self._tocar_faixa_async(max(0, (self.player.idx or 0) - 1),
                                oferecer=False, avisar=False,
                                faixas=self.player.fila)
    def _selecionar_faixa_player(self):
        """Sincroniza por identidade, mesmo após busca ou troca de aba."""
        if not self._em_musicas() or self.mus_modo != "hub":
            return
        atual = self.player.atual() or {}
        pos = next((i for i, m in enumerate(self.musicas)
                    if (atual.get("id") is not None and m.get("id") == atual["id"])
                    or (m.get("musica_path") and m["musica_path"] == atual.get("path"))),
                   None)
        if pos is None:
            return
        self.mus_sel = pos
        try:
            _W._tv_marcar(self._mus_lista, pos)
        except (tk.TclError, AttributeError):
            pass
        self.mostrar_detalhe()
    def _atualizar_transporte(self):
        try:
            btn = self._btn_play
            lbl = self.lbl_agora
        except AttributeError:
            return
        try:
            if btn is not None and btn.winfo_exists():
                btn.configure(text="⏸" if self.player.estado == "tocando"
                              else "▶")
            if lbl is not None and lbl.winfo_exists():
                at = self.player.atual()
                lbl.configure(text=f"Carregando: {self._mus_carregando}…"
                              if self._mus_carregando else f"♪ {at['titulo']}"
                                  f" ({at['estado']})" if at
                              and self.player.estado != "parado"
                              else "♪ parado")
        except tk.TclError:
            pass
    def _vigiar_musica(self):
        """Poll 1s: faixa acabou → próxima (auto-avançar); reagenda sempre."""
        if self._mus_fechado:
            return
        try:
            if not self._mus_carregando and self.player.terminou():
                self.mus_proxima()
            else:
                self._atualizar_transporte()
        except Exception:
            pass
        try:
            self._mus_vigia = self.root.after(1000, self._vigiar_musica)
        except tk.TclError:
            pass
    def _fechar_player(self, evento):
        if evento.widget is not self.root or self._mus_fechado:
            return
        self._mus_fechado = True
        if self._dl_timer is not None:
            self.root.after_cancel(self._dl_timer)
            self._dl_timer = None
        self.mus_parar()
        for chave in ("_mus_poll", "_mus_vigia"):
            ident = getattr(self, chave, None)
            if ident is not None:
                try:
                    self.root.after_cancel(ident)
                except tk.TclError:
                    pass
    def excluir_musica_selecionada(self):
        if self.mus_modo == "fila":
            return
        if self.mus_sel is None or self.mus_sel >= len(self.musicas):
            return
        m = self.musicas[self.mus_sel]
        if not _W.messagebox.askokcancel(
                "Músicas",
                f"Apagar '{core.texto_musica(m)}' do Hub (arquivo junto)?"):
            return
        tocando = ""
        try:
            at = self.player.atual()
            tocando = (at or {}).get("path") or ""
        except Exception:
            pass
        con = self._con()
        try:
            core.excluir_musica(con, m["id"])
        except (LookupError, ValueError) as e:
            _W.messagebox.showwarning("Músicas", str(e))
            return
        finally:
            con.close()
        self.mus_sel = None
        if tocando and tocando == (m.get("musica_path") or ""):
            self.mus_parar()
        self.recarregar()
    def _ir_fila(self):
        self.mus_modo = "fila"
        self._pintar_nav()
        self.recarregar()
    def _ir_musicas(self):
        self.mus_modo = "hub"
        self._pintar_nav()
        self.recarregar()
    def _recarregar_fila(self):
        """Fila CSV → mp3 (contadores + limpar; download vem na Fase B)."""
        for w in self.grade.winfo_children():
            w.destroy()
        self.cards = []
        self._imgs_cards = []
        self._mus_lista = None
        con = self._con()
        try:
            try:
                self.fila = core.listar_downloads(con)
            except Exception:
                self.fila = []
        finally:
            con.close()
        if self.fila_sel is None or self.fila_sel >= len(self.fila):
            self.fila_sel = 0 if self.fila else None
        fr_btn = BarraAcoes(self.grade)
        fr_btn.pack(side="bottom", fill="x", pady=(8, 0))
        fr_btn.adicionar("Músicas", self._ir_musicas)
        fr_btn.adicionar("CSV…", self.baixar_csv)
        fr_btn.adicionar("Baixar fila", self.baixar_fila)
        fr_btn.adicionar("Importar baixadas", self.importar_baixadas)
        fr_btn.adicionar("Limpar prontas/falhas", self.limpar_fila)
        lst = _W._nova_grade_tv(self.grade, ("Faixa", "Estado"))
        lst.pack(fill="both", expand=True)
        _W._com_rolagem(lst)
        linhas_fila = []
        for d in self.fila:
            try:
                rot = core.texto_musica(d)
                est = d.get("estado") or ""
                extra = (f" — {d.get('erro')}"
                         if est == "falha" and d.get("erro") else "")
                linhas_fila.append((rot, f"{est}{extra}"))
            except Exception:
                continue
        _W._tv_por(lst, linhas_fila)
        _W._tv_marcar(lst, self.fila_sel)
        lst.bind("<<TreeviewSelect>>", self._ao_sel_fila)
        self._mus_lista = lst
        n = len(self.fila)
        np_ = sum(1 for d in self.fila if d.get("estado") == "pendente")
        nbx = sum(1 for d in self.fila if d.get("estado") == "baixado")
        nok = sum(1 for d in self.fila if d.get("estado") == "pronta")
        nf = sum(1 for d in self.fila if d.get("estado") == "falha")
        try:
            self.lbl_cont.configure(
                text=f"{n} na fila · {np_} pendente(s) · {nbx} baixada(s)"
                     f" · {nok} pronta(s) · {nf} falha(s)")
        except tk.TclError:
            pass
        if n == 0:
            self.lbl_vazio.configure(text="Fila vazia — use ⬇ CSV… (Exportify)")
            self.lbl_vazio.pack(anchor="w", padx=14)
        else:
            self.lbl_vazio.pack_forget()
        self.mostrar_detalhe()
    def _ao_sel_fila(self, _e=None):
        i = _W._tv_sel(self._mus_lista)
        if i is None:
            return
        self.fila_sel = i
        self.mostrar_detalhe()
    def baixar_csv(self):
        """Exportify CSV → fila (dedup; download é Fase B)."""
        arq = filedialog.askopenfilename(
            title="CSV do Exportify (Spotify)",
            parent=self.root,
            filetypes=[("CSV", "*.csv"), ("todos", "*.*")])
        if not arq:
            return
        parsed = core.ler_csv_exportify(arq)
        if parsed["erros"] and not parsed["itens"]:
            _W.messagebox.showwarning("Baixar de CSV", parsed["erros"][0])
            return
        self._backup_pre_import()
        con = self._con()
        try:
            res = core.enfileirar_downloads(con, parsed["itens"])
        finally:
            con.close()
        detalhe = f"{res['novos']} na fila, {res['ignorados']} ignorada(s)"
        if parsed["ignorados"]:
            detalhe += f" (+{parsed['ignorados']} sem título no CSV)"
        if parsed["erros"]:
            detalhe += f"\n{parsed['erros'][0]}"
        _W.messagebox.showinfo("Baixar de CSV", detalhe)
        if self._em_musicas():
            try:
                self.recarregar()
            except tk.TclError:
                pass
    def baixar_fila(self, oferecer=True):
        """Start Downloads do Harmoni: baixa pendentes em thread (Fase B)."""
        th = getattr(self, "_th_fila", None)
        if th is not None and th.is_alive():
            _W.messagebox.showinfo("Baixar fila", "Download já em andamento.")
            return
        if not core.localizar_ytdlp():
            if oferecer:
                self.instalar_deps_audio(
                    ("ytdlp",),
                    ao_fim=lambda: self.baixar_fila(oferecer=False))
            else:
                _W.messagebox.showwarning("Baixar fila", core.erro_sem_ytdlp())
            return
        con = self._con()
        try:
            try:
                ids = [d["id"] for d in core.listar_downloads(con)
                       if d.get("estado") in ("pendente", "falha")]
            except Exception as e:
                _W.messagebox.showwarning("Baixar fila", f"falha: {e}")
                return
        finally:
            con.close()
        if not ids:
            _W.messagebox.showinfo("Baixar fila", "Nada pendente.")
            return
        self._aviso_barra(f"Baixando {len(ids)} faixa(s)…")

        def trabalho(ids_fx=ids):
            for did in ids_fx:
                c2 = None
                try:
                    c2 = self._con()
                    core.baixar_faixa(c2, did, progresso=self._prog_fila)
                except Exception as e:
                    try:
                        if c2 is not None:
                            core.marcar_download(c2, did, "falha",
                                                 erro=str(e)[:200])
                    except Exception:
                        pass
                finally:
                    try:
                        if c2 is not None:
                            c2.close()
                    except Exception:
                        pass
            self._depois(self._fim_fila)

        self._th_fila = threading.Thread(target=trabalho, daemon=True)
        self._th_fila.start()
    def _prog_fila(self, did, pct):
        try:
            self._depois(
                lambda: self._aviso_barra(f"Baixando #{did}: {pct:.0f}%"))
        except tk.TclError:
            pass
    def _fim_fila(self):
        try:
            self.recarregar()
        except tk.TclError:
            pass
        self._aviso_barra("Fila atualizada.")
    def importar_baixadas(self):
        """Fase C: converte `baixado` → `musicas/` em thread."""
        th = getattr(self, "_th_fila", None)
        if th is not None and th.is_alive():
            _W.messagebox.showinfo("Importar baixadas", "Operação em andamento.")
            return
        con = self._con()
        try:
            try:
                n = len(core.listar_downloads(con, estado="baixado"))
            except Exception as e:
                _W.messagebox.showwarning("Importar baixadas", f"falha: {e}")
                return
        finally:
            con.close()
        if not n:
            _W.messagebox.showinfo("Importar baixadas",
                                "Nada baixado (⬇ Baixar fila primeiro).")
            return
        self._aviso_barra(f"Importando {n} faixa(s)…")

        def trabalho():
            c2 = None
            try:
                self._backup_pre_import()
                c2 = self._con()
                res = core.importar_fila_pronta(c2)
            except Exception as e:
                res = {"novas": 0, "ignoradas": 0, "erros": [str(e)],
                       "avisos": []}
            finally:
                try:
                    if c2 is not None:
                        c2.close()
                except Exception:
                    pass
            detalhe = f"{res['novas']} nova(s), {res['ignoradas']} ignorada(s)"
            if res["erros"]:
                detalhe += f"\n{res['erros'][0]}"
            if res.get("avisos"):
                detalhe += f"\n{res['avisos'][0][:160]}"
            self._depois(lambda: self._fim_importar(detalhe))

        self._th_fila = threading.Thread(target=trabalho, daemon=True)
        self._th_fila.start()
    def _fim_importar(self, detalhe):
        try:
            self.recarregar()
        except tk.TclError:
            pass
        try:
            _W.messagebox.showinfo("Importar baixadas", detalhe)
        except tk.TclError:
            pass
    def limpar_fila(self):
        """Clear Done do Harmoni: apaga prontas/falhas (CSV recria)."""
        con = self._con()
        try:
            try:
                n = core.limpar_downloads(con)
            except ValueError as e:
                _W.messagebox.showwarning("Fila", str(e))
                return
        finally:
            con.close()
        self.fila_sel = None
        if self._em_musicas():
            try:
                self.recarregar()
            except tk.TclError:
                pass
        self._aviso_barra(f"Fila limpa ({n} removida(s))")
    def importar_musicas(self):
        try:
            sugest = (str(core.harmoni_dir() or "")
                      or str(core.sugestao_harmoni_dir() or ""))
        except Exception:
            sugest = ""
        try:
            pasta = filedialog.askdirectory(
                title="Pasta do Harmoni (music/) ou qualquer pasta de áudio",
                parent=self.root,
                initialdir=sugest or None)
        except tk.TclError:
            pasta = filedialog.askdirectory(
                title="Pasta do Harmoni (music/) ou qualquer pasta de áudio",
                parent=self.root)
        if not pasta:
            return
        prog = tk.Toplevel(self.root)
        _W._titulo_escuro(prog)
        prog.title("Importando músicas…")
        prog.transient(self.root)
        ttk.Label(prog, text="Copiando e catalogando…").pack(padx=24, pady=20)
        try:
            prog.update()
        except tk.TclError:
            return

        def trabalho(pasta_fx=pasta):
            con = None
            try:
                self._backup_pre_import()
                con = self._con()
                res = core.importar_musicas(con, pasta_fx)
            except Exception as e:
                res = {"novos": 0, "ignorados": 0, "erros": [str(e)]}
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
                detalhe = f"{res['novos']} nova(s), {res['ignorados']} ignorada(s)"
                if res["erros"]:
                    detalhe += f"\n{res['erros'][0]}"
                    if len(res["erros"]) > 1:
                        detalhe += f"\n(+{len(res['erros']) - 1})"
                _W.messagebox.showinfo("Músicas", detalhe)
            self._depois(fim)
        threading.Thread(target=trabalho, daemon=True).start()
