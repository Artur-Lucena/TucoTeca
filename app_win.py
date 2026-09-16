#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minha Biblioteca de Jogos — aplicativo local Windows (tkinter, stdlib).
Visual estilo Hydra: sidebar, grade de cards com capas e painel de detalhes.
Mesmo banco e mesmas regras do terminal Linux; nada de navegador.

Uso:
    python app_win.py [--db caminho\\biblioteca.db]
    python app_win.py --selftest   # monta a UI oculta e sai (verificação)
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bib_core as core

BG = "#0f1116"
PANEL = "#16181f"
CARD = "#1c1f27"
LINE = "#2a2e39"
TXT = "#e8eaf0"
MUT = "#9aa0b2"
ACC = "#7c5cff"
OK_C = "#2ecc71"
WARN_C = "#f39c12"
BAD_C = "#e74c3c"

CARD_W, CARD_H = 132, 186
STATUS_CORES = {"backlog": MUT, "jogando": "#7aa2ff", "zerado": OK_C,
                "pausado": WARN_C, "abandonado": BAD_C}

# (rótulo, filtro_status, só_favoritos)
NAV = [("📚 Biblioteca", "", False),
       ("▶ Jogando", "jogando", False),
       ("🕹 Backlog", "backlog", False),
       ("✓ Zerados", "zerado", False),
       ("★ Favoritos", "", True)]


def carregar_miniatura(caminho: Path, largura: int = CARD_W,
                       altura: int = CARD_H) -> tk.PhotoImage | None:
    """PhotoImage reduzido da capa, ou None (só png/gif; resto vira tile)."""
    if Path(caminho).suffix.lower() not in (".png", ".gif"):
        return None
    try:
        img = tk.PhotoImage(file=str(caminho))
    except tk.TclError:
        return None
    try:
        f = max(max(1, img.width() // largura), max(1, img.height() // altura))
        return img.subsample(f, f) if f > 1 else img
    except tk.TclError:
        return None


def desenhar_tile(cv: tk.Canvas, titulo: str, w: int, h: int,
                  selecionado: bool = False, grande: bool = False):
    """Tile estilo Hydra quando não há capa: inicial do título em destaque."""
    cv.delete("all")
    cv.create_rectangle(1, 1, w - 1, h - 1, fill=CARD,
                        outline=ACC if selecionado else LINE,
                        width=3 if selecionado else 1)
    inicial = (titulo.strip()[:1] or "?").upper()
    cv.create_text(w // 2, h // 2 - (14 if grande else 8), text=inicial,
                   fill=ACC if selecionado else MUT,
                   font=("Segoe UI", 64 if grande else 44, "bold"))
    cv.create_text(w // 2, h - (26 if grande else 18), text="sem capa",
                   fill=MUT, font=("Segoe UI", 9 if grande else 8))


class App:
    def __init__(self, root: tk.Tk, db_path: Path):
        self.root = root
        self.db_path = db_path
        self.jogos: list[dict] = []
        self.sel: int | None = None
        self.nav_idx = 0
        self._deb = None
        self.cards: list[dict] = []  # {frame, jogo}
        self._imgs_cards: list = []  # retém miniaturas da grade
        self._img_det = None  # retém a capa do painel de detalhes
        root.title("🎮 Minha Biblioteca")
        root.geometry("1120x680")
        root.minsize(900, 540)
        root.configure(bg=BG)
        self._estilo()
        self._montar()
        self.recarregar()

    # -- construção
    def _estilo(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TFrame", background=BG)
        st.configure("Panel.TFrame", background=PANEL)
        st.configure("Card.TFrame", background=CARD)
        st.configure("TLabel", background=BG, foreground=TXT)
        st.configure("Panel.TLabel", background=PANEL, foreground=TXT)
        st.configure("Mut.TLabel", background=BG, foreground=MUT)
        st.configure("Title.TLabel", background=BG, foreground=TXT,
                     font=("Segoe UI", 13, "bold"))
        st.configure("Side.TButton", background=PANEL, foreground=MUT,
                     borderwidth=0, padding=8, anchor="w",
                     font=("Segoe UI", 11))
        st.map("Side.TButton", background=[("active", CARD)],
               foreground=[("active", TXT)])
        st.configure("SideAct.TButton", background=CARD, foreground=TXT,
                     borderwidth=0, padding=8, anchor="w",
                     font=("Segoe UI", 11, "bold"))
        st.configure("TButton", background=CARD, foreground=TXT,
                     borderwidth=1, padding=6)
        st.map("TButton", background=[("active", ACC)])
        st.configure("Accent.TButton", background=ACC, foreground="white",
                     borderwidth=0, padding=8, font=("Segoe UI", 11, "bold"))
        st.configure("TEntry", fieldbackground="#0b0d12", foreground=TXT,
                     borderwidth=1)
        st.configure("Vertical.TScrollbar", background=CARD)

    def _montar(self):
        # sidebar
        side = ttk.Frame(self.root, style="Panel.TFrame", width=200)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        ttk.Label(side, text="🎮 BIBLIOTECA", style="Panel.TLabel",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(14, 8))
        self.nav_btns: list[ttk.Button] = []
        for i, (rotulo, _st, _fv) in enumerate(NAV):
            b = ttk.Button(side, text=rotulo, style="Side.TButton",
                           command=lambda i=i: self._ir_nav(i))
            b.pack(fill="x", padx=8, pady=1)
            self.nav_btns.append(b)
        ttk.Label(side, text="", style="Panel.TLabel").pack(pady=4)
        ttk.Label(side, text="IMPORTAR", style="Panel.TLabel",
                  font=("Segoe UI", 9, "bold"), foreground=MUT).pack(anchor="w", padx=12)
        for rotulo, cmd in (("🔍 do Hydra", self.prev_hydra),
                            ("💽 do Disco", self.prev_scan),
                            ("🎮 ROMs 3DS", self.prev_roms),
                            ("📦 JSON…", self.importar_json)):
            ttk.Button(side, text=rotulo, style="Side.TButton",
                       command=cmd).pack(fill="x", padx=8, pady=1)
        ttk.Label(side, text="", style="Panel.TLabel").pack(pady=4)
        ttk.Label(side, text="BANCO", style="Panel.TLabel",
                  font=("Segoe UI", 9, "bold"), foreground=MUT).pack(anchor="w", padx=12)
        for rotulo, cmd in (("💾 Backup agora", self.backup),
                            ("💾 Saves 3DS", self.backup_saves),
                            ("⬇ Atualizar Azahar", self.atualizar_azahar),
                            ("💾 Exportar JSON…", self.exportar_json),
                            ("📦 Pacote…", self.exportar_pacote),
                            ("📥 Pacote…", self.importar_pacote)):
            ttk.Button(side, text=rotulo, style="Side.TButton",
                       command=cmd).pack(fill="x", padx=8, pady=1)
        self._pintar_nav()

        # coluna central
        centro = ttk.Frame(self.root)
        centro.pack(side="left", fill="both", expand=True)
        topo = ttk.Frame(centro)
        topo.pack(fill="x", padx=12, pady=(12, 4))
        self.var_q = tk.StringVar()
        self.ent_busca = ttk.Entry(topo, textvariable=self.var_q, width=36)
        self.ent_busca.pack(side="left")
        self.ent_busca.bind("<KeyRelease>", self._ao_digitar)
        ttk.Label(topo, text="  🔎 buscar", style="Mut.TLabel").pack(side="left")
        self.lbl_cont = ttk.Label(centro, text="", style="Mut.TLabel")
        self.lbl_cont.pack(anchor="w", padx=14)
        self.canvas = tk.Canvas(centro, bg=BG, highlightthickness=0)
        self.vscroll = ttk.Scrollbar(centro, orient="vertical",
                                     command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vscroll.set)
        self.vscroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=6)
        self.grade = ttk.Frame(self.canvas)
        self._win_grade = self.canvas.create_window((0, 0), window=self.grade, anchor="nw")
        self.grade.bind("<Configure>", self._ao_mudar_grade)
        self.canvas.bind("<Configure>", self._ao_redimensionar)
        self.canvas.bind_all("<MouseWheel>", self._rodar, add="+")
        self.lbl_vazio = ttk.Label(centro, text="", style="Mut.TLabel")

        # painel de detalhes
        det = ttk.Frame(self.root, style="Panel.TFrame", width=272)
        det.pack(side="right", fill="y")
        det.pack_propagate(False)
        self.det_capa = tk.Canvas(det, width=200, height=260, bg=PANEL,
                                  highlightthickness=0)
        self.det_capa.pack(padx=16, pady=(16, 8))
        self.det_titulo = ttk.Label(det, text="", style="Title.TLabel",
                                    wraplength=240)
        self.det_titulo.pack(anchor="w", padx=16)
        self.det_meta = ttk.Label(det, text="", style="Mut.TLabel",
                                  background=PANEL, wraplength=240,
                                  justify="left")
        self.det_meta.pack(anchor="w", padx=16, pady=(4, 2))
        self.det_exe = ttk.Label(det, text="", style="Mut.TLabel",
                                 background=PANEL, wraplength=240,
                                 justify="left", font=("Segoe UI", 8))
        self.det_exe.pack(anchor="w", padx=16, pady=(0, 8))
        ttk.Button(det, text="▶  JOGAR", style="Accent.TButton",
                   command=self.jogar).pack(fill="x", padx=16, pady=2)
        lin = ttk.Frame(det, style="Panel.TFrame")
        lin.pack(fill="x", padx=16, pady=2)
        ttk.Button(lin, text="✏ Editar", command=self.dlg_editar).pack(
            side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(lin, text="🗑 Excluir", command=self.excluir).pack(
            side="left", expand=True, fill="x", padx=(2, 0))
        ttk.Button(det, text="+ Adicionar jogo", command=self.dlg_novo).pack(
            fill="x", padx=16, pady=(8, 2))
        self.root.bind("<Control-n>", lambda _e: self.dlg_novo())
        self.root.bind("<Control-f>", lambda _e: self.ent_busca.focus_set())
        self.canvas.bind("<Return>", lambda _e: self.jogar())
        self.canvas.bind("<Delete>", lambda _e: self.excluir())

    # -- navegação / grade
    def _pintar_nav(self):
        for i, b in enumerate(self.nav_btns):
            b.configure(style="SideAct.TButton" if i == self.nav_idx else "Side.TButton")

    def _ir_nav(self, i: int):
        self.nav_idx = i
        self._pintar_nav()
        self.recarregar()

    def _ao_digitar(self, _e=None):
        if self._deb is not None:  # debounce: 1 recarga após parar de digitar
            try:
                self.root.after_cancel(self._deb)
            except tk.TclError:
                pass
        self._deb = self.root.after(250, self.recarregar)

    def _ao_mudar_grade(self, _e=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _ao_redimensionar(self, e):
        self.canvas.itemconfig(self._win_grade, width=e.width)
        self._reorganizar()

    def _rodar(self, e):
        try:
            alvo = str(e.widget)
        except Exception:
            return
        base = str(self.canvas)
        if alvo != base and not alvo.startswith(base + "."):
            return  # scroll sobre diálogos/outros painéis não move a grade
        try:
            self.canvas.yview_scroll(-int(e.delta / 120), "units")
        except tk.TclError:
            pass

    def _reorganizar(self):
        larg = max(200, self.canvas.winfo_width())
        cols = max(1, larg // (CARD_W + 24))
        for i, c in enumerate(self.cards):
            c["frame"].grid(row=i // cols, column=i % cols, padx=12, pady=10)

    # -- dados
    def _con(self):
        return core.get_db(self.db_path)

    def recarregar(self):
        _rot, status, fav = NAV[self.nav_idx]
        con = self._con()
        try:
            self.jogos = core.listar_jogos(
                con, q=self.var_q.get().strip(), status=status, favorito=fav)
        finally:
            con.close()
        for w in self.grade.winfo_children():
            w.destroy()
        self.cards = []
        self._imgs_cards = []
        for j in self.jogos:
            self.cards.append(self._criar_card(j))
        self._reorganizar()
        if self.sel is None or self.sel >= len(self.jogos):
            self.sel = 0 if self.jogos else None
        self._pintar_selecao()
        self.mostrar_detalhe()
        n = len(self.jogos)
        az = core.azahar_status()
        az_txt = "🎮 Azahar ✓" if az["instalado"] and az["chaves"] else (
            "🎮 Azahar !" if az["instalado"] else "🎮 Azahar ✗")
        self.lbl_cont.configure(text=f"{n} jogo(s) · {az_txt}")
        if n == 0:
            self.lbl_vazio.configure(
                text="Nada aqui — importe do Hydra ou faça um scan do disco. 📥")
            self.lbl_vazio.pack(anchor="w", padx=14)
        else:
            self.lbl_vazio.pack_forget()

    def _criar_card(self, j: dict) -> dict:
        fr = ttk.Frame(self.grade, style="Card.TFrame", cursor="hand2")
        img = None
        if j.get("capa"):
            alvo = core.caminho_capa(j["capa"])
            if alvo is not None:
                img = carregar_miniatura(alvo)
        if img is not None:
            self._imgs_cards.append(img)
            lb = tk.Label(fr, image=img, bg=CARD, cursor="hand2")
            lb.pack(padx=6, pady=(6, 2))
            fr._imgw = lb  # type: ignore[attr-defined]
        else:
            cv = tk.Canvas(fr, width=CARD_W, height=CARD_H, bg=CARD,
                           highlightthickness=0, cursor="hand2")
            cv.pack(padx=6, pady=(6, 2))
            desenhar_tile(cv, j["titulo"], CARD_W, CARD_H)
            fr._tile = cv  # type: ignore[attr-defined]
            fr._imgw = cv  # type: ignore[attr-defined]
        t = tk.Label(fr, text=f"{'★ ' if j['favorito'] else ''}{j['titulo']}",
                     bg=CARD, fg=TXT, wraplength=CARD_W + 8,
                     font=("Segoe UI", 10, "bold"), cursor="hand2")
        t.pack()
        cor = STATUS_CORES.get(j["status"], MUT)
        horas = f" · {j['horas']}h" if j["horas"] else ""
        m = tk.Label(fr, text=f"{j['status']}{horas}", bg=CARD, fg=cor,
                     font=("Segoe UI", 9), cursor="hand2")
        m.pack(pady=(0, 6))
        for w in (fr, t, m, getattr(fr, "_imgw", None)):
            if w is None:
                continue
            w.bind("<Button-1>", lambda e: self._clicar(e))
            w.bind("<Double-Button-1>", lambda _e: self.jogar())
            w.bind("<Button-3>", lambda e: self._menu_ctx(e))
            w.bind("<Enter>", lambda _e, t=t: t.configure(foreground=ACC))
            w.bind("<Leave>", lambda _e, t=t: t.configure(foreground=TXT))
        return {"frame": fr, "jogo": j}

    def _indice_do_widget(self, w) -> int | None:
        while w is not None:
            for i, c in enumerate(self.cards):
                if c["frame"] == w or getattr(w, "_card", None) == c["frame"]:
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
        for i, c in enumerate(self.cards):
            fr = c["frame"]
            sel = (i == self.sel)
            fr.configure(style="Card.TFrame")
            for w in fr.winfo_children():
                if isinstance(w, tk.Canvas) and w not in (self.det_capa,):
                    desenhar_tile(w, c["jogo"]["titulo"], CARD_W, CARD_H,
                                  selecionado=sel)

    # -- detalhe / seleção
    def selecionado(self) -> dict | None:
        if self.sel is None or self.sel >= len(self.jogos):
            messagebox.showinfo("Biblioteca", "Selecione um jogo na grade.")
            return None
        return self.jogos[self.sel]

    def mostrar_detalhe(self):
        if self.sel is None or self.sel >= len(self.jogos):
            self.det_titulo.configure(text="Nenhum jogo")
            self.det_meta.configure(text="")
            self.det_exe.configure(text="")
            desenhar_tile(self.det_capa, "?", 200, 260, grande=True)
            return
        j = self.jogos[self.sel]
        self.det_titulo.configure(
            text=f"{'★ ' if j['favorito'] else ''}{j['titulo']}")
        nota = f" · nota {j['nota']}" if j.get("nota") is not None else ""
        horas = f" · {j['horas']}h" if j["horas"] else ""
        fichas = [x for x in (j.get("game_code"), j.get("regiao")) if x]
        self.det_meta.configure(
            text=f"{j['status']}{nota}{horas} · {core.provedor_nome(j)}"
            + (f"\n🔖 {' · '.join(fichas)}" if fichas else "")
            + (f"\n🎛 preset {j['azahar_preset']}" if j.get("azahar_preset") else "")
            + (f"\n▶ {j['ultima_execucao']}" if j.get("ultima_execucao") else "")
            + (f"\n📝 {j['observacoes']}" if j.get("observacoes") else ""))
        exe = j["exe_traduzido"] or j["executable_path"] or "(sem executável)"
        marca = "●" if j["exe_existe"] else ("○" if j["executable_path"] else "–")
        self.det_exe.configure(text=f"{marca} {exe}")
        self.det_capa.delete("all")
        alvo = core.caminho_capa(j["capa"]) if j.get("capa") else None
        img = carregar_miniatura(alvo, 200, 260) if alvo else None
        self._img_det = img
        if img is not None:
            self.det_capa.create_image(100, 130, image=img)
        else:
            desenhar_tile(self.det_capa, j["titulo"], 200, 260, grande=True)

    # -- ações
    def jogar(self):
        j = self.selecionado()
        if not j:
            return
        prep = core.preparar_lancamento(j)
        if prep.get("aviso"):
            messagebox.showwarning("Preset Azahar", prep["aviso"])
        con = self._con()
        try:
            res = core.executar_monitorado(
                j, ao_fim=lambda sessao, rastreado, _gid=j["id"]:
                    self._depois(lambda: self._sessao_fim(_gid, sessao, rastreado)))
            if res.get("requer_elevacao") and messagebox.askyesno(
                    "Jogar", "Esse jogo exige administrador.\nTentar com elevação (UAC)?"):
                res = core.executar_jogo_dict(j, elevar=True)
                if res.get("ok"):
                    core.marcar_execucao(con, j["id"])
                    messagebox.showinfo("Jogar", "Executando ✓ (UAC — horas manuais)")
                else:
                    messagebox.showerror("Jogar", res.get("erro", "falha"))
            elif res.get("ok"):
                core.marcar_execucao(con, j["id"])
                extra = " ⏱ tempo será registrado" if res.get("rastreado") else ""
                messagebox.showinfo("Jogar", f"Executando ✓ ({res.get('modo')}){extra}")
            else:
                messagebox.showerror("Jogar", res.get("erro", "falha"))
        finally:
            con.close()
        self.recarregar()

    def _sessao_fim(self, gid: int, sessao: float, rastreado: bool) -> None:
        """Callback da vigia (já na thread de UI): soma, recarrega, avisa."""
        if not rastreado:
            return
        con = self._con()
        try:
            ok, msg = self._registrar_sessao(con, gid, sessao)
        finally:
            con.close()
        self.recarregar()
        if ok:
            messagebox.showinfo("Sessão registrada", msg)

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
        j = self.selecionado()
        if not j:
            return
        if not messagebox.askyesno("Excluir", f"Excluir '{j['titulo']}' da biblioteca?"):
            return
        con = self._con()
        try:
            core.excluir_jogo(con, j["id"])
        except LookupError as e:
            messagebox.showerror("Excluir", str(e))
        finally:
            con.close()
        self.sel = None
        self.recarregar()

    def dlg_novo(self):
        self._dlg_jogo(None)

    def dlg_editar(self):
        j = self.selecionado()
        if j:
            self._dlg_jogo(j)

    def _dlg_jogo(self, j: dict | None):
        dlg = tk.Toplevel(self.root)
        dlg.title("Editar jogo" if j else "Adicionar jogo")
        dlg.configure(bg=BG)
        dlg.transient(self.root)
        dlg.grab_set()
        campos: dict[str, tk.Variable | tk.Text] = {}

        def linha(rotulo, chave, valor="", largura=60):
            ttk.Label(dlg, text=rotulo).pack(anchor="w", padx=10, pady=(6, 0))
            v = tk.StringVar(value=valor)
            ttk.Entry(dlg, textvariable=v, width=largura).pack(fill="x", padx=10)
            campos[chave] = v

        linha("Título *", "titulo", j["titulo"] if j else "")
        linha("Executável", "executable_path", j["executable_path"] if j else "")

        def procurar_exe():
            arq = filedialog.askopenfilename(
                title="Executável do jogo",
                filetypes=[("Executáveis", "*.exe *.lnk *.sh *.AppImage"), ("Todos", "*.*")])
            if arq:
                campos["executable_path"].set(arq)

        ttk.Button(dlg, text="Procurar...", command=procurar_exe).pack(anchor="e", padx=10)
        linha("Executável Windows (vazio = usa o de cima)", "exe_win",
              j["exe_win"] if j else "")
        linha("Executável Linux (vazio = usa o de cima)", "exe_linux",
              j["exe_linux"] if j else "")
        ttk.Label(dlg, text="Status").pack(anchor="w", padx=10, pady=(6, 0))
        var_st = tk.StringVar(value=j["status"] if j else "backlog")
        ttk.Combobox(dlg, textvariable=var_st, values=list(core.STATUS_VALIDOS),
                     state="readonly").pack(anchor="w", padx=10)
        campos["status"] = var_st
        frow = ttk.Frame(dlg)
        frow.pack(fill="x", padx=10, pady=6)
        var_nota = tk.StringVar(value="" if not j or j["nota"] is None else str(j["nota"]))
        var_horas = tk.StringVar(value="0" if not j else str(j["horas"] or 0))
        var_fav = tk.BooleanVar(value=bool(j and j["favorito"]))
        ttk.Label(frow, text="Nota 0–10").pack(side="left")
        ttk.Entry(frow, textvariable=var_nota, width=6).pack(side="left", padx=(2, 10))
        ttk.Label(frow, text="Horas").pack(side="left")
        ttk.Entry(frow, textvariable=var_horas, width=8).pack(side="left", padx=(2, 10))
        ttk.Checkbutton(frow, text="★ favorito", variable=var_fav).pack(side="left")
        campos["nota"], campos["horas"], campos["favorito"] = var_nota, var_horas, var_fav
        linha("Opções de lançamento", "launch_options", j["launch_options"] if j else "")
        ttk.Label(dlg, text="Preset Azahar (só ROMs 3DS; vazio = nenhum)").pack(
            anchor="w", padx=10, pady=(6, 0))
        var_preset = tk.StringVar(
            value=(j.get("azahar_preset") if j else "") or "")
        cmb_preset = ttk.Combobox(dlg, textvariable=var_preset,
                                  values=core.listar_presets())
        cmb_preset.pack(fill="x", padx=10)
        campos["azahar_preset"] = var_preset

        def foto_preset():
            nome = simpledialog.askstring(
                "Preset Azahar",
                "Nome do preset (fotografa a config atual do Azahar):",
                parent=dlg)
            if not nome:
                return
            r = core.salvar_preset_de_atual(nome)
            if r.get("ok"):
                cmb_preset.configure(values=core.listar_presets())
                var_preset.set(r["preset"])
            else:
                messagebox.showwarning("Preset Azahar", r.get("erro", "falha"))

        ttk.Button(dlg, text="📸 Fotografar config atual como preset...",
                   command=foto_preset).pack(anchor="e", padx=10)
        ttk.Label(dlg, text="Observações").pack(anchor="w", padx=10, pady=(6, 0))
        txt = tk.Text(dlg, height=3, bg="#0b0d12", fg=TXT, insertbackground=TXT)
        txt.pack(fill="x", padx=10)
        if j and j["observacoes"]:
            txt.insert("1.0", j["observacoes"])
        campos["observacoes"] = txt

        var_capa = tk.StringVar(value="")
        lbl_capa = ttk.Label(dlg, text=f"Capa atual: {j['capa']}" if j and j.get("capa") else "")
        lbl_capa.pack(anchor="w", padx=10)
        self._img_capa = None
        if j and j.get("capa"):
            alvo = core.caminho_capa(j["capa"])
            if alvo is not None and alvo.suffix.lower() in (".png", ".gif"):
                try:
                    self._img_capa = tk.PhotoImage(file=str(alvo))
                    ttk.Label(dlg, image=self._img_capa).pack(anchor="w", padx=10)
                except tk.TclError:
                    pass  # mantém só o nome do arquivo

        def trocar_capa():
            arq = filedialog.askopenfilename(
                title="Capa (png/jpg/webp até 2 MB)",
                filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp")])
            if arq:
                var_capa.set(arq)
                lbl_capa.configure(text=f"Nova capa: {Path(arq).name}")

        ttk.Button(dlg, text="Escolher capa...", command=trocar_capa).pack(anchor="e", padx=10)

        def salvar():
            try:
                nota_txt = var_nota.get().strip()
                dados = {
                    "titulo": campos["titulo"].get().strip(),
                    "executable_path": campos["executable_path"].get().strip(),
                    "exe_win": campos["exe_win"].get().strip(),
                    "exe_linux": campos["exe_linux"].get().strip(),
                    "status": var_st.get(),
                    "nota": None if nota_txt == "" else int(nota_txt),
                    "horas": float(var_horas.get().strip() or 0),
                    "favorito": var_fav.get(),
                    "wine_prefix": "",
                    "launch_options": campos["launch_options"].get().strip(),
                    "azahar_preset": campos["azahar_preset"].get().strip(),
                    "observacoes": txt.get("1.0", "end").strip(),
                }
            except ValueError:
                messagebox.showerror("Salvar", "Nota deve ser inteiro 0–10; horas, número.")
                return
            con = self._con()
            try:
                try:
                    novo = (core.atualizar_jogo(con, j["id"], dados) if j
                            else core.criar_jogo(con, dados))
                except (ValueError, LookupError) as e:
                    messagebox.showerror("Salvar", str(e))
                    return
                if var_capa.get():
                    p = Path(var_capa.get())
                    if p.suffix.lower() not in core.CAPA_EXTS:
                        messagebox.showerror("Capa", "Use png/jpg/webp.")
                        return
                    try:
                        raw = p.read_bytes()
                    except OSError as e:
                        messagebox.showerror("Capa", f"não consegui ler o arquivo: {e}")
                        return
                    if len(raw) > 2_000_000:
                        messagebox.showerror("Capa", "Arquivo maior que 2 MB.")
                        return
                    res = core.salvar_capa(con, novo["id"], p.name,
                                           base64.b64encode(raw).decode())
                    if not res.get("ok"):
                        messagebox.showerror("Capa", res.get("erro", "falha"))
                        return
            finally:
                con.close()
            dlg.destroy()
            self.sel = None
            self.recarregar()
            messagebox.showinfo("Biblioteca", "Salvo ✓")

        ttk.Button(dlg, text="Salvar", command=salvar,
                   style="Accent.TButton").pack(pady=10)

    # -- preview / importação
    def _dlg_prev(self, titulo: str, sub: str, itens: list[dict]):
        dlg = tk.Toplevel(self.root)
        dlg.title(titulo)
        dlg.configure(bg=BG)
        dlg.geometry("700x480")
        dlg.transient(self.root)
        dlg.grab_set()
        ttk.Label(dlg, text=sub, wraplength=660).pack(anchor="w", padx=10, pady=6)
        lb = tk.Listbox(dlg, selectmode="multiple", bg="#0b0d12", fg=TXT,
                        selectbackground=ACC, font=("Segoe UI", 10))
        lb.pack(fill="both", expand=True, padx=10)
        for i, it in enumerate(itens):
            bola = "●" if it["exe_existe"] else "○"
            tag = f" [{it['regiao']}]" if it.get("regiao") else ""
            lb.insert("end", f"{bola} [{it['score']:.2f}] {it['titulo']}{tag} — {it['origem']}"
                             + (f" · {it['shop']}" if it.get("shop") else ""))
            if it["score"] >= 0.3:
                lb.selection_set(i)

        def importar():
            idx = list(lb.curselection())
            if not idx:
                messagebox.showinfo(titulo, "Nada selecionado.")
                return
            sel = [itens[i] for i in idx]
            con = self._con()
            try:
                res = core.importar_lista(con, sel)
            finally:
                con.close()
            dlg.destroy()
            self.sel = None
            self.recarregar()
            messagebox.showinfo(titulo, f"Importados {res['novos']} "
                                        f"(total {res['total_no_banco']})")

        ttk.Button(dlg, text="Importar selecionados", command=importar,
                   style="Accent.TButton").pack(pady=8)

    def prev_hydra(self):
        db, itens = core.preview_hydra()
        if db is None:
            messagebox.showwarning("Hydra", "hydra-db não encontrado neste PC.")
            return
        self._dlg_prev("Preview — Hydra", f"{len(itens)} achado(s) em {db}. "
                                          "Pré-marcados: score ≥ 0.3.", itens)

    def prev_scan(self):
        padrao = core.default_scan_roots()
        resp = messagebox.askquestion(
            "Scan disco", "Varrer as raízes padrão (só leitura)?\n"
            + "; ".join(padrao) + "\n\nSim = padrão · Não = escolher pasta")
        if resp == "no":
            pasta = filedialog.askdirectory(title="Pasta para varrer")
            if not pasta:
                return
            roots = [pasta]
        else:
            roots = padrao
        prog = tk.Toplevel(self.root)
        prog.title("Scan disco")
        prog.transient(self.root)
        ttk.Label(prog, text="Varrendo disco (só leitura)...").pack(padx=24, pady=24)
        prog.update()

        def trabalho():
            def na_ui(fn):
                try:
                    self.root.after(0, fn)
                except tk.TclError:
                    pass  # janela fechada no meio do scan

            def falhou(e):
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                messagebox.showerror("Scan disco", f"falha na varredura: {e}")

            try:
                _roots_u, itens, info = core.preview_scan(roots)
            except Exception as e:
                na_ui(lambda: falhou(e))
                return

            def pronto():
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                sub = f"{len(itens)} achado(s)."
                if info.get("truncado"):
                    sub += " LISTA PARCIAL (teto de varredura)."
                self._dlg_prev("Preview — Disco",
                               sub + " Pré-marcados: score ≥ 0.3.", itens)
            na_ui(pronto)

        threading.Thread(target=trabalho, daemon=True).start()

    def prev_roms(self):
        emu = core.default_emu_3ds()
        if not emu:
            arq = filedialog.askopenfilename(
                title="Onde está o Azahar?",
                filetypes=[("Executáveis", "*.exe *.AppImage"), ("Todos", "*.*")])
            if not arq:
                return
            emu = arq
        prog = tk.Toplevel(self.root)
        prog.title("ROMs 3DS")
        prog.transient(self.root)
        ttk.Label(prog, text="Procurando ROMs (só leitura)...").pack(padx=24, pady=24)
        prog.update()

        def trabalho():
            def na_ui(fn):
                try:
                    self.root.after(0, fn)
                except tk.TclError:
                    pass  # janela fechada no meio do scan

            def falhou(e):
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                messagebox.showerror("ROMs 3DS", f"falha na busca: {e}")

            try:
                _roots_u, itens, info, emu_u = core.preview_roms(None, emu)
            except Exception as e:
                na_ui(lambda: falhou(e))
                return

            def pronto():
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                sub = f"{len(itens)} achado(s) [{emu_u or 'sem emu'}]."
                if info.get("truncado"):
                    sub += " LISTA PARCIAL (teto de varredura)."
                self._dlg_prev("Preview — ROMs 3DS",
                               sub + " Pré-marcados: score ≥ 0.3.", itens)
            na_ui(pronto)

        threading.Thread(target=trabalho, daemon=True).start()

    def backup_saves(self):
        try:
            res = core.backup_saves_azahar()
        except Exception as e:
            messagebox.showerror("Saves 3DS", f"falha: {e}")
            return
        if res.get("ok"):
            messagebox.showinfo("Saves 3DS",
                                f"{res['arquivos']} arquivo(s)\n{res['arquivo']}")
        else:
            messagebox.showwarning("Saves 3DS", res.get("erro", "falha"))

    def _depois(self, fn):
        try:
            self.root.after(0, fn)
        except tk.TclError:
            pass  # janela fechada

    def atualizar_azahar(self):
        prog = tk.Toplevel(self.root)
        prog.title("Azahar")
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
            info = core.azahar_release_info()
            if info.get("erro"):
                return self._depois(lambda: (prog.destroy(), messagebox.showerror(
                    "Azahar", info["erro"])))
            local = core.azahar_versao_local()
            tag = info.get("tag") or "?"

            def decidir():
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                if local and local == tag:
                    messagebox.showinfo("Azahar", f"Já está na {tag} ✓")
                    return
                mb = round((info.get("size") or 0) / 1048576)
                if not messagebox.askyesno(
                        "Azahar",
                        f"Instalada: {local or '?'} → remota: {tag} (~{mb} MB).\n"
                        "Baixar e instalar agora? (demora alguns minutos)"):
                    return
                self._baixar_azahar(info)

            self._depois(decidir)

        threading.Thread(target=trabalho, daemon=True).start()

    def _baixar_azahar(self, info):
        prog = tk.Toplevel(self.root)
        prog.title("Azahar")
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
                self._depois(lambda: lbl.configure(text=txt))

            res = core.azahar_instalar(info, progresso=andamento)

            def fim():
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                if res.get("ok"):
                    messagebox.showinfo("Azahar", f"{res.get('tag')} instalado ✓")
                else:
                    messagebox.showerror("Azahar", res.get("erro", "falha"))
                self.recarregar()

            self._depois(fim)

        threading.Thread(target=trabalho, daemon=True).start()

    def backup(self):
        try:
            res = core.fazer_backup(self.db_path)
        except Exception as e:
            messagebox.showerror("Backup", f"backup falhou: {e}")
            return
        messagebox.showinfo("Backup", f"Backup ok: {res['jogos']} jogo(s)\n{res['db']}")

    def exportar_json(self):
        dest = filedialog.asksaveasfilename(
            title="Exportar biblioteca", defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="biblioteca.json")
        if not dest:
            return
        con = self._con()
        try:
            jogos = core.listar_jogos(con)
            dados = {"exportado_em": core.agora_iso(), "jogos": jogos}
        finally:
            con.close()
        try:
            Path(dest).write_text(json.dumps(dados, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
        except OSError as e:
            messagebox.showerror("Exportar", f"falha ao gravar: {e}")
            return
        messagebox.showinfo("Exportar", f"Exportados {len(jogos)} jogo(s).")

    def importar_json(self):
        arq = filedialog.askopenfilename(
            title="Importar JSON", filetypes=[("JSON", "*.json")])
        if not arq:
            return
        try:
            dados = json.loads(Path(arq).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            messagebox.showerror("Importar", f"JSON inválido: {e}")
            return
        lista = dados if isinstance(dados, list) else dados.get("jogos", [])
        if not isinstance(lista, list):
            messagebox.showerror("Importar", "JSON deve ser lista ou {jogos:[...]}.")
            return
        con = self._con()
        try:
            res = core.importar_lista(con, lista)
        finally:
            con.close()
        self.sel = None
        self.recarregar()
        messagebox.showinfo("Importar", f"Novos: {res['novos']} "
                                        f"(total {res['total_no_banco']}).")

    def exportar_pacote(self):
        dest = filedialog.asksaveasfilename(
            title="Pacote portátil (banco + capas + presets + saves 3DS)",
            defaultextension=".zip", filetypes=[("ZIP", "*.zip")],
            initialfile="biblioteca-pacote.zip")
        if not dest:
            return
        try:
            res = core.exportar_pacote(dest, db_path=self.db_path, incluir_saves=True)
        except Exception as e:
            messagebox.showerror("Pacote", f"falha: {e}")
            return
        if not res.get("ok"):
            messagebox.showerror("Pacote", res.get("erro", "falha"))
            return
        kb = res["bytes"] // 1024
        messagebox.showinfo("Pacote",
                            f"{res['jogos']} jogo(s) · {res['arquivos']} arquivo(s) · "
                            f"{kb} KB{' · +saves 3DS' if res['inclui_saves'] else ''}\n"
                            f"{res['destino']}")

    def importar_pacote(self):
        arq = filedialog.askopenfilename(
            title="Pacote portátil", filetypes=[("ZIP", "*.zip")])
        if not arq:
            return
        try:
            res = core.importar_pacote(
                arq, db_path=self.db_path,
                restaurar_saves=messagebox.askyesno(
                    "Pacote", "Restaurar os saves 3DS do pacote?"))
        except Exception as e:
            messagebox.showerror("Pacote", f"falha: {e}")
            return
        if not res.get("ok"):
            messagebox.showerror("Pacote", res.get("erro", "falha"))
            return
        self.sel = None
        self.recarregar()
        messagebox.showinfo("Pacote",
                            f"Novos: {res['novos']} (total {res['total_no_banco']}) · "
                            f"capas {res['capas']} · presets {res['presets']} · "
                            f"saves {res['saves']}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Minha Biblioteca de Jogos — app Windows (tkinter)")
    ap.add_argument("--db", default=str(core.DEFAULT_DB))
    ap.add_argument("--selftest", action="store_true",
                    help="monta a UI oculta, recarrega e sai")
    args = ap.parse_args(argv)
    core.garantir_dirs()
    core.get_db(Path(args.db)).close()
    root = tk.Tk()
    app = App(root, Path(args.db))
    if args.selftest:
        root.withdraw()
        root.update()
        n = len(app.jogos)
        ncards = len(app.cards)
        root.destroy()
        print(f"[ok] selftest: UI montada, {n} jogo(s), {ncards} card(s)")
        return 0
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
