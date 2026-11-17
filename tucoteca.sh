#!/bin/sh
# TucoTeca no Linux/macOS (TUI no terminal): ./tucoteca.sh
# No macOS, rode pelo Terminal (1ª vez: chmod +x tucoteca.sh).
# A coleção fica na pasta do projeto, salvo BIBLIOTECA_HOME já definido.
HUB="$(cd "$(dirname "$0")" && pwd -P)"
if [ -z "${BIBLIOTECA_HOME:-}" ]; then
  export BIBLIOTECA_HOME="$HUB"
fi
exec python3 "$HUB/codigo/frontends/app_tui.py" "$@"
