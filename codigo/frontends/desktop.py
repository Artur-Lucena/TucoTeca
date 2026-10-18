"""Frontend desktop: interface Electron (substitui o antigo Qt Quick).

A TUI curses (app_tui.py) continua disponivel para Linux/macOS. O modo
classico (janela Tk) e o desktop Qt (PySide6) foram removidos na F5.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main(argv=None):
    raiz = Path(__file__).resolve().parents[2]
    app_dir = raiz / "codigo" / "frontends" / "electron"
    if not app_dir.exists():
        print("Electron app nao encontrado em " + str(app_dir), file=sys.stderr)
        return 1
    exe = app_dir / "node_modules" / "electron" / "dist" / "electron.exe"
    if not exe.exists():
        print("Instale as dependencias: npm --prefix codigo/frontends/electron install",
              file=sys.stderr)
        return 1
    try:
        return subprocess.call([str(exe), "."], cwd=str(app_dir))
    except OSError as erro:
        print("Falha ao abrir o Electron: " + str(erro), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
