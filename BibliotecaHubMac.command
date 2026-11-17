#!/bin/sh
# TucoTeca no macOS: duplo-clique abre a TUI no Terminal (1ª vez: chmod +x).
exec "$(cd "$(dirname "$0")" && pwd -P)/BibliotecaHub.sh" "$@"
