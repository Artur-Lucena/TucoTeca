"""Diálogo de jogo: monta seções escuras e salva de ponta a ponta."""
import tempfile
from pathlib import Path

import bib_core as core
from executar import afirmar


def _app_oculto(db_nome="d.db"):
    try:
        import tkinter as tk
    except ModuleNotFoundError:
        return None, None
    import app_win
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.withdraw()
    tmp = Path(tempfile.mkdtemp(prefix="suite-d-"))
    return root, app_win.App(root, tmp / db_nome)


def _dlg(app, root, jogo=None):
    app._dlg_jogo(jogo)
    root.update()
    dlgs = [w for w in root.winfo_children()
            if w.winfo_class() == "Toplevel"]
    afirmar(dlgs, "diálogo não abriu")
    return dlgs[-1]


def _listas(dlg):
    out = []

    def walk(w):
        for ch in w.winfo_children():
            if ch.winfo_class() == "Listbox":
                out.append(ch)
            walk(ch)
    walk(dlg)
    return out


def teste_dialogo_listas_tem_rolagem():
    try:
        import tkinter as tk
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    root, app = _app_oculto("d4.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        app._janela_musicas()
        root.update()
        wins = [w for w in root.winfo_children()
                if w.winfo_class() == "Toplevel"]
        afirmar(wins, "janela músicas não abriu")
        lbs = []

        def walk(w):
            for ch in w.winfo_children():
                if ch.winfo_class() == "Listbox":
                    lbs.append(ch)
                walk(ch)
        walk(wins[-1])
        afirmar(lbs, "janela sem Listbox?")
        for lb in lbs:
            irmas = [ch for ch in lb.master.winfo_children()
                     if ch.winfo_class() == "TScrollbar"]
            afirmar(irmas, "Listbox sem Scrollbar irmã")
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def _combos(dlg):
    out = []

    def walk(w):
        for ch in w.winfo_children():
            if ch.winfo_class() == "TCombobox":
                out.append(ch)
            walk(ch)
    walk(dlg)
    return out


def teste_dialogo_emulador_autodetect():
    try:
        import tkinter as tk
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    root, app = _app_oculto("d3.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        jogo = {"titulo": "Z", "executable_path": "", "exe_win": "", "exe_linux": "",
                "status": "backlog", "nota": None, "horas": 0, "favorito": False,
                "launch_options": "D:\\roms\\jogo.nds", "origem": "rom-nds",
                "azahar_preset": "", "observacoes": "", "capa": ""}
        dlg = _dlg(app, root, jogo)
        combos = _combos(dlg)
        textos = [c.get() for c in combos]
        afirmar(any("DeSmuME" in t for t in textos), textos)
        dlg.destroy()
        jogo3 = dict(jogo, origem="rom-3ds", launch_options="D:\\roms\\jogo.3ds")
        dlg = _dlg(app, root, jogo3)
        textos = [c.get() for c in _combos(dlg)]
        afirmar(any("Azahar" in t for t in textos), textos)
        dlg.destroy()
        dlg = _dlg(app, root, None)
        textos = [c.get() for c in _combos(dlg)]
        afirmar(any(t == "—" for t in textos), textos)
        dlg.destroy()
    finally:
        root.destroy()


def teste_resolver_jogo_cli():
    import tempfile
    import app_win
    tmp = Path(tempfile.mkdtemp(prefix="suite-dj-"))
    con = core.get_db(tmp / "j.db")
    try:
        a = core.criar_jogo(con, {"titulo": "Megabonk", "executable_path": "",
                                  "status": "backlog"})
        core.criar_jogo(con, {"titulo": "Megabonk 2", "executable_path": "",
                              "status": "backlog"})
        afirmar(app_win.resolver_jogo_cli(con, str(a["id"]))["id"] == a["id"])
        afirmar(app_win.resolver_jogo_cli(con, "megabonk")["id"] == a["id"])
        try:
            app_win.resolver_jogo_cli(con, "megabonk 2 x")
            afirmar(False, "devia levantar")
        except LookupError:
            pass
        try:
            app_win.resolver_jogo_cli(con, "mega")
            afirmar(False, "ambíguo devia levantar")
        except LookupError as e:
            afirmar("ambíguo" in str(e), e)
        try:
            app_win.resolver_jogo_cli(con, "   ")
            afirmar(False, "vazio devia levantar")
        except LookupError:
            pass
    finally:
        con.close()


def teste_dialogo_secoes_escuras():
    try:
        import tkinter as tk
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    root, app = _app_oculto()
    if root is None:
        print("(sem display: skip)")
        return
    try:
        dlg = _dlg(app, root, None)
        secs = [w for w in dlg.winfo_children()
                if w.winfo_class() == "TLabelframe"]
        afirmar(len(secs) == 6, [s.cget("text") for s in secs])
        estilos = {s.cget("style") for s in secs}
        afirmar(estilos == {"Sec.TLabelframe"}, estilos)
        dlg.destroy()
    finally:
        root.destroy()


def teste_dialogo_salva():
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    root, app = _app_oculto("d2.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        dlg = _dlg(app, root, None)
        entradas = [w for w in dlg.winfo_children()
                    for w in ([w] + list(w.winfo_children()))
                    if w.winfo_class() == "TEntry"]
        afirmar(entradas, "sem entries")
        entradas[0].delete(0, tk.END)
        entradas[0].insert(0, "Jogo Teste Diálogo")
        botoes = [w for w in dlg.winfo_children()
                  for w in ([w] + list(w.winfo_children()))
                  if w.winfo_class() == "TButton" and "Salvar" in str(w.cget("text"))]
        afirmar(botoes, "sem botão Salvar")
        orig_info = messagebox.showinfo
        messagebox.showinfo = lambda *a, **k: None
        try:
            botoes[0].invoke()
            root.update()
        finally:
            messagebox.showinfo = orig_info
        con = core.get_db(app.db_path)
        try:
            n = con.execute("SELECT COUNT(*) AS n FROM jogos WHERE titulo=?",
                            ("Jogo Teste Diálogo",)).fetchone()["n"]
        finally:
            con.close()
        afirmar(n == 1, "linha não foi salva")
    finally:
        root.destroy()
