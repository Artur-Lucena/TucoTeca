"""Seleciona o frontend desktop e permite trocar para as ferramentas clássicas."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Entry point instalável (console script) e execução via -m/direta: garante que
# os módulos irmãos (app_qt/app_win) fiquem importáveis em qualquer cenário.
_AQUI = Path(__file__).resolve().parent
if str(_AQUI) not in sys.path:
    sys.path.insert(0, str(_AQUI))


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    classico = "--classico" in args or "--jogar" in args or "--ignorar-lock" in args
    args = [a for a in args if a != "--classico"]
    if not classico and importlib.util.find_spec("PySide6") is not None:
        import app_qt
        resultado = app_qt.main(args)
        if resultado != 42:
            return resultado
    import app_win
    return app_win.main([a for a in args if a != "--big-picture"])


if __name__ == "__main__":
    raise SystemExit(main())
