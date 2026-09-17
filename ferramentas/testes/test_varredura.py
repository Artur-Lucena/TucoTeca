"""Varredura: horas finitas, erro do update visível, previews tolerantes, pacote em thread."""
import tempfile
import threading
import time
from pathlib import Path

import bib_core as core
from executar import afirmar


def teste_horas_nao_finitas():
    for v in ("inf", "-inf", "nan", float("inf"), float("nan")):
        try:
            core.validar_dados({"titulo": "T", "executable_path": "",
                                "status": "backlog", "horas": v})
        except ValueError:
            continue
        raise AssertionError(f"aceitou horas={v!r}")


def _app_oculto(db_nome="v.db"):
    import tkinter as tk
    import app_win
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.withdraw()
    tmp = Path(tempfile.mkdtemp(prefix="suite-v-"))
    app = app_win.App(root, tmp / db_nome)
    return root, app


def teste_update_mostra_erro_rede():
    import tkinter as tk
    from tkinter import messagebox
    root, app = _app_oculto()
    if root is None:
        print("(sem display: skip)")
        return
    try:
        visto = []
        from bib_nucleo import emuladores as EMU  # patch onde a spec lê
        orig_info, orig_err = EMU.azahar_release_info, messagebox.showerror
        EMU.azahar_release_info = lambda *a, **k: {"erro": "rede-x"}
        messagebox.showerror = lambda t, m: visto.append((t, m))
        try:
            app.atualizar_azahar()
            # mainloop de verdade (after() de thread vale); sai ao ver o erro ou no teto
            fim = time.time() + 8

            def _espera():
                if visto or time.time() > fim:
                    root.quit()
                else:
                    root.after(100, _espera)
            root.after(100, _espera)
            root.mainloop()
        finally:
            EMU.azahar_release_info = orig_info
            messagebox.showerror = orig_err
        afirmar(visto and visto[0][1] == "rede-x", visto)
    finally:
        root.destroy()


def teste_prev_tui_sem_score():
    import app_tui as tui

    class FakeScr:
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

    class FakeCurses:
        COLOR_CYAN = COLOR_BLACK = COLOR_GREEN = COLOR_RED = 1

        def curs_set(self, *a):
            pass

        def has_colors(self):
            return False

    tui.curses = FakeCurses()
    tmp = Path(tempfile.mkdtemp(prefix="suite-vp-"))
    t = tui.Tui(FakeScr(), tmp / "u.db")
    t.tela_prev("T", [{"titulo": "Sem score", "origem": "x"}])  # voltar com q sem levantar


def teste_prev_gui_sem_score():
    import tkinter as tk
    root, app = _app_oculto("v2.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        app._dlg_prev("T", "sub", [{"titulo": "Sem score", "origem": "x"}])
        root.update()
        for w in root.winfo_children():
            if isinstance(w, tk.Toplevel):
                w.destroy()
        root.update()
    finally:
        root.destroy()


def teste_pacote_exporta_em_thread():
    import tkinter as tk
    from tkinter import filedialog, messagebox
    root, app = _app_oculto("v3.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        tmp = Path(tempfile.mkdtemp(prefix="suite-ve-"))
        mudou = []
        orig_ask = filedialog.asksaveasfilename
        filedialog.asksaveasfilename = lambda **k: str(tmp / "p.zip")
        messagebox.showinfo = lambda *a, **k: mudou.append("info")
        messagebox.showerror = lambda *a, **k: mudou.append("erro")
        try:
            app.exportar_pacote()
            fim = time.time() + 15

            def _espera():
                if (tmp / "p.zip").is_file() or time.time() > fim:
                    root.quit()
                else:
                    root.after(100, _espera)
            root.after(100, _espera)
            root.mainloop()
        finally:
            filedialog.asksaveasfilename = orig_ask
        afirmar((tmp / "p.zip").is_file(), "zip não gerado")
    finally:
        root.destroy()


def teste_pacote_importa_em_thread():
    import tkinter as tk
    from tkinter import filedialog, messagebox
    root, app = _app_oculto("v4.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        tmp = Path(tempfile.mkdtemp(prefix="suite-vi-"))
        con = core.get_db(tmp / "outro.db")
        try:
            core.criar_jogo(con, {"titulo": "Z", "executable_path": "",
                                  "status": "backlog"})
        finally:
            con.close()
        zp = tmp / "pack.zip"
        r = core.exportar_pacote(zp, db_path=tmp / "outro.db", incluir_saves=False)
        afirmar(r.get("ok"), r)
        orig_ask = filedialog.askopenfilename
        orig_yn = messagebox.askyesno
        filedialog.askopenfilename = lambda **k: str(zp)
        messagebox.askyesno = lambda *a, **k: False
        avisos = []
        messagebox.showinfo = lambda *a, **k: avisos.append(a)
        messagebox.showerror = lambda *a, **k: avisos.append(("erro", a))
        try:
            app.importar_pacote()
            fim = time.time() + 15

            def _espera():
                if avisos or time.time() > fim:
                    root.quit()
                else:
                    root.after(100, _espera)
            root.after(100, _espera)
            root.mainloop()
        finally:
            filedialog.askopenfilename = orig_ask
            messagebox.askyesno = orig_yn
        con = core.get_db(app.db_path)
        try:
            n = con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()["n"]
        finally:
            con.close()
        afirmar(n == 1 and avisos, (n, avisos))
    finally:
        root.destroy()
