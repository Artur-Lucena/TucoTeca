#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TucoTeca terminal: MixPlayer de Tui (verbatim do modulo original)."""
from __future__ import annotations

import bib_core as core


class MixPlayer:
    def _player_tui(self):
        """Player interno preguiçoso (cria no 1º uso)."""
        if self.player is None:
            self.player = core.Player()
        return self.player
    def _tocar_interno(self, itens, pos) -> dict:
        try:
            pl = self._player_tui()
            pl.carregar([{"path": m.get("musica_path") or "",
                          "titulo": core.texto_musica(m)} for m in itens],
                        inicio=pos)
            return pl.tocar()
        except Exception as e:
            return {"ok": False, "erro": str(e)}
    def _alternar_interno(self) -> dict:
        try:
            pl = self._player_tui()
            r = pl.alternar()
            if not r.get("ok") and pl.estado == "parado":
                return {"ok": False, "erro": "nada tocando (Tocar primeiro)"}
            r["estado"] = pl.estado
            return r
        except Exception as e:
            return {"ok": False, "erro": str(e)}
    def _proxima_interno(self) -> dict:
        try:
            pl = self._player_tui()
            r = pl.proxima()
            if r.get("ok"):
                at = pl.atual() or {}
                return {"ok": True, "titulo": at.get("titulo") or ""}
            return r
        except Exception as e:
            return {"ok": False, "erro": str(e)}
    def _parar_interno(self) -> None:
        try:
            if self.player is not None:
                self.player.parar()
        except Exception:
            pass
    def _vigiar_player(self) -> None:
        """Faixa acabou → próxima sozinha (auto-avançar, sem travar o TUI)."""
        try:
            if self.player is not None and self.player.terminou():
                r = self.player.proxima()
                at = self.player.atual() if r.get("ok") else None
                self.msg = (f"Seguindo: {at.get('titulo')}" if at
                            else "Fim da fila.")
        except Exception:
            pass

