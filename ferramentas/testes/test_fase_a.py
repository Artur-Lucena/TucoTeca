"""Fase A: wine preservado, quit aplica sessões, erros.log, lambdas sanados."""
import os
import tempfile
from pathlib import Path

import bib_core as core
from executar import afirmar

REPO = Path(__file__).resolve().parent.parent.parent


def _nova_db():
    tmp = Path(tempfile.mkdtemp(prefix="suite-a-"))
    db = tmp / "t.db"
    return core.get_db(db), tmp


def teste_wine_omitido_preserva():
    """Contrato que o salvar da GUI usa: chave ausente em dados = mantém."""
    con, _tmp = _nova_db()
    try:
        gid = core.criar_jogo(con, {"titulo": "W", "executable_path": "",
                                    "status": "backlog",
                                    "wine_prefix": "/ Bless/prefix"})["id"]
        core.atualizar_jogo(con, gid, {"nota": 9})  # sem wine_prefix
        row = con.execute("SELECT wine_prefix, nota FROM jogos WHERE id=?",
                          (gid,)).fetchone()
        afirmar(row["wine_prefix"] == "/ Bless/prefix", dict(row))
        afirmar(row["nota"] == 9, dict(row))
    finally:
        con.close()


def teste_wine_explicito_troca():
    con, _tmp = _nova_db()
    try:
        gid = core.criar_jogo(con, {"titulo": "W", "executable_path": "",
                                    "status": "backlog"})["id"]
        core.atualizar_jogo(con, gid, {"wine_prefix": "/novo"})
        row = con.execute("SELECT wine_prefix FROM jogos WHERE id=?",
                          (gid,)).fetchone()
        afirmar(row["wine_prefix"] == "/novo", dict(row))
    finally:
        con.close()


def teste_quit_aplica_sessoes():
    import app_tui as tui

    class FakeScr:
        injetado = False

        def getmaxyx(self):
            return (24, 80)

        def addnstr(self, *a):
            pass

        def erase(self):
            pass

        def refresh(self):
            pass

        def getch(self):
            # a vigia encerra DURANTE o getch: sem o fix do quit, perdia
            if not FakeScr.injetado:
                FakeScr.injetado = True
                t.sessoes_pendentes.put((gid, 1.5, True))
            return ord("q")

    class FakeCurses:
        COLOR_CYAN = COLOR_BLACK = COLOR_GREEN = COLOR_RED = 1

        def curs_set(self, *a):
            pass

        def has_colors(self):
            return False

    tui.curses = FakeCurses()
    tmp = Path(tempfile.mkdtemp(prefix="suite-aq-"))
    db = tmp / "u.db"
    t = tui.Tui(FakeScr(), db)
    con = core.get_db(db)
    try:
        gid = core.criar_jogo(con, {"titulo": "Q", "executable_path": "",
                                    "status": "backlog"})["id"]
    finally:
        con.close()
    t.rodar()  # getch injeta a sessão e sai com q
    con = core.get_db(db)
    try:
        h = con.execute("SELECT horas FROM jogos WHERE id=?", (gid,)).fetchone()["horas"]
    finally:
        con.close()
    afirmar(h == 1.5, f"horas={h}")
    afirmar("+1.5h" in t.msg_final, f"msg_final={t.msg_final!r}")


def teste_log_erro_anexa():
    from unittest.mock import patch
    from bib_nucleo import base
    tmp = Path(tempfile.mkdtemp(prefix="suite-al-"))
    with patch.object(base, "HOME_DIR", tmp):
        core.log_erro("ctx-teste", "detalhe-x")
        core.log_erro("ctx-teste", "detalhe-y")
        txt = (tmp / "erros.log").read_text(encoding="utf-8")
        afirmar("ctx-teste" in txt and "detalhe-x" in txt and "detalhe-y" in txt, txt)
        afirmar(len(txt.strip().splitlines()) == 2, txt)


def teste_sem_lambda_e_morta():
    """Regressão: nenhum callback diferido pode referenciar `e` do except."""
    src = (REPO / "app_win.py").read_text(encoding="utf-8")
    afirmar("lambda: falhou(e)" not in src, "padrão NameError reintroduzido")
    afirmar("lambda m=msg_erro: falhou(m)" in src, "captura por string ausente")
