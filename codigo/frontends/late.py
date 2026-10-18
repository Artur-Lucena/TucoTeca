#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Acesso tardio a um módulo que também roda como script.

`app_tui.py` é entry point (`python app_tui.py`) e módulo importável ao
mesmo tempo. Quando roda como script, o módulo vive em `__main__`; um
`import app_tui` criaria uma segunda cópia. Os mixins resolvem o módulo
na hora do uso por este proxy.
"""
from __future__ import annotations

import sys


class ModuloTardio:
    """Proxy: `_W.attr` resolve o módulo por nome (importado) ou `__main__` (script)."""

    def __init__(self, nome: str):
        self._nome = nome

    def __getattr__(self, nome: str):
        mod = sys.modules.get(self._nome) or sys.modules.get("__main__")
        if mod is None:
            raise AttributeError(f"módulo {self._nome!r} não carregado")
        return getattr(mod, nome)

    def __dir__(self):
        mod = sys.modules.get(self._nome) or sys.modules.get("__main__")
        return dir(mod) if mod is not None else []


__all__ = ["ModuloTardio"]
