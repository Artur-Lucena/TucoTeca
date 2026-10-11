#!/bin/sh
# TucoTeca Linux — execute em um terminal: ./BibliotecaHub.sh
# BIBLIOTECA_HOME é a pasta-mãe de dados/. Override explícito é preservado.
HUB="$(dirname "$(readlink -f "$0")")"
if [ -z "${BIBLIOTECA_HOME:-}" ]; then
  export BIBLIOTECA_HOME="$HUB"
fi
exec python3 "$HUB/codigo/frontends/app_tui.py" "$@"
