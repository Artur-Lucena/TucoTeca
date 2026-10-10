"""Tema local, barras adaptáveis e painéis roláveis (Tk/ttk, sem downloads)."""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import font, ttk

BG = "#0e1622"
PANEL = "#131f2e"
CARD = "#1c2c40"
HOVER = "#28425b"
LINE = "#344b63"
TXT = "#f0f3fa"
MUT = "#a5b1c7"
ACC = "#59c7f3"


def _superficie(root, cor, borda=None, tamanho=24):
    """Elemento nine-slice: cantos transparentes, borda suave de 1 pixel."""
    img = tk.PhotoImage(master=root, width=tamanho, height=tamanho)
    raio = 6
    for y in range(tamanho):
        for x in range(tamanho):
            dx = max(raio - x - 0.5, x + 0.5 - (tamanho - raio), 0)
            dy = max(raio - y - 0.5, y + 0.5 - (tamanho - raio), 0)
            if dx * dx + dy * dy > raio * raio:
                continue
            limite = min(x, y, tamanho - 1 - x, tamanho - 1 - y) < 1
            curva = dx * dx + dy * dy > (raio - 1) ** 2
            img.put(borda if borda and (limite or curva) else cor, (x, y))
    return img


def aplicar_tema(root):
    """Completa os estilos do Hub e de seus diálogos no mesmo interpretador."""
    st = ttk.Style(root)
    familias = set(font.families(root))
    familia = next((f for f in ("Segoe UI", "Inter", "DejaVu Sans", "Helvetica")
                    if f in familias), "TkDefaultFont")
    for nome in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        font.nametofont(nome, root=root).configure(family=familia, size=10)
    root.option_add("*Listbox.font", (familia, 10))
    root.option_add("*Text.font", (familia, 10))
    root.option_add("*Menu.font", (familia, 10))
    root.option_add("*Toplevel.background", BG)
    root.option_add("*Listbox.background", BG)
    root.option_add("*Listbox.foreground", TXT)
    root.option_add("*Listbox.selectBackground", "#25465f")
    root.option_add("*Listbox.selectForeground", TXT)
    root.option_add("*Listbox.exportSelection", False)
    root.option_add("*Listbox.borderWidth", 0)
    root.option_add("*Listbox.highlightThickness", 1)
    root.option_add("*Listbox.highlightBackground", LINE)
    root.option_add("*TCombobox*Listbox.background", CARD)
    root.option_add("*TCombobox*Listbox.foreground", TXT)
    root.option_add("*TCombobox*Listbox.selectBackground", "#25465f")
    root.configure(background=BG)
    st.configure(".", font=(familia, 10), foreground=TXT, background=BG)
    st.configure("TFrame", background=BG)
    st.configure("Panel.TFrame", background=PANEL)
    st.configure("Card.TFrame", background=CARD, padding=2)
    st.configure("Hover.Card.TFrame", background=HOVER, padding=2)
    st.configure("Selected.Card.TFrame", background=ACC, padding=2)
    for nome, bg, fg in (("TLabel", BG, TXT), ("Mut.TLabel", BG, MUT),
                         ("Panel.TLabel", PANEL, TXT), ("Sec.TLabel", CARD, MUT)):
        st.configure(nome, background=bg, foreground=fg, font=(familia, 10))
    st.configure("Title.TLabel", background=BG, foreground=TXT,
                 font=(familia, 20, "bold"))
    st.configure("Panel.Title.TLabel", background=PANEL, foreground=TXT,
                 font=(familia, 15, "bold"))
    st.configure("Subtitle.TLabel", background=BG, foreground=MUT,
                 font=(familia, 10))
    st.configure("Group.TButton", font=(familia, 9, "bold"))
    imagens = []

    def botao(nome, cor, hover, fg=TXT, fundo=BG, borda=LINE, padding=(12, 8)):
        normal = _superficie(root, cor, borda)
        ativo = _superficie(root, hover, borda)
        foco = _superficie(root, cor, ACC)
        disabled = _superficie(root, CARD)
        imagens.extend((normal, ativo, foco, disabled))
        elemento = "Tuco." + nome
        if elemento not in st.element_names():
            st.element_create(elemento, "image", normal,
                              ("disabled", disabled), ("pressed", ativo),
                              ("active", ativo), ("focus", foco),
                              border=7, sticky="nsew")
        st.layout(nome, [(elemento, {"sticky": "nsew", "children": [
            ("Button.padding", {"sticky": "nsew", "children": [
                ("Button.label", {"sticky": "nsew"})]})]})])
        st.configure(nome, background=fundo, foreground=fg, padding=padding,
                     font=(familia, 10), borderwidth=0, anchor="center", width=0)
        st.map(nome, foreground=[("disabled", "#68768e")])

    botao("TButton", CARD, HOVER)
    botao("Accent.TButton", "#167ca7", "#2298c6", "white", padding=(14, 12))
    botao("Side.TButton", PANEL, CARD, MUT, PANEL, None, (12, 8))
    botao("SideAct.TButton", "#25465f", "#305873", TXT, PANEL, None, (12, 8))
    botao("Group.TButton", PANEL, CARD, MUT, PANEL, None, (10, 6))
    botao("Chip.TButton", CARD, HOVER, MUT, padding=(8, 6))
    botao("ChipAct.TButton", "#25465f", "#305873", TXT, padding=(8, 6))
    botao("Volume.TButton", CARD, HOVER, padding=(3, 4))
    st.configure("Volume.TButton", font=(familia, 9))
    for nome in ("Side.TButton", "SideAct.TButton", "Group.TButton"):
        st.configure(nome, anchor="w")
    st.configure("TEntry", fieldbackground=BG, foreground=TXT, insertcolor=ACC,
                 bordercolor=LINE, lightcolor=LINE, darkcolor=LINE, padding=7)
    st.map("TEntry", bordercolor=[("focus", ACC)])
    st.configure("TCombobox", fieldbackground=CARD, background=CARD,
                 foreground=TXT, arrowcolor=MUT, bordercolor=LINE,
                 lightcolor=LINE, darkcolor=LINE, padding=6)
    st.map("TCombobox", fieldbackground=[("readonly", CARD), ("disabled", PANEL)],
           foreground=[("disabled", MUT), ("readonly", TXT)],
           selectbackground=[("readonly", CARD)], selectforeground=[("readonly", TXT)])
    for nom in ("TCheckbutton", "Star.TCheckbutton", "TRadiobutton"):
        st.configure(nom, background=BG, foreground=MUT,
                     indicatorbackground=CARD, indicatorforeground=ACC)
        st.map(nom, background=[("active", BG)],
               foreground=[("disabled", "#68768e"), ("active", TXT)])
    st.configure("Sec.TLabelframe", background=CARD, padding=14)
    st.configure("Sec.TLabelframe.Label", background=CARD, foreground=ACC,
                 font=(familia, 12, "bold"))
    for nom in ("Treeview", "Lista.Treeview"):
        st.configure(nom, background=BG, fieldbackground=BG, foreground=TXT,
                     borderwidth=0, rowheight=int(root.winfo_fpixels("24p")),
                     font=(familia, 10))
        st.map(nom, background=[("selected", "#25465f")],
               foreground=[("selected", TXT)])
    st.layout("Lista.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    st.configure("Lista.Treeview.Heading", background=CARD, foreground=MUT,
                 font=(familia, 9, "bold"), padding=8, relief="flat")
    for nom in ("Vertical.TScrollbar", "Lista.Vertical.TScrollbar"):
        st.configure(nom, background=LINE, troughcolor=BG, borderwidth=0,
                     arrowsize=10, width=9, relief="flat")
        st.layout(nom, [("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
            ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        st.map(nom, background=[("active", MUT)])
    st.configure("Down.Horizontal.TProgressbar", background=ACC,
                 troughcolor=CARD, lightcolor=CARD, darkcolor=CARD,
                 bordercolor=CARD, borderwidth=0, thickness=8)
    st.configure("Volume.Horizontal.TScale", background=PANEL, troughcolor=CARD,
                 lightcolor=LINE, darkcolor=LINE, bordercolor=LINE)
    root._tuco_imagens = imagens
    icone = tk.PhotoImage(master=root, width=48, height=48)
    for y in range(48):
        for x in range(48):
            if 5 <= x < 43 and 5 <= y < 43:
                icone.put("#167ca7", (x, y))
            if 10 <= x < 38 and 18 <= y < 32:
                icone.put(TXT, (x, y))
            if (14 <= x < 17 and 21 <= y < 29) or (12 <= x < 20 and 24 <= y < 27):
                icone.put("#167ca7", (x, y))
            if (x - 29) ** 2 + (y - 23) ** 2 < 4 or (x - 34) ** 2 + (y - 27) ** 2 < 4:
                icone.put("#167ca7", (x, y))
    root.iconphoto(True, icone)
    root._tuco_icone = icone


class BarraAcoes(ttk.Frame):
    """Ações que quebram linha pela largura medida, sem esconder controles."""
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self._botoes = []
        self._timer = None
        self.bind("<Configure>", self._agendar)
        self.bind("<Destroy>", self._fechar)

    def adicionar(self, texto, comando, **kw):
        b = ttk.Button(self, text=texto, command=comando, **kw)
        self._botoes.append(b)
        self._agendar()
        return b

    def _agendar(self, _e=None):
        if self._timer is None:
            self._timer = self.after_idle(self._organizar)

    def _organizar(self):
        self._timer = None
        largura = max(1, self.winfo_width())
        x = y = altura = 0
        for b in self._botoes:
            w, h = b.winfo_reqwidth(), b.winfo_reqheight()
            if x and x + w > largura:
                y += altura + 6
                x = altura = 0
            b.place(x=x, y=y, width=min(w, largura), height=h)
            x += w + 6
            altura = max(altura, h)
        self.configure(height=max(1, y + altura))

    def _fechar(self, e):
        if e.widget is self and self._timer is not None:
            self.after_cancel(self._timer)
            self._timer = None


class PainelRolavel(ttk.Frame):
    """Conteúdo vertical; mantém as ações do painel alcançáveis em telas baixas."""
    def __init__(self, master, fundo=PANEL, **kw):
        super().__init__(master, style="Panel.TFrame", **kw)
        self.canvas = tk.Canvas(self, background=fundo, highlightthickness=0,
                                width=1, height=1)
        self.barra = ttk.Scrollbar(self, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.barra.set)
        self.barra.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.corpo = ttk.Frame(self.canvas, style="Panel.TFrame")
        self._janela = self.canvas.create_window((0, 0), window=self.corpo, anchor="nw")
        self.canvas.bind("<Configure>", self._dimensionar)
        self.corpo.bind("<Configure>", self._regiao)
        self._rodar_id = self.winfo_toplevel().bind("<MouseWheel>", self._rodar, add="+")
        self.bind("<Destroy>", self._fechar)

    def _dimensionar(self, e):
        self.canvas.itemconfigure(self._janela, width=e.width)

    def _regiao(self, _e=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _rodar(self, e):
        if str(e.widget).startswith(str(self.canvas)):
            self.canvas.yview_scroll(-int(math.copysign(1, e.delta)), "units")
            return "break"

    def _fechar(self, e):
        if e.widget is self:
            self.winfo_toplevel().unbind("<MouseWheel>", self._rodar_id)
