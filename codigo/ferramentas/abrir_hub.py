"""Entrada do checkout: runtime local, fontes atuais e coleção preservada."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def preparar():
    os.environ.setdefault("BIBLIOTECA_HOME", str(REPO))
    runtime = REPO / "programa/windows-x64"
    arq = runtime / "manifesto-runtime.json"
    if arq.is_file():
        d = json.loads(arq.read_text(encoding="utf-8"))
        serie = d["versoes"]["serie_tk"]
        os.environ["TCL_LIBRARY"] = str(runtime / "python/tcl" / ("tcl" + serie))
        os.environ["TK_LIBRARY"] = str(runtime / "python/tcl" / ("tk" + serie))
        variaveis = {"7z": "BIBLIOTECA_7Z", "ffmpeg": "BIBLIOTECA_FFMPEG",
                     "ytdlp": "BIBLIOTECA_YTDLP", "quickjs": "BIBLIOTECA_QUICKJS",
                     "qbittorrent": "BIBLIOTECA_QBITTORRENT"}
        for nome, env in variaveis.items():
            item = d["componentes"].get(nome)
            if item:
                os.environ.setdefault(env, str(runtime / item["executavel"]))
    # Emulação desta coleção conserva os caminhos/perfis/saves já cadastrados.
    sys.path[:0] = [str(REPO / "codigo/frontends"), str(REPO / "codigo")]


def main():
    preparar()
    from desktop import main as desktop_main
    return desktop_main()


if __name__ == "__main__":
    raise SystemExit(main())
