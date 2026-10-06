#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TucoTeca — aplicativo local Windows (tkinter, stdlib).
Visual estilo Hydra: sidebar, grade de cards com capas e painel de detalhes.
Mesmo banco e mesmas regras do terminal Linux; nada de navegador.

Uso:
    python codigo/frontends/app_win.py [--db caminho\\biblioteca.db]
    python codigo/frontends/app_win.py --selftest   # monta a UI oculta e sai (verificação)
Ou duplo-clique em BibliotecaHub.bat na raiz do projeto.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bib_core as core

BG = "#0f1116"
PANEL = "#16181f"
CARD = "#1c1f27"
CARD_HOVER = "#242834"
LINE = "#2a2e39"
TXT = "#e8eaf0"
MUT = "#9aa0b2"
ACC = "#7c5cff"
OK_C = "#2ecc71"
WARN_C = "#f39c12"
BAD_C = "#e74c3c"

CARD_W, CARD_H = 140, 196
STATUS_CORES = {"backlog": MUT, "jogando": "#7aa2ff", "zerado": OK_C,
                "pausado": WARN_C, "abandonado": BAD_C}

# (rótulo, filtro_status, só_favoritos)
NAV = [("📚 Biblioteca", "", False),
       ("▶ Jogando", "jogando", False),
       ("✓ Zerados", "zerado", False),
       ("★ Favoritos", "", True),
       ("🎵 Músicas", "", False)]

_MINI_CACHE: dict = {}


def carregar_miniatura(caminho: Path, largura: int = CARD_W,
                       altura: int = CARD_H) -> tk.PhotoImage | None:
    """PhotoImage reduzido da capa, ou None (vira tile).

    Tenta Pillow (jpg/webp/png/gif) quando instalado; senão, PhotoImage
    nativo (só png/gif). Cacheado por (caminho, mtime, tamanho) p/ não
    recarregar a cada recarregar().
    """
    try:
        st = Path(caminho).stat()
        chave = (str(caminho), st.st_mtime_ns, st.st_size, largura, altura)
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
        img = ImageTk.PhotoImage(pil)
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
        base = tk.PhotoImage(file=str(caminho))
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
        hwnd = ctypes.c_void_p(janela.winfo_id())
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


def _com_rolagem(lst: tk.Listbox) -> tk.Listbox:
    """Acopla Scrollbar vertical num Listbox já empacotado. Nunca levanta."""
    try:
        bar = ttk.Scrollbar(lst.master, orient="vertical", command=lst.yview)
        bar.pack(side="right", fill="y")
        lst.configure(yscrollcommand=bar.set)
    except (tk.TclError, AttributeError):
        pass
    return lst


def desenhar_tile(cv: tk.Canvas, titulo: str, w: int, h: int,
                   selecionado: bool = False, grande: bool = False,
                   subtitulo: str = ""):
    """Tile estilo Hydra quando não há capa: inicial do título em destaque."""
    cv.delete("all")
    borda = ACC if selecionado else LINE
    cv.create_rectangle(2, 2, w - 2, h - 2, fill=CARD,
                        outline=borda, width=3 if selecionado else 1)
    cv.create_rectangle(2, 2, w - 2, 7, fill=borda, outline="")
    inicial = (titulo.strip()[:1] or "?").upper()
    cv.create_text(w // 2, h // 2 - (16 if grande else 10), text=inicial,
                   fill=ACC if selecionado else TXT,
                   font=("Segoe UI", 68 if grande else 48, "bold"))
    base_y = h - (30 if grande else 22)
    if subtitulo:
        cv.create_text(w // 2, base_y - (16 if grande else 13), text=subtitulo,
                       fill=ACC, font=("Segoe UI", 10 if grande else 9, "bold"))
    cv.create_text(w // 2, base_y, text="sem capa",
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
        self.filtro_plat: str | None = None  # PC/3DS/NDS (derivado da origem)
        self.plat_btns: dict[str, ttk.Button] = {}
        self._deb = None
        self.cards: list[dict] = []  # {frame, jogo}
        self._imgs_cards: list = []  # retém miniaturas da grade
        self._img_det = None  # retém a capa do painel de detalhes
        self.musicas: list[dict] = []
        self.mus_sel: int | None = None
        self.mus_ids: list[int] = []
        self._mus_lista = None  # Listbox da aba Músicas (recriado a cada recarga)
        self.mus_modo = "hub"  # "hub" catalogadas | "fila" downloads CSV
        self.fila: list[dict] = []
        self.fila_sel: int | None = None
        self.player = core.Player()  # interno (MCI no Win); externo é fallback
        self._btn_play = None  # ▶/⏸ da aba (texto acompanha o estado)
        root.title("🎮 TucoTeca")
        root.geometry("1200x720")
        root.minsize(960, 600)
        root.configure(bg=BG)
        self._estilo()
        self._montar()
        self.recarregar()
        try:
            self.root.after(1000, self._vigiar_musica)
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
                      borderwidth=1, padding=10, font=("Segoe UI", 11))
        st.map("TButton", background=[("active", ACC)])
        st.configure("Accent.TButton", background=ACC, foreground="white",
                      borderwidth=0, padding=10, font=("Segoe UI", 13, "bold"))
        st.configure("TEntry", fieldbackground="#0b0d12", foreground=TXT,
                      borderwidth=1)
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

    def _montar(self):
        # sidebar
        side = ttk.Frame(self.root, style="Panel.TFrame", width=200)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        ttk.Label(side, text="🎮 TUCOTECA", style="Panel.TLabel",
                  font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=12, pady=(14, 8))
        self.nav_btns: list[ttk.Button] = []
        for i, (rotulo, _st, _fv) in enumerate(NAV):
            b = ttk.Button(side, text=rotulo, style="Side.TButton",
                           command=lambda i=i: self._ir_nav(i))
            b.pack(fill="x", padx=8, pady=1)
            self.nav_btns.append(b)
        ttk.Label(side, text="", style="Panel.TLabel").pack(pady=4)
        ttk.Label(side, text="PROVEDORES", style="Panel.TLabel",
                  font=("Segoe UI", 10, "bold"), foreground=MUT).pack(anchor="w", padx=12)
        for chave in core.provedores():
            b = ttk.Button(side, text=chave, style="Side.TButton",
                           command=lambda c=chave: self._ir_prov(c))
            b.pack(fill="x", padx=8, pady=1)
            self.prov_btns[chave] = b
        ttk.Label(side, text="", style="Panel.TLabel").pack(pady=4)
        ttk.Label(side, text="IMPORTAR", style="Panel.TLabel",
                  font=("Segoe UI", 10, "bold"), foreground=MUT).pack(anchor="w", padx=12)
        for rotulo, cmd in (("📥 Importar…", self.importar_unificado),):
            ttk.Button(side, text=rotulo, style="Side.TButton",
                       command=cmd).pack(fill="x", padx=8, pady=1)
        ttk.Label(side, text="", style="Panel.TLabel").pack(pady=4)
        ttk.Button(side, text="⚙ Configurações", style="Side.TButton",
                   command=self.abrir_configuracoes).pack(fill="x", padx=8, pady=1)
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
        self.btn_usuario = ttk.Button(topo, text="👤 —", style="Chip.TButton",
                                      command=self.dlg_usuario)
        self.btn_usuario.pack(side="right")
        # linha de filtros: plataforma (PC/3DS/NDS) + etiqueta livre
        ffilt = ttk.Frame(centro)
        ffilt.pack(fill="x", padx=12, pady=(0, 2))
        for plat in ("PC", "3DS", "NDS"):
            b = ttk.Button(ffilt, text=plat, width=5, style="Chip.TButton",
                           command=lambda p=plat: self._ir_plat(p))
            b.pack(side="left", padx=(0, 4))
            self.plat_btns[plat] = b
        ttk.Label(ffilt, text="🏷", style="Mut.TLabel").pack(side="left", padx=(8, 2))
        self.var_tagfiltro = tk.StringVar(value="")
        self.cmb_tagfiltro = ttk.Combobox(ffilt, textvariable=self.var_tagfiltro,
                                          values=[], width=22, font=("Segoe UI", 10))
        self.cmb_tagfiltro.pack(side="left")
        self.cmb_tagfiltro.bind("<<ComboboxSelected>>", lambda _e: self.recarregar())
        self.cmb_tagfiltro.bind("<Return>", lambda _e: self.recarregar())
        ttk.Button(ffilt, text="✕", width=3,
                   command=self._limpar_filtros).pack(side="left", padx=(4, 0))
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
        self.det_capa = tk.Canvas(det, width=216, height=280, bg=PANEL,
                                  highlightthickness=2, highlightbackground=LINE)
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
        self.btn_jogar = ttk.Button(det, text="▶  JOGAR",
                                      style="Accent.TButton",
                                      command=self.jogar)
        self.btn_jogar.pack(fill="x", padx=16, pady=2)
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
        for plat, b in self.plat_btns.items():
            try:
                b.configure(style="ChipAct.TButton" if plat == self.filtro_plat else "Chip.TButton")
            except tk.TclError:
                pass

    def _ir_nav(self, i: int):
        self.nav_idx = i
        self._pintar_nav()
        self.recarregar()

    def _ir_prov(self, chave: str):
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
        try:
            self.var_tagfiltro.set("")
        except (tk.TclError, AttributeError):
            pass
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
        passo = CARD_W + 28
        if self.cards:
            try:
                self.grade.update_idletasks()
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
        # trava de segurança: a grade nunca estoura a viewport (cards têm
        # larguras distintas; a estimativa pode errar para mais)
        try:
            for _ in range(10):
                self.grade.update_idletasks()
                if self.grade.winfo_reqwidth() <= vp or cols <= 1:
                    break
                cols -= 1
                for i, c in enumerate(self.cards):
                    c["frame"].grid(row=i // cols, column=i % cols,
                                    padx=14, pady=12)
        except tk.TclError:
            pass

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

    def recarregar(self):
        if self._em_musicas():
            return self._recarregar_musicas()
        _rot, status, fav = NAV[self.nav_idx]
        try:
            tag_txt = self.var_tagfiltro.get().strip()
        except (tk.TclError, AttributeError):
            tag_txt = ""
        tags = [t.strip() for t in tag_txt.replace(";", ",").split(",") if t.strip()]
        con = self._con()
        try:
            self.jogos = core.listar_jogos(
                con, q=self.var_q.get().strip(), status=status, favorito=fav,
                etiquetas=tags or None,
                plataformas=[self.filtro_plat] if self.filtro_plat else None)
            if self.filtro_prov:
                self.jogos = core.jogos_do_provedor(self.jogos, self.filtro_prov)
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
        if self.sel is None or self.sel >= len(self.jogos):
            self.sel = 0 if self.jogos else None
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
        self.lbl_cont.configure(text=f"{n} jogo(s) · {az_txt}{extra}")
        try:
            self._atualizar_chip_usuario()
        except Exception:
            pass
        if n == 0:
            if (self.filtro_plat or self.filtro_prov or tag_txt
                    or self.var_q.get().strip()):
                self.lbl_vazio.configure(text="Nada aqui — ajuste busca/filtros ou ✕ limpa tudo")
            else:
                self.lbl_vazio.configure(text="Nada aqui — use 📥 Importar…")
            self.lbl_vazio.pack(anchor="w", padx=14)
        else:
            self.lbl_vazio.pack_forget()

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
        fr_btn = ttk.Frame(self.grade)
        fr_btn.pack(side="bottom", fill="x", pady=(8, 0))
        ttk.Button(fr_btn, text="▶ Tocar",
                   command=self.tocar_musica_selecionada).pack(side="left")
        ttk.Button(fr_btn, text="📥 Importar…",
                   command=self.importar_musicas).pack(side="left", padx=6)
        ttk.Button(fr_btn, text="🗑 Excluir",
                   command=self.excluir_musica_selecionada).pack(side="left")
        ttk.Button(fr_btn, text="⬇ CSV…",
                   command=self.baixar_csv).pack(side="left", padx=6)
        try:
            con2 = self._con()
            try:
                n_pend = len(core.listar_downloads(con2, estado="pendente"))
            finally:
                con2.close()
        except Exception:
            n_pend = 0
        ttk.Button(fr_btn, text=f"Fila ({n_pend})",
                   command=self._ir_fila).pack(side="left")
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
        lst = tk.Listbox(self.grade, selectmode="single", width=64, height=18,
                         bg="#0b0d12", fg=TXT, selectbackground=ACC,
                         font=("Segoe UI", 11))
        lst.pack(fill="both", expand=True)
        _com_rolagem(lst)
        for m in self.musicas:
            try:
                lst.insert("end", core.texto_musica(m))
            except Exception:
                continue
        if self.mus_sel is not None:
            try:
                lst.selection_set(self.mus_sel)
                lst.see(self.mus_sel)
            except tk.TclError:
                pass
        lst.bind("<<ListboxSelect>>", self._ao_sel_musica)
        lst.bind("<Double-Button-1>",
                 lambda _e: self.tocar_musica_selecionada())
        self._mus_lista = lst
        n = len(self.musicas)
        try:
            self.lbl_cont.configure(
                text=f"{n} música(s) · player externo (segue com o jogo aberto)")
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

    def _ao_sel_musica(self, _e=None):
        try:
            sel = self._mus_lista.curselection()
        except (tk.TclError, AttributeError):
            return
        if sel:
            self.mus_sel = sel[0]
            self.mostrar_detalhe()

    def tocar_musica_selecionada(self):
        """Toca no player interno (segue com o jogo; externo em Externo…)."""
        if self.mus_modo == "fila":
            messagebox.showinfo("Fila", "Aqui é a fila de downloads (Fase B).")
            return
        if self.mus_sel is None or self.mus_sel >= len(self.musicas):
            messagebox.showinfo("Músicas", "Selecione uma música na lista.")
            return
        faixas = [{"path": m.get("musica_path") or "",
                   "titulo": core.texto_musica(m)} for m in self.musicas]
        self.player.carregar(faixas, inicio=self.mus_sel)
        r = self.player.tocar()
        if r.get("ok"):
            self._aviso_barra(f"Tocando: {core.texto_musica(self.musicas[self.mus_sel])}")
            self._atualizar_transporte()
        else:
            messagebox.showwarning(
                "Músicas",
                f"{r.get('erro', 'falha')}\nTente Externo… como alternativa.")

    def abrir_externo_musica(self):
        """Fallback: abre no player do SO (como era antes do interno)."""
        if self.mus_modo == "fila" or self.mus_sel is None \
                or self.mus_sel >= len(self.musicas):
            return
        m = self.musicas[self.mus_sel]
        r = core.tocar_musica(m.get("musica_path") or "")
        if r.get("ok"):
            self._aviso_barra(f"Tocando (externo): {core.texto_musica(m)}")
        else:
            messagebox.showwarning("Músicas", r.get("erro", "falha"))

    def mus_alternar(self):
        r = self.player.alternar()
        if not r.get("ok") and self.player.estado == "parado":
            self.tocar_musica_selecionada()
            return
        if not r.get("ok"):
            messagebox.showwarning("Músicas", r.get("erro", "falha"))
        self._atualizar_transporte()

    def mus_parar(self):
        self.player.parar()
        self._atualizar_transporte()

    def mus_proxima(self):
        r = self.player.proxima()
        if not r.get("ok"):
            self._atualizar_transporte()
            return
        self.mus_sel = self.player.idx
        try:
            self._mus_lista.selection_clear(0, "end")
            self._mus_lista.selection_set(self.mus_sel)
            self._mus_lista.see(self.mus_sel)
        except (tk.TclError, AttributeError):
            pass
        self.mostrar_detalhe()
        self._atualizar_transporte()

    def mus_anterior(self):
        r = self.player.anterior()
        if not r.get("ok"):
            return
        self.mus_sel = self.player.idx
        try:
            self._mus_lista.selection_clear(0, "end")
            self._mus_lista.selection_set(self.mus_sel)
            self._mus_lista.see(self.mus_sel)
        except (tk.TclError, AttributeError):
            pass
        self.mostrar_detalhe()
        self._atualizar_transporte()

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
                lbl.configure(text=f"♪ {at['titulo']}"
                                  f" ({at['estado']})" if at
                              and self.player.estado != "parado"
                              else "♪ parado")
        except tk.TclError:
            pass

    def _vigiar_musica(self):
        """Poll 1s: faixa acabou → próxima (auto-avançar); reagenda sempre."""
        try:
            if self.player.terminou():
                self.mus_proxima()
            else:
                self._atualizar_transporte()
        except Exception:
            pass
        try:
            self.root.after(1000, self._vigiar_musica)
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
            self.player.parar()
        self.recarregar()

    def _ir_fila(self):
        self.mus_modo = "fila"
        self.recarregar()

    def _ir_musicas(self):
        self.mus_modo = "hub"
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
        fr_btn = ttk.Frame(self.grade)
        fr_btn.pack(side="bottom", fill="x", pady=(8, 0))
        ttk.Button(fr_btn, text="⟵ Músicas",
                   command=self._ir_musicas).pack(side="left")
        ttk.Button(fr_btn, text="⬇ CSV…",
                   command=self.baixar_csv).pack(side="left", padx=6)
        ttk.Button(fr_btn, text="⬇ Baixar fila",
                   command=self.baixar_fila).pack(side="left")
        ttk.Button(fr_btn, text="Importar baixadas",
                   command=self.importar_baixadas).pack(side="left", padx=6)
        ttk.Button(fr_btn, text="Limpar prontas/falhas",
                   command=self.limpar_fila).pack(side="left")
        lst = tk.Listbox(self.grade, selectmode="single", width=64, height=18,
                         bg="#0b0d12", fg=TXT, selectbackground=ACC,
                         font=("Segoe UI", 11))
        lst.pack(fill="both", expand=True)
        _com_rolagem(lst)
        for d in self.fila:
            try:
                rot = core.texto_musica(d)
                est = d.get("estado") or ""
                extra = (f" — {d.get('erro')}"
                         if est == "falha" and d.get("erro") else "")
                lst.insert("end", f"{rot} [{est}]{extra}")
            except Exception:
                continue
        if self.fila_sel is not None:
            try:
                lst.selection_set(self.fila_sel)
                lst.see(self.fila_sel)
            except tk.TclError:
                pass
        lst.bind("<<ListboxSelect>>", self._ao_sel_fila)
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
        try:
            sel = self._mus_lista.curselection()
        except (tk.TclError, AttributeError):
            return
        if sel:
            self.fila_sel = sel[0]
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

    def baixar_fila(self):
        """Start Downloads do Harmoni: baixa pendentes em thread (Fase B)."""
        th = getattr(self, "_th_fila", None)
        if th is not None and th.is_alive():
            messagebox.showinfo("Baixar fila", "Download já em andamento.")
            return
        if not core.localizar_ytdlp():
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
                c2 = self._con()
                try:
                    core.baixar_faixa(c2, did, progresso=self._prog_fila)
                except Exception as e:
                    try:
                        core.marcar_download(c2, did, "falha",
                                             erro=str(e)[:200])
                    except Exception:
                        pass
                finally:
                    c2.close()
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
            c2 = self._con()
            try:
                res = core.importar_fila_pronta(c2)
            except Exception as e:
                res = {"novas": 0, "ignorados": 0, "erros": [str(e)],
                       "avisos": []}
            finally:
                c2.close()
            detalhe = f"{res['novas']} nova(s), {res['ignorados']} ignorada(s)"
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
        fr = ttk.Frame(self.grade, style="Card.TFrame", cursor="hand2")
        img = None
        if j.get("capa"):
            alvo = core.caminho_capa(j["capa"])
            if alvo is not None:
                img = carregar_miniatura(alvo)
        if img is not None:
            self._imgs_cards.append(img)
            lb = tk.Label(fr, image=img, bg=CARD, cursor="hand2",
                          highlightthickness=2, highlightbackground=CARD,
                          borderwidth=0)
            lb.pack(padx=6, pady=(6, 2))
            fr._imgw = lb  # type: ignore[attr-defined]
        else:
            cv = tk.Canvas(fr, width=CARD_W, height=CARD_H, bg=CARD,
                           highlightthickness=2, highlightbackground=CARD,
                           cursor="hand2")
            cv.pack(padx=6, pady=(6, 2))
            try:
                plat_cv = j.get("plataforma") or core.plataforma_jogo(j)
            except Exception:
                plat_cv = ""
            desenhar_tile(cv, j["titulo"], CARD_W, CARD_H, subtitulo=plat_cv)
            fr._tile = cv  # type: ignore[attr-defined]
            fr._imgw = cv  # type: ignore[attr-defined]
        # etiqueta de plataforma no canto (roxo, como no print) + tags livres
        try:
            plat = j.get("plataforma") or core.plataforma_jogo(j)
        except Exception:
            plat = "PC"
        tags = list(j.get("etiquetas_lista") or [])
        badge_plat = tk.Label(fr, text=plat, bg=ACC, fg="white",
                              font=("Segoe UI", 9, "bold"), padx=6, pady=2,
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
                     bg=CARD, fg=TXT, wraplength=CARD_W + 8,
                     font=("Segoe UI", 11, "bold"), cursor="hand2")
        t.pack()
        cor = STATUS_CORES.get(j["status"], MUT)
        try:
            horas_n = round(float(j["horas"] or 0), 2)
        except (TypeError, ValueError):
            horas_n = 0
        horas = f" · {horas_n:g}h" if horas_n else ""
        m = tk.Label(fr, text=f"{j['status']}{horas}{core.selo_confianca(j)}", bg=CARD, fg=cor,
                     font=("Segoe UI", 9), wraplength=CARD_W + 8, justify="center", cursor="hand2")
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
        for i, c in enumerate(self.cards):
            fr = c["frame"]
            sel = (i == self.sel)
            fr.configure(style="Card.TFrame")
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
                    desenhar_tile(w, c["jogo"]["titulo"], CARD_W, CARD_H,
                                  selecionado=sel,
                                  subtitulo=(c["jogo"].get("plataforma") or ""))

    # -- detalhe / seleção
    def selecionado(self) -> dict | None:
        if self.sel is None or self.sel >= len(self.jogos):
            messagebox.showinfo("Biblioteca", "Selecione um jogo na grade.")
            return None
        return self.jogos[self.sel]

    def mostrar_detalhe(self):
        if self._em_musicas() and self.mus_modo == "fila":
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
                    except Exception:
                        pass
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
            res = core.encerrar_sessao_manual(alvo["_arquivo"], float(horas))
        except Exception as e:
            messagebox.showerror("Sessão", f"falha: {e}")
            return
        if res.get("ok"):
            self.recarregar()
            messagebox.showinfo("Sessão", f"+{horas}h registradas ✓" if horas else "Sessão encerrada (sem horas).")
        else:
            messagebox.showerror("Sessão", res.get("erro", "falha"))

    def _verificar_sessoes_pendentes(self):
        """Compat: avisos agora vão na barra de status (ver recarregar)."""
        return 0

    def _verificar_backup_antigo(self, dias: int = 7):
        """Compat: avisos agora vão na barra de status (ver recarregar)."""
        return None

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
        if self._em_musicas():
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
            anterior = getattr(_troca_prov, "anterior", _prov_do_jogo(j))
            preset_vals["azahar_preset"] = var_preset.get()
            chave = _chave_sel()
            var_preset.set(preset_vals["azahar_preset"])
            _troca_prov.anterior = chave
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
                f"Nome do preset (fotografa a config atual):",
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
                except Exception:
                    pass
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
                except Exception:
                    pass

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
                except Exception:
                    pass

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

    def _importar_pasta(self, pasta: str):
        prog = tk.Toplevel(self.root)
        _titulo_escuro(prog)
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
        prog.update()

        def trabalho():
            def na_ui(fn):
                try:
                    self.root.after(0, fn)
                except tk.TclError:
                    pass  # janela fechada no meio

            def falhou(msg):
                try:
                    prog.destroy()
                except tk.TclError:
                    return
                messagebox.showerror("Importar repack", msg)
                core.log_erro("importar-repack", msg)

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
            con = self._con()
            try:
                res = core.baixar_capas_faltantes(con)
            except Exception as e:
                res = {"novas": 0, "pendentes": 0, "erros": [str(e)]}
            finally:
                con.close()

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
        try:
            self.root.after(0, fn)
        except tk.TclError:
            pass  # janela fechada

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
            con = self._con()
            try:
                res = core.importar_musicas(con, pasta_fx)
            except Exception as e:
                res = {"novos": 0, "ignorados": 0, "erros": [str(e)]}
            finally:
                con.close()

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
        lista = dados if isinstance(dados, list) else dados.get("jogos", [])
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
        prog.update()

        def trabalho():
            def na_ui(fn):
                try:
                    self.root.after(0, fn)
                except tk.TclError:
                    pass

            def _falhou(msg):
                try:
                    prog.destroy()
                except tk.TclError:
                    return
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
        prog.update()

        def trabalho():
            def na_ui(fn):
                try:
                    self.root.after(0, fn)
                except tk.TclError:
                    pass

            def _falhou(msg):
                try:
                    prog.destroy()
                except tk.TclError:
                    return
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
    import time
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
