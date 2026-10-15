#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TucoTeca classico: MixJogos de App (verbatim do modulo original)."""
from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, simpledialog, ttk

import app_win as _W
import bib_core as core
from aparencia import ACC, BG, CARD, LINE, MUT, PANEL, TXT
from aparencia import HOVER as CARD_HOVER


class MixJogos:
    def recarregar(self):
        selecionado_id = (self.jogos[self.sel]["id"] if self.sel is not None
                          and 0 <= self.sel < len(self.jogos) else None)
        if self._deb is not None:
            self.root.after_cancel(self._deb)
            self._deb = None
        self.nav_idx = max(0, min(int(self.nav_idx), len(_W.NAV) - 1))
        self._atualizar_contexto()
        if self._em_desejos():
            return self._recarregar_desejos()
        if self._em_downloads():
            self._recarregar_downloads()
            self._consultar_downloads()
            return
        if self._em_musicas():
            return self._recarregar_musicas()
        try:
            self.nav_idx = max(0, min(int(self.nav_idx), len(_W.NAV) - 1))
        except Exception:
            self.nav_idx = 0
        status = (self.filtro_status or "").strip()
        fav = bool(self.so_fav)
        try:
            tag_txt = self.var_tagfiltro.get().strip()
        except (tk.TclError, AttributeError):
            tag_txt = ""
        tags = [t.strip() for t in tag_txt.replace(";", ",").split(",") if t.strip()]
        try:
            busca = self.var_q.get().strip()
        except (tk.TclError, AttributeError):
            busca = ""
        con = self._con()
        erro_lista = ""
        try:
            try:
                self.jogos = core.listar_jogos(
                    con, q=busca, status=status, favorito=fav,
                    etiquetas=tags or None,
                    plataformas=[self.filtro_plat] if self.filtro_plat else None)
            except Exception as e:
                # filtro inválido nunca apaga a lista em silêncio: mostra tudo
                try:
                    self.jogos = core.listar_jogos(con)
                except Exception:
                    self.jogos = []
                erro_lista = f"filtro falhou ({e}); mostrando tudo"
            if self.filtro_prov:
                try:
                    self.jogos = core.jogos_do_provedor(self.jogos, self.filtro_prov)
                except Exception as e:
                    erro_lista = f"filtro provider falhou ({e})"
            for r in core.provedores_resumo(con):
                b = self.prov_btns.get(r["chave"])
                if b is not None:
                    marca = "✓" if r["instalado"] else "!"
                    b.configure(text=f"🎮{marca} {r['nome']} · {r['n']}")
            try:
                nomes_tags = [e["nome"] for e in core.listar_etiquetas(con)]
                self.cmb_tagfiltro.configure(values=nomes_tags)
            except (tk.TclError, AttributeError):
                pass
        finally:
            con.close()
        for w in self.grade.winfo_children():
            w.destroy()
        self.cards = []
        self._imgs_cards = []
        # virtualização simples: grade completa trava com 100s de capas;
        # renderiza os 150 primeiros e orienta refinar a busca.
        LIMITE_GRADE = 150
        visiveis = self.jogos[:LIMITE_GRADE]
        ocultos = len(self.jogos) - len(visiveis)
        for j in visiveis:
            self.cards.append(self._criar_card(j))
        self._reorganizar()
        self.sel = next((i for i, j in enumerate(visiveis) if j["id"] == selecionado_id),
                        0 if visiveis else None)
        self._pintar_selecao()
        self.mostrar_detalhe()
        n = len(self.jogos)
        az = core.azahar_status()
        az_txt = "🎮 Azahar ✓" if az["instalado"] and az["chaves"] else (
            "🎮 Azahar !" if az["instalado"] else "🎮 Azahar ✗")
        extra = f" · mostrando {len(visiveis)} (+{ocultos} ocultos — refine a busca)" if ocultos else ""
        # avisos não-modais na barra (modais aqui travariam testes/sandbox)
        try:
            pend = core.listar_sessoes_pendentes()
            if pend:
                extra += f" · ⏱ {len(pend)} sessão(ões) pendente(s)"
        except Exception:
            pass
        try:
            idade = core.idade_ultimo_backup_dias()
            if idade is None:
                extra += " · sem backup"
            elif idade > 7:
                extra += f" · backup há {int(idade)}d"
        except Exception:
            pass
        if erro_lista:
            extra += f" · {erro_lista}"
        self.lbl_cont.configure(text=f"{n} jogo(s) · {az_txt}{extra}")
        try:
            self._atualizar_chip_usuario()
        except Exception:
            pass
        try:
            busca_atual = self.var_q.get().strip()
        except (tk.TclError, AttributeError):
            busca_atual = ""
        if n == 0:
            if (self.filtro_plat or self.filtro_prov or tag_txt
                    or busca_atual or status or fav):
                self.lbl_vazio.configure(text="Nada aqui — ajuste busca/filtros ou ✕ Limpar")
            else:
                self.lbl_vazio.configure(text="Nada aqui — use 📥 Importar…")
            self.lbl_vazio.pack(anchor="w", padx=14)
        else:
            self.lbl_vazio.pack_forget()
        try:
            self.canvas.yview_moveto(0)
        except (tk.TclError, AttributeError):
            pass
    def _criar_card(self, j: dict) -> dict:
        largura, altura = self._tamanho_card()
        fr = ttk.Frame(self.grade, style="Card.TFrame", cursor="hand2")
        img = None
        if j.get("capa"):
            alvo = core.caminho_capa(j["capa"])
            if alvo is not None:
                img = _W.carregar_miniatura(alvo, largura, altura, master=self.root)
        if img is not None:
            self._imgs_cards.append(img)
            lb = tk.Label(fr, image=img, width=largura, height=altura,
                          bg=CARD, cursor="hand2",
                          highlightthickness=2, highlightbackground=CARD,
                          borderwidth=0)
            lb.pack(padx=6, pady=(6, 2))
            fr._imgw = lb  # type: ignore[attr-defined]
        else:
            cv = tk.Canvas(fr, width=largura, height=altura, bg=CARD,
                           highlightthickness=2, highlightbackground=CARD,
                           cursor="hand2")
            cv.pack(padx=6, pady=(6, 2))
            try:
                plat_cv = j.get("plataforma") or core.plataforma_jogo(j)
            except Exception:
                plat_cv = ""
            _W.desenhar_tile(cv, j["titulo"], largura, altura, subtitulo=plat_cv)
            fr._tile = cv  # type: ignore[attr-defined]
            fr._imgw = cv  # type: ignore[attr-defined]
        # Plataforma no canto da capa + etiquetas livres.
        try:
            plat = j.get("plataforma") or core.plataforma_jogo(j)
        except Exception:
            plat = "PC"
        tags = list(j.get("etiquetas_lista") or [])
        badge_plat = tk.Label(fr, text=plat, bg=PANEL, fg=ACC,
                              font=("Segoe UI", 8, "bold"), padx=7, pady=3,
                              cursor="hand2")
        badge_plat.place(x=6, y=6)
        fr._badge_plat = badge_plat  # type: ignore[attr-defined]
        if tags:
            txt_tags = ", ".join(tags[:2]) + (f" +{len(tags) - 2}" if len(tags) > 2 else "")
            badge_tags = tk.Label(fr, text=f"🏷 {txt_tags}", bg="#0b0d12", fg=TXT,
                                  font=("Segoe UI", 8), padx=5, pady=2, cursor="hand2")
            badge_tags.place(x=6, y=30)
            fr._badge_tags = badge_tags  # type: ignore[attr-defined]
        t = tk.Label(fr, text=f"{'★ ' if j['favorito'] else ''}{j['titulo']}",
                     bg=CARD, fg=TXT, wraplength=largura + 8,
                     font=("Segoe UI", 10, "bold"), cursor="hand2")
        t.pack(fill="x", pady=(6, 4), padx=6)
        cor = _W.STATUS_CORES.get(j["status"], MUT)
        try:
            horas_n = round(float(j["horas"] or 0), 2)
        except (TypeError, ValueError):
            horas_n = 0
        horas = f" · {horas_n:g}h" if horas_n else ""
        m = tk.Label(fr, text=f"{j['status']}{horas}{core.selo_confianca(j)}", bg=CARD, fg=cor,
                     font=("Segoe UI", 9), wraplength=largura + 8, justify="center", cursor="hand2")
        m.pack(pady=(0, 8))
        fr._titulo = t  # type: ignore[attr-defined]
        fr._meta = m  # type: ignore[attr-defined]
        for w in (fr, t, m, getattr(fr, "_imgw", None),
                    getattr(fr, "_badge_plat", None), getattr(fr, "_badge_tags", None)):
            if w is None:
                continue
            try:
                w._card = fr  # type: ignore[attr-defined]
            except Exception:
                pass
            w.bind("<Button-1>", lambda e: self._clicar(e))
            w.bind("<Double-Button-1>", lambda _e: self.jogar())
            w.bind("<Button-3>", lambda e: self._menu_ctx(e))
            w.bind("<Enter>", lambda e: self._hover_card(e, True))
            w.bind("<Leave>", lambda e: self._hover_card(e, False))
        return {"frame": fr, "jogo": j}
    def _hover_card(self, e, on: bool):
        """Acende o card inteiro no hover (fundo + título)."""
        try:
            fr = getattr(e.widget, "_card", None) or e.widget
            t = getattr(fr, "_titulo", None)
            m = getattr(fr, "_meta", None)
            imgw = getattr(fr, "_imgw", None)
            bg = CARD_HOVER if on else CARD
            idx = self._indice_do_widget(fr)
            fr.configure(style="Selected.Card.TFrame" if idx == self.sel else
                         "Hover.Card.TFrame" if on else "Card.TFrame")
            if t is not None:
                t.configure(bg=bg, foreground=ACC if on else TXT)
            if m is not None:
                m.configure(bg=bg)
            if isinstance(imgw, tk.Label):
                imgw.configure(bg=bg)
        except tk.TclError:
            pass
    def _indice_do_widget(self, w) -> int | None:
        while w is not None:
            card = getattr(w, "_card", None) or w
            for i, c in enumerate(self.cards):
                if c["frame"] is card or c["frame"] == w:
                    return i
            w = getattr(w, "master", None)
        return None
    def _clicar(self, e):
        i = self._indice_do_widget(e.widget)
        if i is not None:
            self.sel = i
            self._pintar_selecao()
            self.mostrar_detalhe()
            try:
                self.canvas.focus_set()  # ativa Return/Delete do teclado
            except tk.TclError:
                pass
    def _menu_ctx(self, e):
        i = self._indice_do_widget(e.widget)
        if i is None:
            return
        self.sel = i
        self._pintar_selecao()
        self.mostrar_detalhe()
        menu = tk.Menu(self.root, tearoff=0, bg=CARD, fg=TXT,
                       activebackground=ACC, activeforeground="white")
        menu.add_command(label="▶ Jogar", command=self.jogar)
        menu.add_command(label="✏ Editar", command=self.dlg_editar)
        menu.add_command(label="🗑 Excluir", command=self.excluir)
        try:
            menu.tk_popup(e.x_root, e.y_root)
        finally:
            menu.grab_release()
    def _pintar_selecao(self):
        jogo = self.jogos[self.sel] if self.sel is not None and 0 <= self.sel < len(self.jogos) else None
        self.destaque_titulo.configure(text=jogo["titulo"] if jogo else "Sua próxima aventura começa aqui",
                                       wraplength=max(200, self.centro.winfo_width() - 230))
        self.destaque_jogar.configure(state="normal" if jogo else "disabled")
        for i, c in enumerate(self.cards):
            fr = c["frame"]
            sel = (i == self.sel)
            fr.configure(style="Selected.Card.TFrame" if sel else "Card.TFrame")
            fr._titulo.configure(bg=CARD, foreground=TXT)
            fr._meta.configure(bg=CARD)
            imgw = getattr(fr, "_imgw", None)
            if isinstance(imgw, tk.Label):
                try:
                    imgw.configure(highlightbackground=ACC if sel else CARD)
                except tk.TclError:
                    pass
            for w in fr.winfo_children():
                if isinstance(w, tk.Canvas) and w not in (self.det_capa,):
                    try:
                        w.configure(highlightbackground=ACC if sel else CARD)
                    except tk.TclError:
                        pass
                    _W.desenhar_tile(w, c["jogo"]["titulo"], *self._tamanho_card(),
                                  selecionado=sel,
                                  subtitulo=(c["jogo"].get("plataforma") or ""))
    def selecionado(self) -> dict | None:
        if self.sel is None or self.sel >= len(self.jogos):
            _W.messagebox.showinfo("Biblioteca", "Selecione um jogo na grade.")
            return None
        return self.jogos[self.sel]
    def _botoes_detalhe(self, modo: str) -> None:
        """Ativa/desativa botões do detalhe por contexto.

        jogo: tudo vale; musica: só TOCAR+Excluir (Editar/Novo é de jogo);
        fila: tudo parado (é fila de download, não catálogo);
        desejo: só Buscar+Excluir (Editar/Novo é de jogo);
        download: tudo parado (torrent externo; gerenciar no qBittorrent).
        """
        try:
            estados = {"jogo": ("normal", "normal", "normal"),
                       "musica": ("disabled", "normal", "disabled"),
                       "fila": ("disabled", "disabled", "disabled"),
                       "desejo": ("disabled", "normal", "disabled"),
                       "download": ("disabled", "disabled", "disabled")}[modo]
        except KeyError:
            return
        for btn, est in zip((self.btn_det_editar, self.btn_det_excluir,
                             self.btn_det_novo), estados):
            try:
                btn.configure(state=est)
            except (tk.TclError, AttributeError):
                pass
    def mostrar_detalhe(self):
        self.det_progresso.pack_forget()
        if self.det_janela is not None:
            self.root.after_idle(self._replicar_detalhe)
        if self._em_downloads():
            self._botoes_detalhe("download")
            try:
                self.btn_jogar.configure(text="📂 PASTA", state="normal")
            except tk.TclError:
                pass
            d = self._dl_sel_atual()
            if d is None:
                self.det_titulo.configure(text="Nenhum download")
                self.det_meta.configure(text="")
                self.det_exe.configure(text="")
                _W.desenhar_tile(self.det_capa, "⬇", 216, 280, grande=True)
                return
            tam = (f"{core.formatar_tamanho(d['feito'])}/"
                   f"{core.formatar_tamanho(d['total'])}")
            self.det_titulo.configure(text=d["nome"])
            origem = "estimativa em disco" if d.get("fonte_progresso") == "estimativa" else "estado do cliente"
            if d.get("fonte_progresso") == "api":
                eta = d.get("eta", 0)
                restante = f"{eta // 60} min" if 0 < eta < 8640000 else "sem previsão"
                origem = f"{core.formatar_tamanho(d.get('velocidade', 0))}/s · {restante}\n{d.get('estado', '')}"
            self.det_meta.configure(text=f"{d['pct']}% · {tam}\n{origem}")
            self.det_exe.configure(text=d.get("save_path") or "")
            self.det_progresso.configure(value=d["pct"])
            self.det_progresso.pack(fill="x", padx=16, pady=8, before=self.det_exe)
            _W.desenhar_tile(self.det_capa, "⬇", 216, 280, grande=True,
                          subtitulo=f"{d['pct']}%" if not d["completo"] else "✓")
            return
        if self._em_desejos():
            self._botoes_detalhe("desejo")
            try:
                self.btn_jogar.configure(text="🔎 BUSCAR", state="normal")
            except tk.TclError:
                pass
            d = self._desejo_sel()
            if d is None:
                self.det_titulo.configure(text="Nenhum desejo")
                self.det_meta.configure(text="")
                self.det_exe.configure(text="")
                _W.desenhar_tile(self.det_capa, "☆", 216, 280, grande=True)
                return
            self.det_titulo.configure(text=d["titulo"])
            self.det_meta.configure(text=f"Steam appid {d['appid']}")
            self.det_exe.configure(
                text=f"https://store.steampowered.com/app/{d['appid']}/")
            _W.desenhar_tile(self.det_capa, "☆", 216, 280, grande=True,
                          subtitulo="desejo")
            return
        if self._em_musicas() and self.mus_modo == "fila":
            self._botoes_detalhe("fila")
            try:
                self.btn_jogar.configure(text="⬇ FILA", state="disabled")
            except tk.TclError:
                pass
            if self.fila_sel is None or self.fila_sel >= len(self.fila):
                self.det_titulo.configure(text="Fila vazia")
                self.det_meta.configure(text="")
                self.det_exe.configure(text="")
                _W.desenhar_tile(self.det_capa, "⬇", 216, 280, grande=True)
                return
            d = self.fila[self.fila_sel]
            self.det_titulo.configure(
                text=core.texto_musica(d) or "Sem título")
            meta = " · ".join(x for x in (d.get("estado"), d.get("artista"),
                                          d.get("album")) if x)
            self.det_meta.configure(text=meta)
            self.det_exe.configure(
                text=d.get("erro") or d.get("video_id") or d.get("uri") or "")
            _W.desenhar_tile(self.det_capa, "⬇", 216, 280, grande=True,
                          subtitulo=d.get("estado") or "")
            return
        if self._em_musicas():
            self._botoes_detalhe("musica")
            try:
                self.btn_jogar.configure(text="▶  TOCAR", state="normal")
            except tk.TclError:
                pass
            if self.mus_sel is None or self.mus_sel >= len(self.musicas):
                self.det_titulo.configure(text="Nenhuma música")
                self.det_meta.configure(text="")
                self.det_exe.configure(text="")
                _W.desenhar_tile(self.det_capa, "♪", 216, 280, grande=True)
                return
            m = self.musicas[self.mus_sel]
            self.det_titulo.configure(text=core.texto_musica(m) or "Sem título")
            meta = " · ".join(x for x in (m.get("artista"), m.get("album")) if x)
            if m.get("musica_capa"):
                meta += " · 🖼" if meta else "🖼"
            self.det_meta.configure(text=meta)
            try:
                base_nome = Path(m.get("musica_path") or "").name
            except (TypeError, ValueError):
                base_nome = ""
            self.det_exe.configure(text=base_nome)
            self.det_capa.delete("all")
            try:
                alvo = core.caminho_capa(m.get("musica_capa") or "") \
                    if m.get("musica_capa") else None
            except Exception:
                alvo = None
            img = None
            if alvo is not None:
                try:
                    img = _W.carregar_miniatura(alvo, 216, 280)
                except Exception:
                    img = None
            self._img_det = img
            if img is not None:
                try:
                    self.det_capa.create_image(108, 140, image=img)
                except tk.TclError:
                    _W.desenhar_tile(self.det_capa, "♪", 216, 280, grande=True,
                                  subtitulo="música")
            else:
                _W.desenhar_tile(self.det_capa, "♪", 216, 280, grande=True,
                              subtitulo="música")
            return
        self._botoes_detalhe("jogo")
        try:
            self.btn_jogar.configure(text="▶  JOGAR", state="normal")
        except tk.TclError:
            pass
        if self.sel is None or self.sel >= len(self.jogos):
            self.det_titulo.configure(text="Nenhum jogo")
            self.det_meta.configure(text="")
            self.det_exe.configure(text="")
            _W.desenhar_tile(self.det_capa, "?", 216, 280, grande=True)
            return
        j = self.jogos[self.sel]
        self.det_titulo.configure(
            text=f"{'★ ' if j['favorito'] else ''}{j['titulo']}")
        nota = f" · nota {j['nota']}" if j.get("nota") is not None else ""
        try:
            horas_n = round(float(j["horas"] or 0), 2)
        except (TypeError, ValueError):
            horas_n = 0
        horas = f" · {horas_n:g}h" if horas_n else ""
        try:
            plat = j.get("plataforma") or core.plataforma_jogo(j)
        except Exception:
            plat = "PC"
        tags = list(j.get("etiquetas_lista") or [])
        fichas = [x for x in (j.get("game_code"), j.get("regiao")) if x]
        mods = list(j.get("mods_lista") or [])
        mods_txt = ""
        if mods:
            mods_txt = ((f"\n🎨 OFF · {', '.join(mods)}") if j.get("mods_off")
                        else (f"\n🎨 {', '.join(mods)}"))
        tex_txt = ""
        try:
            _launch = core.traduzir_para_atual(
                (j.get("launch_options") or "").strip())
            _tid = core.title_id_da_rom(_launch)
            _base = core.load_textures_dir() if _tid else None
            if _base is not None:
                if (_base / _tid).is_dir():
                    tex_txt = "\n🖼️ HD ligado"
                elif (_base / (_tid + ".off")).is_dir():
                    tex_txt = "\n🖼️ HD desligado"
        except Exception:
            tex_txt = ""
        ch_txt = ""
        try:
            _cl = core.listar_cheats(_tid) if _tid else []
            if _cl:
                _on = sum(1 for c in _cl if c["ativo"])
                ch_txt = (f"\n💥 {_on}/{len(_cl)} cheats"
                          if _on else f"\n💥 {len(_cl)} cheats off")
        except Exception:
            ch_txt = ""
        self.det_meta.configure(
            text=f"{j['status']}{nota}{horas}{core.selo_confianca(j)} · {core.provedor_nome(j)}"
            + f"\n🏷 {plat}" + (f" · {', '.join(tags)}" if tags else "")
            + (f"\n💾 {j['save_path']}" if (j.get("save_path") or "").strip() else "")
            + (f"\n🔖 {' · '.join(fichas)}" if fichas else "")
            + (f"\n🎛 preset {j['azahar_preset']}" if j.get("azahar_preset") else "")
            + mods_txt
            + tex_txt
            + ch_txt
            + (f"\n▶ {j['ultima_execucao']}" if j.get("ultima_execucao") else "")
            + (f"\n📝 {j['observacoes']}" if j.get("observacoes") else ""))
        exe = j["exe_traduzido"] or j["executable_path"] or "(sem executável)"
        marca = "●" if j["exe_existe"] else ("○" if j["executable_path"] else "–")
        self.det_exe.configure(text=f"{marca} {exe}")
        self.det_capa.delete("all")
        try:
            self.det_capa.configure(highlightthickness=2,
                                    highlightbackground=LINE)
        except tk.TclError:
            pass
        alvo = core.caminho_capa(j["capa"]) if j.get("capa") else None
        img = _W.carregar_miniatura(alvo, 216, 280) if alvo else None
        self._img_det = img
        if img is not None:
            self.det_capa.create_image(108, 140, image=img)
        else:
            _W.desenhar_tile(self.det_capa, j["titulo"], 216, 280, grande=True,
                          subtitulo=plat)
    def jogar(self):
        if self._em_downloads():
            self.abrir_pasta_dl()
            return
        if self._em_desejos():
            self.buscar_desejo_download()
            return
        if self._em_musicas():
            self.tocar_musica_selecionada()
            return
        j = self.selecionado()
        if not j:
            return
        con = self._con()
        try:
            j = self._resolver_antes_de_jogar(con, j)
            if j is None:
                return
            prep = core.preparar_lancamento(j)
            if prep.get("aviso"):
                _W.messagebox.showwarning("Preset", prep["aviso"])
            res = core.executar_monitorado(
                j, ao_fim=lambda sessao, rastreado, _gid=j["id"]:
                    self._depois(lambda: self._sessao_fim(_gid, sessao, rastreado)))
            if res.get("requer_elevacao") and _W.messagebox.askyesno(
                    "Jogar", "Esse jogo exige administrador.\nTentar com elevação (UAC)?"):
                res = core.executar_jogo_dict(j, elevar=True)
                if res.get("ok"):
                    core.marcar_execucao(con, j["id"])
                    try:
                        core.iniciar_sessao_manual(j["id"], j.get("titulo") or "")
                    except Exception as e:
                        core.log_erro("jogar", f"sessao manual nao abriu: {e}")
                    self._minimizar_janela()
                    self._aviso_barra("Executando (UAC) — ao terminar use ⏱ Registrar sessão")
                else:
                    _W.messagebox.showerror("Jogar", res.get("erro", "falha"))
            elif res.get("ok"):
                core.marcar_execucao(con, j["id"])
                if res.get("rastreado"):
                    extra = "⏱ tempo será registrado"
                else:
                    extra = "⏱ sem rastreio — sessão manual aberta; ao terminar use ⏱ Registrar sessão"
                self._minimizar_janela()
                self._aviso_barra(f"Executando ({res.get('modo')}) — {extra}")
            else:
                _W.messagebox.showerror("Jogar", res.get("erro", "falha"))
        finally:
            con.close()
        self.recarregar()
    def registrar_sessao_manual(self):
        """Fecha sessão manual: pergunta horas e soma (fallback UAC/startfile)."""
        try:
            pend = core.listar_sessoes_pendentes()
        except Exception as e:
            _W.messagebox.showerror("Sessão", f"falha ao listar: {e}")
            return
        if not pend:
            _W.messagebox.showinfo("Sessão", "Nenhuma sessão manual pendente.")
            return
        if len(pend) == 1:
            alvo = pend[0]
        else:
            lista = "\n".join(f"{i+1}. {p.get('titulo') or p.get('gid')} · {p.get('inicio')}" for i, p in enumerate(pend))
            idx = simpledialog.askinteger("Sessão manual", lista + "\nNúmero:", minvalue=1, maxvalue=len(pend), parent=self.root)
            if not idx:
                return
            alvo = pend[idx - 1]
        horas = simpledialog.askfloat("Sessão manual", f"Horas jogadas em '{alvo.get('titulo') or alvo.get('gid')}'?", minvalue=0.0, parent=self.root)
        if horas is None:
            return
        try:
            res = core.encerrar_sessao_manual(alvo["_arquivo"], float(horas), db_path=self.db_path)
        except Exception as e:
            _W.messagebox.showerror("Sessão", f"falha: {e}")
            return
        if res.get("ok"):
            self.recarregar()
            _W.messagebox.showinfo("Sessão", f"+{horas}h registradas ✓" if horas else "Sessão encerrada (sem horas).")
        else:
            _W.messagebox.showerror("Sessão", res.get("erro", "falha"))
    def _resolver_antes_de_jogar(self, con, j):
        """Perguntar-antes: emulador trocado? ROM sumida? Devolve jogo (talvez
        religado) ou None (cancelado)."""
        diag = core.diagnosticar_exe(j)
        if diag["estado"] == "trocou-emulador":
            r = _W.messagebox.askyesnocancel(
                "Jogar",
                f"O emulador gravado não existe aqui:\n{diag['gravado']}\n\n"
                f"Atual ({diag['nome']}):\n{diag['atual']}\n\n"
                "Sim = usar e gravar · Não = só desta vez · Cancelar = voltar")
            if r is None:
                return None
            if r:
                j = core.atualizar_jogo(con, j["id"],
                                        {"executable_path": "",
                                         "exe_win" if os.name == "nt" else "exe_linux": ""})
            else:
                j = {**j, "executable_path": "", "exe_win": "", "exe_linux": ""}
        drom = core.diagnosticar_rom(j)
        if drom["estado"] == "rom-ausente":
            cands = drom["candidatos"]
            escolhido = None
            if cands:
                if len(cands) == 1:
                    if _W.messagebox.askyesno("Localizar ROM", f"Religar esta entrada para:\n{cands[0]}?"):
                        escolhido = cands[0]
                else:
                    lista = "\n".join(f"{i + 1}. {p}" for i, p in enumerate(cands))
                    idx = simpledialog.askinteger("Localizar ROM", lista + "\nNúmero da ROM:",
                                                  minvalue=1, maxvalue=len(cands), parent=self.root)
                    if idx:
                        escolhido = cands[idx - 1]
            if escolhido is None:
                escolhido = filedialog.askopenfilename(title="Localizar ROM movida", parent=self.root,
                    filetypes=[("ROMs 3DS", "*.cci *.cxi *.3ds *.3dsx *.app *.elf *.axf"),
                               ("ROMs NDS", "*.nds *.dsi"), ("Todos", "*.*")])
                if escolhido and not _W.messagebox.askyesno("Localizar ROM", f"Gravar este novo caminho?\n{escolhido}"):
                    return None
            if not escolhido:
                return None
            j = core.atualizar_jogo(con, j["id"], {"launch_options": escolhido})
        return j
    def _sessao_fim(self, gid: int, sessao: float, rastreado: bool) -> None:
        """Callback da vigia (já na thread de UI): soma, recarrega, avisa na barra."""
        if not rastreado:
            return
        con = self._con()
        try:
            ok, msg = self._registrar_sessao(con, gid, sessao)
        finally:
            con.close()
        self._restaurar_janela()
        self.recarregar()
        if ok:
            self._aviso_barra(msg)
    @staticmethod
    def _registrar_sessao(con, gid: int, sessao: float) -> tuple[bool, str]:
        """Soma a sessão e devolve (ok, mensagem). Sem Tk: testável."""
        if sessao <= 0:
            return False, "Sessão curta (<30 s): nada registrado."
        r = core.adicionar_horas(con, gid, sessao)
        if not r.get("ok"):
            return False, f"Sessão não registrada: {r.get('erro')}"
        return True, f"+{r['somado']}h registradas (total {r['total']}h)."
    def excluir(self):
        if self._em_downloads():
            return
        if self._em_desejos():
            self.excluir_desejo_selecionado()
            return
        if self._em_musicas():
            self.excluir_musica_selecionada()
            return
        j = self.selecionado()
        if not j:
            return
        if not _W.messagebox.askyesno("Excluir", f"Excluir '{j['titulo']}' da biblioteca?"):
            return
        con = self._con()
        try:
            core.excluir_jogo(con, j["id"])
        except LookupError as e:
            _W.messagebox.showerror("Excluir", str(e))
        finally:
            con.close()
        self.sel = None
        self.recarregar()
    def dlg_novo(self):
        self._dlg_jogo(None)
    def dlg_editar(self):
        if self._em_musicas() or self._em_desejos() or self._em_downloads():
            return
        j = self.selecionado()
        if j:
            self._dlg_jogo(j)
    def _dlg_jogo(self, j: dict | None):
        dlg = tk.Toplevel(self.root)
        _W._titulo_escuro(dlg)
        dlg.title("Editar jogo" if j else "Adicionar jogo")
        dlg.configure(bg=BG)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.minsize(640, 0)
        campos: dict[str, tk.Variable | tk.Text] = {}

        def secao(titulo):
            fr = ttk.LabelFrame(dlg, text=f"  {titulo}  ", style="Sec.TLabelframe")
            fr.pack(fill="x", padx=12, pady=(10, 0))
            fr.grid_columnconfigure(1, weight=1)
            return fr

        def campo(pai, linha_n, rotulo, chave, valor=""):
            ttk.Label(pai, text=rotulo, style="Sec.TLabel").grid(
                row=linha_n, column=0, sticky="w", padx=(0, 8), pady=6)
            v = tk.StringVar(value=valor)
            e = ttk.Entry(pai, textvariable=v, font=("Segoe UI", 12))
            e.grid(row=linha_n, column=1, sticky="ew", pady=6)
            campos[chave] = v
            return e

        # -- jogo (só o essencial; status/nota/favorito preservados)
        fr_jogo = secao("Jogo")
        campo(fr_jogo, 0, "Título *", "titulo", (j.get("titulo") if j else "") or "")
        campo(fr_jogo, 1, "Etiquetas", "etiquetas", (j.get("etiquetas") if j else "") or "")
        ttk.Label(fr_jogo, text="Livres, separadas por vírgula (ex.: rpg, souls-like)",
                  style="Sec.TLabel", font=("Segoe UI", 11, "italic")).grid(
                      row=2, column=1, sticky="w")

        # -- execução (só o executável; resto preservado)
        fr_exe = secao("Execução")
        campo(fr_exe, 0, "Executável", "executable_path",
              (j.get("executable_path") if j else "") or "")

        def procurar_exe():
            arq = filedialog.askopenfilename(
                title="Executável do jogo",
                filetypes=[("Executáveis", "*.exe *.lnk *.sh *.AppImage"), ("Todos", "*.*")])
            if arq:
                campos["executable_path"].set(arq)

        ttk.Button(fr_exe, text="🔍", width=4, command=procurar_exe).grid(
            row=0, column=2, padx=(6, 0))

        # -- avaliação (só horas; nota preservada)
        fr_av = secao("Avaliação")
        fr_av.grid_columnconfigure(1, weight=0)
        var_horas = tk.StringVar(value="0" if not j else str((j.get("horas") or 0)))
        ttk.Label(fr_av, text="Horas", style="Sec.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=6)
        ttk.Entry(fr_av, textvariable=var_horas, width=10, font=("Segoe UI", 12)).grid(
            row=0, column=1, sticky="w", pady=6)
        campos["horas"] = var_horas

        # -- emulador (provider detectado pelo jogo; pode trocar)
        fr_emu = secao("Emulador")
        rotulos_prov = {"": "—"}
        chaves_prov = {"—": ""}
        for _ch, _pv in core.provedores().items():
            _rot = f"{_pv['nome']} · {'/'.join(_pv['sistemas'])}"
            rotulos_prov[_ch] = _rot
            chaves_prov[_rot] = _ch

        def _prov_do_jogo(jogo):
            if jogo:
                _pv = core.provedor_por_origem(jogo.get("origem") or "")
                if _pv is not None:
                    return _pv["chave"]
                _pv = core.provedor_por_extensao(
                    Path(jogo.get("launch_options") or "").suffix)
                if _pv is not None:
                    return _pv["chave"]
            return ""

        var_prov = tk.StringVar(value=rotulos_prov[_prov_do_jogo(j)])
        ttk.Label(fr_emu, text="Sistema", style="Sec.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=6)
        cmb_prov = ttk.Combobox(fr_emu, textvariable=var_prov,
                                values=list(chaves_prov),
                                state="readonly", font=("Segoe UI", 12))
        cmb_prov.grid(row=0, column=1, columnspan=2, sticky="ew", pady=6)
        fr_emu.grid_columnconfigure(1, weight=1)
        ttk.Label(fr_emu, text="Preset", style="Sec.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=6)
        preset_vals = {"azahar_preset": ((j.get("azahar_preset") or "") if j else "")}
        var_preset = tk.StringVar(value=preset_vals["azahar_preset"])
        cmb_preset = ttk.Combobox(fr_emu, textvariable=var_preset,
                                  font=("Segoe UI", 12))
        cmb_preset.grid(row=1, column=1, sticky="ew", pady=6)
        campos["azahar_preset"] = var_preset

        def _chave_sel():
            return chaves_prov.get(var_prov.get(), "")

        def _recarrega_presets():
            chave = _chave_sel()
            vals = core.listar_presets(chave) if chave else []
            cmb_preset.configure(values=vals)

        def _troca_prov(_e=None):
            _recarrega_presets()

        cmb_prov.bind("<<ComboboxSelected>>", _troca_prov)
        _recarrega_presets()

        def foto_preset():
            chave = _chave_sel()
            if not chave:
                _W.messagebox.showwarning("Preset", "Escolha o sistema primeiro.")
                return
            nome = simpledialog.askstring(
                "Preset",
                "Nome do preset (fotografa a config atual):",
                parent=dlg)
            if not nome:
                return
            r = core.salvar_preset_de_atual(nome, chave)
            if r.get("ok"):
                cmb_preset.configure(values=core.listar_presets(chave))
                var_preset.set(r["preset"])
            else:
                _W.messagebox.showwarning("Preset", r.get("erro", "falha"))

        ttk.Button(fr_emu, text="📸", width=4, command=foto_preset).grid(
            row=1, column=2, padx=(6, 0))
        ttk.Label(fr_emu, text="Mods", style="Sec.TLabel").grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=6)
        mods_sel = {"ativos": list((j.get("mods_lista") or []) if j else []),
                    "off": bool((j.get("azahar_mods_off") or 0) if j else False)}
        var_mods = tk.StringVar()
        ttk.Entry(fr_emu, textvariable=var_mods, state="readonly",
                  font=("Segoe UI", 12)).grid(row=2, column=1, sticky="ew", pady=6)
        btn_mods_off = ttk.Button(fr_emu, width=9)
        btn_mods_off.grid(row=2, column=2, padx=(6, 0))

        def _refresh_mods():
            base = ", ".join(mods_sel["ativos"]) or "—"
            var_mods.set(("OFF · " if mods_sel["off"] else "") + base)
            try:
                btn_mods_off.configure(text="Ligar" if mods_sel["off"] else "Desligar")
            except tk.TclError:
                pass

        def alternar_mods():
            mods_sel["off"] = not mods_sel["off"]
            _refresh_mods()

        btn_mods_off.configure(command=alternar_mods)

        def _tid_do_jogo():
            if not j:
                return ""
            try:
                launch = core.traduzir_para_atual(
                    (j.get("launch_options") or "").strip())
                return core.title_id_da_rom(launch)
            except Exception:
                return ""

        def gerenciar_mods():
            tid = _tid_do_jogo()
            if not tid:
                _W.messagebox.showwarning(
                    "Mods", "Salve o jogo com a ROM primeiro.")
                return
            self._janela_mods(dlg, tid, mods_sel, _refresh_mods)

        ttk.Button(fr_emu, text="…", width=4, command=gerenciar_mods).grid(
            row=2, column=3, padx=(6, 0))
        _refresh_mods()

        ttk.Label(fr_emu, text="Texturas HD",
                  style="Sec.TLabel").grid(
            row=3, column=0, sticky="w", padx=(0, 8), pady=6)
        tex_sel = {"ativo": False, "arquivos": 0, "instalado": False}
        var_tex = tk.StringVar()
        ttk.Entry(fr_emu, textvariable=var_tex, state="readonly",
                  font=("Segoe UI", 12)).grid(row=3, column=1, sticky="ew",
                                              pady=6)
        btn_tex = ttk.Button(fr_emu, width=9)
        btn_tex.grid(row=3, column=2, padx=(6, 0))

        def _refresh_tex():
            if not tex_sel["instalado"]:
                var_tex.set("—")
            else:
                base = (f"{tex_sel['arquivos']} arqs · "
                        f"{'ligado 🖼️' if tex_sel['ativo'] else 'desligado'}")
                var_tex.set(base)
            try:
                btn_tex.configure(
                    text="Desligar" if tex_sel["ativo"] else "Ligar")
            except tk.TclError:
                pass

        def _ler_tex():
            tid = _tid_do_jogo()
            if not tid:
                tex_sel.update(instalado=False, ativo=False, arquivos=0)
                _refresh_tex()
                return
            # estado barato primeiro (sem contar PNGs — 15k arqs = ~2s);
            # a contagem vem em thread como a capa.
            try:
                base = core.load_textures_dir()
                on = bool(base) and (base / tid).is_dir()
                off = bool(base) and (base / (tid + ".off")).is_dir()
            except Exception:
                on = off = False
            tex_sel.update(instalado=bool(on or off), ativo=bool(on),
                           arquivos=0)
            _refresh_tex()
            if not tex_sel["instalado"]:
                return

            def _contar(tid_fx=tid):
                try:
                    est = core.estado_textura(tid_fx)
                except Exception:
                    return

                def _aplica(est=est, tid_fx=tid_fx):
                    try:
                        if _tid_do_jogo() != tid_fx:
                            return
                    except tk.TclError:
                        return
                    tex_sel.update(
                        instalado=bool(est.get("instalado")),
                        ativo=bool(est.get("ativo")),
                        arquivos=int(est.get("arquivos") or 0))
                    _refresh_tex()
                self._depois(_aplica)
            threading.Thread(target=_contar, daemon=True).start()

        def alternar_tex():
            tid = _tid_do_jogo()
            if not tid:
                _W.messagebox.showwarning(
                    "Texturas", "Salve o jogo com a ROM primeiro.")
                return
            try:
                res = core.definir_textura(tid, not tex_sel["ativo"])
            except Exception as e:
                _W.messagebox.showwarning("Texturas", f"falha: {e}")
                return
            if not res.get("ok"):
                _W.messagebox.showwarning("Texturas", res.get("erro", "falha"))
                return
            _ler_tex()

        btn_tex.configure(command=alternar_tex)
        _ler_tex()

        ttk.Label(fr_emu, text="Cheats", style="Sec.TLabel").grid(
            row=4, column=0, sticky="w", padx=(0, 8), pady=6)
        var_cheats = tk.StringVar()
        ttk.Entry(fr_emu, textvariable=var_cheats, state="readonly",
                  font=("Segoe UI", 12)).grid(row=4, column=1, sticky="ew",
                                              pady=6)

        def _refresh_cheats():
            tid = _tid_do_jogo()
            try:
                lst = core.listar_cheats(tid) if tid else []
            except Exception:
                lst = []
            on = sum(1 for c in lst if c["ativo"])
            var_cheats.set("—" if not lst else
                           (f"{on}/{len(lst)} ativos" if on
                            else f"{len(lst)} desligados"))

        def gerenciar_cheats():
            tid = _tid_do_jogo()
            if not tid:
                _W.messagebox.showwarning(
                    "Cheats", "Salve o jogo com a ROM primeiro.")
                return
            self._janela_cheats(dlg, tid, _refresh_cheats)

        ttk.Button(fr_emu, text="…", width=4,
                   command=gerenciar_cheats).grid(row=4, column=2,
                                                 padx=(6, 0))
        _refresh_cheats()

        # -- notas
        fr_obs = secao("Observações")
        txt = tk.Text(fr_obs, height=4, bg="#0b0d12", fg=TXT, insertbackground=TXT,
                      font=("Segoe UI", 12))
        txt.pack(fill="x")
        if j and j.get("observacoes"):
            txt.insert("1.0", j.get("observacoes") or "")
        campos["observacoes"] = txt

        # -- capa
        fr_capa = secao("Capa")
        var_capa = tk.StringVar(value="")
        self._img_capa = None
        prev = None
        if j and j.get("capa"):
            alvo = core.caminho_capa(j["capa"])
            if alvo is not None:
                try:
                    img = _W.carregar_miniatura(alvo, 200, 140)
                    if img is not None:
                        self._img_capa = img
                        prev = ttk.Label(fr_capa, image=self._img_capa, background=CARD)
                        prev.grid(row=0, column=0, rowspan=2, padx=(0, 12))
                except Exception:
                    pass  # segue sem preview
        try:
            from PIL import Image  # noqa: F401
            dica_pillow = ""
        except Exception:
            dica_pillow = " (jpg/webp exigem Pillow p/ preview; png sempre funciona)"
        lbl_capa = ttk.Label(fr_capa, style="Sec.TLabel", wraplength=380,
                             justify="left",
                             text=f"{j['capa']}" if j and j.get("capa") else "Sem capa" + dica_pillow)
        lbl_capa.grid(row=0, column=1, sticky="w")

        def trocar_capa():
            arq = filedialog.askopenfilename(
                title="Capa (png/jpg/webp até 2 MB)",
                filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp *.gif")])
            if arq:
                var_capa.set(arq)
                lbl_capa.configure(text=Path(arq).name)

        ttk.Button(fr_capa, text="Escolher capa…", command=trocar_capa).grid(
            row=1, column=1, sticky="w", pady=(6, 0))

        btn_salvar = ttk.Button(dlg, text="  Salvar  ", style="Big.Accent.TButton")
        btn_salvar.pack(pady=18)

        def salvar():
            try:
                preset_vals["azahar_preset"] = var_preset.get().strip()
                dados = {
                    "titulo": campos["titulo"].get().strip(),
                    "executable_path": campos["executable_path"].get().strip(),
                    # removidos da tela: preserva o gravado (ou padrão ao criar)
                    "exe_win": ((j.get("exe_win") or "") if j else ""),
                    "exe_linux": ((j.get("exe_linux") or "") if j else ""),
                    "wine_prefix": ((j.get("wine_prefix") or "") if j else ""),
                    "status": ((j.get("status") or "backlog") if j else "backlog"),
                    "nota": ((j.get("nota")) if j else None),
                    "horas": float(var_horas.get().strip() or 0),
                    "favorito": (bool(j.get("favorito")) if j else False),
                    "launch_options": ((j.get("launch_options") or "") if j else ""),
                    "azahar_preset": preset_vals["azahar_preset"].strip(),
                    "azahar_mods": list(mods_sel["ativos"]),
                    "azahar_mods_off": 1 if mods_sel["off"] else 0,
                    "etiquetas": campos["etiquetas"].get().strip(),
                    "observacoes": txt.get("1.0", "end").strip(),
                }
            except ValueError:
                _W.messagebox.showerror("Salvar", "Horas deve ser número.")
                return
            con = self._con()
            try:
                try:
                    novo = (core.atualizar_jogo(con, j["id"], dados) if j
                            else core.criar_jogo(con, dados))
                except (ValueError, LookupError) as e:
                    _W.messagebox.showerror("Salvar", str(e))
                    return
                capa_orig = var_capa.get().strip()
                gid = novo["id"]
            finally:
                con.close()
            if not capa_orig:
                dlg.destroy()
                self.sel = None
                self.recarregar()
                _W.messagebox.showinfo("Biblioteca", "Salvo ✓")
                return
            # capa em thread: não trava a UI com arquivos de 2MB
            p = Path(capa_orig)
            if p.suffix.lower() not in core.CAPA_EXTS:
                _W.messagebox.showerror("Capa", "Use png/jpg/webp.")
                return
            try:
                btn_salvar.configure(state="disabled", text="Salvando capa…")
            except tk.TclError:
                pass

            def trabalho_capa(caminho=p, gid_capa=gid):
                try:
                    raw = caminho.read_bytes()
                except OSError as e:
                    msg = f"não consegui ler o arquivo: {e}"
                    return self._depois(lambda m=msg: _falha_capa(m))
                if len(raw) > 2_000_000:
                    return self._depois(lambda: _falha_capa("Arquivo maior que 2 MB."))
                con2 = self._con()
                try:
                    res = core.salvar_capa_bytes(con2, gid_capa, caminho.name, raw)
                except Exception as e:
                    core.log_erro("salvar-capa", f"{type(e).__name__}: {e}")
                    res = {"ok": False, "erro": f"{type(e).__name__}: {e}"}
                finally:
                    con2.close()

                def fim(res=res):
                    try:
                        dlg.destroy()
                    except tk.TclError:
                        pass
                    self.sel = None
                    self.recarregar()
                    if not res.get("ok"):
                        _W.messagebox.showerror("Capa", res.get("erro", "falha"))
                    else:
                        _W.messagebox.showinfo("Biblioteca", "Salvo ✓")
                self._depois(fim)

            def _falha_capa(msg):
                try:
                    btn_salvar.configure(state="normal", text="  Salvar  ")
                except tk.TclError:
                    pass
                _W.messagebox.showerror("Capa", msg)

            threading.Thread(target=trabalho_capa, daemon=True).start()

        btn_salvar.configure(command=salvar)
