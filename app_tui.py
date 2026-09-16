#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minha Biblioteca de Jogos — aplicativo de terminal (curses, stdlib).
Alvo principal: Linux. Mesmo banco e mesmas regras da GUI Windows.

Uso:
    python app_tui.py [--db ~/.../biblioteca.db]

Teclas (lista): ↑/↓ ou j/k navegar · PgUp/PgDn · / buscar · f status ·
  * favoritos · Enter jogar · a adicionar · e editar · d excluir ·
  h preview Hydra · s scan disco · R ROMs 3DS · b backup · U saves 3DS ·
  E exportar JSON · I importar JSON · A atualizar Azahar ·
  r recarregar · q sair
Preview: Espaço marca/desmarca · i importa marcados · q volta
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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
        self.msg = ""
        self._cores()
        self.recarregar()

    # -- base
    def _cores(self):
        try:
            curses.curs_set(0)
        except Exception:
            pass
        self.cor = {"txt": 0, "mut": 0, "acc": 0, "ok": 0, "ruim": 0}
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(3, curses.COLOR_GREEN, -1)
            curses.init_pair(4, curses.COLOR_RED, -1)
            self.cor = {"txt": 0, "mut": curses.color_pair(1),
                        "acc": curses.color_pair(2), "ok": curses.color_pair(3),
                        "ruim": curses.color_pair(4)}

    def _con(self):
        return core.get_db(self.db_path)

    def recarregar(self):
        con = self._con()
        try:
            self.jogos = core.listar_jogos(
                con, q=self.q, status=self.statuses[self.si], favorito=self.fav)
        finally:
            con.close()
        self.cur = max(0, min(self.cur, max(0, len(self.jogos) - 1)))
        self.top = max(0, min(self.top, max(0, len(self.jogos) - 1)))

    # -- desenho
    def linha_jogo(self, j: dict) -> str:
        marca = "●" if j["exe_existe"] else ("○" if j["executable_path"] else "–")
        estrela = "★ " if j["favorito"] else ""
        horas = f" {j['horas']}h" if j["horas"] else ""
        nota = f" n{j['nota']}" if j.get("nota") is not None else ""
        reg = f" · {j['regiao']}" if j.get("regiao") else ""
        return f"{marca} {estrela}{j['titulo']} [{j['status']}]{horas}{nota}{reg}"

    def desenhar(self):
        s = self.stdscr
        s.erase()
        rows, cols = s.getmaxyx()
        titulo = "🎮 Biblioteca  │  / busca · f status · * fav · Enter joga · a/e/d · h hydra · s scan · R roms · b/U/E/I/A · q sai"
        s.addnstr(0, 0, titulo, cols - 1, self.cor["mut"])
        az = core.azahar_status()
        azg = "🎮✓" if az["instalado"] and az["chaves"] else ("🎮!" if az["instalado"] else "🎮✗")
        filtro = f"busca='{self.q}' status={self.statuses[self.si] or 'todos'} fav={'sim' if self.fav else 'não'} {azg}"
        s.addnstr(1, 0, f"{filtro} — {len(self.jogos)} jogo(s)", cols - 1, self.cor["mut"])
        area = rows - 4
        if self.cur < self.top:
            self.top = self.cur
        if self.cur >= self.top + area:
            self.top = self.cur - area + 1
        for i in range(area):
            idx = self.top + i
            if idx >= len(self.jogos):
                break
            attr = self.cor["acc"] if idx == self.cur else self.cor["txt"]
            s.addnstr(2 + i, 0, self.linha_jogo(self.jogos[idx]), cols - 1, attr)
        if self.jogos and rows >= 4:
            j = self.jogos[self.cur]
            exe = j["exe_traduzido"] or j["executable_path"] or "(sem executável)"
            s.addnstr(rows - 2, 0, exe[: cols - 1], cols - 1, self.cor["mut"])
        if self.msg:
            s.addnstr(rows - 1, 0, self.msg[: cols - 1], cols - 1, self.cor["ok"])
            self.msg = ""
        s.refresh()

    # -- entrada
    def perguntar(self, prompt: str, inicial: str = "") -> str | None:
        s = self.stdscr
        rows, cols = s.getmaxyx()
        s.addnstr(rows - 1, 0, prompt[: cols - 1], cols - 1, self.cor["mut"])
        s.refresh()
        curses.echo()
        try:
            raw = s.getstr(rows - 1, min(len(prompt), cols - 1), 500)
        except KeyboardInterrupt:
            return None
        finally:
            curses.noecho()
        try:
            txt = raw.decode("utf-8", errors="replace")
        except Exception:
            return None
        if txt == "\x1b":  # ESC cancela
            return None
        if txt == "" and inicial:
            return inicial
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
        if not j["executable_path"]:
            self.msg = "Jogo sem executável cadastrado."
            return
        con = self._con()
        try:
            res = core.executar_jogo_dict(j)
            if res.get("requer_elevacao") and self.confirmar("Exige administrador. Elevar?"):
                res = core.executar_jogo_dict(j, elevar=True)
            if res.get("ok"):
                core.marcar_execucao(con, j["id"])
                self.msg = f"Executando ✓ ({res.get('modo')})"
            else:
                self.msg = f"Falha: {res.get('erro')}"
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
            "wine_prefix": self.perguntar("Wine prefix (Linux): ",
                                          j["wine_prefix"] if j else ""),
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
                "wine_prefix": (vals["wine_prefix"] or "").strip(),
                "observacoes": (vals["observacoes"] or "").strip(),
            }
        except (TypeError, ValueError):
            self.msg = "Nota/horas inválidos. Cancelado."
            return None

    def adicionar(self):
        dados = self.formulario(None)
        if not dados:
            return
        con = self._con()
        try:
            try:
                core.criar_jogo(con, dados)
                self.msg = "Salvo ✓"
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

    def tela_prev(self, titulo: str, itens: list[dict]):
        if not itens:
            self.msg = "Nada encontrado."
            return
        s = self.stdscr
        marcados = {i for i, it in enumerate(itens) if it["score"] >= 0.3}
        cur = 0
        while True:
            s.erase()
            rows, cols = s.getmaxyx()
            s.addnstr(0, 0, f"{titulo} — Espaço marca · i importa · q volta",
                      cols - 1, self.cor["mut"])
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
                bola = "●" if it["exe_existe"] else "○"
                tag = f" [{it['regiao']}]" if it.get("regiao") else ""
                linha = f"{chk} {bola} [{it['score']:.2f}] {it['titulo']}{tag} ({it['origem']})"
                attr = self.cor["acc"] if idx == cur else self.cor["txt"]
                s.addnstr(1 + i, 0, linha, cols - 1, attr)
            s.addnstr(rows - 1, 0, f"{len(marcados)} marcado(s) de {len(itens)}",
                      cols - 1, self.cor["mut"])
            s.refresh()
            ch = s.getch()
            if ch in (ord("q"), 27):
                return
            elif ch in (curses.KEY_UP, ord("k")):
                cur = max(0, cur - 1)
            elif ch in (curses.KEY_DOWN, ord("j")):
                cur = min(len(itens) - 1, cur + 1)
            elif ch == ord(" "):
                if cur in marcados:
                    marcados.discard(cur)
                else:
                    marcados.add(cur)
            elif ch == ord("i"):
                if not marcados:
                    continue
                sel = [itens[i] for i in sorted(marcados)]
                con = self._con()
                try:
                    res = core.importar_lista(con, sel)
                finally:
                    con.close()
                self.msg = f"Importados {res['novos']} (total {res['total_no_banco']})"
                self.recarregar()
                return

    def prev_hydra(self):
        db, itens = core.preview_hydra()
        if db is None:
            self.msg = "hydra-db não encontrado neste PC."
            return
        self.tela_prev(f"Hydra: {len(itens)} achado(s)", itens)

    def prev_scan(self):
        r = self.perguntar("Raízes (; separadas, vazio=padrão): ")
        if r is None:
            return
        roots = [x.strip() for x in r.split(";") if x.strip()] or None
        self.msg = "Varrendo disco (só leitura)..."
        self.desenhar()
        _roots_u, itens, info = core.preview_scan(roots)
        sub = f"Disco: {len(itens)} achado(s)"
        if info.get("truncado"):
            sub += " (PARCIAL: teto de varredura)"
        self.tela_prev(sub, itens)

    def prev_roms(self):
        emu = self.perguntar(f"Emulador (vazio={core.default_emu_3ds() or 'auto'}): ")
        if emu is None:
            return
        emu = emu.strip() or None
        r = self.perguntar("Raízes (; separadas, vazio=padrão): ")
        if r is None:
            return
        roots = [x.strip() for x in r.split(";") if x.strip()] or None
        self.msg = "Procurando ROMs (só leitura)..."
        self.desenhar()
        _ru, itens, info, emu_u = core.preview_roms(roots, emu)
        sub = f"ROMs: {len(itens)} achado(s) [{emu_u or 'sem emu'}]"
        if info.get("truncado"):
            sub += " (PARCIAL)"
        self.tela_prev(sub, itens)

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
        con = self._con()
        try:
            jogos = core.listar_jogos(con)
            dados = {"exportado_em": core.agora_iso(), "jogos": jogos}
        finally:
            con.close()
        try:
            Path(dest).write_text(json.dumps(dados, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
        except OSError as e:
            self.msg = f"Falha ao gravar: {e}"
            return
        self.msg = f"Exportados {len(jogos)} jogo(s)."

    def importar_json(self):
        arq = self.perguntar("Importar JSON de: ")
        if not arq:
            return
        try:
            dados = json.loads(Path(arq.strip()).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            self.msg = f"JSON inválido: {e}"
            return
        lista = dados if isinstance(dados, list) else dados.get("jogos", [])
        if not isinstance(lista, list):
            self.msg = "JSON deve ser lista ou {jogos:[...]}."
            return
        con = self._con()
        try:
            res = core.importar_lista(con, lista)
        finally:
            con.close()
        self.msg = f"Novos: {res['novos']} (total {res['total_no_banco']})."
        self.recarregar()

    def atualizar_azahar(self):
        self.msg = "Consultando releases..."
        self.desenhar()
        info = core.azahar_release_info()
        if info.get("erro"):
            self.msg = f"Azahar: {info['erro']}"
            return
        local, tag = core.azahar_versao_local(), info.get("tag") or "?"
        if local and local == tag:
            self.msg = f"Azahar já está na {tag} ✓"
            return
        mb = round((info.get("size") or 0) / 1048576)
        if not self.confirmar(f"Azahar {local or '?'} -> {tag} (~{mb} MB). Baixar?"):
            return
        self.msg = "Baixando e instalando (aguarde)..."
        self.desenhar()
        try:
            res = core.azahar_instalar(info, progresso=self._prog_azahar)
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
        while True:
            self.desenhar()
            ch = s.getch()
            if ch in (ord("q"),):
                return
            elif ch in (curses.KEY_DOWN, ord("j")):
                self.cur = min(len(self.jogos) - 1, self.cur + 1) if self.jogos else 0
            elif ch in (curses.KEY_UP, ord("k")):
                self.cur = max(0, self.cur - 1)
            elif ch == curses.KEY_NPAGE:
                self.cur = min(len(self.jogos) - 1, self.cur + 10) if self.jogos else 0
            elif ch == curses.KEY_PPAGE:
                self.cur = max(0, self.cur - 10)
            elif ch == ord("/"):
                r = self.perguntar("Buscar: ", self.q)
                if r is not None:
                    self.q = r.strip()
                    self.cur = 0
                    self.recarregar()
            elif ch == ord("f"):
                self.si = (self.si + 1) % len(self.statuses)
                self.cur = 0
                self.recarregar()
            elif ch == ord("*"):
                self.fav = not self.fav
                self.cur = 0
                self.recarregar()
            elif ch in (curses.KEY_ENTER, 10, 13):
                self.jogar()
            elif ch == ord("a"):
                self.adicionar()
            elif ch == ord("e"):
                self.editar()
            elif ch == ord("d"):
                self.excluir()
            elif ch == ord("h"):
                self.prev_hydra()
            elif ch == ord("s"):
                self.prev_scan()
            elif ch == ord("R"):
                self.prev_roms()
            elif ch == ord("b"):
                self.backup()
            elif ch == ord("U"):
                self.backup_saves()
            elif ch == ord("E"):
                self.exportar_json()
            elif ch == ord("I"):
                self.importar_json()
            elif ch == ord("A"):
                self.atualizar_azahar()
            elif ch == ord("r"):
                self.recarregar()
                self.msg = "Recarregado."


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Minha Biblioteca de Jogos — terminal (curses)")
    ap.add_argument("--db", default=str(core.DEFAULT_DB))
    args = ap.parse_args(argv)
    if curses is None:
        print("curses indisponível neste Python (no Windows, use app_win.py).",
              file=sys.stderr)
        return 2
    core.garantir_dirs()
    core.get_db(Path(args.db)).close()
    try:
        cols = int(__import__("shutil").get_terminal_size().columns)
        rows = int(__import__("shutil").get_terminal_size().lines)
    except Exception:
        cols, rows = 80, 24
    if rows < 10 or cols < 60:
        print(f"terminal pequeno ({cols}x{rows}); use ao menos 60x10.", file=sys.stderr)
        return 2

    def _run(stdscr):
        Tui(stdscr, Path(args.db)).rodar()

    curses.wrapper(_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
