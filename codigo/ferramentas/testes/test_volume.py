"""Volume geral do PC: limites, mute, falhas e guards (sem alterar áudio real)."""
import os
import sys
from unittest.mock import patch

import bib_core as core
from bib_nucleo import volume as VOL
from executar import afirmar


class EndpointFake:
    def __init__(self):
        self.nivel = 50.0
        self.mudo = False
        self.entradas = self.saidas = 0
        self.escritas = []

    def __enter__(self):
        self.entradas += 1
        return self

    def __exit__(self, *_exc):
        self.saidas += 1

    def ler(self):
        return {"nivel": self.nivel, "mudo": self.mudo}

    def definir(self, nivel):
        self.escritas.append(("nivel", nivel))
        self.nivel = nivel

    def silenciar(self, mudo):
        self.escritas.append(("mudo", mudo))
        self.mudo = mudo


def teste_volume_pc_ajuste_limites_e_mudo():
    ep = EndpointFake()
    with patch.object(VOL, "volume_pc_disponivel", return_value=True), \
            patch.object(VOL, "_EndpointWindows", return_value=ep):
        afirmar(VOL.ler_volume_pc() == {"ok": True, "nivel": 50.0, "mudo": False})
        afirmar(ep.escritas == [], "ler volume não deve alterar o PC")
        r = VOL.definir_volume_pc(97)
        afirmar(r["ok"] and r["nivel"] == 97, r)
        r = VOL.ajustar_volume_pc(5)
        afirmar(r["ok"] and r["nivel"] == 100, r)
        r = VOL.ajustar_volume_pc(-150)
        afirmar(r["ok"] and r["nivel"] == 0, r)
        r = VOL.alternar_mudo_pc()
        afirmar(r["mudo"] and r["nivel"] == 0, r)
        r = VOL.definir_volume_pc(25.5)
        afirmar(r["mudo"] and r["nivel"] == 25.5, "set preserva mute se omitido")
        r = VOL.ajustar_volume_pc(5)
        afirmar(not r["mudo"] and r["nivel"] == 30.5, "ajuste deve restaurar som")
        r = VOL.definir_volume_pc(18, mudo=True)
        afirmar(r["mudo"] and r["nivel"] == 18, r)
        r = VOL.alternar_mudo_pc()
        afirmar(not r["mudo"] and r["nivel"] == 18, r)
        afirmar(VOL.definir_volume_pc(-1)["nivel"] == 0)
        afirmar(VOL.definir_volume_pc(200)["nivel"] == 100)
    afirmar(ep.entradas == ep.saidas, "operação deve liberar o endpoint")
    afirmar("ajustar_volume_pc" in core.__all__)


def teste_volume_pc_invalido_e_falhas():
    ep = EndpointFake()
    with patch.object(VOL, "volume_pc_disponivel", return_value=True), \
            patch.object(VOL, "_EndpointWindows", return_value=ep):
        for ruim in (None, "x", float("nan"), float("inf"), float("-inf")):
            afirmar(not VOL.definir_volume_pc(ruim)["ok"], ruim)
            afirmar(not VOL.ajustar_volume_pc(ruim)["ok"], ruim)
        afirmar(ep.entradas == 0 and ep.escritas == [],
                "parâmetro inválido não deve abrir/controlar o áudio")
        with patch.object(ep, "ler", side_effect=OSError("sem saída de áudio")):
            r = VOL.ler_volume_pc()
        afirmar(not r["ok"] and "sem saída" in r["erro"], r)
    afirmar(ep.entradas == ep.saidas == 1, "endpoint deve fechar na falha")


def teste_volume_pc_guard_outros_sistemas():
    with patch.object(sys, "platform", "darwin"), patch.object(os, "name", "nt"):
        afirmar(not VOL.volume_pc_disponivel(), "darwin deve ser verificado antes de nt")
    with patch.object(sys, "platform", "linux"), patch.object(os, "name", "posix"):
        afirmar(not VOL.volume_pc_disponivel())
    with patch.object(VOL, "volume_pc_disponivel", return_value=False), \
            patch.object(VOL, "_EndpointWindows") as native:
        for r in (VOL.ler_volume_pc(), VOL.definir_volume_pc(50),
                  VOL.ajustar_volume_pc(5), VOL.alternar_mudo_pc()):
            afirmar(not r["ok"], r)
        native.assert_not_called()
