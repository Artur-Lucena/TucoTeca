#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TucoTeca terminal: MixBase de Tui (verbatim do modulo original)."""
from __future__ import annotations

import os
from pathlib import Path
from queue import SimpleQueue

import bib_core as core
from late import ModuloTardio

_T = ModuloTardio("app_tui")


class MixBase:
    TECLAS_RODAPE = "↑↓ move · Enter menu · ESC ações · q sai"

    AJUDA_LADO = (
        (" NAVEGAÇÃO ", [(("↑↓/jk", "mover"), ("PgUp/Dn", "página")),
                         (("Enter", "menu jogo"), ("ESC", "ações")),
                         (("q", "sair"), ("", ""))]),
        (" MENU (ESC) ", [(("›", "Buscar"), ("›", "Filtros")),
                          (("›", "Adicionar"), ("›", "Importar")),
                          (("›", "Backup"), ("›", "Sessão")),
                          (("›", "Emuladores"), ("›", "Sair"))]),
    )

    def __init__(self, stdscr, db_path: Path):
        self.stdscr = stdscr
        self.db_path = db_path
        self.jogos: list[dict] = []
        self.cur = 0
        self.top = 0
        self.q = ""
        self.statuses = ["", *core.STATUS_VALIDOS]
        self.si = 0
        self.fav = False
        self.filtro_prov: str | None = None
        self.filtro_tags: list[str] = []
        self.filtro_plat: str | None = None
        self.msg = ""
        self.msg_final = ""
        self.player = None  # interno, criado no 1º Tocar (externo é fallback)
        self.sessoes_pendentes = SimpleQueue()  # fila entre vigia e UI
        self._cores()
        self.recarregar()
        self._sessoes_verificadas = False
        self._backup_verificado = False
    def _cores(self):
        try:
            _T.curses.curs_set(0)
        except Exception:
            pass
        self.cor = {"txt": 0, "mut": 0, "acc": 0, "ok": 0, "ruim": 0,
                    "fav": 0, "tag": 0, "head": 0}
        self.abold = getattr(_T.curses, "A_BOLD", 0)
        self.adim = getattr(_T.curses, "A_DIM", 0)
        try:
            if _T.curses.has_colors():
                _T.curses.start_color()
                try:
                    _T.curses.use_default_colors()
                except Exception:
                    pass
                _T.curses.init_pair(1, _T.curses.COLOR_CYAN, -1)
                _T.curses.init_pair(2, _T.curses.COLOR_BLACK, _T.curses.COLOR_CYAN)
                _T.curses.init_pair(3, _T.curses.COLOR_GREEN, -1)
                _T.curses.init_pair(4, _T.curses.COLOR_RED, -1)
                try:
                    _T.curses.init_pair(5, _T.curses.COLOR_YELLOW, -1)
                    _T.curses.init_pair(6, _T.curses.COLOR_MAGENTA, -1)
                    _T.curses.init_pair(7, _T.curses.COLOR_WHITE, -1)
                except Exception:
                    pass
                self.cor = {"txt": 0, "mut": _T.curses.color_pair(1),
                            "acc": _T.curses.color_pair(2), "ok": _T.curses.color_pair(3),
                            "ruim": _T.curses.color_pair(4), "fav": _T.curses.color_pair(5),
                            "tag": _T.curses.color_pair(6), "head": _T.curses.color_pair(7)}
        except Exception:
            pass
    def _attr_linha(self, j: dict, selecionada: bool) -> int:
        """Cor da linha: seleção vence; ★ negrito amarelo; ○ ausente vermelho."""
        if selecionada:
            return self.cor["acc"] | self.abold
        if not j.get("exe_existe"):
            return self.cor["ruim"] | (self.abold if j.get("favorito") else 0)
        if j.get("favorito"):
            return self.cor["fav"] | self.abold
        return self.cor["txt"]
    def _con(self):
        return core.get_db(self.db_path)
    def recarregar(self):
        con = self._con()
        try:
            self.jogos = core.listar_jogos(
                con, q=self.q, status=self.statuses[self.si], favorito=self.fav,
                etiquetas=self.filtro_tags or None,
                plataformas=[self.filtro_plat] if self.filtro_plat else None)
            if self.filtro_prov:
                self.jogos = core.jogos_do_provedor(self.jogos, self.filtro_prov)
        finally:
            con.close()
        self.cur = max(0, min(self.cur, max(0, len(self.jogos) - 1)))
        self.top = max(0, min(self.top, max(0, len(self.jogos) - 1)))
    def linha_jogo(self, j: dict) -> str:
        marca = "●" if j["exe_existe"] else ("○" if j["executable_path"] else "–")
        estrela = "★ " if j["favorito"] else ""
        try:
            plat = j.get("plataforma") or core.plataforma_jogo(j)
        except Exception:
            plat = "PC"
        tags = list(j.get("etiquetas_lista") or [])
        sufixo_tags = f" #{', #'.join(tags)}" if tags else ""
        try:
            horas_n = round(float(j["horas"] or 0), 2)
        except (TypeError, ValueError):
            horas_n = 0
        horas = f" {horas_n:g}h" if horas_n else ""
        nota = f" n{j['nota']}" if j.get("nota") is not None else ""
        reg = f" · {j['regiao']}" if j.get("regiao") else ""
        return (f"{marca} {estrela}{j['titulo']} [{plat}]{sufixo_tags} "
                f"[{j['status']}]{horas}{nota}{reg}{core.selo_confianca(j)}")
    def _desenhar_ajuda_lado(self, s, x0: int, larg_p: int, rows: int) -> None:
        """Quadrinho duplo de teclas à direita (terminal largo e alto)."""
        linhas: list[tuple[str, int]] = []
        for titulo, pares in self.AJUDA_LADO:
            linhas.append((titulo, 1))
            for (t1, f1), (t2, f2) in pares:
                esq = f" {t1.ljust(6)[:6]} {f1}"[:22].ljust(22)
                if t2:
                    dir_ = f"{t2.ljust(7)[:7]} {f2}"[:18].ljust(18)
                else:
                    dir_ = " " * 18
                linhas.append((esq + dir_, 0))
        if len(linhas) + 2 > rows - 1:
            return
        cor_t = self.cor["head"] | self.abold
        cor_b = self.cor["fav"] | self.abold
        s.addnstr(0, x0, "╔" + "═" * (larg_p - 2) + "╗", larg_p, cor_b)
        y = 1
        for texto, destaque in linhas:
            if destaque:
                s.addnstr(y, x0, f"║{texto.center(larg_p - 2)[:larg_p - 2]}║",
                          larg_p, cor_t)
            else:
                s.addnstr(y, x0, ("║" + texto[:larg_p - 2]).ljust(larg_p - 1) + "║",
                          larg_p, self.cor["txt"])
            y += 1
        s.addnstr(y, x0, "╚" + "═" * (larg_p - 2) + "╝", larg_p, cor_b)
    def desenhar(self):
        s = self.stdscr
        try:
            s.erase()
            rows, cols = s.getmaxyx()
            larg_total = max(1, cols - 1)
            painel = 42 if cols >= 100 else 0
            larg = larg_total - painel
            if painel:
                self._desenhar_ajuda_lado(s, larg, painel, rows)
            titulo = "🎮 TucoTeca"
            s.addnstr(0, 0, titulo.ljust(larg)[:larg], larg,
                      self.cor["head"] | self.abold)
            az = core.azahar_status()
            azg = "🎮✓" if az["instalado"] and az["chaves"] else ("🎮!" if az["instalado"] else "🎮✗")
            ndsg = ("NDS✓" if core.default_emu_nds() else "NDS✗")
            prov_txt = f" prov={self.filtro_prov or 'todos'}"
            plat_txt = f" plat={self.filtro_plat or 'todas'}"
            tags = getattr(self, "filtro_tags", []) or []
            tags_txt = f" tags={','.join(tags)}" if tags else ""
            filtro = f"busca='{self.q}' status={self.statuses[self.si] or 'todos'} fav={'sim' if self.fav else 'não'}{prov_txt}{plat_txt}{tags_txt} {azg} {ndsg}"
            s.addnstr(1, 0, f"{filtro} — {len(self.jogos)} jogo(s)", larg, self.cor["mut"])
            area = rows - 4
            if self.cur < self.top:
                self.top = self.cur
            if self.cur >= self.top + area:
                self.top = self.cur - area + 1
            for i in range(area):
                idx = self.top + i
                if idx >= len(self.jogos):
                    break
                j = self.jogos[idx]
                sel = idx == self.cur
                linha = self.linha_jogo(j).ljust(larg)[:larg]
                s.addnstr(2 + i, 0, linha, larg, self._attr_linha(j, sel))
            if self.jogos and rows >= 4:
                j = self.jogos[self.cur]
                exe = j["exe_traduzido"] or j["executable_path"] or "(sem executável)"
                s.addnstr(rows - 2, 0, f"▶ {exe}"[:larg], larg, self.cor["mut"] | self.adim)
            if self.msg:
                cor_msg = self.cor["ruim"] if self.msg[:6].lower().startswith(
                    ("falha", "[erro", "erro")) else self.cor["ok"]
                s.addnstr(rows - 1, 0, self.msg[:larg], larg, cor_msg | self.abold)
                self.msg = ""
            else:
                s.addnstr(rows - 1, 0, self.TECLAS_RODAPE[:larg], larg,
                          self.cor["mut"] | self.adim)
            s.refresh()
        except Exception:
            # resize ou terminal pequeno no meio do desenho: ignora, próximo loop redesenha
            try:
                s.refresh()
            except Exception:
                pass
    def perguntar(self, prompt: str, inicial: str = "") -> str | None:
        s = self.stdscr
        rows, cols = s.getmaxyx()
        mostra = f"{prompt}[{inicial}] " if inicial else prompt
        try:
            s.addnstr(rows - 1, 0, mostra[: cols - 1], cols - 1, self.cor["mut"])
            s.refresh()
        except Exception:
            pass
        try:
            _T.curses.curs_set(1)
        except Exception:
            pass
        _T.curses.echo()
        try:
            try:
                s.timeout(-1)  # entrada bloqueante aqui (restaura depois)
                raw = s.getstr(rows - 1, min(len(mostra), cols - 1), 2000)
            except KeyboardInterrupt:
                return None
            except Exception:
                return None
            finally:
                try:
                    s.timeout(500)
                except Exception:
                    pass
                _T.curses.noecho()
                try:
                    _T.curses.curs_set(0)
                except Exception:
                    pass
        except Exception:
            try:
                _T.curses.noecho()
            except Exception:
                pass
            return None
        try:
            txt = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        except Exception:
            return None
        # ESC sozinho (b'\x1b') ou com prefixo cancela; getstr pode devolver str também
        if txt == "\x1b" or txt == "\x1b\x1b" or (len(txt) == 1 and ord(txt) == 27):
            return None
        if isinstance(raw, bytes) and raw in (b"\x1b", b"\x1b\x1b"):
            return None
        txt = txt.strip()
        if txt == "" and inicial:
            return inicial
        if len(txt) >= 2 and txt.startswith('"') and txt.endswith('"'):
            txt = txt[1:-1].strip()
        if txt.startswith("~"):
            try:
                txt = os.path.expanduser(txt)
            except Exception:
                pass
        return txt
    def confirmar(self, pergunta: str) -> bool:
        r = self.perguntar(pergunta + " (s/N) ")
        return (r or "").strip().lower() in ("s", "sim", "y", "yes")
    def atual(self) -> dict | None:
        if not self.jogos:
            self.msg = "Lista vazia."
            return None
        return self.jogos[self.cur]
    def escolher(self, titulo: str, opcoes: list[str]) -> int | None:
        """Caixinha central: ↑↓/jk move, Enter confirma, ESC/q cancela.

        Com rolagem (listas longas) e largura limitada ao terminal.
        """
        if not opcoes:
            return None
        s = self.stdscr
        cur = 0
        k_down = getattr(_T.curses, "KEY_DOWN", -2)
        k_up = getattr(_T.curses, "KEY_UP", -2)
        k_enter = getattr(_T.curses, "KEY_ENTER", -2)
        rodape = "↑↓ move · Enter ok · ESC volta"
        while True:
            try:
                rows, cols = s.getmaxyx()
                larg_m = max(26, max((len(titulo) + 4,
                                      *(len(o) + 6 for o in opcoes))))
                larg_m = min(larg_m, max(12, cols))
                max_vis = max(1, rows - 6)  # título+bordas+rodapé+setas
                if len(opcoes) > max_vis:
                    ini = min(max(0, cur - max_vis // 2),
                              len(opcoes) - max_vis)
                else:
                    ini = 0
                vis = opcoes[ini:ini + max_vis]
                x0 = max(0, (cols - larg_m) // 2)
                y0 = max(0, (rows - (len(vis) + 2)) // 2)
                if ini > 0:
                    s.addnstr(y0, x0, ("▲" + " " * (larg_m - 1))[:larg_m],
                              larg_m, self.cor["mut"])
                s.addnstr(y0 + (1 if ini > 0 else 0), x0,
                          "┌" + "─" * (larg_m - 2) + "┐", larg_m,
                          self.cor["mut"])
                s.addnstr(y0 + (2 if ini > 0 else 1), x0,
                          ("│" + f" {titulo} ".center(larg_m - 2)[:larg_m - 2] + "│"),
                          larg_m, self.cor["head"] | self.abold)
                base = y0 + (3 if ini > 0 else 2)
                for pos, op in enumerate(vis):
                    i = ini + pos
                    attr = self.cor["acc"] | self.abold if i == cur else self.cor["txt"]
                    s.addnstr(base + pos, x0,
                              (f"│ {'▶' if i == cur else ' '} {op}".ljust(larg_m - 1) + "│")[:larg_m],
                              larg_m, attr)
                fim = base + len(vis)
                if ini + len(vis) < len(opcoes):
                    s.addnstr(fim, x0, ("▼" + " " * (larg_m - 1))[:larg_m],
                              larg_m, self.cor["mut"])
                    fim += 1
                s.addnstr(fim, x0,
                          "└" + "─" * (larg_m - 2) + "┘", larg_m, self.cor["mut"])
                if fim + 1 < rows:
                    s.addnstr(fim + 1, x0, rodape[:larg_m].center(larg_m),
                              larg_m, self.cor["mut"])
                s.refresh()
            except Exception:
                return None
            try:
                ch = s.getch()
            except Exception:
                return None  # terminal fechado/erro real; -1 é apenas timeout normal
            if ch == -1:
                continue
            if ch in (k_down, ord("j")):
                cur = min(len(opcoes) - 1, cur + 1)
            elif ch in (k_up, ord("k")):
                cur = max(0, cur - 1)
            elif ch in (27, ord("q")):
                return None
            elif ch in (k_enter, 10, 13):
                return cur
    def formulario(self, j: dict | None) -> dict | None:
        vals = {
            "titulo": self.perguntar("Título*: ", j["titulo"] if j else ""),
            "executable_path": self.perguntar("Executável: ", j["executable_path"] if j else ""),
            "exe_win": self.perguntar("Exe Windows (vazio=igual): ",
                                      (j["exe_win"] if j else "") or ""),
            "exe_linux": self.perguntar("Exe Linux (vazio=igual): ",
                                        (j["exe_linux"] if j else "") or ""),
            "status": self.perguntar(f"Status {list(core.STATUS_VALIDOS)}: ",
                                     j["status"] if j else "backlog"),
            "nota": self.perguntar("Nota 0-10 (vazio=sem): ",
                                   "" if not j or j["nota"] is None else str(j["nota"])),
            "horas": self.perguntar("Horas: ", "0" if not j else str(j["horas"] or 0)),
            "favorito": self.perguntar("Favorito? (s/N): ",
                                       "s" if j and j["favorito"] else ""),
            "launch_options": self.perguntar("Opções lançamento: ",
                                             j["launch_options"] if j else ""),
            "azahar_preset": self.perguntar("Preset Azahar p/ ROMs 3DS (vazio=nenhum): ",
                                            (j.get("azahar_preset") if j else "") or ""),
            "wine_prefix": self.perguntar("Wine prefix (Linux): ",
                                          j["wine_prefix"] if j else ""),
            "etiquetas": self.perguntar("Etiquetas (vírgula, ex.: rpg, souls-like): ",
                                        (j.get("etiquetas") if j else "") or ""),
            "save_path": self.perguntar("Pasta de saves (vazio=sem): ",
                                        (j.get("save_path") if j else "") or ""),
            "observacoes": self.perguntar("Observações: ", j["observacoes"] if j else ""),
        }
        if vals["titulo"] is None or not vals["titulo"].strip():
            self.msg = "Cancelado (título obrigatório)."
            return None
        try:
            return {
                "titulo": vals["titulo"].strip(),
                "executable_path": (vals["executable_path"] or "").strip(),
                "exe_win": (vals["exe_win"] or "").strip(),
                "exe_linux": (vals["exe_linux"] or "").strip(),
                "status": (vals["status"] or "backlog").strip(),
                "nota": None if (vals["nota"] or "").strip() == "" else int(vals["nota"]),
                "horas": float((vals["horas"] or "0").strip() or 0),
                "favorito": (vals["favorito"] or "").strip().lower() in ("s", "sim", "y"),
                "launch_options": (vals["launch_options"] or "").strip(),
                "azahar_preset": (vals["azahar_preset"] or "").strip(),
                "wine_prefix": (vals["wine_prefix"] or "").strip(),
                "etiquetas": (vals["etiquetas"] or "").strip(),
                "save_path": (vals["save_path"] or "").strip(),
                "observacoes": (vals["observacoes"] or "").strip(),
            }
        except (TypeError, ValueError):
            self.msg = "Nota/horas inválidos. Cancelado."
            return None

