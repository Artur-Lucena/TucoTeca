#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bib_core — núcleo compartilhado da Biblioteca de Jogos (compat).

O código mora em bib_nucleo/ (base, banco, scans, emuladores, pacotes);
aqui só reexporta para frontends e scripts (`import bib_core as core`).
Para monkeypatch em testes, altere bib_nucleo.<modulo> (onde mora a função).
"""
from __future__ import annotations

from bib_nucleo import (
                     baixar,
                     banco,
                     base,
                     cheats,
                     controles,
                     editores_imagem,
                     emuladores,
                     equalizadores,
                     ferramentas,
                     fontes,
                     musicas,
                     pacotes,
                     player,
                     qbit,
                     repacks,
                     reprodutores_video,
                     scans,
                     texturas,
                     torrents,
                     videos,
                     videos_youtube,
                     volume,
)
from bib_nucleo.baixar import *
from bib_nucleo.banco import *
from bib_nucleo.base import *
from bib_nucleo.cheats import *
from bib_nucleo.controles import *
from bib_nucleo.editores_imagem import *
from bib_nucleo.emuladores import *
from bib_nucleo.equalizadores import *
from bib_nucleo.ferramentas import *
from bib_nucleo.musicas import *
from bib_nucleo.pacotes import *
from bib_nucleo.player import *
from bib_nucleo.qbit import *
from bib_nucleo.rede.fontes import *
from bib_nucleo.rede.repacks import *
from bib_nucleo.rede.torrents import *
from bib_nucleo.rede.videos_youtube import *
from bib_nucleo.reprodutores_video import *
from bib_nucleo.scans import *
from bib_nucleo.texturas import *
from bib_nucleo.videos import *
from bib_nucleo.volume import *

__all__ = sorted(set(base.__all__ + banco.__all__ + scans.__all__
                     + emuladores.__all__ + pacotes.__all__
                     + texturas.__all__ + cheats.__all__ + musicas.__all__
                     + controles.__all__ + repacks.__all__ + baixar.__all__
                     + player.__all__ + fontes.__all__ + volume.__all__
                     + torrents.__all__ + ferramentas.__all__ + qbit.__all__
                     + editores_imagem.__all__ + equalizadores.__all__
                     + reprodutores_video.__all__ + videos.__all__
                     + videos_youtube.__all__))
