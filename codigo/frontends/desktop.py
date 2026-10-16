"""Frontend desktop único: interface Qt Quick (PySide6).

A TUI curses (app_tui.py) continua disponível para Linux/macOS. O modo
clássico (janela Tk) foi removido; as flags antigas degradam com aviso.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Entry point instalável (console script) e execução via -m/direta: garante que
# o módulo irmão app_qt fique importável em qualquer cenário.
_AQUI = Path(__file__).resolve().parent
if str(_AQUI) not in sys.path:
    sys.path.insert(0, str(_AQUI))

_LEGADAS_SEM_VALOR = ("--classico", "--ignorar-lock")

_AVISO_LEGADO = "aviso: modo clássico removido; abrindo a interface Qt"

_MENSAGEM_SEM_QT = (
    "A interface principal precisa do PySide6. Instale: "
    "py -3.14 -m pip install -r codigo/ferramentas/requirements-ui.txt — "
    "ou use um pacote pronto. Em Linux/macOS, o TUI continua: ./BibliotecaHub.sh"
)


def _sem_flags_legadas(args: list[str]) -> tuple[list[str], bool]:
    """Remove as flags do modo clássico (--jogar consome o valor seguinte)."""
    limpos: list[str] = []
    removeu = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in _LEGADAS_SEM_VALOR:
            removeu = True
            i += 1
            continue
        if arg == "--jogar":
            removeu = True
            i += 2 if i + 1 < len(args) and not args[i + 1].startswith("-") else 1
            continue
        if arg.startswith("--jogar="):
            removeu = True
            i += 1
            continue
        limpos.append(arg)
        i += 1
    return limpos, removeu


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    args, removeu = _sem_flags_legadas(args)
    if removeu:
        print(_AVISO_LEGADO, file=sys.stderr)
    if importlib.util.find_spec("PySide6") is None:
        print(_MENSAGEM_SEM_QT, file=sys.stderr)
        return 1
    import app_qt
    return app_qt.main(args)


if __name__ == "__main__":
    raise SystemExit(main())
