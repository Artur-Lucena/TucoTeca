#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TucoTeca — aplicativo local Windows (tkinter, stdlib).
Modo clássico, congelado: só correções críticas. O frontend principal é Qt.
Biblioteca com capas, painel de detalhes e modo Big Picture por teclado.
Mesmo banco e mesmas regras do terminal Linux; nada de navegador.

Uso:
    python codigo/frontends/app_win.py [--db caminho\\biblioteca.db]
    python codigo/frontends/app_win.py --selftest   # monta a UI oculta e sai (verificação)
Ou duplo-clique em BibliotecaHub.bat na raiz do projeto.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import threading
import tkinter as tk
import traceback
from pathlib import Path
from queue import Empty, SimpleQueue
from tkinter import filedialog, messagebox, simpledialog, ttk
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bib_core as core
from aparencia import ACC, BG, CARD, HOVER as CARD_HOVER, LINE, MUT, PANEL, TXT
from aparencia import BarraAcoes, PainelRolavel, aplicar_tema
from despacho import DespachanteUi

OK_C = "#2ecc71"
WARN_C = "#f39c12"
BAD_C = "#e74c3c"

CARD_W, CARD_H = 156, 216
STATUS_CORES = {"backlog": MUT, "jogando": "#7aa2ff", "zerado": OK_C,
                "pausado": WARN_C, "abandonado": BAD_C}

# (rótulo, reservado, reservado) — status/favorito filtram na barra única
NAV = [("📚 Biblioteca", "", False),
       ("🎵 Músicas", "", False),
       ("☆ Desejos", "", False),
       ("⬇ Downloads", "", False)]
STATUS_FILTROS = ("Todos", "backlog", "jogando", "zerado", "pausado",
                  "abandonado")

_MINI_CACHE: dict = {}


def carregar_miniatura(caminho: Path, largura: int = CARD_W,
                       altura: int = CARD_H, master=None) -> tk.PhotoImage | None:
    """PhotoImage reduzido da capa, ou None (vira tile).

    Tenta Pillow (jpg/webp/png/gif) quando instalado; senão, PhotoImage
    nativo (só png/gif). Cacheado por (caminho, mtime, tamanho) p/ não
    recarregar a cada recarregar().
    """
    try:
        st = Path(caminho).stat()
        root = master or tk._default_root
        chave = (id(root.tk) if root is not None else None,
                 str(caminho), st.st_mtime_ns, st.st_size, largura, altura)
    except OSError:
        return None
    if chave in _MINI_CACHE:
        return _MINI_CACHE[chave]
    img = None
    # 1) Pillow (opcional): cobre jpg/webp e reduz com qualidade
    try:
        from PIL import Image, ImageTk  # type: ignore
        pil = Image.open(caminho)
        pil.load()
        pil.thumbnail((largura, altura), Image.LANCZOS)
        img = ImageTk.PhotoImage(pil, master=root)
        _MINI_CACHE[chave] = img
        if len(_MINI_CACHE) > 300:
            _MINI_CACHE.pop(next(iter(_MINI_CACHE)))
        return img
    except Exception:
        pass
    # 2) Nativo Tk (zero deps): png/gif apenas. Teto na divisão para a
    # imagem NUNCA estourar o alvo (piso deixava 141–279px intactos e a
    # grade transbordava a viewport).
    if Path(caminho).suffix.lower() not in (".png", ".gif"):
        return None
    try:
        base = tk.PhotoImage(master=root, file=str(caminho))
    except tk.TclError:
        return None
    try:
        f = max(1, -(-base.width() // largura), -(-base.height() // altura))
        img = base.subsample(f, f) if f > 1 else base
    except tk.TclError:
        return None
    _MINI_CACHE[chave] = img
    if len(_MINI_CACHE) > 300:
        _MINI_CACHE.pop(next(iter(_MINI_CACHE)))
    return img


def _titulo_escuro(janela) -> None:
    """Barra de título escura no Windows 10/11 via DWM (só stdlib).

    Sem efeito em outros SOs ou Windows antigos; nunca levanta.
    """
    try:
        if os.name != "nt":
            return
        import ctypes
        valor = ctypes.c_int(1)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetParent.argtypes = [ctypes.c_void_p]
        user32.GetParent.restype = ctypes.c_void_p
        interno = janela.winfo_id()
        hwnd = ctypes.c_void_p(user32.GetParent(interno) or interno)
        for attr in (20, 19):  # 20 = Win11/20H1+; 19 = builds antigas
            try:
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, attr, ctypes.byref(valor),
                        ctypes.sizeof(valor)) == 0:
                    return
            except Exception:
                continue
    except Exception:
        pass


def _com_rolagem(lst):
    """Acopla Scrollbar vertical num Listbox/Treeview já empacotado."""
    try:
        bar = ttk.Scrollbar(lst.master, orient="vertical", command=lst.yview,
                            style="Lista.Vertical.TScrollbar")
        bar.pack(side="right", fill="y", before=lst)
        lst.pack_configure(side="left")
        lst.configure(yscrollcommand=bar.set)
    except (tk.TclError, AttributeError):
        pass
    return lst


def _nova_grade_tv(mae, colunas=("Item", "Detalhe")) -> ttk.Treeview:
    """Lista moderna das abas (Treeview zebrada, 2 colunas)."""
    area = ttk.Frame(mae)
    area.pack(fill="both", expand=True)
    tv = ttk.Treeview(area, columns=list(colunas), show="headings",
                      height=14, selectmode="browse", style="Lista.Treeview")
    for j, col in enumerate(colunas):
        tv.heading(col, text=col)
        tv.column(col, width=(300 if j == 0 else 160), minwidth=40,
                  stretch=True, anchor="w")
    tv.tag_configure("par", background=BG)
    tv.tag_configure("impar", background=PANEL)

    def dimensionar(e):
        largura = max(80, e.width - 4)
        for j, col in enumerate(colunas):
            tv.column(col, width=int(largura * (0.62 if j == 0 else 0.38)))

    tv.bind("<Configure>", dimensionar)
    return tv


def _tv_por(tv: ttk.Treeview, linhas) -> None:
    """Preenche [(col0, col1)] com zebra. Linha ruim é pulada."""
    for i, par in enumerate(linhas):
        try:
            a, b = par
            tv.insert("", "end", iid=str(i), values=(str(a), str(b)),
                      tags=("par" if i % 2 else "impar",))
        except Exception:
            continue


def _tv_sel(tv) -> int | None:
    """Índice selecionado ou None. Nunca levanta."""
    try:
        sel = tv.selection()
    except (tk.TclError, AttributeError):
        return None
    if not sel:
        return None
    try:
        return int(sel[0])
    except (TypeError, ValueError):
        return None


def _tv_marcar(tv, idx) -> None:
    """Seleciona e mostra a linha. Nunca levanta."""
    if idx is None:
        return
    try:
        tv.selection_set(str(idx))
        tv.see(str(idx))
    except tk.TclError:
        pass


def desenhar_tile(cv: tk.Canvas, titulo: str, w: int, h: int,
                   selecionado: bool = False, grande: bool = False,
                   subtitulo: str = ""):
    """Capa local de reserva, com monograma e gradiente discreto."""
    cv.delete("all")
    borda = ACC if selecionado else LINE
    for y in range(0, h, 4):
        t = y / max(1, h)
        cor = "#%02x%02x%02x" % (int(40 - 12 * t), int(47 - 13 * t), int(73 - 30 * t))
        cv.create_rectangle(0, y, w, y + 4, fill=cor, outline="")
    cv.create_oval(w * 0.12, h * 0.16, w * 0.88, h * 0.73, outline="#45405e", width=1)
    cv.create_rectangle(1, 1, w - 1, h - 1, outline=borda, width=2)
    inicial = (titulo.strip()[:1] or "?").upper()
    cor = ACC if selecionado else "#c6baff"
    cx, cy = w / 2, h * 0.44
    if titulo == "⬇":
        cv.create_line(cx, cy - 30, cx, cy + 20, fill=cor, width=5)
        cv.create_line(cx - 17, cy + 5, cx, cy + 22, cx + 17, cy + 5, fill=cor, width=5)
        cv.create_line(cx - 24, cy + 34, cx + 24, cy + 34, fill=cor, width=4)
    elif titulo == "☆":
        pontos = []
        for i in range(10):
            raio = 34 if i % 2 == 0 else 15
            angulo = math.pi * i / 5 - math.pi / 2
            pontos.extend((cx + raio * math.cos(angulo), cy + raio * math.sin(angulo)))
        cv.create_polygon(*pontos, fill="", outline=cor, width=3)
    elif titulo == "♪":
        cv.create_line(cx + 8, cy - 28, cx + 8, cy + 18, fill=cor, width=4)
        cv.create_line(cx + 8, cy - 28, cx + 27, cy - 20, fill=cor, width=5)
        cv.create_oval(cx - 12, cy + 10, cx + 9, cy + 25, fill=cor, outline="")
    else:
        cv.create_text(cx, cy, text=inicial, fill=cor,
                       font=("Segoe UI", 56 if grande else 42, "bold"))
    base_y = h - (30 if grande else 22)
    if subtitulo:
        cv.create_text(w // 2, base_y - (16 if grande else 13), text=subtitulo,
                       fill=ACC, font=("Segoe UI", 10 if grande else 9, "bold"))
    caption = {"⬇": "Download", "♪": "Música local", "☆": "Lista de desejos"}.get(titulo, "sem capa")
    cv.create_text(w // 2, base_y, text=caption,
                   fill=MUT, font=("Segoe UI", 9 if grande else 8))


class App:
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
        self.root.after_idle(lambda: _titulo_escuro(self.root))
        self.root.bind("<Destroy>", self._fechar_player, add="+")
        try:
            self._mus_poll = self.root.after(50, self._processar_mus_resultados)
            self._mus_vigia = self.root.after(1000, self._vigiar_musica)
            self._dl_timer = self.root.after(3000, self._vigiar_downloads)
        except tk.TclError:
            pass

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
        idx_mus = next(i for i, (rot, _s, _f) in enumerate(NAV)
                       if rot.startswith("🎵"))
        idx_des = next(i for i, (rot, _s, _f) in enumerate(NAV)
                       if rot.startswith("☆"))
        idx_dl = next(i for i, (rot, _s, _f) in enumerate(NAV)
                      if rot.startswith("⬇ D"))
        por_nav: dict[int, ttk.Button] = {}

        def filha(mae, i, texto=None):
            b = ttk.Button(mae["corpo"], text=texto or NAV[i][0],
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
        por_nav[idx_des] = item(NAV[idx_des][0],
                                lambda i=idx_des: self._ir_nav(i))
        por_nav[idx_dl] = item(NAV[idx_dl][0],
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
        self.nav_btns = [por_nav[i] for i in range(len(NAV))]
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
        for i, (rotulo, _s, _f) in enumerate(NAV):
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
            lin2, textvariable=self.var_statusfiltro, values=list(STATUS_FILTROS),
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
        return (216, 288) if self.big_picture else (CARD_W, CARD_H)

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
        _titulo_escuro(dlg)

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
        titulo = NAV[self.nav_idx][0].split(" ", 1)[-1]
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

    def _ir_fila_arvore(self):
        """Filha Fila: vai p/ Músicas e troca o modo (fora dela, só o modo)."""
        if not self._em_musicas():
            for i, (rot, _s, _f) in enumerate(NAV):
                if rot.startswith("🎵"):
                    self._ir_nav(i)
                    break
        self._ir_fila()

    # -- volume geral do PC (persistente entre abas, separado do player)
    def _montar_volume_pc(self, side):
        if not core.volume_pc_disponivel():
            return
        self._vol_sincronizando = True
        self._vol_arrastando = False
        self._vol_fechado = False
        self._vol_pendente = None
        self._vol_poll = None
        self.var_volume_pc = tk.DoubleVar(value=0)
        self.var_volume_pct = tk.StringVar(value="—")
        fr = ttk.Frame(side, style="Panel.TFrame")
        fr.pack(side="bottom", fill="x", padx=10, pady=(8, 12))
        cab = ttk.Frame(fr, style="Panel.TFrame")
        cab.pack(fill="x")
        ttk.Label(cab, text="VOLUME DO PC", style="Panel.TLabel",
                  foreground=MUT, font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Label(cab, textvariable=self.var_volume_pct,
                  style="Panel.TLabel").pack(side="right")
        self.escala_volume_pc = ttk.Scale(
            fr, from_=0, to=100, orient="horizontal",
            variable=self.var_volume_pc, style="Volume.Horizontal.TScale",
            command=self._volume_arrastar, state="disabled")
        self.escala_volume_pc.pack(fill="x", pady=6)
        self.escala_volume_pc.bind("<ButtonPress-1>", self._volume_iniciar_arrasto)
        self.escala_volume_pc.bind("<ButtonRelease-1>", self._volume_fim_arrasto)
        botoes = ttk.Frame(fr, style="Panel.TFrame")
        botoes.pack(fill="x")
        self.btn_volume_menos = ttk.Button(
            botoes, text="−", width=3, state="disabled", style="Volume.TButton",
            command=lambda: self._volume_ajustar(-5))
        self.btn_volume_menos.pack(side="left")
        self.btn_volume_mudo = ttk.Button(
            botoes, text="Silenciar", width=9, state="disabled", style="Volume.TButton",
            command=self._volume_alternar_mudo)
        self.btn_volume_mudo.pack(side="left", fill="x", expand=True, padx=4)
        self.btn_volume_mais = ttk.Button(
            botoes, text="+", width=3, state="disabled", style="Volume.TButton",
            command=lambda: self._volume_ajustar(5))
        self.btn_volume_mais.pack(side="right")
        self._vol_sincronizando = False
        self.root.bind("<Destroy>", self._fechar_volume_pc, add="+")
        self._vol_poll = self.root.after(0, self._sincronizar_volume_pc)

    def _volume_iniciar_arrasto(self, _e=None):
        self._vol_arrastando = True

    def _volume_fim_arrasto(self, _e=None):
        self._vol_arrastando = False

    def _volume_mostrar(self, estado: dict, avisar=False):
        if self._vol_fechado:
            return
        self._vol_sincronizando = True
        try:
            if estado.get("ok"):
                self.var_volume_pc.set(estado["nivel"])
                self.var_volume_pct.set(f"{round(estado['nivel'])}%")
                self.btn_volume_mudo.configure(
                    text="Ativar som" if estado["mudo"] else "Silenciar")
                state = "normal"
            else:
                self.var_volume_pct.set("—")
                self.btn_volume_mudo.configure(text="Sem saída")
                state = "disabled"
                if avisar:
                    self._aviso_barra(estado.get("erro") or "Volume do PC indisponível")
            for w in (self.escala_volume_pc, self.btn_volume_menos,
                      self.btn_volume_mudo, self.btn_volume_mais):
                w.configure(state=state)
        finally:
            self._vol_sincronizando = False

    def _sincronizar_volume_pc(self):
        if self._vol_fechado:
            return
        if not self._vol_arrastando and self._vol_pendente is None:
            self._volume_mostrar(core.ler_volume_pc())
        self._vol_poll = self.root.after(1000, self._sincronizar_volume_pc)

    def _volume_cancelar_pendente(self):
        if self._vol_pendente is not None:
            self.root.after_cancel(self._vol_pendente)
            self._vol_pendente = None

    def _volume_arrastar(self, valor):
        if self._vol_sincronizando or self._vol_fechado:
            return
        nivel = round(float(valor))
        self.var_volume_pct.set(f"{nivel}%")
        self._volume_cancelar_pendente()
        self._vol_pendente = self.root.after(80, self._volume_aplicar, nivel)

    def _volume_aplicar(self, nivel):
        self._vol_pendente = None
        if not self._vol_fechado:
            self._volume_mostrar(
                core.definir_volume_pc(nivel, mudo=False if nivel > 0 else None),
                avisar=True)

    def _volume_ajustar(self, delta):
        self._volume_cancelar_pendente()
        self._volume_mostrar(core.ajustar_volume_pc(delta), avisar=True)

    def _volume_alternar_mudo(self):
        self._volume_cancelar_pendente()
        self._volume_mostrar(core.alternar_mudo_pc(), avisar=True)

    def _fechar_volume_pc(self, evento):
        if evento.widget is not self.root or self._vol_fechado:
            return
        self._vol_fechado = True
        self._volume_cancelar_pendente()
        if self._vol_poll is not None:
            self.root.after_cancel(self._vol_poll)

    # -- navegação / grade
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
            i = max(0, min(int(i), len(NAV) - 1))
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
        # Não chama update/update_idletasks aqui: Configure pode reentrar
        # e deixar a reorganização antiga sobrescrever a largura nova.

    # -- dados
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
                        messagebox.showerror(contexto, f"falha inesperada: {msg}")
                    except Exception:
                        pass
                try:
                    self._depois(fim)
                except Exception:
                    pass
        return alvo

    # -- usuário jogador (perfis de D:\Games\trocar-nome-jogador.py)
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
            messagebox.showinfo(
                "Usuário jogador",
                "Perfis indisponíveis: D:\\Games\\trocar-nome-jogador.py não encontrado.")
            return
        est = self._estado_jogador()
        dlg = tk.Toplevel(self.root)
        _titulo_escuro(dlg)
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
        _com_rolagem(lb)
        usuarios = list(est.get("usuarios") or [])
        atual = (est.get("atual") or "").strip()
        for u in usuarios:
            lb.insert("end", f"● {u}" if u == atual else f"○ {u}")
        if usuarios:
            lb.selection_set(usuarios.index(atual) if atual in usuarios else 0)

        def usar():
            idx = lb.curselection()
            if not idx and usuarios:
                messagebox.showinfo("Usuário", "Selecione um usuário na lista.")
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
                        messagebox.showinfo(
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
        _titulo_escuro(prog)
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
                    messagebox.showinfo("Usuário jogador",
                                        f"'{nome}' aplicado aos jogos ✓")
                else:
                    messagebox.showerror("Usuário jogador",
                                         "Falhou em algum jogo (backups .bak intactos).")

            self._depois(fim)

        import threading
        threading.Thread(target=self._thread_segura(
            trabalho, prog, "Usuário jogador"), daemon=True).start()

    def _em_musicas(self) -> bool:
        """Aba Músicas ativa? (mesma janela e banco dos jogos)."""
        try:
            return NAV[self.nav_idx][0].startswith("🎵")
        except (IndexError, AttributeError):
            return False

    def _em_desejos(self) -> bool:
        """Aba Desejos ativa? (wishlist Steam espelhada)."""
        try:
            return NAV[self.nav_idx][0].startswith("☆")
        except (IndexError, AttributeError):
            return False

    def _em_downloads(self) -> bool:
        """Aba Downloads ativa? (% dos torrents do qBittorrent)."""
        try:
            return NAV[self.nav_idx][0].startswith("⬇ D")
        except (IndexError, AttributeError):
            return False

    def recarregar(self):
        selecionado_id = (self.jogos[self.sel]["id"] if self.sel is not None
                          and 0 <= self.sel < len(self.jogos) else None)
        if self._deb is not None:
            self.root.after_cancel(self._deb)
            self._deb = None
        self.nav_idx = max(0, min(int(self.nav_idx), len(NAV) - 1))
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
            self.nav_idx = max(0, min(int(self.nav_idx), len(NAV) - 1))
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

    # -- aba Desejos (wishlist Steam espelhada; download pelas fontes)
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
        lst = _nova_grade_tv(self.grade, ("Desejo", "Steam"))
        lst.pack(fill="both", expand=True)
        _com_rolagem(lst)
        _tv_por(lst, [(d.get("titulo", "?"), f"appid {d.get('appid', '?')}")
                      for d in self.desejos])
        _tv_marcar(lst, self.des_sel)
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

    # -- aba Downloads (% dos torrents do qBittorrent; auto-import ao fechar)
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
        lst = _nova_grade_tv(self.grade, ("Download", "Progresso"))
        lst.pack(fill="both", expand=True)
        _com_rolagem(lst)
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
        _tv_por(lst, linhas_dl)
        _tv_marcar(lst, self.dl_sel)
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
            messagebox.showinfo("qBittorrent", "Este item pertence ao histórico local, não ao cliente conectado.")
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
                    messagebox.showwarning(contexto, res.get("erro", "falha"))
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
        i = _tv_sel(self._dl_lista)
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
            messagebox.showinfo("Downloads", "Selecione um download na lista.")
            return
        try:
            alvo = str(Path(t["save_path"]).parent) \
                if Path(t["save_path"]).is_file() \
                else str(Path(t["save_path"]))
        except (TypeError, ValueError):
            messagebox.showwarning("Downloads", "Pasta inválida.")
            return
        if os.name == "nt":
            try:
                os.startfile(alvo)
            except OSError as e:
                messagebox.showwarning("Downloads", f"falha: {e}")
        else:
            messagebox.showinfo("Downloads", alvo)

    def verificar_concluidos_ui(self):
        """Importa p/ o Hub todo torrent 100% (thread, com backup)."""
        prontos = [t for t in self.dls if t.get("completo") and t.get("save_path")]
        if not prontos:
            messagebox.showinfo("Downloads", "Nada 100% ainda.")
            return
        prog = tk.Toplevel(self.root)
        _titulo_escuro(prog)
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
                messagebox.showinfo("Downloads", "\n".join(linhas[:12]))
            self._depois(fim)

        threading.Thread(target=self._thread_segura(
            trabalho, prog, "Verificar concluídos"), daemon=True).start()

    def _ao_sel_desejo(self, _e=None):
        i = _tv_sel(self._des_lista)
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
        _titulo_escuro(prog)
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
                    messagebox.showwarning("Desejos", "\n".join(res["erros"]))
                else:
                    messagebox.showinfo("Desejos", detalhe)
            self._depois(lambda: fim())

        threading.Thread(target=trabalho, daemon=True).start()

    def adicionar_desejo_ui(self):
        """➕ Adicionar: busca o título na loja pública e grava o escolhido."""
        win = tk.Toplevel(self.root)
        _titulo_escuro(win)
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
        _com_rolagem(lst)
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
                messagebox.showinfo("Desejos", "Busque e escolha um jogo.")
                return
            it = achados[sel[0]]
            con = self._con()
            try:
                self._backup_pre_import()
                core.adicionar_desejo(con, it["appid"], it["titulo"])
            except (ValueError, LookupError) as e:
                messagebox.showwarning("Desejos", f"falha: {e}")
                return
            except Exception as e:
                core.log_erro("adicionar-desejo", f"{type(e).__name__}: {e}")
                messagebox.showwarning("Desejos", f"falha: {e}")
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
            messagebox.showinfo(
                "Desejos", "Conta Steam não achada neste PC.")
            return
        url = ("https://store.steampowered.com/wishlist/profiles/"
               f"{conta['steamid']}/")
        res = core.abrir_url(url)
        if not res.get("ok"):
            messagebox.showwarning(
                "Desejos",
                f"Navegador não abriu ({res.get('erro', 'falha')}).\n"
                f"Cole no navegador logado:\n{url}")
            return
        messagebox.showinfo(
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
            messagebox.showerror("Desejos", leitura["erros"][0])
            return
        self._backup_pre_import()
        con = self._con()
        try:
            res = core.sincronizar_desejos(con, leitura["itens"])
        except Exception as e:
            messagebox.showerror("Desejos", f"falha: {e}")
            return
        finally:
            con.close()
        self.recarregar()
        messagebox.showinfo(
            "Desejos",
            f"{res['novos']} novo(s), {res['atualizados']} atualizado(s), "
            f"{res['removidos']} removido(s)")

    def excluir_desejo_selecionado(self):
        d = self._desejo_sel()
        if d is None:
            return
        if not messagebox.askokcancel(
                "Desejos", f"Tirar '{d['titulo']}' da lista?"):
            return
        con = self._con()
        try:
            core.remover_desejo(con, d["id"])
        except LookupError as e:
            messagebox.showwarning("Desejos", str(e))
            return
        finally:
            con.close()
        self.des_sel = None
        self.recarregar()

    def buscar_desejo_download(self):
        """Abre os catálogos já buscando o título do desejo."""
        d = self._desejo_sel()
        if d is None:
            messagebox.showinfo("Desejos", "Selecione um desejo na lista.")
            return
        opcoes = tk.Toplevel(self.root)
        _titulo_escuro(opcoes)
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

    # -- aba Músicas (lista embutida na grade; play externo segue com o jogo)
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
        lst = _nova_grade_tv(self.grade, ("Música", "Artista · Álbum"))
        lst.pack(fill="both", expand=True)
        _com_rolagem(lst)
        linhas_mus = []
        for m in self.musicas:
            try:
                linhas_mus.append((core.texto_musica(m), " · ".join(
                    x for x in (m.get("artista"), m.get("album")) if x)))
            except Exception:
                continue
        _tv_por(lst, linhas_mus)
        _tv_marcar(lst, self.mus_sel)
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
        i = _tv_sel(self._mus_lista)
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
            messagebox.showinfo("Fila", "Aqui é a fila de downloads (Fase B).")
            return
        if self.mus_sel is None or self.mus_sel >= len(self.musicas):
            messagebox.showinfo("Músicas", "Selecione uma música na lista.")
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
            messagebox.showinfo("Músicas", "Selecione uma música na lista.")
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
                messagebox.showwarning("Músicas", r.get("erro", "falha"))
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
        if not messagebox.askyesno(
                "Dependências de áudio",
                "Falta: " + ", ".join(p[1] for p in pend)
                + ".\nBaixar do oficial agora?"):
            return
        prog = tk.Toplevel(self.root)
        _titulo_escuro(prog)
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
                messagebox.showwarning("Dependências de áudio",
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
            messagebox.showwarning("Músicas", r.get("erro", "falha"))

    def mus_alternar(self):
        if self._mus_carregando:
            return
        if self.player.estado == "parado":
            self.tocar_musica_selecionada()
            return
        r = self.player.alternar()
        if not r.get("ok"):
            messagebox.showwarning("Músicas", r.get("erro", "falha"))
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
            _tv_marcar(self._mus_lista, pos)
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
        if not messagebox.askokcancel(
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
            messagebox.showwarning("Músicas", str(e))
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
        lst = _nova_grade_tv(self.grade, ("Faixa", "Estado"))
        lst.pack(fill="both", expand=True)
        _com_rolagem(lst)
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
        _tv_por(lst, linhas_fila)
        _tv_marcar(lst, self.fila_sel)
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
        i = _tv_sel(self._mus_lista)
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
            messagebox.showwarning("Baixar de CSV", parsed["erros"][0])
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
        messagebox.showinfo("Baixar de CSV", detalhe)
        if self._em_musicas():
            try:
                self.recarregar()
            except tk.TclError:
                pass

    def baixar_fila(self, oferecer=True):
        """Start Downloads do Harmoni: baixa pendentes em thread (Fase B)."""
        th = getattr(self, "_th_fila", None)
        if th is not None and th.is_alive():
            messagebox.showinfo("Baixar fila", "Download já em andamento.")
            return
        if not core.localizar_ytdlp():
            if oferecer:
                self.instalar_deps_audio(
                    ("ytdlp",),
                    ao_fim=lambda: self.baixar_fila(oferecer=False))
            else:
                messagebox.showwarning("Baixar fila", core.erro_sem_ytdlp())
            return
        con = self._con()
        try:
            try:
                ids = [d["id"] for d in core.listar_downloads(con)
                       if d.get("estado") in ("pendente", "falha")]
            except Exception as e:
                messagebox.showwarning("Baixar fila", f"falha: {e}")
                return
        finally:
            con.close()
        if not ids:
            messagebox.showinfo("Baixar fila", "Nada pendente.")
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
            messagebox.showinfo("Importar baixadas", "Operação em andamento.")
            return
        con = self._con()
        try:
            try:
                n = len(core.listar_downloads(con, estado="baixado"))
            except Exception as e:
                messagebox.showwarning("Importar baixadas", f"falha: {e}")
                return
        finally:
            con.close()
        if not n:
            messagebox.showinfo("Importar baixadas",
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
            messagebox.showinfo("Importar baixadas", detalhe)
        except tk.TclError:
            pass

    # -- catálogos (buscar → links → baixar/abrir → importar repack)
    def dlg_catalogo(self, fonte="steamrip", termo=None):
        fontes = {
            "steamrip": {"titulo": "Catálogo SteamRip",
                         "lista": "Hosts da página:",
                         "buscar": core.buscar_steamrip},
            "fitgirl": {"titulo": "Catálogo FitGirl",
                        "lista": "Espelhos e magnets:",
                        "buscar": core.buscar_fitgirl},
        }
        cfg = fontes.get(fonte) or fontes["steamrip"]
        marca = "FitGirl" if fonte == "fitgirl" else "SteamRip"
        win = tk.Toplevel(self.root)
        _titulo_escuro(win)
        win.title(cfg["titulo"])
        win.transient(self.root)
        win.minsize(560, 460)
        fr = ttk.Frame(win, padding=12)
        fr.pack(fill="both", expand=True)
        topo = ttk.Frame(fr)
        topo.pack(fill="x")
        var_q = tk.StringVar()
        ent = ttk.Entry(topo, textvariable=var_q, width=40)
        ent.pack(side="left", fill="x", expand=True)
        ent.bind("<Return>", lambda _e: buscar())
        resultados: list[dict] = []
        links: list[dict] = []  # {tipo: host/espelho/magnet, nome, url}
        consulta = {"busca": 0, "hosts": 0}
        suprimir = {"evento": False}  # seleção programática não recarrega
        self._sr_ultimo = getattr(self, "_sr_ultimo", "")
        area_r = ttk.Frame(fr)
        area_r.pack(fill="both", expand=True, pady=(8, 0))
        lst_r = tk.Listbox(area_r, selectmode="single", width=70, height=9,
                           bg="#0b0d12", fg=TXT, selectbackground=ACC,
                           exportselection=False,
                           font=("Segoe UI", 11))
        lst_r.pack(fill="both", expand=True)
        _com_rolagem(lst_r)
        ttk.Label(fr, text=cfg["lista"], style="Mut.TLabel").pack(
            anchor="w", pady=(8, 0))
        area_h = ttk.Frame(fr)
        area_h.pack(fill="x")
        lst_h = tk.Listbox(area_h, selectmode="single", width=70, height=4,
                           bg="#0b0d12", fg=TXT, selectbackground=ACC,
                           exportselection=False,
                           font=("Segoe UI", 10))
        lst_h.pack(fill="x")
        _com_rolagem(lst_h)
        lbl = ttk.Label(fr, text="Busque um jogo.", style="Mut.TLabel")
        lbl.pack(anchor="w", pady=(8, 0))
        fr_btn = BarraAcoes(fr)
        fr_btn.pack(fill="x", pady=(8, 0))
        fr_btn.adicionar("Buscar", lambda: buscar())
        if fonte == "fitgirl":
            fr_btn.adicionar("Abrir selecionado", lambda: abrir_link())
            fr_btn.adicionar("Abrir página", lambda: abrir())
            fr_btn.adicionar("Importar arquivo…", lambda: importar_arquivo())
        else:
            fr_btn.adicionar("⬇ Baixar p/ Piratas", lambda: baixar())
            fr_btn.adicionar("Abrir página", lambda: abrir())
            fr_btn.adicionar("Importar último", lambda: importar_ultimo())
        fr_btn.adicionar("Fechar", win.destroy)

        def estado(txt):
            self._depois(lambda: lbl.configure(text=txt))

        def buscar(q=None):
            termo = (q if q is not None else var_q.get()).strip()
            if not termo:
                return
            consulta["busca"] += 1
            consulta["hosts"] += 1
            meu = consulta["busca"]
            estado(f"Buscando '{termo}'…")

            def trabalho(termo_fx=termo):
                try:
                    res = cfg["buscar"](termo_fx)
                except Exception as e:
                    res = {"itens": [], "erros": [str(e)]}
                self._depois(lambda: fim_busca(res, termo_fx, meu))

            threading.Thread(target=trabalho, daemon=True).start()

        def fim_busca(res, termo, meu):
            if not win.winfo_exists() or meu != consulta["busca"]:
                return
            resultados.clear()
            resultados.extend(res.get("itens") or [])
            links.clear()
            lst_r.delete(0, "end")
            lst_h.delete(0, "end")
            for it in resultados:
                lst_r.insert("end", it["titulo"])
            if res.get("erros"):
                estado(f"Falha: {res['erros'][0]}")
            else:
                estado(f"{len(resultados)} resultado(s) p/ '{termo}'.")
                if resultados:
                    suprimir["evento"] = True
                    try:
                        lst_r.selection_set(0)
                    finally:
                        suprimir["evento"] = False
                    ver_links()

        def pagina_sel():
            sel = lst_r.curselection()
            if not sel or sel[0] >= len(resultados):
                return None
            return resultados[sel[0]]

        def ver_links(_e=None):
            if suprimir["evento"]:
                return
            pg = pagina_sel()
            consulta["hosts"] += 1
            meu = consulta["hosts"]
            links.clear()
            lst_h.delete(0, "end")
            if not pg:
                return
            estado("Consultando links…")

            def trabalho(pg_fx=pg):
                try:
                    if fonte == "fitgirl":
                        det = core.detalhes_fitgirl(pg_fx["url"])
                    else:
                        det = core.detalhes_steamrip(pg_fx["url"])
                except Exception as e:
                    det = {"erro": str(e)}

                def fim():
                    if not win.winfo_exists() or meu != consulta["hosts"]:
                        return
                    if det.get("erro"):
                        estado(f"Falha: {det['erro']}")
                        return
                    if fonte == "fitgirl":
                        for h in det.get("espelhos") or []:
                            links.append({"tipo": "espelho", **h})
                        for m in det.get("magnets") or []:
                            links.append({"tipo": "magnet",
                                          "nome": core.nome_magnet(m),
                                          "url": m})
                    else:
                        for h in det.get("hosts") or []:
                            links.append({"tipo": "host", **h})
                    for e in links:
                        if e["tipo"] == "magnet":
                            lst_h.insert("end", f"🧲 {e['nome']}")
                        else:
                            lst_h.insert("end", f"{e['nome']} — {e['url'][:70]}")
                    estado(f"{pg_fx['titulo']}: {len(links)} link(s) — "
                           "clique escolhe o host, duplo-clique baixa.")
                self._depois(fim)

            threading.Thread(target=trabalho, daemon=True).start()

        def host_sel():
            sel = lst_h.curselection()
            if sel and sel[0] < len(links) \
                    and links[sel[0]]["tipo"] != "magnet":
                return links[sel[0]]["nome"]
            return ""

        def host_feedback(_e=None):
            nome = host_sel()
            if nome:
                estado(f"via {nome} (duplo-clique baixa direto).")
            elif links:
                estado(f"{len(links)} link(s) — automático (todos).")
            else:
                estado("Sem links — busque e escolha um resultado.")

        def link_sel():
            sel = lst_h.curselection()
            if sel and sel[0] < len(links):
                return links[sel[0]]
            return None

        def baixar():
            pg = pagina_sel()
            if not pg:
                messagebox.showinfo(marca, "Escolha um resultado.")
                return
            estado(f"Baixando '{pg['titulo']}'…")

            def trabalho(pg_fx=pg, host_fx=host_sel()):
                try:
                    res = core.baixar_steamrip(
                        pg_fx["url"], host=host_fx,
                        progresso=lambda f, t: estado(
                            f"Baixando: {f/1048576:.0f}/"
                            f"{t/1048576:.0f}MB" if t
                            else f"Baixando: {f/1048576:.0f}MB"))
                except Exception as e:
                    res = {"ok": False, "erro": str(e)}
                self._depois(lambda: fim_baixar(res))

            threading.Thread(target=trabalho, daemon=True).start()

        def fim_baixar(res):
            if not res.get("ok"):
                estado(f"Falha: {res.get('erro', 'falha')}")
                if fonte == "steamrip" and messagebox.askyesno(
                        marca, f"{res.get('erro', 'falha')}\n\n"
                        "Links mortos no SteamRip. Tentar no FitGirl?"):
                    try:
                        termo_atual = var_q.get().strip()
                    except tk.TclError:
                        termo_atual = ""
                    self.dlg_catalogo("fitgirl", termo_atual)
                    return
                messagebox.showwarning(marca, res.get("erro", "falha"))
                return
            self._sr_ultimo = res["path"]
            estado(f"Em Piratas/: {Path(res['path']).name}")
            if messagebox.askyesno(marca,
                                   "Baixado. Importar para o Hub agora?"):
                importar_ultimo()

        def abrir():
            pg = pagina_sel()
            if not pg:
                return
            r = core.abrir_url(pg["url"])
            if not r.get("ok"):
                messagebox.showwarning(marca, r.get("erro", "falha"))

        def abrir_link():
            e = link_sel()
            if not e:
                messagebox.showinfo(marca, "Escolha um espelho ou magnet.")
                return
            r = core.abrir_url(e["url"])
            if r.get("ok"):
                estado(f"Aberto: {e['nome'][:60]}")
            else:
                messagebox.showwarning(marca, r.get("erro", "falha"))

        def importar_arquivo():
            try:
                from bib_nucleo.repacks import pasta_piratas
                ini = str(pasta_piratas())
            except Exception:
                ini = ""
            arq = filedialog.askopenfilename(
                title="Repack baixado (.rar/.zip/.7z/.iso)", parent=win,
                initialdir=ini or None,
                filetypes=[("Repacks", "*.rar *.zip *.7z *.iso"),
                           ("Todos", "*.*")]) or ""
            if arq:
                importar_ultimo(arq)

        def importar_ultimo(arq=None):
            if arq is None:
                arq = getattr(self, "_sr_ultimo", "")
            if not arq or not Path(arq).is_file():
                messagebox.showinfo(marca, "Nada baixado ainda.")
                return
            estado("Importando…")

            def trabalho(arq_fx=arq):
                con = None
                try:
                    self._backup_pre_import()
                    con = self._con()
                    res = core.importar_repack(con, arq_fx)
                except Exception as e:
                    res = {"ok": False, "erro": str(e)}
                finally:
                    try:
                        if con is not None:
                            con.close()
                    except Exception:
                        pass
                self._depois(lambda: fim_imp(res))

            threading.Thread(target=trabalho, daemon=True).start()

        def fim_imp(res):
            if res.get("ok"):
                self.recarregar()
                estado("Importado ✓")
                messagebox.showinfo(marca, "Jogo importado ✓")
            else:
                estado(f"Falha: {res.get('erro', 'falha')}")
                messagebox.showwarning(marca, res.get("erro", "falha"))

        lst_r.bind("<<ListboxSelect>>", ver_links)
        lst_h.bind("<<ListboxSelect>>", host_feedback)
        if fonte == "fitgirl":
            lst_r.bind("<Double-Button-1>", lambda _e: abrir())
            lst_h.bind("<Double-Button-1>", lambda _e: abrir_link())
        else:
            lst_r.bind("<Double-Button-1>", lambda _e: baixar())
            lst_h.bind("<Double-Button-1>", lambda _e: baixar())
        ent.focus_set()
        if (termo or "").strip():
            var_q.set(termo.strip())
            buscar(termo.strip())

    def limpar_fila(self):
        """Clear Done do Harmoni: apaga prontas/falhas (CSV recria)."""
        con = self._con()
        try:
            try:
                n = core.limpar_downloads(con)
            except ValueError as e:
                messagebox.showwarning("Fila", str(e))
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

    def _criar_card(self, j: dict) -> dict:
        largura, altura = self._tamanho_card()
        fr = ttk.Frame(self.grade, style="Card.TFrame", cursor="hand2")
        img = None
        if j.get("capa"):
            alvo = core.caminho_capa(j["capa"])
            if alvo is not None:
                img = carregar_miniatura(alvo, largura, altura, master=self.root)
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
            desenhar_tile(cv, j["titulo"], largura, altura, subtitulo=plat_cv)
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
        cor = STATUS_CORES.get(j["status"], MUT)
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
                    desenhar_tile(w, c["jogo"]["titulo"], *self._tamanho_card(),
                                  selecionado=sel,
                                  subtitulo=(c["jogo"].get("plataforma") or ""))

    # -- detalhe / seleção
    def selecionado(self) -> dict | None:
        if self.sel is None or self.sel >= len(self.jogos):
            messagebox.showinfo("Biblioteca", "Selecione um jogo na grade.")
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
                desenhar_tile(self.det_capa, "⬇", 216, 280, grande=True)
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
            desenhar_tile(self.det_capa, "⬇", 216, 280, grande=True,
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
                desenhar_tile(self.det_capa, "☆", 216, 280, grande=True)
                return
            self.det_titulo.configure(text=d["titulo"])
            self.det_meta.configure(text=f"Steam appid {d['appid']}")
            self.det_exe.configure(
                text=f"https://store.steampowered.com/app/{d['appid']}/")
            desenhar_tile(self.det_capa, "☆", 216, 280, grande=True,
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
                desenhar_tile(self.det_capa, "⬇", 216, 280, grande=True)
                return
            d = self.fila[self.fila_sel]
            self.det_titulo.configure(
                text=core.texto_musica(d) or "Sem título")
            meta = " · ".join(x for x in (d.get("estado"), d.get("artista"),
                                          d.get("album")) if x)
            self.det_meta.configure(text=meta)
            self.det_exe.configure(
                text=d.get("erro") or d.get("video_id") or d.get("uri") or "")
            desenhar_tile(self.det_capa, "⬇", 216, 280, grande=True,
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
                desenhar_tile(self.det_capa, "♪", 216, 280, grande=True)
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
                    img = carregar_miniatura(alvo, 216, 280)
                except Exception:
                    img = None
            self._img_det = img
            if img is not None:
                try:
                    self.det_capa.create_image(108, 140, image=img)
                except tk.TclError:
                    desenhar_tile(self.det_capa, "♪", 216, 280, grande=True,
                                  subtitulo="música")
            else:
                desenhar_tile(self.det_capa, "♪", 216, 280, grande=True,
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
            desenhar_tile(self.det_capa, "?", 216, 280, grande=True)
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
        img = carregar_miniatura(alvo, 216, 280) if alvo else None
        self._img_det = img
        if img is not None:
            self.det_capa.create_image(108, 140, image=img)
        else:
            desenhar_tile(self.det_capa, j["titulo"], 216, 280, grande=True,
                          subtitulo=plat)

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

    # -- ações
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
                messagebox.showwarning("Preset", prep["aviso"])
            res = core.executar_monitorado(
                j, ao_fim=lambda sessao, rastreado, _gid=j["id"]:
                    self._depois(lambda: self._sessao_fim(_gid, sessao, rastreado)))
            if res.get("requer_elevacao") and messagebox.askyesno(
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
                    messagebox.showerror("Jogar", res.get("erro", "falha"))
            elif res.get("ok"):
                core.marcar_execucao(con, j["id"])
                if res.get("rastreado"):
                    extra = "⏱ tempo será registrado"
                else:
                    extra = "⏱ sem rastreio — sessão manual aberta; ao terminar use ⏱ Registrar sessão"
                self._minimizar_janela()
                self._aviso_barra(f"Executando ({res.get('modo')}) — {extra}")
            else:
                messagebox.showerror("Jogar", res.get("erro", "falha"))
        finally:
            con.close()
        self.recarregar()

    def registrar_sessao_manual(self):
        """Fecha sessão manual: pergunta horas e soma (fallback UAC/startfile)."""
        try:
            pend = core.listar_sessoes_pendentes()
        except Exception as e:
            messagebox.showerror("Sessão", f"falha ao listar: {e}")
            return
        if not pend:
            messagebox.showinfo("Sessão", "Nenhuma sessão manual pendente.")
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
            messagebox.showerror("Sessão", f"falha: {e}")
            return
        if res.get("ok"):
            self.recarregar()
            messagebox.showinfo("Sessão", f"+{horas}h registradas ✓" if horas else "Sessão encerrada (sem horas).")
        else:
            messagebox.showerror("Sessão", res.get("erro", "falha"))

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
                    filetypes=[("ROMs 3DS", "*.cci *.cxi *.3ds *.3dsx *.app *.elf *.axf"),
                               ("ROMs NDS", "*.nds *.dsi"), ("Todos", "*.*")])
                if escolhido and not messagebox.askyesno("Localizar ROM", f"Gravar este novo caminho?\n{escolhido}"):
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
        if self._em_musicas() or self._em_desejos() or self._em_downloads():
            return
        j = self.selecionado()
        if j:
            self._dlg_jogo(j)

    def _dlg_jogo(self, j: dict | None):
        dlg = tk.Toplevel(self.root)
        _titulo_escuro(dlg)
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
                messagebox.showwarning("Preset", "Escolha o sistema primeiro.")
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
                messagebox.showwarning("Preset", r.get("erro", "falha"))

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
                messagebox.showwarning(
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
                messagebox.showwarning(
                    "Texturas", "Salve o jogo com a ROM primeiro.")
                return
            try:
                res = core.definir_textura(tid, not tex_sel["ativo"])
            except Exception as e:
                messagebox.showwarning("Texturas", f"falha: {e}")
                return
            if not res.get("ok"):
                messagebox.showwarning("Texturas", res.get("erro", "falha"))
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
                messagebox.showwarning(
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
                    img = carregar_miniatura(alvo, 200, 140)
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
                messagebox.showerror("Salvar", "Horas deve ser número.")
                return
            con = self._con()
            try:
                try:
                    novo = (core.atualizar_jogo(con, j["id"], dados) if j
                            else core.criar_jogo(con, dados))
                except (ValueError, LookupError) as e:
                    messagebox.showerror("Salvar", str(e))
                    return
                capa_orig = var_capa.get().strip()
                gid = novo["id"]
            finally:
                con.close()
            if not capa_orig:
                dlg.destroy()
                self.sel = None
                self.recarregar()
                messagebox.showinfo("Biblioteca", "Salvo ✓")
                return
            # capa em thread: não trava a UI com arquivos de 2MB
            p = Path(capa_orig)
            if p.suffix.lower() not in core.CAPA_EXTS:
                messagebox.showerror("Capa", "Use png/jpg/webp.")
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
                        messagebox.showerror("Capa", res.get("erro", "falha"))
                    else:
                        messagebox.showinfo("Biblioteca", "Salvo ✓")
                self._depois(fim)

            def _falha_capa(msg):
                try:
                    btn_salvar.configure(state="normal", text="  Salvar  ")
                except tk.TclError:
                    pass
                messagebox.showerror("Capa", msg)

            threading.Thread(target=trabalho_capa, daemon=True).start()

        btn_salvar.configure(command=salvar)

    # -- mods LayeredFS (biblioteca dados/mods/azahar/<tid>/; play ativa via junction)
    def _janela_mods(self, pai, tid, holder, ao_ok=None):
        win = tk.Toplevel(pai)
        _titulo_escuro(win)
        win.title(f"Mods — {tid}" + (" (desligados)" if holder.get("off") else ""))
        win.transient(pai)
        win.grab_set()
        win.minsize(420, 320)
        fr = ttk.Frame(win, padding=12)
        fr.pack(fill="both", expand=True)
        tmp_ativos = set(holder["ativos"])
        lst = tk.Listbox(fr, selectmode="single", width=52, height=10,
                         bg="#0b0d12", fg=TXT, selectbackground=ACC,
                         font=("Segoe UI", 11))
        lst.pack(fill="both", expand=True)
        _com_rolagem(lst)

        def disp():
            try:
                return core.listar_mods(tid)
            except Exception:
                return []

        def redesenhar():
            nomes = disp()
            lst.delete(0, "end")
            for nome in nomes:
                lst.insert("end", f"[{'x' if nome in tmp_ativos else ' '}] {nome}")
            tmp_ativos.intersection_update(nomes)
            return nomes

        def alternar(_e=None):
            sel = lst.curselection()
            if not sel:
                return
            nomes = disp()
            if sel[0] >= len(nomes):
                return
            nome = nomes[sel[0]]
            if nome in tmp_ativos:
                tmp_ativos.discard(nome)
            else:
                tmp_ativos.add(nome)
            redesenhar()
            lst.selection_set(sel[0])

        def adicionar():
            if not messagebox.askyesno("Mods", "De arquivo (.zip/.7z)?\n(Não = de pasta)"):
                pasta = filedialog.askdirectory(title="Pasta do mod", parent=win)
                origem = pasta or ""
            else:
                origem = filedialog.askopenfilename(
                    title="Arquivo do mod", parent=win,
                    filetypes=[("Mods", "*.zip *.7z"), ("Todos", "*.*")]) or ""
            if not origem:
                return
            nome = simpledialog.askstring(
                "Mods", "Nome do mod (vazio=automático):", parent=win)
            if nome is None:
                return
            r = core.importar_mod(origem, tid, (nome or "").strip())
            if not r.get("ok"):
                messagebox.showwarning("Mods", r.get("erro", "falha"))
                return
            tmp_ativos.add(r["mod"])
            redesenhar()

        def remover():
            sel = lst.curselection()
            nomes = disp()
            if not sel or sel[0] >= len(nomes):
                return
            nome = nomes[sel[0]]
            if not messagebox.askokcancel(
                    "Mods", f"Apagar '{nome}' da biblioteca?"):
                return
            r = core.remover_mod(tid, nome)
            if not r.get("ok"):
                messagebox.showwarning("Mods", r.get("erro", "falha"))
                return
            tmp_ativos.discard(nome)
            redesenhar()

        def ok():
            holder["ativos"] = [m for m in disp() if m in tmp_ativos]
            if ao_ok:
                try:
                    ao_ok()
                except Exception as e:
                    core.log_erro("mods", f"ao_ok falhou: {e}")
            win.destroy()

        lst.bind("<Double-Button-1>", alternar)
        redesenhar()
        fr_btn = ttk.Frame(fr)
        fr_btn.pack(fill="x", pady=(10, 0))
        ttk.Button(fr_btn, text="Alternar", command=alternar).pack(side="left")
        ttk.Button(fr_btn, text="Adicionar…", command=adicionar).pack(side="left", padx=6)
        ttk.Button(fr_btn, text="Remover", command=remover).pack(side="left")
        ttk.Button(fr_btn, text="OK", command=ok).pack(side="right")
        ttk.Button(fr_btn, text="Cancelar", command=win.destroy).pack(side="right", padx=6)

    # -- cheats Gateway (user/cheats/<tid>.txt; toggle imediato, vale no reboot)
    def _janela_cheats(self, pai, tid, ao_ok=None):
        win = tk.Toplevel(pai)
        _titulo_escuro(win)
        win.title(f"Cheats — {tid} (vale após reiniciar)")
        win.transient(pai)
        win.grab_set()
        win.minsize(420, 320)
        fr = ttk.Frame(win, padding=12)
        fr.pack(fill="both", expand=True)
        lst = tk.Listbox(fr, selectmode="single", width=52, height=10,
                         bg="#0b0d12", fg=TXT, selectbackground=ACC,
                         font=("Segoe UI", 11))
        lst.pack(fill="both", expand=True)
        _com_rolagem(lst)

        def redesenhar():
            try:
                nomes = core.listar_cheats(tid)
            except Exception:
                nomes = []
            lst.delete(0, "end")
            for c in nomes:
                lst.insert("end", f"[{'x' if c['ativo'] else ' '}] {c['nome']}")
            return [c["nome"] for c in nomes]

        def alternar(_e=None):
            sel = lst.curselection()
            nomes = redesenhar()
            if not sel or sel[0] >= len(nomes):
                return
            try:
                core.alternar_cheat(tid, nomes[sel[0]])
            except Exception as e:
                messagebox.showwarning("Cheats", f"falha: {e}")
                return
            redesenhar()
            lst.selection_set(sel[0])
            if ao_ok:
                try:
                    ao_ok()
                except Exception as e:
                    core.log_erro("cheats", f"ao_ok falhou: {e}")

        def adicionar():
            nome = simpledialog.askstring(
                "Cheats", "Nome do cheat:", parent=win)
            if not nome:
                return
            caixa = tk.Toplevel(win)
            _titulo_escuro(caixa)
            caixa.title("Código (XXXXXXXX YYYYYYYY por linha)")
            caixa.transient(win)
            caixa.grab_set()
            txt = tk.Text(caixa, width=52, height=8, bg="#0b0d12", fg=TXT,
                          insertbackground=TXT, font=("Consolas", 11))
            txt.pack(fill="both", expand=True, padx=12, pady=12)

            def gravar():
                r = core.adicionar_cheat(tid, nome.strip(),
                                         txt.get("1.0", "end"))
                if not r.get("ok"):
                    messagebox.showwarning("Cheats", r.get("erro", "falha"))
                    return
                caixa.destroy()
                redesenhar()

            ttk.Button(caixa, text="Salvar (desligado)",
                       command=gravar).pack(pady=(0, 12))

        def remover():
            sel = lst.curselection()
            nomes = redesenhar()
            if not sel or sel[0] >= len(nomes):
                return
            if not messagebox.askokcancel(
                    "Cheats", f"Apagar '{nomes[sel[0]]}'?"):
                return
            r = core.remover_cheat(tid, nomes[sel[0]])
            if not r.get("ok"):
                messagebox.showwarning("Cheats", r.get("erro", "falha"))
                return
            redesenhar()
            if ao_ok:
                try:
                    ao_ok()
                except Exception as e:
                    core.log_erro("cheats", f"ao_ok falhou: {e}")

        lst.bind("<Double-Button-1>", alternar)
        redesenhar()
        fr_btn = ttk.Frame(fr)
        fr_btn.pack(fill="x", pady=(10, 0))
        ttk.Button(fr_btn, text="Alternar", command=alternar).pack(side="left")
        ttk.Button(fr_btn, text="Adicionar…", command=adicionar).pack(side="left", padx=6)
        ttk.Button(fr_btn, text="Remover", command=remover).pack(side="left")
        ttk.Button(fr_btn, text="Fechar",
                   command=win.destroy).pack(side="right")

    # -- importação unificada (pasta ou arquivo; emulador detectado sozinho)
    def importar_unificado(self):
        dlg = tk.Toplevel(self.root)
        _titulo_escuro(dlg)
        dlg.title("Importar")
        dlg.configure(bg=BG)
        dlg.transient(self.root)
        dlg.grab_set()
        ttk.Label(dlg, wraplength=420, justify="left", text=(
            "Escolha uma PASTA (varre jogos de PC + ROMs de uma vez), um "
            "ARQUIVO (exe, ROM, JSON, pacote .zip ou repack .rar/.7z/.iso) ou LEIA DO DISCO "
            "(Hydra + Steam + Epic + GOG + Riot + programas instalados).\n"
            "Repack extrai p/ Piratas, organiza, acha o exe e importa sozinho; "
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
                    messagebox.showwarning("Sanear", res.get("erro", "falha"))
                    return
                detalhe = f"Pasta: {res['pasta']}"
                if res.get("avisos"):
                    detalhe += "\n" + "\n".join(res["avisos"][:6])
                if res.get("precisa_instalar"):
                    messagebox.showinfo("Sanear", detalhe + "\nSó há instalador — rode o setup antes.")
                    return
                detalhe += f"\nExe: {Path(res['exe']).name}"
                if messagebox.askyesno("Sanear", detalhe + "\n\nImportar para o Hub?"):
                    self._importar_pasta(res["pasta"])
            self._depois(fim)
        threading.Thread(target=self._thread_segura(trabalho, prog, "Sanear"), daemon=True).start()

    def _importar_pasta(self, pasta: str):
        prog = tk.Toplevel(self.root)
        _titulo_escuro(prog)
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
                messagebox.showerror("Importar pasta", f"falha na varredura: {e}")

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
                        messagebox.showwarning(
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
            if ana.get("aviso") and not messagebox.askyesno("Importar", f"{ana['aviso']}\n\nImportar mesmo assim?"):
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
                messagebox.showinfo("Importar", f"{ana['detalhe']} ✓")
            else:
                messagebox.showinfo("Importar", "Já estava na biblioteca (nada novo).")
        else:
            messagebox.showwarning("Importar", ana["detalhe"] or "não suportado.")

    def _importar_repack(self, arq: str):
        prog = tk.Toplevel(self.root)
        _titulo_escuro(prog)
        prog.title("Importar repack")
        prog.transient(self.root)
        ttk.Label(prog, text="Extraindo p/ Piratas e importando...").pack(
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
                messagebox.showerror("Importar repack", msg)

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
                    messagebox.showwarning("Importar repack", detalhe)
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
                messagebox.showinfo("Importar repack", detalhe)
            na_ui(pronto)
        threading.Thread(target=self._thread_segura(trabalho, prog, "Importar repack"), daemon=True).start()

    # -- preview / importação
    def _dlg_prev(self, titulo: str, sub: str, itens: list[dict]):
        dlg = tk.Toplevel(self.root)
        _titulo_escuro(dlg)
        dlg.title(titulo)
        dlg.configure(bg=BG)
        dlg.geometry("700x480")
        dlg.transient(self.root)
        dlg.grab_set()
        ttk.Label(dlg, text=sub, wraplength=660).pack(anchor="w", padx=10, pady=6)
        lb = tk.Listbox(dlg, selectmode="multiple", bg="#0b0d12", fg=TXT,
                        selectbackground=ACC, font=("Segoe UI", 10))
        lb.pack(fill="both", expand=True, padx=10)
        _com_rolagem(lb)
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
                messagebox.showinfo(titulo, "Nada selecionado.")
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
            messagebox.showinfo(titulo, core.resumo_importacao(res))

        ttk.Button(dlg, text="Importar selecionados", command=importar,
                   style="Accent.TButton").pack(pady=8)

    def _backup_pre_import(self):
        """Backup silencioso antes de importar (nunca bloqueia o import)."""
        core.backup_pre_import(self.db_path)

    def _ler_do_disco(self):
        prog = tk.Toplevel(self.root)
        _titulo_escuro(prog)
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
                messagebox.showerror("Ler do disco", f"falha na leitura: {e}")

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
            messagebox.showerror("Saves 3DS", f"falha: {e}")
            return
        if res.get("ok"):
            messagebox.showinfo("Saves 3DS",
                                f"{res['arquivos']} arquivo(s)\n{res['arquivo']}")
        else:
            messagebox.showwarning("Saves 3DS", res.get("erro", "falha"))

    def abrir_configuracoes(self):
        """Técnico fora da tela inicial: backup, sessão, emuladores, JSON."""
        dlg = tk.Toplevel(self.root)
        _titulo_escuro(dlg)
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
        for i, (rot, _s, _f) in enumerate(NAV):
            if rot.startswith("🎵"):
                self._ir_nav(i)
                return

    def baixar_capas_ui(self):
        """Arte dos álbuns faltantes em thread (rede falhou = pendente)."""
        prog = tk.Toplevel(self.root)
        _titulo_escuro(prog)
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
                messagebox.showinfo("Capas", detalhe)
            self._depois(fim)
        threading.Thread(target=trabalho, daemon=True).start()

    def _depois(self, fn):
        self._despacho.enviar(fn)

    def _erro_callback(self, erro):
        if isinstance(erro, tk.TclError):
            return  # diálogo destruído antes de uma entrega pendente
        detalhe = "".join(traceback.format_exception(type(erro), erro, erro.__traceback__))
        core.log_erro("interface", detalhe)
        self._aviso_barra(f"Erro interno: {type(erro).__name__} (veja dados/erros.log)")

    # -- músicas (selfhost de áudio; play no player do SO por ação explícita)
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
        _titulo_escuro(prog)
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
                messagebox.showinfo("Músicas", detalhe)
            self._depois(fim)
        threading.Thread(target=trabalho, daemon=True).start()

    # -- controles (configura no Hub, aplica no Azahar fechado)
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
        _titulo_escuro(win)
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
        _com_rolagem(lst)

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
                messagebox.showwarning("Controles", f"falha: {e}")
                return
            if not r.get("ok"):
                messagebox.showwarning("Controles", r.get("erro", "falha"))
                return
            redesenhar()

        def aplicar():
            nome = selecionado()
            if not nome:
                return
            try:
                r = core.aplicar_preset_controle(nome)
            except Exception as e:
                messagebox.showwarning("Controles", f"falha: {e}")
                return
            if not r.get("ok"):
                messagebox.showwarning("Controles", r.get("erro", "falha"))
                return
            messagebox.showinfo(
                "Controles",
                f"{r.get('chaves', 0)} binds no Azahar ✓")

        def gerar():
            tipos = sorted(core.NOMES_TIPO)
            win2 = tk.Toplevel(win)
            _titulo_escuro(win2)
            win2.title("Gerar mapa padrão")
            win2.transient(win)
            win2.grab_set()
            lb = tk.Listbox(win2, selectmode="single", width=40, height=6,
                            bg="#0b0d12", fg=TXT, selectbackground=ACC,
                            font=("Segoe UI", 11))
            lb.pack(fill="both", expand=True, padx=12, pady=12)
            _com_rolagem(lb)
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
                    messagebox.showwarning("Controles", str(e))
                    return
                if not r.get("ok"):
                    messagebox.showwarning(
                        "Controles", r.get("erro", "falha"))
                    return
                win2.destroy()
                redesenhar()
                messagebox.showinfo(
                    "Controles",
                    f"Preset {r['preset']} ✓ — aplique p/ usar.")

            ttk.Button(win2, text="Gerar",
                       command=ok).pack(pady=(0, 12))

        def testar():
            vw = tk.Toplevel(win)
            _titulo_escuro(vw)
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
        _titulo_escuro(prog)
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
                    messagebox.showerror(nome, msg)

                return self._depois(mostra_erro)
            local = prov["versao_local"]()
            tag = info.get("tag") or "?"

            def decidir():
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                if local and local == tag:
                    messagebox.showinfo(nome, f"Já está na {tag} ✓")
                    return
                mb = round((info.get("size") or 0) / 1048576)
                if not messagebox.askyesno(
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
        _titulo_escuro(prog)
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
                    messagebox.showinfo(nome, f"{res.get('tag')} instalado ✓")
                else:
                    messagebox.showerror(nome, res.get("erro", "falha"))
                self.recarregar()

            self._depois(fim)

        threading.Thread(target=self._thread_segura(trabalho, prog, "Baixar emulador"), daemon=True).start()

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
        try:
            res = core.exportar_json(dest, db_path=self.db_path)
        except Exception as e:
            messagebox.showerror("Exportar", f"falha ao gravar: {e}")
            core.log_erro("exportar-json", str(e))
            return
        if not res.get("ok"):
            messagebox.showerror("Exportar", res.get("erro", "falha"))
            return
        messagebox.showinfo("Exportar", f"Exportados {res['jogos']} jogo(s).")

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
        lista = dados if isinstance(dados, list) else dados.get("jogos") if isinstance(dados, dict) else None
        if not isinstance(lista, list):
            messagebox.showerror("Importar", "JSON deve ser lista ou {jogos:[...]}.")
            return
        self._backup_pre_import()
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
            title="Pacote portátil (banco + capas + presets + saves)",
            defaultextension=".zip", filetypes=[("ZIP", "*.zip")],
            initialfile="biblioteca-pacote.zip")
        if not dest:
            return
        prog = tk.Toplevel(self.root)
        _titulo_escuro(prog)
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
                messagebox.showerror("Pacote", f"falha: {msg}")

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
                    messagebox.showerror("Pacote", res.get("erro", "falha"))
                    return
                kb = res["bytes"] // 1024
                messagebox.showinfo("Pacote",
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
        quer_saves = messagebox.askyesno("Pacote", "Restaurar os saves do pacote?")
        prog = tk.Toplevel(self.root)
        _titulo_escuro(prog)
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
                messagebox.showerror("Pacote", f"falha: {msg}")

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
                    messagebox.showerror("Pacote", res.get("erro", "falha"))
                    return
                self.sel = None
                self.recarregar()
                messagebox.showinfo("Pacote",
                                    core.resumo_importacao(res) + "\n" +
                                    f"capas {res['capas']} · presets {res['presets']} · "
                                    f"saves {res['saves']}")

            na_ui(pronto)

        threading.Thread(target=self._thread_segura(trabalho, prog, "Pacote"), daemon=True).start()


def resolver_jogo_cli(con, busca: str) -> dict:
    """Acha 1 jogo por id ou título (exato vence parcial). Sem Tk.

    Levanta LookupError se zero ou ambíguo. Para `tucoteca --jogar`.
    """
    chave = (busca or "").strip()
    if not chave:
        raise LookupError("informe o id ou parte do título.")
    if chave.isdigit():
        row = con.execute("SELECT * FROM jogos WHERE id=?",
                          (int(chave),)).fetchone()
        if row is None:
            raise LookupError(f"jogo id {chave} não encontrado.")
        return core.row_to_dict(row)
    nsa = chave.lower()
    todos = [core.row_to_dict(r)
             for r in con.execute("SELECT * FROM jogos").fetchall()]
    exatos = [j for j in todos if (j.get("titulo") or "").lower() == nsa]
    if len(exatos) == 1:
        return exatos[0]
    parciais = [j for j in todos if nsa in (j.get("titulo") or "").lower()]
    if len(parciais) == 1:
        return parciais[0]
    if not parciais:
        raise LookupError(f"nenhum jogo bate com '{chave}'.")
    nomes = ", ".join(f"{j['id']}:{j['titulo']}" for j in parciais[:8])
    raise LookupError(f"'{chave}' é ambíguo: {nomes}.")


def main_jogar(args) -> int:
    """`--jogar BUSCA`: abre o jogo sem a janela (p/ atalhos do Desktop)."""
    import threading
    con = core.get_db(Path(args.db))
    try:
        try:
            j = resolver_jogo_cli(con, args.jogar)
        except (LookupError, ValueError) as e:
            print(f"[erro] {e}")
            return 2
        prep = core.preparar_lancamento(j)
        if prep.get("aviso"):
            print(f"[aviso] {prep['aviso']}")
        pronto: dict = {}
        feito = threading.Event()

        def ao_fim(sessao, rastreado, _gid=j["id"]):
            pronto["sessao"] = sessao
            pronto["rastreado"] = rastreado
            feito.set()

        res = core.executar_monitorado(j, ao_fim=ao_fim)
        if not res.get("ok"):
            print(f"[erro] {res.get('erro', 'falha')}")
            return 1
        if res.get("rastreado"):
            core.marcar_execucao(con, j["id"])
            feito.wait()
            ok, msg = App._registrar_sessao(
                con, j["id"], float(pronto.get("sessao") or 0.0))
            print(f"[ok] Executando ({res.get('modo')}) — {msg}")
            return 0
        try:
            core.iniciar_sessao_manual(j["id"], j.get("titulo") or "")
        except Exception:
            pass
        print("[ok] Executando — ao terminar use o Hub (⏱ Registrar sessão).")
        return 0
    finally:
        try:
            con.close()
        except Exception:
            pass
        try:
            core.liberar_lock()
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="TucoTeca — app Windows (tkinter)")
    ap.add_argument("--db", default=str(core.DEFAULT_DB))
    ap.add_argument("--selftest", action="store_true",
                    help="monta a UI oculta, recarrega e sai")
    ap.add_argument("--ignorar-lock", action="store_true",
                    help="abre mesmo com lock de outra instância (após crash)")
    ap.add_argument("--jogar", default=None, metavar="BUSCA",
                    help="abre o jogo (id ou título) sem a janela")
    args = ap.parse_args(argv)
    core.garantir_dirs()
    lk = core.adquirir_lock(ignorar=args.ignorar_lock)
    if not lk.get("ok"):
        try:
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror("Biblioteca", lk.get("erro", "já aberta"))
            r.destroy()
        except Exception:
            print(f"[erro] {lk.get('erro')}")
        return 2
    import atexit
    atexit.register(core.liberar_lock)
    core.get_db(Path(args.db)).close()
    if args.jogar:
        # mantém o lock adquirido acima durante o jogo (main_jogar libera)
        return main_jogar(args)
    root = tk.Tk()
    _titulo_escuro(root)
    app = App(root, Path(args.db))
    if args.selftest:
        root.withdraw()
        root.update()
        n = len(app.jogos)
        ncards = len(app.cards)
        root.destroy()
        core.liberar_lock()
        print(f"[ok] selftest: UI montada, {n} jogo(s), {ncards} card(s)")
        return 0
    try:
        root.after(1500, app.sincronizar_nomes_boot)
        root.mainloop()
    finally:
        core.liberar_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
