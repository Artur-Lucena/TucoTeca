#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TucoTeca — aplicativo de terminal (curses, stdlib).
Alvo principal: Linux. Mesmo banco e mesmas regras da GUI Windows.

Uso:
    python codigo/frontends/app_tui.py [--db ~/.../biblioteca.db]

Teclas (lista): ↑/↓ ou j/k navegar · PgUp/PgDn · / buscar · f status ·
  * favoritos · V provider · Y plataforma · T etiquetas · Enter jogar ·
  a adicionar · e editar · d excluir ·
  I importar (arquivo, pasta ou disco — ROM liga no emu sozinha) ·
  b backup · U saves 3DS · E exportar JSON · P pacote portátil · S registrar sessão manual ·
  A atualizar Azahar · G atualizar DeSmuME · r recarregar · q sair
Preview: Espaço marca/desmarca · PgUp/PgDn · i importa marcados · q volta

Horas automáticas: ao jogar, o tempo do processo é somado sozinho
(sessões ≥30 s; fechar o launcher antes do jogo perde a sessão).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from queue import Empty, SimpleQueue

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bib_core as core

try:
    import curses
    import curses.textpad
except ImportError:  # Windows sem windows-curses: só avisa ao rodar
    curses = None  # type: ignore[assignment]


class Tui:
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

    # -- base
    def _cores(self):
        try:
            curses.curs_set(0)
        except Exception:
            pass
        self.cor = {"txt": 0, "mut": 0, "acc": 0, "ok": 0, "ruim": 0,
                    "fav": 0, "tag": 0, "head": 0}
        self.abold = getattr(curses, "A_BOLD", 0)
        self.adim = getattr(curses, "A_DIM", 0)
        try:
            if curses.has_colors():
                curses.start_color()
                try:
                    curses.use_default_colors()
                except Exception:
                    pass
                curses.init_pair(1, curses.COLOR_CYAN, -1)
                curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
                curses.init_pair(3, curses.COLOR_GREEN, -1)
                curses.init_pair(4, curses.COLOR_RED, -1)
                try:
                    curses.init_pair(5, curses.COLOR_YELLOW, -1)
                    curses.init_pair(6, curses.COLOR_MAGENTA, -1)
                    curses.init_pair(7, curses.COLOR_WHITE, -1)
                except Exception:
                    pass
                self.cor = {"txt": 0, "mut": curses.color_pair(1),
                            "acc": curses.color_pair(2), "ok": curses.color_pair(3),
                            "ruim": curses.color_pair(4), "fav": curses.color_pair(5),
                            "tag": curses.color_pair(6), "head": curses.color_pair(7)}
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

    # -- desenho
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

    # -- entrada
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
            curses.curs_set(1)
        except Exception:
            pass
        curses.echo()
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
                curses.noecho()
                try:
                    curses.curs_set(0)
                except Exception:
                    pass
        except Exception:
            try:
                curses.noecho()
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

    # -- ações
    def atual(self) -> dict | None:
        if not self.jogos:
            self.msg = "Lista vazia."
            return None
        return self.jogos[self.cur]

    def jogar(self):
        j = self.atual()
        if not j:
            return
        con = self._con()
        try:
            j = self._resolver_antes_de_jogar(con, j)
            if j is None:
                return
            prep = core.preparar_lancamento(j)
            aviso = f" [{prep['aviso']}]" if prep.get("aviso") else ""
            res = core.executar_monitorado(
                j, ao_fim=lambda sessao, rastreado, _gid=j["id"]:
                    self.sessoes_pendentes.put((_gid, sessao, rastreado)))
            if res.get("requer_elevacao") and self.confirmar("Exige administrador. Elevar?"):
                res = core.executar_jogo_dict(j, elevar=True)
                if res.get("ok"):
                    core.marcar_execucao(con, j["id"])
                    try:
                        core.iniciar_sessao_manual(j["id"], j.get("titulo") or "")
                    except Exception:
                        pass
                    self.msg = f"Executando ✓ (UAC — sessão manual; S registra){aviso}"
                else:
                    self.msg = f"Falha: {res.get('erro')}{aviso}"
            elif res.get("ok"):
                core.marcar_execucao(con, j["id"])
                if res.get("rastreado"):
                    extra = " ⏱ tempo será registrado"
                else:
                    extra = " ⏱ sem rastreio — sessão manual; S registra ao terminar"
                self.msg = f"Executando ✓ ({res.get('modo')}){extra}{aviso}"
            else:
                self.msg = f"Falha: {res.get('erro')}{aviso}"
        finally:
            con.close()

    def registrar_sessao_manual(self):
        try:
            pend = core.listar_sessoes_pendentes()
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        if not pend:
            self.msg = "Nenhuma sessão manual pendente."
            return
        alvo = pend[0]
        if len(pend) > 1:
            for i, p in enumerate(pend):
                self.msg = f"{i+1}: {p.get('titulo') or p.get('gid')} · {p.get('inicio')}"
                self.desenhar()
                self.perguntar("Enter p/ continuar…")
            r = self.perguntar(f"Número (1-{len(pend)}, J=primeira): ")
            if r is None:
                return
            r = (r or "").strip().lower()
            if r in ("j", "jogar", ""):
                alvo = pend[0]
            elif r.isdigit() and 1 <= int(r) <= len(pend):
                alvo = pend[int(r) - 1]
            else:
                return
        r = self.perguntar(f"Horas em '{alvo.get('titulo') or alvo.get('gid')}' (0=encerrar sem somar): ")
        if r is None:
            return
        try:
            horas = float((r or "0").strip() or 0)
        except ValueError:
            self.msg = "Horas inválidas."
            return
        try:
            res = core.encerrar_sessao_manual(alvo["_arquivo"], horas)
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        self.msg = f"+{horas}h ✓" if res.get("ok") and horas else (res.get("erro") or "Encerrada.")
        self.recarregar()

    def _verificar_pendencias_inicio(self):
        if self._sessoes_verificadas:
            return
        self._sessoes_verificadas = True
        try:
            pend = core.listar_sessoes_pendentes()
            if pend:
                self.msg = f"{len(pend)} sessão(ões) manual(is) pendente(s) — S registra."
        except Exception:
            pass
        if self._backup_verificado:
            return
        self._backup_verificado = True
        try:
            idade = core.idade_ultimo_backup_dias()
            if idade is None:
                self.msg += (" · " if self.msg else "") + "Sem backup — b faz agora."
            elif idade > 7:
                self.msg += (" · " if self.msg else "") + f"Backup há {int(idade)}d — b faz agora."
        except Exception:
            pass

    def _resolver_antes_de_jogar(self, con, j):
        """Perguntar-antes (TUI): emulador trocado? ROM sumida? Jogo ou None."""
        diag = core.diagnosticar_exe(j)
        if diag["estado"] == "trocou-emulador":
            r = self.perguntar(
                f"Emulador gravado sumiu. Usar o atual ({diag['nome']}) e "
                "[G]ravar, só desta [V]ez ou [C]ancelar? ")
            if r is None:
                return None
            op = r.strip().lower()
            if op in ("g", "gravar"):
                j = core.atualizar_jogo(con, j["id"], {"executable_path": "",
                    "exe_win" if os.name == "nt" else "exe_linux": ""})
            elif op in ("v", "vez"):
                j = {**j, "executable_path": "", "exe_win": "", "exe_linux": ""}
            else:
                return None
        drom = core.diagnosticar_rom(j)
        if drom["estado"] == "rom-ausente":
            cands = drom["candidatos"]
            escolhido = None
            if cands:
                for i, p in enumerate(cands):
                    self.msg = f"{i + 1}: {p}"
                    self.desenhar()
                    self.perguntar("Enter para continuar: ")
                r = self.perguntar("Número da ROM (J=primeira, vazio=informar caminho): ")
                if r is None:
                    return None
                if r.lower() in ("j", "jogar"):
                    escolhido = cands[0]
                elif r.isdigit() and 1 <= int(r) <= len(cands):
                    escolhido = cands[int(r) - 1]
            if not escolhido:
                escolhido = self.perguntar("Novo caminho da ROM (vazio=cancela): ")
            if not escolhido:
                self.msg = "Religação cancelada."
                return None
            escolhido = escolhido.strip()
            ok, trad = core.existe_aqui_ou_traduzido(escolhido)
            if not ok:
                self.msg = "Religação cancelada ou arquivo inexistente (nos 2 SOs)."
                return None
            escolhido = trad
            if not self.confirmar(f"Religar para {escolhido}?"):
                return None
            j = core.atualizar_jogo(con, j["id"], {"launch_options": escolhido})
        return j

    def escolher(self, titulo: str, opcoes: list[str]) -> int | None:
        """Caixinha central: ↑↓/jk move, Enter confirma, ESC/q cancela.

        Com rolagem (listas longas) e largura limitada ao terminal.
        """
        s = self.stdscr
        cur = 0
        k_down = getattr(curses, "KEY_DOWN", -2)
        k_up = getattr(curses, "KEY_UP", -2)
        k_enter = getattr(curses, "KEY_ENTER", -2)
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
                ch = -1
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

    def menu_jogo(self):
        """Enter virou select: caixinha de ações do jogo; ESC volta à lista."""
        j = self.atual()
        if not j:
            return
        opcoes = ["Jogar", "Editar", "Mods", "Texturas", "Cheats",
                  "Apagar", "Voltar"]
        idx = self.escolher(j["titulo"], opcoes)
        if idx is None:
            return
        escolha = opcoes[idx]
        if escolha == "Jogar":
            self.jogar()
        elif escolha == "Editar":
            self.editar()
        elif escolha == "Mods":
            self.menu_mods(j)
        elif escolha == "Texturas":
            self.menu_texturas(j)
        elif escolha == "Cheats":
            self.menu_cheats(j)
        elif escolha == "Apagar":
            self.excluir()

    def menu_mods(self, j):
        """Gerenciar mods LayeredFS (só ROM 3DS com title ID legível)."""
        try:
            launch = core.traduzir_para_atual((j.get("launch_options") or "").strip())
            tid = core.title_id_da_rom(launch)
        except Exception:
            tid = ""
        if not tid:
            self.msg = "Mods só para ROMs 3DS com title ID legível."
            return
        con = self._con()
        try:
            while True:
                row = con.execute("SELECT * FROM jogos WHERE id=?",
                                  (j["id"],)).fetchone()
                if row is None:
                    self.msg = "Jogo sumido."
                    return
                atual = core.row_to_dict(row)
                ativos = set(atual.get("mods_lista") or [])
                off = bool(atual.get("azahar_mods_off"))
                try:
                    disp = core.listar_mods(tid)
                except Exception:
                    disp = []
                estado = "Mods: DESLIGADOS (alternar)" if off else "Mods: ligados (alternar)"
                opcoes = ([estado]
                          + [f"[{'x' if m in ativos else ' '}] {m}" for m in disp]
                          + ["Adicionar mod…", "Remover mod…", "Voltar"])
                idx = self.escolher(f"Mods — {j.get('titulo') or ''}", opcoes)
                if idx is None or opcoes[idx] == "Voltar":
                    self.recarregar()
                    return
                escolha = opcoes[idx]
                if escolha == estado:
                    core.atualizar_jogo(con, j["id"],
                                        {"azahar_mods_off": 0 if off else 1})
                    self.msg = ("Mods ligados ✓" if off
                                else "Mods desligados (lista preservada).")
                elif escolha == "Adicionar mod…":
                    r = self.perguntar("Arquivo (.zip/.7z) ou pasta do mod: ")
                    if not r:
                        continue
                    nome = self.perguntar("Nome do mod (vazio=automático): ")
                    if nome is None:
                        continue
                    res = core.importar_mod(r.strip(), tid, (nome or "").strip())
                    if not res.get("ok"):
                        self.msg = f"Falha: {res.get('erro')}"
                        continue
                    nova = [m for m in disp if m in ativos] + [res["mod"]]
                    core.atualizar_jogo(con, j["id"], {"azahar_mods": nova})
                    self.msg = f"Mod {res['mod']} ✓ ({res['arquivos']} arqs)"
                elif escolha == "Remover mod…":
                    if not disp:
                        self.msg = "Nada para remover."
                        continue
                    idx2 = self.escolher("Remover", [*disp, "Voltar"])
                    if idx2 is None or idx2 >= len(disp):
                        continue
                    alvo = disp[idx2]
                    conf = self.perguntar(f"Apagar '{alvo}' da biblioteca? (s/n): ")
                    if (conf or "").strip().lower() not in ("s", "sim"):
                        continue
                    res = core.remover_mod(tid, alvo)
                    if not res.get("ok"):
                        self.msg = f"Falha: {res.get('erro')}"
                        continue
                    core.atualizar_jogo(
                        con, j["id"],
                        {"azahar_mods": [m for m in ativos if m != alvo]})
                    self.msg = f"Mod {alvo} removido."
                else:
                    pos = next((i for i, m in enumerate(disp)
                                if f"[{'x' if m in ativos else ' '}] {m}" == escolha), None)
                    if pos is None:
                        continue
                    nome = disp[pos]
                    nova = ([m for m in disp if m in ativos and m != nome]
                            + ([nome] if nome not in ativos else []))
                    core.atualizar_jogo(con, j["id"], {"azahar_mods": nova})
        finally:
            con.close()

    def menu_texturas(self, j):
        """Liga/desliga texturas HD (só ROM 3DS com title ID legível)."""
        try:
            launch = core.traduzir_para_atual((j.get("launch_options") or "").strip())
            tid = core.title_id_da_rom(launch)
        except Exception:
            tid = ""
        if not tid:
            self.msg = "Texturas só para ROMs 3DS com title ID legível."
            return
        while True:
            try:
                est = core.estado_textura(tid)
            except Exception:
                est = {"instalado": False, "ativo": False,
                       "arquivos": 0, "mb": 0.0}
            if not est.get("instalado"):
                opcoes = ["Instalar de pasta…", "Voltar"]
            else:
                acao = ("DESLIGAR" if est["ativo"] else "LIGAR")
                opcoes = [f"HD {acao} ({est['arquivos']} arqs)",
                          "Instalar de pasta…", "Voltar"]
            idx = self.escolher(f"Texturas — {j.get('titulo') or ''}", opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                self.recarregar()
                return
            escolha = opcoes[idx]
            if escolha == "Instalar de pasta…":
                r = self.perguntar("Pasta extraída com os .png: ")
                if not r:
                    continue
                res = core.instalar_textura(tid, r.strip())
                self.msg = (f"HD instalado ✓ ({res['arquivos']} arqs)"
                            if res.get("ok") else f"Falha: {res.get('erro')}")
            else:
                res = core.definir_textura(tid, not est["ativo"])
                self.msg = (f"HD {'ligado ✓' if res.get('ativo') else 'desligado.'}"
                            if res.get("ok") else f"Falha: {res.get('erro')}")

    def menu_cheats(self, j):
        """Liga/desliga cheats Gateway (vale após reiniciar o jogo)."""
        try:
            launch = core.traduzir_para_atual((j.get("launch_options") or "").strip())
            tid = core.title_id_da_rom(launch)
        except Exception:
            tid = ""
        if not tid:
            self.msg = "Cheats só para ROMs 3DS com title ID legível."
            return
        while True:
            try:
                disp = core.listar_cheats(tid)
            except Exception:
                disp = []
            ativos = {c["nome"] for c in disp if c["ativo"]}
            opcoes = ([f"[{'x' if c['nome'] in ativos else ' '}] {c['nome']}"
                       for c in disp]
                      + ["Adicionar cheat…", "Remover cheat…", "Voltar"])
            idx = self.escolher(f"Cheats — {j.get('titulo') or ''} (reinicie p/ valer)",
                                opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                self.recarregar()
                return
            escolha = opcoes[idx]
            if escolha == "Adicionar cheat…":
                nome = self.perguntar("Nome do cheat: ")
                if not nome:
                    continue
                linhas = []
                while True:
                    l = self.perguntar(f"Linha {len(linhas) + 1} (vazio termina): ")
                    if l is None or not l.strip():
                        break
                    linhas.append(l)
                if not linhas:
                    continue
                res = core.adicionar_cheat(tid, nome.strip(), "\n".join(linhas))
                self.msg = (f"Cheat {nome.strip()} ✓ (desligado)"
                            if res.get("ok") else f"Falha: {res.get('erro')}")
            elif escolha == "Remover cheat…":
                if not disp:
                    self.msg = "Nada para remover."
                    continue
                idx2 = self.escolher("Remover", [c["nome"] for c in disp]
                                     + ["Voltar"])
                if idx2 is None or idx2 >= len(disp):
                    continue
                alvo = disp[idx2]["nome"]
                conf = self.perguntar(f"Apagar '{alvo}'? (s/n): ")
                if (conf or "").strip().lower() not in ("s", "sim"):
                    continue
                res = core.remover_cheat(tid, alvo)
                self.msg = (f"Cheat {alvo} removido."
                            if res.get("ok") else f"Falha: {res.get('erro')}")
            else:
                pos = next((i for i, c in enumerate(disp)
                            if f"[{'x' if c['nome'] in ativos else ' '}] {c['nome']}"
                            == escolha), None)
                if pos is None:
                    continue
                res = core.alternar_cheat(tid, disp[pos]["nome"])
                self.msg = (f"{disp[pos]['nome']}: "
                            f"{'ligado ✓ (reinicie)' if res.get('ativo') else 'desligado.'}"
                            if res.get("ok") else f"Falha: {res.get('erro')}")

    def menu_principal(self) -> bool:
        """ESC na lista abre as categorias; retorna True se é para sair."""
        opcoes = ["Buscar", "Filtros", "Adicionar jogo", "Importar",
                  "Músicas", "Controles", "Backup e saves", "Sessão",
                  "Emuladores", "Sair"]
        while True:
            idx = self.escolher("TucoTeca", opcoes)
            if idx is None:
                return False
            escolha = opcoes[idx]
            if escolha == "Buscar":
                r = self.perguntar("Buscar: ", self.q)
                if r is not None:
                    self.q = r.strip()
                    self.cur = 0
                    self.recarregar()
            elif escolha == "Filtros":
                self.menu_filtros()
            elif escolha == "Adicionar jogo":
                self.adicionar()
            elif escolha == "Importar":
                self.menu_importar()
            elif escolha == "Músicas":
                self.menu_musicas()
            elif escolha == "Controles":
                self.menu_controles()
            elif escolha == "Backup e saves":
                self.menu_backup()
            elif escolha == "Sessão":
                self.menu_sessao()
            elif escolha == "Emuladores":
                self.menu_emuladores()
            elif escolha == "Sair":
                return True
        return False

    def menu_musicas(self):
        """Catálogo de áudio: buscar, tocar, importar, excluir."""
        con = self._con()
        try:
            q = ""
            while True:
                self._vigiar_player()
                try:
                    itens = core.listar_musicas(con, q=q)
                except Exception:
                    itens = []
                rotulos = [core.texto_musica(m) for m in itens]
                try:
                    at = self.player.atual() if self.player else None
                except Exception:
                    at = None
                titulo = f"Músicas ({len(itens)})"
                if at and (self.player.estado if self.player else "") != "parado":
                    titulo += f" · ♪ {at.get('titulo') or ''}"
                rotulos = [core.texto_musica(m) for m in itens]
                try:
                    n_fila = len(core.listar_downloads(con))
                except Exception:
                    n_fila = 0
                opcoes = (rotulos + ["Buscar…", "Importar de pasta…",
                                     "Baixar de CSV…", f"Fila ({n_fila})…",
                                     "Baixar capas…", "Voltar"])
                idx = self.escolher(titulo, opcoes)
                if idx is None or opcoes[idx] == "Voltar":
                    self.recarregar()
                    return
                escolha = opcoes[idx]
                if escolha == "Buscar…":
                    r = self.perguntar("Buscar música: ", q)
                    if r is not None:
                        q = r.strip()
                elif escolha == "Importar de pasta…":
                    sugest = ""
                    try:
                        sugest = (str(core.harmoni_dir() or "")
                                  or str(core.sugestao_harmoni_dir() or ""))
                    except Exception:
                        pass
                    r = self.perguntar("Pasta de áudio"
                                       + (f" [{sugest}]: " if sugest else ": "))
                    if r is None:
                        continue
                    pasta = (r.strip() or sugest)
                    if not pasta:
                        continue
                    try:
                        res = core.importar_musicas(con, pasta)
                    except Exception as e:
                        res = {"novos": 0, "ignorados": 0, "erros": [str(e)]}
                    detalhe = (f"{res['novos']} nova(s), "
                               f"{res['ignorados']} ignorada(s)")
                    if res["erros"]:
                        detalhe += f" — {res['erros'][0]}"
                    self.msg = detalhe
                elif escolha == "Baixar de CSV…":
                    r = self.perguntar("CSV do Exportify: ")
                    if r is None or not r.strip():
                        continue
                    try:
                        parsed = core.ler_csv_exportify(r.strip())
                    except Exception as e:
                        self.msg = f"Falha: {e}"
                        continue
                    if parsed["erros"] and not parsed["itens"]:
                        self.msg = f"Falha: {parsed['erros'][0]}"
                        continue
                    try:
                        res = core.enfileirar_downloads(con, parsed["itens"])
                    except Exception as e:
                        self.msg = f"Falha: {e}"
                        continue
                    self.msg = (f"{res['novos']} na fila,"
                                f" {res['ignorados']} ignorada(s)")
                elif idx >= len(itens) and escolha.startswith("Fila ("):
                    self.menu_fila(con)
                elif idx >= len(itens) and escolha == "Baixar capas…":
                    try:
                        res = core.baixar_capas_faltantes(con)
                    except Exception as e:
                        self.msg = f"Falha: {e}"
                        continue
                    self.msg = (f"{res['novas']} capa(s),"
                                f" {res['pendentes']} pendente(s)")
                    if res["erros"]:
                        self.msg += f" — {res['erros'][0]}"
                else:
                    pos = idx
                    if 0 <= pos < len(itens):
                        sub = self.escolher(
                            rotulos[pos],
                            ["Tocar", "Pausar/Continuar", "Próxima", "Parar",
                             "Abrir externo", "Excluir", "Voltar"])
                        if sub == 0:
                            r = self._tocar_interno(itens, pos)
                            self.msg = (f"Tocando '{rotulos[pos]}' ✓"
                                        if r.get("ok")
                                        else f"Falha: {r.get('erro')}")
                        elif sub == 1:
                            r = self._alternar_interno()
                            self.msg = (f"{r.get('estado', 'ok')} ✓"
                                        if r.get("ok")
                                        else f"Falha: {r.get('erro')}")
                        elif sub == 2:
                            r = self._proxima_interno()
                            self.msg = (f"Tocando '{r.get('titulo')}' ✓"
                                        if r.get("ok")
                                        else "Fim da fila.")
                        elif sub == 3:
                            self._parar_interno()
                            self.msg = "Parado."
                        elif sub == 4:
                            r = core.tocar_musica(itens[pos].get("musica_path") or "")
                            self.msg = (f"Tocando '{rotulos[pos]}' no player ✓"
                                        " (segue com o jogo aberto)"
                                        if r.get("ok")
                                        else f"Falha: {r.get('erro')}")
                        elif sub == 5:
                            conf = self.perguntar(
                                f"Apagar '{rotulos[pos]}' do Hub? (s/n): ")
                            if (conf or "").strip().lower() in ("s", "sim"):
                                try:
                                    core.excluir_musica(con, itens[pos]["id"])
                                    self.msg = "Música apagada."
                                except (LookupError, ValueError) as e:
                                    self.msg = f"Falha: {e}"
                                    continue
                                try:
                                    at = self.player.atual() \
                                        if self.player else None
                                    if at and at.get("path") == (
                                            itens[pos].get("musica_path")
                                            or ""):
                                        self._parar_interno()
                                except Exception:
                                    pass
        finally:
            con.close()

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

    def menu_fila(self, con):
        """Fila CSV → mp3: estados + limpar (download vem na Fase B)."""
        while True:
            try:
                fila = core.listar_downloads(con)
            except Exception:
                fila = []
            rotulos = []
            for d in fila:
                base = core.texto_musica(d)
                est = d.get("estado") or ""
                extra = (f" — {d.get('erro')}"
                         if est == "falha" and d.get("erro") else "")
                rotulos.append(f"{base} [{est}]{extra}")
            opcoes = rotulos + ["Baixar fila", "Importar baixadas",
                                 "Limpar prontas/falhas", "Voltar"]
            idx = self.escolher(f"Fila ({len(fila)})", opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                return
            if opcoes[idx] == "Baixar fila":
                if not core.localizar_ytdlp():
                    self.msg = core.erro_sem_ytdlp()
                    continue
                alvos = [d for d in fila
                         if d.get("estado") in ("pendente", "falha")]
                if not alvos:
                    self.msg = "Nada pendente."
                    continue
                ok = 0
                for d in alvos:
                    self.msg = f"Baixando {core.texto_musica(d)}…"
                    try:
                        r = core.baixar_faixa(con, d["id"])
                    except Exception as e:
                        r = {"ok": False, "erro": str(e)}
                    ok += 1 if r.get("ok") else 0
                self.msg = f"Baixadas {ok}/{len(alvos)} (Fase C importa)."
                continue
            if opcoes[idx] == "Importar baixadas":
                try:
                    res = core.importar_fila_pronta(con)
                except Exception as e:
                    self.msg = f"Falha: {e}"
                    continue
                self.msg = (f"{res['novas']} nova(s),"
                            f" {res['ignorados']} ignorada(s)")
                if res["erros"]:
                    self.msg += f" — {res['erros'][0]}"
                continue
            if opcoes[idx] == "Limpar prontas/falhas":
                try:
                    n = core.limpar_downloads(con)
                except ValueError as e:
                    self.msg = f"Falha: {e}"
                    continue
                self.msg = f"Fila limpa ({n} removida(s))."
                continue
            pos = idx
            if 0 <= pos < len(fila):
                d = fila[pos]
                det = " · ".join(x for x in (
                    core.texto_musica(d), d.get("estado") or "",
                    d.get("video_id") or "", d.get("erro") or "") if x)
                self.msg = det

    def menu_controles(self):
        """Controles no Hub: listar, testar, fotografar, aplicar, gerar."""
        import time
        while True:
            try:
                pads = core.listar_controles()
            except Exception:
                pads = []
            try:
                presets = core.listar_presets_controle()
            except Exception:
                presets = []
            info = "; ".join(
                f"{p.get('nome') or '?'}"
                f"{' [' + p['familia'] + ']' if p.get('familia') else ''}"
                for p in pads) or "nenhum controle"
            if len(info) > 100:
                info = info[:99] + "…"
            opcoes = [f"Pads: {info}", "Testar apertos (5s)…",
                      "Fotografar perfil do Azahar…", "Aplicar preset…",
                      "Gerar mapa padrão…", "Voltar"]
            idx = self.escolher("Controles (feche o Azahar p/ aplicar)",
                                opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                self.recarregar()
                return
            escolha = opcoes[idx]
            if escolha.startswith("Pads:"):
                continue
            if escolha.startswith("Testar"):
                vistos: set[str] = set()
                t0 = time.monotonic()
                while time.monotonic() - t0 < 5:
                    try:
                        est = core.ler_estado_xinput(0)
                    except Exception:
                        est = None
                    if est:
                        try:
                            vistos.add(core.resumir_estado(est))
                        except Exception:
                            pass
                    time.sleep(0.1)
                vistos.discard("(neutro)")
                self.msg = ("Vistos: " + " | ".join(sorted(vistos))
                            if vistos else "Nada apertado (XInput slot 0).")
            elif escolha.startswith("Fotografar"):
                nome = self.perguntar("Nome do preset: ")
                if not nome:
                    continue
                try:
                    res = core.fotografar_perfil(nome.strip())
                except Exception as e:
                    res = {"ok": False, "erro": str(e)}
                self.msg = (f"Preset {res['preset']} ✓" if res.get("ok")
                            else f"Falha: {res.get('erro')}")
            elif escolha.startswith("Aplicar"):
                if not presets:
                    self.msg = "Sem presets (fotografe ou gere um)."
                    continue
                idx2 = self.escolher("Aplicar", presets + ["Voltar"])
                if idx2 is None or idx2 >= len(presets):
                    continue
                try:
                    res = core.aplicar_preset_controle(presets[idx2])
                except Exception as e:
                    res = {"ok": False, "erro": str(e)}
                self.msg = (f"{res.get('chaves', 0)} binds no Azahar ✓"
                            if res.get("ok")
                            else f"Falha: {res.get('erro')}")
            elif escolha.startswith("Gerar"):
                try:
                    tipos = sorted(core.NOMES_TIPO.items())
                except Exception:
                    continue
                rot = [f"{t} — {core.NOMES_TIPO[t]}" for t, _ in tipos]
                idx2 = self.escolher("Tipo", rot + ["Voltar"])
                if idx2 is None or idx2 >= len(tipos):
                    continue
                tipo = tipos[idx2][0]
                guid, port, rotulos = "", 0, {}
                try:
                    det = core.detectar_sdl()
                    if det:
                        guid, port = det[0]["guid"], det[0]["port"]
                    rotulos = core.nomes_sdl()
                except Exception:
                    pass
                try:
                    res = core.salvar_mapa_gerado(
                        tipo, guid=guid, port=port, nome=f"{tipo}-hub",
                        rotulos=rotulos)
                except ValueError as e:
                    res = {"ok": False, "erro": str(e)}
                if not res.get("ok"):
                    self.msg = f"Falha: {res.get('erro')}"
                    continue
                self.msg = (f"Preset {res['preset']} ✓ "
                            f"({res['chaves']} binds) — aplique p/ usar.")

    def menu_filtros(self):
        while True:
            opcoes = [
                f"Status: {self.statuses[self.si] or 'todos'}",
                f"Favoritos: {'sim' if self.fav else 'não'}",
                f"Provider: {self.filtro_prov or 'todos'}",
                f"Plataforma: {self.filtro_plat or 'todas'}",
                f"Etiquetas: {', '.join(self.filtro_tags) or '—'}",
                "Limpar filtros",
                "Voltar",
            ]
            idx = self.escolher("Filtros", opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                return
            escolha = opcoes[idx]
            if escolha.startswith("Status:"):
                self.si = (self.si + 1) % len(self.statuses)
                self.cur = 0
                self.recarregar()
            elif escolha.startswith("Favoritos:"):
                self.fav = not self.fav
                self.cur = 0
                self.recarregar()
            elif escolha.startswith("Provider:"):
                chaves = [None, *core.provedores()]
                i = chaves.index(self.filtro_prov) if self.filtro_prov in chaves else 0
                self.filtro_prov = chaves[(i + 1) % len(chaves)]
                self.cur = 0
                self.recarregar()
                self.msg = f"Filtro prov: {self.filtro_prov or 'todos'}."
            elif escolha.startswith("Plataforma:"):
                plats = [None, "PC", "3DS", "NDS"]
                i = plats.index(self.filtro_plat) if self.filtro_plat in plats else 0
                self.filtro_plat = plats[(i + 1) % len(plats)]
                self.cur = 0
                self.recarregar()
                self.msg = f"Filtro plataforma: {self.filtro_plat or 'todas'}."
            elif escolha.startswith("Etiquetas:"):
                r = self.perguntar("Filtrar etiquetas (vírgula=vazio limpa): ",
                                   ", ".join(self.filtro_tags))
                if r is not None:
                    self.filtro_tags = [t.strip() for t in
                                        r.replace(";", ",").split(",") if t.strip()]
                    self.cur = 0
                    self.recarregar()
            elif escolha == "Limpar filtros":
                self.si = 0
                self.fav = False
                self.filtro_prov = None
                self.filtro_plat = None
                self.filtro_tags = []
                self.cur = 0
                self.recarregar()
                self.msg = "Filtros limpos."

    def menu_importar(self):
        opcoes = ["Arquivo (exe, ROM, JSON, .zip, repack)", "Pasta", "Disco (Hydra/lojas)",
                  "Voltar"]
        while True:
            idx = self.escolher("Importar", opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                return
            escolha = opcoes[idx]
            if escolha.startswith("Arquivo"):
                arq = self.perguntar("Arquivo (exe, ROM, JSON, .zip, repack): ")
                if arq:
                    self._importar_arquivo(arq.strip())
            elif escolha == "Pasta":
                r = self.perguntar("Pasta (; separadas, vazio=tudo): ")
                if r is None:
                    continue
                roots = [x.strip() for x in r.split(";") if x.strip()] or None
                self._prev_pasta(roots)
            elif escolha.startswith("Disco"):
                self._prev_disco()

    def menu_backup(self):
        opcoes = ["Backup do banco", "Backup saves 3DS", "Exportar JSON",
                  "Exportar pacote", "Importar pacote", "Voltar"]
        while True:
            idx = self.escolher("Backup e saves", opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                return
            escolha = opcoes[idx]
            if escolha == "Backup do banco":
                self.backup()
            elif escolha == "Backup saves 3DS":
                self.backup_saves()
            elif escolha == "Exportar JSON":
                self.exportar_json()
            elif escolha == "Exportar pacote":
                self.exportar_pacote()
            elif escolha == "Importar pacote":
                arq = self.perguntar("Pacote .zip: ")
                if arq:
                    self.importar_pacote(arq.strip())

    def menu_sessao(self):
        opcoes = ["Registrar sessão manual", "Voltar"]
        while True:
            idx = self.escolher("Sessão", opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                return
            self.registrar_sessao_manual()

    def menu_emuladores(self):
        opcoes = ["Atualizar Azahar", "Atualizar DeSmuME", "Voltar"]
        while True:
            idx = self.escolher("Emuladores", opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                return
            if opcoes[idx] == "Atualizar Azahar":
                self.atualizar_azahar()
            elif opcoes[idx] == "Atualizar DeSmuME":
                self.atualizar_desmume()

    def _aplicar_sessoes(self):
        """Drena a fila de sessões sem trocar sua referência na thread vigia."""
        pend = []
        while True:
            try:
                pend.append(self.sessoes_pendentes.get_nowait())
            except Empty:
                break
        if not pend:
            return
        con = self._con()
        try:
            msgs = []
            for gid, sessao, rastreado in pend:
                if not rastreado:
                    continue
                if sessao <= 0:
                    msgs.append("sessão curta: nada registrado")
                    continue
                r = core.adicionar_horas(con, gid, sessao)
                msgs.append(f"+{r['somado']}h (total {r['total']}h)"
                            if r.get("ok") else f"sessão: {r.get('erro')}")
            if msgs:
                self.msg = " · ".join(msgs)
                self.recarregar()
        finally:
            con.close()

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

    def _avisar_preset(self, dados: dict) -> None:
        pres = [(dados.get("azahar_preset") or "").strip()]
        pres = [p for p in pres if p]
        if not pres:
            return
        try:
            todos = set()
            for chave in core.provedores():
                todos |= set(core.listar_presets(chave))
        except Exception:
            return
        for pre in pres:
            if pre not in todos:
                self.msg = f"Preset '{pre}' não existe (play ignora; foto na GUI)."
                return

    def adicionar(self):
        dados = self.formulario(None)
        if not dados:
            return
        con = self._con()
        try:
            try:
                core.criar_jogo(con, dados)
                self.msg = "Salvo ✓"
                self._avisar_preset(dados)
            except ValueError as e:
                self.msg = f"Erro: {e}"
        finally:
            con.close()
        self.recarregar()

    def editar(self):
        j = self.atual()
        if not j:
            return
        dados = self.formulario(j)
        if not dados:
            return
        con = self._con()
        try:
            try:
                core.atualizar_jogo(con, j["id"], dados)
                self.msg = "Salvo ✓"
                self._avisar_preset(dados)
            except (ValueError, LookupError) as e:
                self.msg = f"Erro: {e}"
        finally:
            con.close()
        self.recarregar()

    def excluir(self):
        j = self.atual()
        if not j:
            return
        if not self.confirmar(f"Excluir '{j['titulo']}'?"):
            return
        con = self._con()
        try:
            try:
                core.excluir_jogo(con, j["id"])
                self.msg = "Excluído."
            except LookupError as e:
                self.msg = f"Erro: {e}"
        finally:
            con.close()
        self.recarregar()

    def _backup_pre_import(self):
        core.backup_pre_import(self.db_path)

    def tela_prev(self, titulo: str, itens: list[dict]):
        if not itens:
            self.msg = "Nada encontrado."
            return
        s = self.stdscr
        marcados = {i for i, it in enumerate(itens) if it.get("score", 0) >= 0.3}
        cur = 0
        while True:
            s.erase()
            rows, cols = s.getmaxyx()
            if rows < 4 or cols < 10:
                try:
                    s.addnstr(0, 0, "Terminal pequeno demais (min 10x4).", max(1, cols - 1))
                    s.refresh()
                    s.getch()
                except Exception:
                    pass
                return
            larg = max(1, cols - 1)
            s.addnstr(0, 0, f"{titulo} — Espaço marca · i importa · q volta"[:larg],
                      larg, self.cor["head"] | self.abold)
            area = rows - 2
            top = max(0, min(cur - area + 1, max(0, len(itens) - area)))
            if cur < top:
                top = cur
            for i in range(area):
                idx = top + i
                if idx >= len(itens):
                    break
                it = itens[idx]
                chk = "[x]" if idx in marcados else "[ ]"
                bola = "●" if it.get("exe_existe") else "○"
                tag = f" [{it['regiao']}]" if it.get("regiao") else ""
                shop = f" · {it['shop']}" if it.get("shop") else ""
                linha = f"{chk} {bola} [{it.get('score', 0):.2f}] {it['titulo']}{tag}{shop} ({it.get('fonte') or it['origem']})"
                linha = linha.ljust(larg)[:larg]
                if idx == cur:
                    attr = self.cor["acc"] | self.abold
                elif it.get("score", 0) >= 0.7:
                    attr = self.cor["ok"]
                elif it.get("score", 0) >= 0.3:
                    attr = self.cor["txt"]
                else:
                    attr = self.cor["ruim"]
                s.addnstr(1 + i, 0, linha, larg, attr)
            s.addnstr(rows - 1, 0, f"{len(marcados)} marcado(s) de {len(itens)}"[:larg],
                      larg, self.cor["mut"] | self.adim)
            s.refresh()
            ch = s.getch()
            if ch in (ord("q"), 27):
                return
            elif ch in (curses.KEY_UP, ord("k")):
                cur = max(0, cur - 1)
            elif ch in (curses.KEY_DOWN, ord("j")):
                cur = min(len(itens) - 1, cur + 1)
            elif ch == curses.KEY_PPAGE:
                cur = max(0, cur - 10)
            elif ch == curses.KEY_NPAGE:
                cur = min(len(itens) - 1, cur + 10)
            elif ch == ord(" "):
                if cur in marcados:
                    marcados.discard(cur)
                else:
                    marcados.add(cur)
            elif ch == ord("i"):
                if not marcados:
                    continue
                sel = [itens[i] for i in sorted(marcados)]
                self._backup_pre_import()
                con = self._con()
                try:
                    res = core.importar_lista(con, sel)
                finally:
                    con.close()
                self.msg = core.resumo_importacao(res).replace("\n", " · ")
                self.recarregar()
                return

    def _prev_disco(self):
        self.msg = "Lendo Hydra, lojas e programas (só leitura)..."
        self.desenhar()
        try:
            itens, info = core.ler_do_disco()
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        partes = [f"{f['fonte']}: {f['n']}" for f in info["fontes"]
                  if f["ok"] and f["n"]]
        falhas = [f"{f['fonte']}: {f.get('detalhe') or 'falha'}" for f in info["fontes"]
                  if not f["ok"]]
        sub = f"Disco: {len(itens)} achado(s) ({'; '.join(partes) or 'nada'})"
        if falhas:
            sub += f" [falhas: {'; '.join(falhas)}]"
        self.tela_prev(sub, itens)

    def _prev_pasta(self, roots):
        self.msg = "Varrendo (só leitura)..."
        self.desenhar()
        try:
            _ru, itens, info = core.preview_pasta(roots)
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        sub = f"Pasta: {len(itens)} achado(s)"
        if info.get("truncado"):
            sub += f" (PARCIAL: {info.get('vistos', 0)} vistos — refine a pasta)"
        if not info.get("emu"):
            sub += " [Azahar ausente: ROMs importam; instale com A]"
        self.tela_prev(sub, itens)

    def _importar_arquivo(self, arq: str):
        ana = core.analisar_arquivo(arq)
        tipo = ana["tipo"]
        if tipo == "pasta":
            self._prev_pasta([arq])
        elif tipo == "json":
            self.importar_json(arq)
        elif tipo == "pacote":
            self.importar_pacote(arq)
        elif tipo == "arquivo-jogo":
            self._backup_pre_import()
            con = self._con()
            try:
                res = core.importar_repack(con, arq)
            except Exception as e:
                res = {"ok": False, "erro": f"{type(e).__name__}: {e}"}
            finally:
                con.close()
            if not res.get("ok"):
                detalhe = res["erro"]
                if res.get("precisa_instalar"):
                    detalhe += " (rode o setup na pasta e importe a pasta.)"
                self.msg = detalhe
            elif res.get("novos"):
                self.msg = f"'{res['titulo']}' ✓ em {res['pasta']}"
                if res.get("capa_auto"):
                    self.msg += " + capa ✓"
                if res.get("capa_pendente"):
                    self.msg += " (sem capa: ajuste na GUI)."
            else:
                self.msg = "Já estava na biblioteca (nada novo)."
            self.recarregar()
        elif tipo in ("rom", "jogo"):
            if ana.get("aviso") and not self.confirmar(f"{ana['aviso']} Importar?"):
                return
            self._backup_pre_import()
            con = self._con()
            try:
                res = core.importar_lista(con, [ana["item"]])
            finally:
                con.close()
            if res["novos"]:
                self.msg = f"{ana['detalhe']} ✓"
            else:
                self.msg = "Já estava na biblioteca (nada novo)."
            self.recarregar()
        else:
            self.msg = ana["detalhe"] or "não suportado."

    def backup(self):
        try:
            res = core.fazer_backup(self.db_path)
            self.msg = f"Backup ok: {res['jogos']} jogo(s)"
        except Exception as e:
            self.msg = f"Backup falhou: {e}"

    def backup_saves(self):
        try:
            res = core.backup_saves_azahar()
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        if res.get("ok"):
            self.msg = f"Saves ok: {res['arquivos']} arquivo(s)"
        else:
            self.msg = f"Saves: {res.get('erro')}"

    def exportar_json(self):
        dest = self.perguntar("Exportar para (caminho .json): ")
        if not dest:
            return
        dest = dest.strip()
        try:
            res = core.exportar_json(dest, db_path=self.db_path)
        except Exception as e:
            self.msg = f"Falha ao gravar: {e}"
            return
        if not res.get("ok"):
            self.msg = f"Falha ao gravar: {res.get('erro')}"
            return
        self.msg = f"Exportados {res['jogos']} jogo(s)."

    def importar_json(self, arq: str | None = None):
        if not arq:
            arq = self.perguntar("Importar de (JSON ou pacote .zip): ")
            if not arq:
                return
            arq = arq.strip()
        if arq.lower().endswith(".zip") and core.eh_pacote_hub(arq):
            self.importar_pacote(arq)
            return
        if arq.lower().endswith(".zip"):
            self._importar_arquivo(arq)
            return
        try:
            dados = json.loads(Path(arq).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            self.msg = f"JSON inválido: {e}"
            return
        lista = dados if isinstance(dados, list) else dados.get("jogos", [])
        if not isinstance(lista, list):
            self.msg = "JSON deve ser lista ou {jogos:[...]}."
            return
        self._backup_pre_import()
        con = self._con()
        try:
            res = core.importar_lista(con, lista)
        finally:
            con.close()
        self.msg = core.resumo_importacao(res).replace("\n", " · ")
        self.recarregar()

    def exportar_pacote(self):
        dest = self.perguntar("Pacote (.zip) destino: ",
                              str(core.BACKUP_DIR / "biblioteca-pacote.zip"))
        if not dest:
            return
        try:
            res = core.exportar_pacote(dest.strip(), db_path=self.db_path,
                                       incluir_saves=True)
        except Exception as e:
            self.msg = f"Pacote falhou: {e}"
            return
        if not res.get("ok"):
            self.msg = f"Pacote: {res.get('erro')}"
            return
        kb = res["bytes"] // 1024
        self.msg = (f"Pacote: {res['jogos']} jogo(s), {res['arquivos']} arq, "
                    f"{kb} KB{' +saves' if res['inclui_saves'] else ''}.")

    def importar_pacote(self, arq: str):
        try:
            res = core.importar_pacote(
                arq, db_path=self.db_path,
                restaurar_saves=self.confirmar("Restaurar os saves do pacote?"))
        except Exception as e:
            self.msg = f"Pacote falhou: {e}"
            return
        if not res.get("ok"):
            self.msg = f"Pacote: {res.get('erro')}"
            return
        self.msg = (core.resumo_importacao(res).replace("\n", " · ") + " · " +
                    f"capas {res['capas']} · presets {res['presets']} · "
                    f"saves {res['saves']}")
        self.recarregar()

    def atualizar_azahar(self):
        self.atualizar_emu("azahar")

    def atualizar_desmume(self):
        self.atualizar_emu("desmume")

    def atualizar_emu(self, chave: str):
        try:
            prov = core.provedores()[chave]
        except KeyError:
            self.msg = f"Provider '{chave}' desconhecido."
            return
        nome = prov["nome"]
        self.msg = "Consultando releases..."
        self.desenhar()
        try:
            info = prov["release_info"]()
        except Exception as e:
            self.msg = f"{nome}: falha de rede ({type(e).__name__}: {e})"
            return
        if info.get("erro"):
            self.msg = f"{nome}: {info['erro']}"
            return
        local, tag = prov["versao_local"](), info.get("tag") or "?"
        if local and local == tag:
            self.msg = f"{nome} já está na {tag} ✓"
            return
        mb = round((info.get("size") or 0) / 1048576)
        if not self.confirmar(f"{nome} {local or '?'} -> {tag} (~{mb} MB). Baixar?"):
            return
        self.msg = "Baixando e instalando (aguarde)..."
        self.desenhar()
        try:
            res = prov["instalar"](info, progresso=self._prog_azahar)
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        if res.get("ok"):
            self.msg = f"{res.get('tag')} instalado ✓"
        else:
            self.msg = f"Falha: {res.get('erro')}"
        self.recarregar()

    def _prog_azahar(self, feito, total):
        self.msg = f"Baixando... {feito // 1048576} MB"
        if total:
            self.msg += f" / {total // 1048576} MB"
        try:
            self.desenhar()
        except Exception:
            pass

    # -- loop
    def rodar(self):
        s = self.stdscr
        try:
            s.timeout(500)  # getch não-bloqueante: sessões aplicam sem tecla
        except Exception:
            pass
        self._verificar_pendencias_inicio()
        while True:
            self._aplicar_sessoes()
            self.desenhar()
            try:
                ch = s.getch()
            except Exception:
                ch = -1
            if ch == -1:
                continue  # timeout: só drenou sessões e redesenhou
            if ch in (ord("q"),):
                antes = self.msg  # desenhar consome; guarda p/ exibir após sair
                self._aplicar_sessoes()  # vigia pode ter encerrado no último instante
                self.msg_final = self.msg or antes
                return
            elif ch in (curses.KEY_DOWN, ord("j")):
                self.cur = min(len(self.jogos) - 1, self.cur + 1) if self.jogos else 0
            elif ch in (curses.KEY_UP, ord("k")):
                self.cur = max(0, self.cur - 1)
            elif ch == curses.KEY_NPAGE:
                self.cur = min(len(self.jogos) - 1, self.cur + 10) if self.jogos else 0
            elif ch == curses.KEY_PPAGE:
                self.cur = max(0, self.cur - 10)
            elif ch == 27:
                if self.menu_principal():
                    antes = self.msg
                    self._aplicar_sessoes()
                    self.msg_final = self.msg or antes
                    return
            elif ch in (curses.KEY_ENTER, 10, 13):
                self.menu_jogo()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="TucoTeca — terminal (curses)")
    ap.add_argument("--db", default=str(core.DEFAULT_DB))
    ap.add_argument("--ignorar-lock", action="store_true",
                    help="abre mesmo com lock de outra instância (após crash)")
    ap.add_argument("--selftest", action="store_true",
                    help="monta o TUI sem terminal e sai (verificação)")
    args = ap.parse_args(argv)
    if curses is None:
        print("curses indisponível neste Python (no Windows, use app_win.py).",
              file=sys.stderr)
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
        app.rodar()
        return getattr(app, "msg_final", "")

    msg_final = curses.wrapper(_run)
    core.liberar_lock()
    if msg_final:
        print(msg_final)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
