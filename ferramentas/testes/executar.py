#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runner mínimo da suíte (stdlib): importa test_*.py e roda teste_*().

    python ferramentas/testes/executar.py

Cada teste recebe nada e deve levantar AssertionError ao falhar (use
afirmar). Banco fake em temp; nunca toca na casa de verdade.
"""
from __future__ import annotations

import importlib.util
import sys
import traceback
from pathlib import Path

TESTES_DIR = Path(__file__).resolve().parent
REPO = TESTES_DIR.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def afirmar(cond, msg=""):
    if not cond:
        raise AssertionError(msg or "afirmação falhou")


def main() -> int:
    total = falhou = 0
    for arq in sorted(TESTES_DIR.glob("test_*.py")):
        nome_mod = "suite_" + arq.stem
        spec = importlib.util.spec_from_file_location(nome_mod, arq)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for nome in sorted(dir(mod)):
            if not nome.startswith("teste_"):
                continue
            total += 1
            rotulo = f"{arq.stem}.{nome}"
            try:
                getattr(mod, nome)()
            except Exception:
                falhou += 1
                print(f"FAIL {rotulo}")
                traceback.print_exc(limit=3)
            else:
                print(f"PASS {rotulo}")
    print(f"\n{total - falhou}/{total} verdes.")
    return 1 if falhou else 0


if __name__ == "__main__":
    raise SystemExit(main())
