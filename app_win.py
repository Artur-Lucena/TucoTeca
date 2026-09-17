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
import os
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
        self.filtro_prov: str | None = None  # chave do provider (fundo, não jogo)
        self.prov_btns: dict[str, ttk.Button] = {}
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
        ttk.Label(side, text="PROVEDORES", style="Panel.TLabel",
                  font=("Segoe UI", 9, "bold"), foreground=MUT).pack(anchor="w", padx=12)
        for chave in core.provedores():
            b = ttk.Button(side, text=chave, style="Side.TButton",
                           command=lambda c=chave: self._ir_prov(c))
            b.pack(fill="x", padx=8, pady=1)
            self.prov_btns[chave] = b
        ttk.Label(side, text="", style="Panel.TLabel").pack(pady=4)
        ttk.Label(side, text="IMPORTAR", style="Panel.TLabel",
                  font=("Segoe UI", 9, "bold"), foreground=MUT).pack(anchor="w", padx=12)
        for rotulo, cmd in (("📥 Importar…", self.importar_unificado),):
            ttk.Button(side, text=rotulo, style="Side.TButton",
                       command=cmd).pack(fill="x", padx=8, pady=1)
        ttk.Label(side, text="", style="Panel.TLabel").pack(pady=4)
        ttk.Label(side, text="BANCO", style="Panel.TLabel",
                  font=("Segoe UI", 9, "bold"), foreground=MUT).pack(anchor="w", padx=12)
        for rotulo, cmd in (("💾 Backup agora", self.backup),
                            ("💾 Saves 3DS", self.backup_saves),
                            ("⬇ Atualizar Azahar", self.atualizar_azahar),
                            ("💾 Exportar JSON…", self.exportar_json),
                            ("📦 Pacote…", self.exportar_pacote)):
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
        for chave, b in self.prov_btns.items():
            b.configure(style="SideAct.TButton" if chave == self.filtro_prov else "Side.TButton")

    def _ir_nav(self, i: int):
        self.nav_idx = i
        self._pintar_nav()
        self.recarregar()

    def _ir_prov(self, chave: str):
        self.filtro_prov = None if self.filtro_prov == chave else chave
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
            if self.filtro_prov:
                self.jogos = core.jogos_do_provedor(self.jogos, self.filtro_prov)
            for r in core.provedores_resumo(con):
                b = self.prov_btns.get(r["chave"])
                if b is not None:
                    marca = "✓" if r["instalado"] else "!"
                    b.configure(text=f"🎮{marca} {r['nome']} · {r['n']}")
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
            self.lbl_vazio.configure(text="Nada aqui — use 📥 Importar…")
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
        con = self._con()
        try:
            j = self._resolver_antes_de_jogar(con, j)
            if j is None:
                return
            prep = core.preparar_lancamento(j)
            if prep.get("aviso"):
                messagebox.showwarning("Preset Azahar", prep["aviso"])
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

    def _resolver_antes_de_jogar(self, con, j):
        """Perguntar-antes: emulador trocado? ROM sumida? Devolve jogo (talvez
        religado) ou None (cancelado)."""
        diag = core.diagnosticar_exe(j)
        if diag["estado"] == "trocou-emulador":
            r = messagebox.askyesnocancel(
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
            launch = (j.get("launch_options") or "").strip()
            cands = drom["candidatos"]
            escolhido = None
            if cands:
                if len(cands) == 1:
                    if messagebox.askyesno("Localizar ROM", f"Religar esta entrada para:\n{cands[0]}?"):
                        escolhido = cands[0]
                else:
                    lista = "\n".join(f"{i + 1}. {p}" for i, p in enumerate(cands))
                    idx = simpledialog.askinteger("Localizar ROM", lista + "\nNúmero da ROM:",
                                                  minvalue=1, maxvalue=len(cands), parent=self.root)
                    if idx:
                        escolhido = cands[idx - 1]
            if escolhido is None:
                escolhido = filedialog.askopenfilename(title="Localizar ROM movida", parent=self.root,
                    filetypes=[("ROMs 3DS", "*.cci *.cxi *.3ds *.3dsx *.app *.elf *.axf"), ("Todos", "*.*")])
                if escolhido and not messagebox.askyesno("Localizar ROM", f"Gravar este novo caminho?\n{escolhido}"):
                    return None
            if not escolhido:
                return None
            j = core.atualizar_jogo(con, j["id"], {"launch_options": escolhido})
        return j

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
        dlg.minsize(540, 0)
        campos: dict[str, tk.Variable | tk.Text] = {}

        def secao(titulo):
            fr = ttk.LabelFrame(dlg, text=f" {titulo} ", padding=(10, 6))
            fr.pack(fill="x", padx=10, pady=(8, 0))
            return fr

        def linha(pai, rotulo, chave, valor="", largura=40):
            ttk.Label(pai, text=rotulo, width=16, anchor="w").grid(
                row=linha.n, column=0, sticky="w", pady=2)
            v = tk.StringVar(value=valor)
            ttk.Entry(pai, textvariable=v, width=largura).grid(
                row=linha.n, column=1, sticky="ew", pady=2)
            pai.grid_columnconfigure(1, weight=1)
            campos[chave] = v
            linha.n += 1
            return v
        linha.n = 0

        # -- jogo
        fr_jogo = secao("Jogo")
        linha.n = 0
        linha(fr_jogo, "Título *", "titulo", j["titulo"] if j else "")
        ttk.Label(fr_jogo, text="Status", width=16, anchor="w").grid(
            row=1, column=0, sticky="w", pady=2)
        var_st = tk.StringVar(value=j["status"] if j else "backlog")
        ttk.Combobox(fr_jogo, textvariable=var_st, values=list(core.STATUS_VALIDOS),
                     state="readonly", width=18).grid(row=1, column=1, sticky="w", pady=2)
        campos["status"] = var_st

        # -- execução
        fr_exe = secao("Execução")
        linha.n = 0
        linha(fr_exe, "Executável", "executable_path", j["executable_path"] if j else "")

        def procurar_exe():
            arq = filedialog.askopenfilename(
                title="Executável do jogo",
                filetypes=[("Executáveis", "*.exe *.lnk *.sh *.AppImage"), ("Todos", "*.*")])
            if arq:
                campos["executable_path"].set(arq)

        ttk.Button(fr_exe, text="Procurar...", command=procurar_exe).grid(
            row=1, column=1, sticky="e", pady=2)
        linha.n = 2
        linha(fr_exe, "Exe Windows", "exe_win", j["exe_win"] if j else "")
        linha(fr_exe, "Exe Linux", "exe_linux", j["exe_linux"] if j else "")
        linha(fr_exe, "Lançamento", "launch_options", j["launch_options"] if j else "")
        ttk.Label(fr_exe, text="Vazio = usa o executável de cima",
                  style="Mut.TLabel").grid(row=5, column=1, sticky="w")

        # -- avaliação
        fr_av = secao("Avaliação")
        var_nota = tk.StringVar(value="" if not j or j["nota"] is None else str(j["nota"]))
        var_horas = tk.StringVar(value="0" if not j else str(j["horas"] or 0))
        var_fav = tk.BooleanVar(value=bool(j and j["favorito"]))
        ttk.Label(fr_av, text="Nota 0–10").pack(side="left")
        ttk.Entry(fr_av, textvariable=var_nota, width=6).pack(side="left", padx=(2, 14))
        ttk.Label(fr_av, text="Horas").pack(side="left")
        ttk.Entry(fr_av, textvariable=var_horas, width=8).pack(side="left", padx=(2, 14))
        ttk.Checkbutton(fr_av, text="★ favorito", variable=var_fav).pack(side="left")
        campos["nota"], campos["horas"], campos["favorito"] = var_nota, var_horas, var_fav

        # -- 3ds
        fr_3ds = secao("Nintendo 3DS")
        ttk.Label(fr_3ds, text="Preset", width=16, anchor="w").grid(
            row=0, column=0, sticky="w", pady=2)
        var_preset = tk.StringVar(
            value=(j.get("azahar_preset") if j else "") or "")
        cmb_preset = ttk.Combobox(fr_3ds, textvariable=var_preset,
                                  values=core.listar_presets(), width=36)
        cmb_preset.grid(row=0, column=1, sticky="ew", pady=2)
        fr_3ds.grid_columnconfigure(1, weight=1)
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

        ttk.Button(fr_3ds, text="📸 Fotografar config atual...",
                   command=foto_preset).grid(row=1, column=1, sticky="e", pady=2)

        # -- notas
        fr_obs = secao("Observações")
        txt = tk.Text(fr_obs, height=3, bg="#0b0d12", fg=TXT, insertbackground=TXT)
        txt.pack(fill="x")
        if j and j["observacoes"]:
            txt.insert("1.0", j["observacoes"])
        campos["observacoes"] = txt

        # -- capa
        fr_capa = secao("Capa")
        var_capa = tk.StringVar(value="")
        lbl_capa = ttk.Label(fr_capa, text=f"Atual: {j['capa']}" if j and j.get("capa") else "Sem capa")
        lbl_capa.pack(anchor="w")
        self._img_capa = None
        if j and j.get("capa"):
            alvo = core.caminho_capa(j["capa"])
            if alvo is not None and alvo.suffix.lower() in (".png", ".gif"):
                try:
                    img = tk.PhotoImage(file=str(alvo))
                    f = max(1, img.height() // 160)
                    self._img_capa = img.subsample(f, f) if f > 1 else img
                    ttk.Label(fr_capa, image=self._img_capa).pack(anchor="w", pady=4)
                except tk.TclError:
                    pass  # mantém só o nome do arquivo

        def trocar_capa():
            arq = filedialog.askopenfilename(
                title="Capa (png/jpg/webp até 2 MB)",
                filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp")])
            if arq:
                var_capa.set(arq)
                lbl_capa.configure(text=f"Nova capa: {Path(arq).name}")

        ttk.Button(fr_capa, text="Escolher capa...", command=trocar_capa).pack(anchor="e")

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

    # -- importação unificada (pasta ou arquivo; emulador detectado sozinho)
    def importar_unificado(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Importar")
        dlg.configure(bg=BG)
        dlg.transient(self.root)
        dlg.grab_set()
        ttk.Label(dlg, wraplength=420, justify="left", text=(
            "Escolha uma PASTA (varre jogos de PC + ROMs de uma vez), um "
            "ARQUIVO (exe, ROM, JSON ou pacote .zip) ou LEIA DO DISCO "
            "(Hydra + Steam + Epic + GOG + Riot + programas instalados).\n"
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
                            "*.elf *.app *.axf *.json *.zip"),
                           ("Executáveis", "*.exe *.lnk *.bat *.cmd"),
                           ("ROMs 3DS", "*.3ds *.3dsx *.cci *.cxi *.elf *.app *.axf"),
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

    def _importar_pasta(self, pasta: str):
        prog = tk.Toplevel(self.root)
        prog.title("Importar pasta")
        prog.transient(self.root)
        ttk.Label(prog, text="Varrendo pasta (só leitura)...").pack(padx=24, pady=24)
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
                messagebox.showerror("Importar pasta", f"falha na varredura: {e}")
                core.log_erro("importar-pasta", str(e))

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
                    sub += " LISTA PARCIAL (teto de varredura)."
                if not info.get("emu"):
                    sub += (" ROMs importam sem executável (Azahar ausente) — "
                            "instale com 'Atualizar Azahar'.")
                self._dlg_prev("Preview — Pasta",
                               sub + " Pré-marcados: score ≥ 0.3.", itens)
            na_ui(pronto)

        threading.Thread(target=trabalho, daemon=True).start()

    def _importar_arquivo(self, arq: str):
        ana = core.analisar_arquivo(arq)
        tipo = ana["tipo"]
        if tipo == "pasta":
            self._importar_pasta(arq)
        elif tipo == "json":
            self.importar_json(arq)
        elif tipo == "pacote":
            self.importar_pacote(arq)
        elif tipo in ("rom", "jogo"):
            if ana.get("aviso") and not messagebox.askyesno("Importar", f"{ana['aviso']}\n\nImportar mesmo assim?"):
                return
            con = self._con()
            try:
                res = core.importar_lista(con, [ana["item"]])
            finally:
                con.close()
            self.sel = None
            self.recarregar()
            if res["novos"]:
                messagebox.showinfo("Importar", f"{ana['detalhe']} ✓")
            else:
                messagebox.showinfo("Importar", "Já estava na biblioteca (nada novo).")
        else:
            messagebox.showwarning("Importar", ana["detalhe"] or "não suportado.")

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
            lb.insert("end", f"{bola} [{it['score']:.2f}] {it['titulo']}{tag} — {it.get('fonte') or it['origem']}"
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
            messagebox.showinfo(titulo, core.resumo_importacao(res))

        ttk.Button(dlg, text="Importar selecionados", command=importar,
                   style="Accent.TButton").pack(pady=8)

    def _ler_do_disco(self):
        prog = tk.Toplevel(self.root)
        prog.title("Ler do disco")
        prog.transient(self.root)
        ttk.Label(prog, text="Lendo Hydra, lojas e programas (só leitura)...").pack(
            padx=24, pady=24)
        prog.update()

        def trabalho():
            def na_ui(fn):
                try:
                    self.root.after(0, fn)
                except tk.TclError:
                    pass  # janela fechada no meio da leitura

            def falhou(e):
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                messagebox.showerror("Ler do disco", f"falha na leitura: {e}")
                core.log_erro("ler-do-disco", str(e))

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

    def importar_json(self, arq: str | None = None):
        if not arq:
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
        messagebox.showinfo("Importar", core.resumo_importacao(res))

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

    def importar_pacote(self, arq: str | None = None):
        if not arq:
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
                            core.resumo_importacao(res) + "\n" +
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
