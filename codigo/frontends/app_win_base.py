#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TucoTeca classico: MixBase de App (verbatim do modulo original)."""
from __future__ import annotations

import threading
import tkinter as tk
import traceback
from pathlib import Path
from queue import SimpleQueue
from tkinter import ttk
from types import SimpleNamespace

import bib_core as core
from aparencia import ACC, BG, CARD, LINE, MUT, PANEL, TXT, BarraAcoes, PainelRolavel, aplicar_tema
from aparencia import HOVER as CARD_HOVER
from despacho import DespachanteUi
from late import ModuloTardio

_W = ModuloTardio("app_win")


class MixBase:
    def __init__(self, root: tk.Tk, db_path: Path):
        self.root = root
        self.db_path = db_path
        self.jogos: list[dict] = []
        self.sel: int | None = None
        self.big_picture = False
        self.nav_idx = 0
        self.filtro_prov: str | None = None  # chave do provider (fundo, não jogo)
        self.prov_btns: dict[str, ttk.Button] = {}
        self.filtro_plat: str | None = None  # PC/3DS/NDS (derivado da origem)
        self.plat_btns: dict[str, ttk.Button] = {}
        self.filtro_status: str = ""  # "" = todos; senão um de STATUS_VALIDOS
        self.so_fav: bool = False
        self._deb = None
        self.cards: list[dict] = []  # {frame, jogo}
        self._imgs_cards: list = []  # retém miniaturas da grade
        self._img_det = None  # retém a capa do painel de detalhes
        self.desejos: list[dict] = []
        self.des_sel: int | None = None
        self._des_lista = None  # Listbox da aba Desejos (recriado a cada recarga)
        self.dls: list[dict] = []
        self.dl_sel: int | None = None
        self._dl_lista = None  # Listbox da aba Downloads (recriado a cada recarga)
        self.musicas: list[dict] = []
        self.mus_sel: int | None = None
        self.mus_ids: list[int] = []
        self._mus_lista = None  # Listbox da aba Músicas (recriado a cada recarga)
        self.mus_modo = "hub"  # "hub" catalogadas | "fila" downloads CSV
        self.fila: list[dict] = []
        self.fila_sel: int | None = None
        self.player = core.Player()  # interno (MCI no Win); externo é fallback
        self._btn_play = None  # ▶/⏸ da aba (texto acompanha o estado)
        self._mus_token = 0  # resultados antigos nunca alteram o player atual
        self._mus_resultados = SimpleQueue()
        self._mus_preparo_lock = threading.Lock()
        self._mus_carregando = ""
        self._mus_fechado = False
        self._dl_ocupado = False
        self._dl_timer = None
        self._dl_snapshot = {"torrents": [], "erros": []}
        self._despacho = DespachanteUi(root, ao_erro=self._erro_callback)
        root.title("TucoTeca — clássico (congelado)")
        root.geometry(f"{min(1280, root.winfo_screenwidth() - 80)}x"
                      f"{min(800, root.winfo_screenheight() - 100)}")
        root.minsize(860, 560)
        root.configure(bg=BG)
        self._estilo()
        self._montar()
        self.recarregar()
        self.root.after_idle(lambda: _W._titulo_escuro(self.root))
        self.root.bind("<Destroy>", self._fechar_player, add="+")
        try:
            self._mus_poll = self.root.after(50, self._processar_mus_resultados)
            self._mus_vigia = self.root.after(1000, self._vigiar_musica)
            self._dl_timer = self.root.after(3000, self._vigiar_downloads)
        except tk.TclError:
            pass
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
                      font=("Segoe UI", 14, "bold"))
        st.configure("Panel.Title.TLabel", background=PANEL, foreground=TXT,
                      font=("Segoe UI", 14, "bold"))
        st.configure("Side.TButton", background=PANEL, foreground=MUT,
                     borderwidth=0, padding=8, anchor="w",
                     font=("Segoe UI", 11))
        st.map("Side.TButton", background=[("active", CARD)],
               foreground=[("active", TXT)])
        st.configure("SideAct.TButton", background=CARD, foreground=TXT,
                     borderwidth=0, padding=8, anchor="w",
                     font=("Segoe UI", 11, "bold"))
        st.configure("TButton", background=CARD, foreground=TXT,
                       borderwidth=1, padding=10, font=("Segoe UI", 11),
                       relief="flat", focuscolor="")
        st.map("TButton", background=[("active", ACC), ("pressed", "#5a3fd4")],
               relief=[("pressed", "flat")])
        st.configure("Accent.TButton", background=ACC, foreground="white",
                       borderwidth=0, padding=10, font=("Segoe UI", 13, "bold"),
                       relief="flat", focuscolor="")
        st.map("Accent.TButton", background=[("active", "#8f6fff"),
                                             ("pressed", "#5a3fd4")])
        st.configure("TEntry", fieldbackground="#0b0d12", foreground=TXT,
                       borderwidth=1, relief="flat", insertcolor=ACC,
                       padding=6)
        st.map("TEntry", bordercolor=[("focus", ACC)],
               fieldbackground=[("disabled", CARD)])
        st.configure("TCombobox", fieldbackground="#0b0d12",
                       background=CARD, foreground=TXT, arrowcolor=ACC,
                       borderwidth=0, padding=6)
        st.map("TCombobox", fieldbackground=[("readonly", "#0b0d12")],
               foreground=[("readonly", TXT)])
        st.configure("TSeparator", background=LINE)
        st.configure("Lista.Treeview", background="#101218",
                       fieldbackground="#101218", foreground=TXT,
                       borderwidth=0, relief="flat", rowheight=28,
                       font=("Segoe UI", 11), focuscolor="")
        st.map("Lista.Treeview", background=[("selected", ACC)],
               foreground=[("selected", "white")])
        st.configure("Lista.Treeview.Heading", background=CARD,
                       foreground=MUT, font=("Segoe UI", 10, "bold"),
                       relief="flat", padding=6)
        st.map("Lista.Treeview.Heading", background=[("active", CARD_HOVER)],
               foreground=[("active", TXT)])
        st.configure("Lista.Vertical.TScrollbar", background=CARD,
                       troughcolor=BG, borderwidth=0, arrowsize=0)
        st.map("Lista.Vertical.TScrollbar", background=[("active", ACC)])
        st.configure("Down.Horizontal.TProgressbar", background=ACC,
                       troughcolor=CARD, borderwidth=0, thickness=10)
        st.configure("Star.TCheckbutton", background=BG, foreground=MUT,
                       font=("Segoe UI", 13, "bold"), focuscolor="")
        st.map("Star.TCheckbutton", foreground=[("active", TXT),
                                                ("selected", "#ffd75e")])
        st.configure("Sec.TLabelframe", background=CARD, borderwidth=0, padding=12)
        st.configure("Sec.TLabelframe.Label", background=CARD, foreground=ACC,
                      font=("Segoe UI", 13, "bold"))
        st.configure("Sec.TLabel", background=CARD, foreground=MUT,
                      font=("Segoe UI", 12))
        st.configure("Big.Accent.TButton", background=ACC, foreground="white",
                      borderwidth=0, padding=16, font=("Segoe UI", 14, "bold"))
        st.configure("Vertical.TScrollbar", background=CARD, troughcolor=BG,
                      borderwidth=0, arrowsize=13)
        st.map("Vertical.TScrollbar", background=[("active", ACC)])
        st.configure("Chip.TButton", background=CARD, foreground=MUT,
                      borderwidth=1, padding=6, font=("Segoe UI", 10, "bold"))
        st.map("Chip.TButton", background=[("active", CARD_HOVER)],
               foreground=[("active", TXT)])
        st.configure("ChipAct.TButton", background=ACC, foreground="white",
                       borderwidth=0, padding=6, font=("Segoe UI", 10, "bold"))
        st.configure("Volume.Horizontal.TScale", background=PANEL,
                      troughcolor=CARD)
        st.configure("Volume.TButton", background=CARD, foreground=TXT,
                       borderwidth=0, padding=(4, 5), font=("Segoe UI", 9))
        aplicar_tema(self.root)
    def _montar(self):
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        # sidebar
        side = ttk.Frame(self.root, style="Panel.TFrame", width=212)
        side.grid(row=0, column=0, sticky="nsew")
        side.pack_propagate(False)
        self.sidebar = side
        self._montar_volume_pc(side)
        ttk.Label(side, text="TUCOTECA", image=self.root._tuco_icone, compound="left",
                  style="Panel.TLabel", font=("Segoe UI", 12, "bold")).pack(
                      anchor="w", padx=10, pady=(10, 4))
        nav_area = PainelRolavel(side)
        nav_area.pack(fill="both", expand=True, pady=(6, 0))
        self.nav_area = nav_area
        nav = nav_area.corpo
        self.nav_btns: list[ttk.Button] = []
        self._maes: dict[str, dict] = {}
        idx_mus = next(i for i, (rot, _s, _f) in enumerate(_W.NAV)
                       if rot.startswith("🎵"))
        idx_des = next(i for i, (rot, _s, _f) in enumerate(_W.NAV)
                       if rot.startswith("☆"))
        idx_dl = next(i for i, (rot, _s, _f) in enumerate(_W.NAV)
                      if rot.startswith("⬇ D"))
        por_nav: dict[int, ttk.Button] = {}

        def filha(mae, i, texto=None):
            b = ttk.Button(mae["corpo"], text=texto or _W.NAV[i][0],
                           style="Side.TButton",
                           command=lambda i=i: self._ir_nav(i))
            b.pack(fill="x", padx=8, pady=1)
            por_nav[i] = b
            return b

        def item(texto, cmd):
            """Filha direta da sidebar (mãe só se tem 2+ filhas)."""
            b = ttk.Button(nav, text=texto, style="Side.TButton",
                           command=cmd)
            b.pack(fill="x", padx=8, pady=1)
            return b

        mae_bib = self._mae(nav, "📚 BIBLIOTECA")
        filha(mae_bib, 0, "Todos os jogos")
        for chave in core.provedores():
            b = ttk.Button(mae_bib["corpo"], text=chave, style="Side.TButton",
                           command=lambda c=chave: self._ir_prov(c))
            b.pack(fill="x", padx=8, pady=1)
            self.prov_btns[chave] = b
        mae_mus = self._mae(nav, "🎵 MÚSICAS")
        filha(mae_mus, idx_mus, "Minhas faixas")
        self._btn_fila = ttk.Button(mae_mus["corpo"], text="⬇ Fila",
                                    style="Side.TButton",
                                    command=self._ir_fila_arvore)
        self._btn_fila.pack(fill="x", padx=8, pady=1)
        por_nav[idx_des] = item(_W.NAV[idx_des][0],
                                lambda i=idx_des: self._ir_nav(i))
        por_nav[idx_dl] = item(_W.NAV[idx_dl][0],
                               lambda i=idx_dl: self._ir_nav(i))
        mae_arq = self._mae(nav, "⬇ ARQUIVO")
        for rotulo, cmd in (("📥 Importar…", self.importar_unificado),
                            ("🧹 Sanear pasta…", self.sanear_pasta_ui),
                            ("⬇ SteamRip…",
                             lambda: self.dlg_catalogo("steamrip")),
                            ("⬇ FitGirl…",
                             lambda: self.dlg_catalogo("fitgirl"))):
            ttk.Button(mae_arq["corpo"], text=rotulo, style="Side.TButton",
                       command=cmd).pack(fill="x", padx=8, pady=1)
        item("⚙ Configurações", self.abrir_configuracoes)
        self.nav_btns = [por_nav[i] for i in range(len(_W.NAV))]
        self._pintar_nav()

        # coluna central
        centro = ttk.Frame(self.root)
        centro.grid(row=0, column=1, sticky="nsew")
        self.centro = centro
        cabecalho = ttk.Frame(centro)
        cabecalho.pack(fill="x", padx=20, pady=(18, 10))
        cabecalho.columnconfigure(0, weight=1)
        self.btn_detalhes = ttk.Button(cabecalho, text="Detalhes", command=self._abrir_detalhe)
        self.btn_detalhes.grid(row=0, column=2, padx=(6, 0))
        self.btn_usuario = ttk.Button(cabecalho, text="👤 —", style="Chip.TButton",
                                      command=self.dlg_usuario)
        self.btn_usuario.grid(row=0, column=1, padx=6)
        self.lbl_secao = ttk.Label(cabecalho, text="Biblioteca", style="Title.TLabel")
        self.lbl_secao.grid(row=0, column=0, sticky="w")
        self.lbl_subtitulo = ttk.Label(cabecalho, style="Subtitle.TLabel")
        self.lbl_subtitulo.grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 0))
        self.btn_imersivo = ttk.Button(cabecalho, text="Tela cheia · F11",
                                      command=self._alternar_big_picture)
        self.btn_imersivo.grid(row=0, column=3, padx=(6, 0))
        self.nav_superior = ttk.Frame(centro)
        self.nav_superior_btns = []
        for i, (rotulo, _s, _f) in enumerate(_W.NAV):
            botao = ttk.Button(self.nav_superior, text=rotulo.split(" ", 1)[-1],
                               command=lambda i=i: self._ir_nav(i))
            botao.pack(side="left", padx=(0, 8))
            self.nav_superior_btns.append(botao)
        self.destaque = ttk.Frame(centro, style="Panel.TFrame", padding=18)
        self.destaque.columnconfigure(0, weight=1)
        self.destaque_titulo = ttk.Label(self.destaque, style="Panel.Title.TLabel")
        self.destaque_titulo.grid(row=0, column=0, sticky="w")
        ttk.Label(self.destaque, text="↑ ↓ ← →  Navegar     Enter  Jogar     Esc  Voltar",
                  style="Panel.TLabel", foreground=MUT).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.destaque_jogar = ttk.Button(self.destaque, text="▶  JOGAR",
                                        style="Accent.TButton", command=self.jogar)
        self.destaque_jogar.grid(row=0, column=1, rowspan=2, padx=(18, 0))
        # Busca expansível; filtros da biblioteca em uma área adaptável.
        barra = ttk.Frame(centro)
        self.barra_busca = barra
        barra.pack(fill="x", padx=20, pady=(0, 10))
        lin1 = ttk.Frame(barra)
        lin1.pack(fill="x")
        self.btn_limpar = ttk.Button(lin1, text="Limpar", command=self._limpar_filtros)
        self.btn_limpar.pack(side="right", padx=(6, 0))
        ttk.Button(lin1, text="Buscar", command=self.recarregar).pack(side="right", padx=(6, 0))
        self.var_q = tk.StringVar()
        self.ent_busca = ttk.Entry(lin1, textvariable=self.var_q, width=20)
        self.ent_busca.pack(side="left", fill="x", expand=True)
        self.ent_busca.bind("<KeyRelease>", self._ao_digitar)
        self.ent_busca.bind("<Return>", lambda _e: self.recarregar())
        lin2 = ttk.Frame(barra)
        lin2.pack(fill="x", pady=(8, 0))
        self.filtros_area = lin2
        self.var_statusfiltro = tk.StringVar(value="Todos")
        self.cmb_statusfiltro = ttk.Combobox(
            lin2, textvariable=self.var_statusfiltro, values=list(_W.STATUS_FILTROS),
            width=10, state="readonly", font=("Segoe UI", 10))
        self.cmb_statusfiltro.grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.cmb_statusfiltro.bind("<<ComboboxSelected>>", self._ao_trocar_status)
        self.var_sofav = tk.BooleanVar(value=False)
        self.chk_sofav = ttk.Checkbutton(lin2, text="★", variable=self.var_sofav,
                                        command=self._ao_trocar_fav,
                                        style="Star.TCheckbutton")
        self.chk_sofav.grid(row=0, column=1, padx=(0, 6))
        for i, plat in enumerate(("PC", "3DS", "NDS")):
            b = ttk.Button(lin2, text=plat, width=5, style="Chip.TButton",
                           command=lambda p=plat: self._ir_plat(p))
            b.grid(row=0, column=i + 2, sticky="w", padx=(0, 4))
            self.plat_btns[plat] = b
        self.var_tagfiltro = tk.StringVar(value="")
        ttk.Label(lin2, text="Etiquetas", style="Mut.TLabel").grid(
            row=1, column=0, sticky="w", pady=(6, 0))
        self.cmb_tagfiltro = ttk.Combobox(lin2, textvariable=self.var_tagfiltro,
                                          values=[], width=14, font=("Segoe UI", 10))
        self.cmb_tagfiltro.grid(row=1, column=1, columnspan=4, sticky="ew", pady=(6, 0))
        lin2.columnconfigure(4, weight=1)
        self.cmb_tagfiltro.bind("<<ComboboxSelected>>", lambda _e: self.recarregar())
        self.cmb_tagfiltro.bind("<Return>", lambda _e: self.recarregar())
        self.lbl_cont = ttk.Label(barra, text="", style="Mut.TLabel", wraplength=480)
        self.lbl_cont.pack(anchor="w", pady=(8, 0))
        self.lbl_vazio = ttk.Label(barra, text="", style="Mut.TLabel", wraplength=480)
        conteudo = ttk.Frame(centro)
        conteudo.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self.canvas = tk.Canvas(conteudo, bg=BG, highlightthickness=0, width=1, height=1)
        self.vscroll = ttk.Scrollbar(conteudo, orient="vertical",
                                     command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vscroll.set)
        self.vscroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.grade = ttk.Frame(self.canvas)
        self._win_grade = self.canvas.create_window((0, 0), window=self.grade, anchor="nw")
        self.grade.bind("<Configure>", self._ao_mudar_grade)
        self.canvas.bind("<Configure>", self._ao_redimensionar)
        self.canvas.bind_all("<MouseWheel>", self._rodar, add="+")

        # painel de detalhes
        self.det_painel = PainelRolavel(self.root, width=280)
        self.det_painel.grid(row=0, column=2, sticky="nsew")
        self.det_painel.pack_propagate(False)
        self.det_janela = None
        det = self.det_painel.corpo
        ttk.Label(det, text="SELECIONADO", style="Panel.TLabel", foreground=MUT,
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=16, pady=(18, 0))
        self.det_capa = tk.Canvas(det, width=216, height=280, bg=PANEL,
                                  highlightthickness=2, highlightbackground=LINE)
        self.det_capa.pack(padx=16, pady=(16, 8))
        self.det_titulo = ttk.Label(det, text="", style="Panel.Title.TLabel",
                                    wraplength=240)
        self.det_titulo.pack(anchor="w", padx=16)
        self.det_meta = ttk.Label(det, text="", style="Mut.TLabel",
                                  background=PANEL, wraplength=240,
                                  justify="left")
        self.det_meta.pack(anchor="w", padx=16, pady=(4, 2))
        self.det_progresso = ttk.Progressbar(det, maximum=100,
                                             style="Down.Horizontal.TProgressbar")
        self.det_exe = ttk.Label(det, text="", style="Mut.TLabel",
                                 background=PANEL, wraplength=240,
                                 justify="left", font=("Segoe UI", 8))
        self.det_exe.pack(anchor="w", padx=16, pady=(0, 8))
        self.btn_jogar = ttk.Button(det, text="▶  JOGAR",
                                      style="Accent.TButton",
                                      command=self.jogar)
        self.btn_jogar.pack(fill="x", padx=16, pady=2)
        lin = ttk.Frame(det, style="Panel.TFrame")
        lin.pack(fill="x", padx=16, pady=2)
        self.btn_det_editar = ttk.Button(lin, text="✏ Editar",
                                         command=self.dlg_editar)
        self.btn_det_editar.pack(side="left", expand=True, fill="x",
                                 padx=(0, 2))
        self.btn_det_excluir = ttk.Button(lin, text="🗑 Excluir",
                                          command=self.excluir)
        self.btn_det_excluir.pack(side="left", expand=True, fill="x",
                                  padx=(2, 0))
        self.btn_det_novo = ttk.Button(det, text="+ Adicionar jogo",
                                       command=self.dlg_novo)
        self.btn_det_novo.pack(fill="x", padx=16, pady=(8, 2))
        self.root.bind("<Control-n>", lambda _e: self.dlg_novo())
        self.root.bind("<Control-f>", lambda _e: self.ent_busca.focus_set())
        self.canvas.bind("<Return>", lambda _e: self.jogar())
        self.canvas.bind("<Delete>", lambda _e: self.excluir())
        for tecla in ("Left", "Right", "Up", "Down", "Home", "End"):
            self.canvas.bind(f"<{tecla}>", self._navegar_grade)
        self.root.bind("<F11>", self._alternar_big_picture)
        self.root.bind("<Escape>", self._sair_big_picture)
        self.root.bind("<Configure>", self._dimensionar_interface, add="+")
        self._atualizar_contexto()
    def _dimensionar_interface(self, e):
        if e.widget is not self.root:
            return
        compacto = self.big_picture or e.width < 1120
        if compacto != getattr(self, "_compacto", None):
            self._compacto = compacto
            if compacto:
                self.det_painel.grid_remove()
                self.btn_detalhes.grid(row=0, column=2, padx=(6, 0))
            else:
                self._fechar_detalhe()
                self.det_painel.grid(row=0, column=2, sticky="nsew")
                self.btn_detalhes.grid_remove()
        largura = max(180, self.centro.winfo_width() - 40)
        self.lbl_cont.configure(wraplength=largura)
        self.lbl_vazio.configure(wraplength=largura)
    def _alternar_big_picture(self, _e=None):
        """Liga/desliga a tela cheia preservando a aba atual (clássico congelado)."""
        self.big_picture = not self.big_picture
        try:
            self.root.attributes("-fullscreen", self.big_picture)
        except tk.TclError:
            self.big_picture = not self.big_picture
            return
        self.btn_imersivo.configure(text="Sair · Esc" if self.big_picture else "Tela cheia · F11")
        self._fechar_detalhe()
        if self.big_picture:
            self.sidebar.grid_remove()
        else:
            self.sidebar.grid()
        self._pintar_nav()
        self._dimensionar_interface(SimpleNamespace(widget=self.root, width=self.root.winfo_width()))
        self.recarregar()
        try:
            self.canvas.focus_set()
        except tk.TclError:
            pass
        return "break"
    def _sair_big_picture(self, _e=None):
        if self.big_picture:
            return self._alternar_big_picture()
    def _tamanho_card(self):
        return (216, 288) if self.big_picture else (_W.CARD_W, _W.CARD_H)
    def _navegar_grade(self, e):
        if self._em_musicas() or self._em_desejos() or self._em_downloads() or not self.cards:
            return
        cols = max(1, max(1, self.canvas.winfo_width()) // self._largura_coluna())
        atual = self.sel if self.sel is not None else 0
        destinos = {"Left": atual - 1, "Right": atual + 1,
                    "Up": atual - cols, "Down": atual + cols,
                    "Home": 0, "End": len(self.cards) - 1}
        destino = destinos.get(getattr(e, "keysym", ""))
        if destino is None:
            return
        self.sel = max(0, min(len(self.cards) - 1, destino))
        self._pintar_selecao()
        self.mostrar_detalhe()
        fr = self.cards[self.sel]["frame"]
        topo, baixo = fr.winfo_y(), fr.winfo_y() + fr.winfo_height()
        visivel = self.canvas.canvasy(0)
        altura = self.canvas.winfo_height()
        total = max(1, self.grade.winfo_height())
        if topo < visivel:
            self.canvas.yview_moveto(topo / total)
        elif baixo > visivel + altura:
            self.canvas.yview_moveto((baixo - altura) / total)
        return "break"
    def _abrir_detalhe(self):
        if not getattr(self, "_compacto", False):
            return
        if self.det_janela is not None:
            self.det_janela.lift()
            return
        dlg = tk.Toplevel(self.root)
        self.det_janela = dlg
        dlg.title("Detalhes — TucoTeca")
        dlg.transient(self.root)
        dlg.geometry("300x650")
        dlg.minsize(280, 400)
        painel = PainelRolavel(dlg)
        painel.pack(fill="both", expand=True)
        fr = painel.corpo
        cv = tk.Canvas(fr, width=216, height=280, background=PANEL, highlightthickness=0)
        cv.pack(pady=16)
        labels = [ttk.Label(fr, style=estilo, background=PANEL, wraplength=250,
                            justify="left") for estilo in
                  ("Panel.Title.TLabel", "Mut.TLabel", "Mut.TLabel")]
        for lbl in labels:
            lbl.pack(fill="x", padx=16, pady=4)
        barra = BarraAcoes(fr, style="Panel.TFrame")
        barra.pack(fill="x", padx=16, pady=12)
        originais = (self.btn_jogar, self.btn_det_editar, self.btn_det_excluir, self.btn_det_novo)
        botoes = [barra.adicionar(b.cget("text"), b.invoke) for b in originais]
        self._det_replicas = (cv, labels, botoes)
        dlg.protocol("WM_DELETE_WINDOW", self._fechar_detalhe)
        self._replicar_detalhe()
        _W._titulo_escuro(dlg)
    def _fechar_detalhe(self):
        if self.det_janela is not None:
            self.det_janela.destroy()
            self.det_janela = None
    def _replicar_detalhe(self):
        if self.det_janela is None or not self.det_janela.winfo_exists():
            return
        cv, labels, botoes = self._det_replicas
        cv.delete("all")
        for item in self.det_capa.find_all():
            tipo = self.det_capa.type(item)
            config = {k: v[-1] for k, v in self.det_capa.itemconfigure(item).items()}
            getattr(cv, "create_" + tipo)(*self.det_capa.coords(item), **config)
        for clone, origem in zip(labels, (self.det_titulo, self.det_meta, self.det_exe)):
            clone.configure(text=origem.cget("text"))
        for clone, origem in zip(botoes, (self.btn_jogar, self.btn_det_editar,
                                        self.btn_det_excluir, self.btn_det_novo)):
            clone.configure(text=origem.cget("text"), state=origem.cget("state"))
    def _atualizar_contexto(self):
        titulo = _W.NAV[self.nav_idx][0].split(" ", 1)[-1]
        if self._em_musicas() and self.mus_modo == "fila":
            titulo = "Fila de músicas"
        subtitulos = {"Biblioteca": "Sua coleção local, pronta para jogar.",
                      "Músicas": "Suas faixas e o player, em um só lugar.",
                      "Desejos": "Planeje os próximos jogos da sua coleção.",
                      "Downloads": "Acompanhe os arquivos do qBittorrent.",
                      "Fila de músicas": "Downloads, conversão e importação de áudio."}
        self.lbl_secao.configure(text=titulo)
        self.lbl_subtitulo.configure(text=subtitulos.get(titulo, ""))
        biblioteca = not (self._em_musicas() or self._em_desejos() or self._em_downloads())
        if self.big_picture:
            self.nav_superior.pack(fill="x", padx=20, pady=(0, 12), before=self.barra_busca)
        else:
            self.nav_superior.pack_forget()
        if biblioteca and self.big_picture:
            self.destaque.pack(fill="x", padx=20, pady=(0, 12), before=self.barra_busca)
        else:
            self.destaque.pack_forget()
        if biblioteca and not self.big_picture:
            self.filtros_area.pack(fill="x", pady=(8, 0), before=self.lbl_cont)
        else:
            self.filtros_area.pack_forget()
        if biblioteca:
            self.vscroll.pack(side="right", fill="y", before=self.canvas)
        else:
            self.filtros_area.pack_forget()
            self.vscroll.pack_forget()
        self.canvas.itemconfigure(self._win_grade,
                                  height=0 if biblioteca else max(1, self.canvas.winfo_height()))
    def _mae(self, side, titulo: str) -> dict:
        """Pasta mãe expansível da sidebar (filhas somem com pack_forget)."""
        if not hasattr(self, "_maes"):
            self._maes = {}
        corpo = ttk.Frame(side, style="Panel.TFrame")
        corpo.pack(fill="x", padx=0, pady=(6, 0))
        aberto = self._maes.get(titulo, {}).get("aberto", True)
        btn = ttk.Button(corpo, text="", style="Group.TButton")
        btn.pack(fill="x", padx=8, pady=1)
        filhas = ttk.Frame(corpo, style="Panel.TFrame")
        filhas.pack(fill="x")
        mae = {"btn": btn, "corpo": filhas, "titulo": titulo, "aberto": aberto}

        def alternar():
            mae["aberto"] = not mae["aberto"]
            self._maes[titulo] = mae
            self._pintar_mae(mae)

        btn.configure(command=alternar)
        self._maes[titulo] = mae
        self._pintar_mae(mae)
        return mae
    def _pintar_mae(self, mae: dict) -> None:
        try:
            seta = "▼" if mae["aberto"] else "▶"
            mae["btn"].configure(text=f"{seta} {mae['titulo']}")
            if mae["aberto"]:
                mae["corpo"].pack(fill="x")
                for w in list(mae["corpo"].winfo_children()):
                    if isinstance(w, ttk.Button) and str(w.cget("text")):
                        w.pack(fill="x", padx=8, pady=1)
            else:
                for w in list(mae["corpo"].winfo_children()):
                    if isinstance(w, ttk.Button) and w is not mae["btn"]:
                        w.pack_forget()
        except tk.TclError:
            pass
    def _pintar_nav(self):
        for i, botao in enumerate(getattr(self, "nav_superior_btns", [])):
            botao.configure(style="ChipAct.TButton" if i == self.nav_idx else "Chip.TButton")
        for i, b in enumerate(self.nav_btns):
            b.configure(style="SideAct.TButton" if i == self.nav_idx else "Side.TButton")
        try:
            fila_ativa = self._em_musicas() and self.mus_modo == "fila"
            self._btn_fila.configure(
                style="SideAct.TButton" if fila_ativa else "Side.TButton")
        except (tk.TclError, AttributeError):
            pass
        for chave, b in self.prov_btns.items():
            b.configure(style="SideAct.TButton" if chave == self.filtro_prov else "Side.TButton")
        for plat, b in self.plat_btns.items():
            try:
                b.configure(style="ChipAct.TButton" if plat == self.filtro_plat else "Chip.TButton")
            except tk.TclError:
                pass
    def _ir_nav(self, i: int):
        try:
            i = max(0, min(int(i), len(_W.NAV) - 1))
        except Exception:
            i = 0
        self.nav_idx = i
        self._pintar_nav()
        self.recarregar()
        try:
            self.canvas.yview_moveto(0)
        except (tk.TclError, AttributeError):
            pass
    def _ir_prov(self, chave: str):
        self.nav_idx = 0
        self.var_q.set("")
        self.filtro_prov = None if self.filtro_prov == chave else chave
        self._pintar_nav()
        self.recarregar()
    def _ir_plat(self, plat: str):
        self.filtro_plat = None if self.filtro_plat == plat else plat
        self._pintar_nav()
        self.recarregar()
    def _limpar_filtros(self):
        self.filtro_plat = None
        self.filtro_prov = None
        self.filtro_status = ""
        self.so_fav = False
        try:
            self.var_q.set("")
        except (tk.TclError, AttributeError):
            pass
        try:
            self.var_tagfiltro.set("")
        except (tk.TclError, AttributeError):
            pass
        try:
            self.var_statusfiltro.set("Todos")
        except (tk.TclError, AttributeError):
            pass
        try:
            self.var_sofav.set(False)
        except (tk.TclError, AttributeError):
            pass
        self._pintar_nav()
        self.recarregar()
    def _ao_trocar_status(self, _e=None):
        try:
            txt = self.var_statusfiltro.get().strip()
        except (tk.TclError, AttributeError):
            txt = "Todos"
        self.filtro_status = "" if txt == "Todos" else txt
        self.recarregar()
    def _ao_trocar_fav(self):
        try:
            self.so_fav = bool(self.var_sofav.get())
        except (tk.TclError, AttributeError):
            self.so_fav = False
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
        lista = self._em_musicas() or self._em_desejos() or self._em_downloads()
        self.canvas.itemconfig(self._win_grade, width=e.width, height=e.height if lista else 0)
        # coalesce: resize dispara Configure em rajada; reorganiza 1x por ciclo
        try:
            if getattr(self, "_reorg_pend", None):
                self.root.after_cancel(self._reorg_pend)
        except (tk.TclError, AttributeError):
            pass
        try:
            self._reorg_pend = self.root.after_idle(self._reorganizar)
        except tk.TclError:
            pass
    def _rodar(self, e):
        if self._em_musicas() or self._em_desejos() or self._em_downloads():
            return  # as tabelas controlam sua própria rolagem
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
    def _largura_coluna(self) -> int:
        """Passo real de uma coluna (card medido + respiro do grid).

        Mede o card MAIS LARGO (capas têm tamanhos distintos) em vez de
        chutar: a conta fixa estourava a viewport e a última coluna sumia
        atrás da borda do painel.
        """
        passo = self._tamanho_card()[0] + 28
        if self.cards:
            try:
                mais_largo = max(c["frame"].winfo_reqwidth() for c in self.cards)
                passo = max(passo, mais_largo + 28)
            except (tk.TclError, ValueError):
                pass
        return max(1, passo)
    def _reorganizar(self):
        self._reorg_pend = None
        try:
            vp = max(200, self.canvas.winfo_width())
        except tk.TclError:
            return
        cols = max(1, vp // self._largura_coluna())
        for i, c in enumerate(self.cards):
            c["frame"].grid(row=i // cols, column=i % cols, padx=14, pady=12)
    def _con(self):
        return core.get_db(self.db_path)
    def _thread_segura(self, trabalho, prog, contexto: str):
        """Envolve trabalho de thread: nunca deixa modal órfão nem exceção muda."""
        def alvo():
            try:
                trabalho()
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                try:
                    core.log_erro(contexto, msg)
                except Exception:
                    pass

                def fim(msg=msg):
                    try:
                        prog.destroy()
                    except Exception:
                        pass
                    try:
                        _W.messagebox.showerror(contexto, f"falha inesperada: {msg}")
                    except Exception:
                        pass
                try:
                    self._depois(fim)
                except Exception:
                    pass
        return alvo
    def _depois(self, fn):
        self._despacho.enviar(fn)
    def _erro_callback(self, erro):
        if isinstance(erro, tk.TclError):
            return  # diálogo destruído antes de uma entrega pendente
        detalhe = "".join(traceback.format_exception(type(erro), erro, erro.__traceback__))
        core.log_erro("interface", detalhe)
        self._aviso_barra(f"Erro interno: {type(erro).__name__} (veja dados/erros.log)")
    def _ir_fila_arvore(self):
        """Filha Fila: vai p/ Músicas e troca o modo (fora dela, só o modo)."""
        if not self._em_musicas():
            for i, (rot, _s, _f) in enumerate(_W.NAV):
                if rot.startswith("🎵"):
                    self._ir_nav(i)
                    break
        self._ir_fila()
    def _minimizar_janela(self) -> None:
        """Some p/ trás do jogo. Nunca levanta."""
        try:
            self.root.iconify()
        except tk.TclError:
            pass
    def _restaurar_janela(self) -> None:
        """Volta à frente ao fim do jogo. Nunca levanta."""
        try:
            if not self.root.winfo_exists():
                return
            self.root.deiconify()
            self.root.lift()
            try:
                self.root.focus_force()
            except tk.TclError:
                pass
        except tk.TclError:
            pass
    def _aviso_barra(self, msg: str) -> None:
        """Aviso não-modal na barra de contagem (sem popup, sem empilhar)."""
        try:
            base = self.lbl_cont.cget("text")
        except (tk.TclError, AttributeError):
            return
        anterior = getattr(self, "_ultimo_aviso", "")
        if anterior and base.endswith(anterior):
            base = base[: -len(anterior)].rstrip(" ·")
        self._ultimo_aviso = msg
        try:
            self.lbl_cont.configure(text=f"{base} · {msg}" if base else msg)
        except (tk.TclError, AttributeError):
            pass
