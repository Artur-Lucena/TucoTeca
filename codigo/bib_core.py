#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bib_core — núcleo compartilhado da Biblioteca de Jogos (compat).

O código mora em bib_nucleo/ (base, banco, scans, emuladores, pacotes);
aqui só reexporta para frontends e scripts (`import bib_core as core`).
Para monkeypatch em testes, altere bib_nucleo.<modulo> (onde mora a função).
"""
from __future__ import annotations

from bib_nucleo import banco, base, cheats, emuladores, musicas, pacotes, scans, texturas
from bib_nucleo.banco import *
from bib_nucleo.base import *
from bib_nucleo.cheats import *
from bib_nucleo.emuladores import *
from bib_nucleo.musicas import *
from bib_nucleo.pacotes import *
from bib_nucleo.scans import *
from bib_nucleo.texturas import *

__all__ = sorted(set(base.__all__ + banco.__all__ + scans.__all__
                     + emuladores.__all__ + pacotes.__all__
                     + texturas.__all__ + cheats.__all__ + musicas.__all__))
