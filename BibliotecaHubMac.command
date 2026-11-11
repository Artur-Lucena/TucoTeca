#!/bin/sh
# TucoTeca (macOS) — duplo-clique abre a TUI no Terminal. Casa e banco na pasta do projeto.
# No Terminal (1ª vez): chmod +x BibliotecaHubMac.command
HUB="$(cd "$(dirname "$0")" && pwd)"
export BIBLIOTECA_HOME="$HUB"
exec python3 "$HUB/codigo/frontends/app_tui.py" "$@"
