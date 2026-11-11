#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TucoTeca — aplicativo de terminal (curses, stdlib), voltado ao Linux.
Compartilha o núcleo e a coleção com o desktop Electron.

Uso:
    python3 codigo/frontends/app_tui.py [--db ~/.../biblioteca.db]

Lista: ↑/↓ ou j/k navegam; PgUp/PgDn mudam de página; Enter abre ações
do jogo; Esc abre o menu principal; q sai. Busca, filtros, importação,
backup e atualização são escolhas dos menus (sem atalhos antigos de letras).
DeSmuME Linux: pacote do sistema/AppImage manual, sem atualização automática.
Preview: Espaço marca/desmarca · PgUp/PgDn · i importa marcados · q volta

Horas automáticas: ao jogar, o tempo do processo é somado sozinho
(sessões ≥30 s; fechar o launcher antes do jogo perde a sessão).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bib_core as core

try:
    import curses
    import curses.textpad
except ImportError:  # Windows sem windows-curses: só avisa ao rodar
    curses = None  # type: ignore[assignment]


from tui_base import MixBase
from tui_jogo import MixJogo
from tui_menus import MixMenus
from tui_player import MixPlayer
from tui_scans import MixScans


class Tui(MixBase, MixJogo, MixMenus, MixPlayer, MixScans):
    """Terminal: estado no __init__ (MixBase), comportamento nos mixins."""




def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="TucoTeca — terminal (curses)")
    ap.add_argument("--db", default=str(core.DEFAULT_DB))
    ap.add_argument("--ignorar-lock", action="store_true",
                    help="abre mesmo com lock de outra instância (após crash)")
    ap.add_argument("--selftest", action="store_true",
                    help="monta o TUI sem terminal e sai (verificação)")
    args = ap.parse_args(argv)
    if curses is None and not args.selftest:
        print("curses indisponível neste Python (no Windows, use o app desktop: "
              "instalador TucoTeca-Setup ou TucoTeca.bat).", file=sys.stderr)
        return 2
    core.garantir_dirs()
    lk = core.adquirir_lock(ignorar=args.ignorar_lock)
    if not lk.get("ok"):
        print(f"[erro] {lk.get('erro')}", file=sys.stderr)
        return 2
    import atexit
    atexit.register(core.liberar_lock)
    core.get_db(Path(args.db)).close()
    if args.selftest:
        class _FakeScr:
            def getmaxyx(self):
                return (24, 80)

            def addnstr(self, *a):
                pass

            def erase(self):
                pass

            def refresh(self):
                pass

            def getch(self):
                return ord("q")

        class _FakeCurses:
            COLOR_CYAN = COLOR_BLACK = COLOR_GREEN = COLOR_RED = 1

            def curs_set(self, *a):
                pass

            def has_colors(self):
                return False

        real_curses = curses
        try:
            globals()["curses"] = _FakeCurses()
            app = Tui(_FakeScr(), Path(args.db))
            app.desenhar()
            print(f"[ok] selftest: TUI montado, {len(app.jogos)} jogo(s)")
        finally:
            globals()["curses"] = real_curses
            core.liberar_lock()
        return 0
    try:
        cols = int(__import__("shutil").get_terminal_size().columns)
        rows = int(__import__("shutil").get_terminal_size().lines)
    except Exception:
        cols, rows = 80, 24
    if rows < 10 or cols < 60:
        print(f"terminal pequeno ({cols}x{rows}); use ao menos 60x10.", file=sys.stderr)
        return 2

    def _run(stdscr):
        app = Tui(stdscr, Path(args.db))
        try:
            app.rodar()
        finally:
            if app.player is not None:
                app.player.parar()
                app.player.backend.close()
        return getattr(app, "msg_final", "")

    msg_final = curses.wrapper(_run)
    core.liberar_lock()
    if msg_final:
        print(msg_final)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
