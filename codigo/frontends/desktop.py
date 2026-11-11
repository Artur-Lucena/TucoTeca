"""Frontend desktop pelo checkout: abre a interface Electron.

Usuário final usa o instalador (TucoTeca-Setup-*.exe); este módulo serve o
checkout de desenvolvimento (TucoTeca.bat / abrir_hub.py). A TUI curses
(app_tui.py) continua disponível para Linux/macOS.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
APP_DIR = RAIZ / "codigo" / "frontends" / "electron"


def executavel_electron(app_dir: Path = APP_DIR) -> Path | None:
    """Binário do Electron instalado pelo npm, em qualquer SO.

    O pacote `electron` grava em `path.txt` o caminho relativo a `dist/`
    (ex.: `electron.exe`, `Electron.app/Contents/MacOS/Electron`).
    """
    pacote = app_dir / "node_modules" / "electron"
    try:
        relativo = (pacote / "path.txt").read_text(encoding="utf-8").strip()
    except OSError:
        relativo = "electron.exe" if sys.platform == "win32" else "electron"
    exe = pacote / "dist" / relativo
    return exe if relativo and exe.is_file() else None


def main(argv=None):
    if not APP_DIR.is_dir():
        print("Electron app não encontrado em " + str(APP_DIR), file=sys.stderr)
        return 1
    exe = executavel_electron()
    if exe is None:
        print("Instale as dependências: npm --prefix codigo/frontends/electron install",
              file=sys.stderr)
        return 1
    if not (APP_DIR / "out" / "main" / "index.js").is_file():
        print("Compile o app: npm --prefix codigo/frontends/electron run build",
              file=sys.stderr)
        return 1
    try:
        return subprocess.call([str(exe), "."], cwd=str(APP_DIR))
    except OSError as erro:
        print("Falha ao abrir o Electron: " + str(erro), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
