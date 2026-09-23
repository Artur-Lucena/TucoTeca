#!/bin/sh
# Biblioteca Hub (Linux) — duplo-clique ou ./BibliotecaHub.sh no terminal.
# Abre o TUI (aplicativo de terminal). Casa e banco ficam na pasta do projeto.
HUB="$(dirname "$(readlink -f "$0")")"
export BIBLIOTECA_HOME="$HUB"
exec python3 "$HUB/codigo/frontends/app_tui.py" "$@"
