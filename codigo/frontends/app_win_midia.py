#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TucoTeca classico: MixMidia de App (verbatim do modulo original)."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import bib_core as core
from aparencia import MUT


class MixMidia:
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
