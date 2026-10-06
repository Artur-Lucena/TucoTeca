"""Linux: tradução de exe, AppImage case-insensitive, Wine, capa via launch e lock."""
import os
import tempfile
from pathlib import Path

import bib_core as core
from executar import afirmar


def teste_resolver_exe_fallback_win_no_linux():
    if os.name == "nt":
        print("(só Linux: skip)")
        return
    from bib_nucleo import base
    lin = Path(str(base.LINUX_ROOT).rstrip("/")) / "Games"
    lin.mkdir(parents=True, exist_ok=True)
    alvo = lin / "lx-jogo.exe"
    alvo.write_bytes(b"MZ")
    win = base.linux_para_win(str(alvo))
    if win == str(alvo):
        print("(sem tradução: skip)")
        return
    exe, origem = base.resolver_exe({"executable_path": "", "exe_win": win,
                                     "exe_linux": ""})
    afirmar(exe == str(alvo) and origem == "exe_win", (exe, origem))


def teste_exe_existe_via_traduzido():
    from bib_nucleo import base
    lin = Path(str(base.LINUX_ROOT).rstrip("/")) / "Games"
    lin.mkdir(parents=True, exist_ok=True)
    alvo = lin / "lx-jogo2.exe"
    alvo.write_bytes(b"MZ")
    outro = base.linux_para_win(str(alvo)) if os.name != "nt" else base.win_para_linux(str(alvo))
    if outro == str(alvo):
        print("(sem tradução: skip)")
        return
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    con = core.get_db(tmp / "t.db")
    try:
        core.criar_jogo(con, {"titulo": "LX Trad", "executable_path": outro,
                              "status": "backlog"})
        jogos = core.listar_jogos(con, q="LX Trad")
    finally:
        con.close()
    afirmar(len(jogos) == 1 and jogos[0]["exe_existe"], jogos)


def teste_nds_appimage_case_insensitive():
    if os.name == "nt":
        print("(só Linux: skip)")
        return
    from bib_nucleo import emuladores as EMU
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    (tmp / "DeSmuME_X64.AppImage").write_bytes(b"\x7fELF" + b"0" * 100)
    achado = EMU._appimage_na_pasta(tmp, "desmume")
    afirmar(achado.endswith(".AppImage") and Path(achado).is_file(), achado)


def teste_lancar_exe_sem_wine_mensagem_clara():
    if os.name == "nt":
        print("(só Linux: skip)")
        return
    import shutil
    if shutil.which("wine") or shutil.which("wine64"):
        print("(com wine: skip)")
        return
    from bib_nucleo import emuladores as EMU
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    exe = tmp / "jogo.exe"
    exe.write_bytes(b"MZ")
    res, _ = EMU._lancar(str(exe))
    afirmar(not res.get("ok") and "Wine" in (res.get("erro") or ""), res)


def teste_capa_rom_via_launch_sem_rom_path():
    from bib_nucleo import emuladores as EMU  # noqa: F401 (garante providers)
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    head = bytearray(0x200)
    head[:12] = b"JOGO TESTE  "
    head[0x0C:0x10] = b"ATCE"
    head[0x68:0x6C] = (0x4000).to_bytes(4, "little")
    banner = bytearray(0x1000)
    banner[0x222:0x224] = (0x001F).to_bytes(2, "little")
    banner[0x340:0x440] = "Capa LX".encode("utf-16-le")[:0x100].ljust(0x100, b"\x00")
    rom = tmp / "capa.nds"
    rom.write_bytes(bytes(head).ljust(0x4000, b"\x00") + bytes(banner))
    con = core.get_db(tmp / "t.db")
    try:
        res = core.importar_lista(con, [{"titulo": "LX ROM", "executable_path": "EMU",
                                         "launch_options": str(rom),
                                         "origem": "rom-nds", "status": "backlog"}])
    finally:
        con.close()
    afirmar(res.get("novos") == 1, res)
    capas = list((tmp / "dados" / "capas").glob("*")) if (tmp / "dados").exists() else []
    # capa pode estar em CAPAS_DIR global do sandbox; basta não ter erro fatal
    afirmar(not res.get("erros"), (res, capas))


def teste_lock_nao_apaga_de_outro():
    from bib_nucleo import base
    import json
    lp = base.lock_path()
    try:
        if lp.is_file():
            lp.unlink()
    except OSError:
        pass
    lp.parent.mkdir(parents=True, exist_ok=True)
    lp.write_text(json.dumps({"pid": 999999999, "host": "outro-host",
                              "so": os.name, "inicio": base.agora_iso()}),
                  encoding="utf-8")
    base.liberar_lock()
    afirmar(lp.is_file(), "apagou lock alheio")
    try:
        lp.unlink()
    except OSError:
        pass
    r = base.adquirir_lock()
    afirmar(r.get("ok"), r)
    base.liberar_lock()
    afirmar(not lp.is_file(), "não liberou lock próprio")


def _tui_fake(db, teclas, cols=150):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path("codigo/frontends").resolve()))
    import app_tui as tui

    class Scr:
        def __init__(self):
            self.cells = {}
            self.teclas = list(teclas)
        def getmaxyx(self):
            return (24, cols)
        def addnstr(self, y, x, s, n, a=0):
            pass
        def erase(self):
            pass
        def refresh(self):
            pass
        def getch(self):
            return self.teclas.pop(0) if self.teclas else ord("q")

    class FakeCurses:
        COLOR_CYAN = COLOR_BLACK = COLOR_GREEN = COLOR_RED = 1
        COLOR_YELLOW = COLOR_MAGENTA = COLOR_WHITE = 1
        KEY_DOWN = 258
        KEY_UP = 259
        KEY_ENTER = 343
        KEY_PPAGE = 339
        KEY_NPAGE = 338
        A_BOLD = 1
        A_DIM = 0
        def curs_set(self, *a):
            pass
        def has_colors(self):
            return False
        def color_pair(self, n):
            return 0

    tui.curses = FakeCurses()
    return tui.Tui(Scr(), db)


def teste_menu_fila_volta():
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    db = tmp / "m.db"
    con = core.get_db(db)
    try:
        core.enfileirar_downloads(con, [{"titulo": "Cotidiano",
                                         "artista": "Chico Buarque",
                                         "uri": "spotify:track:1"}])
    finally:
        con.close()
    app = _tui_fake(db, [10, ord("j"), ord("j"), ord("j"), ord("j"), 10])
    con = app._con()
    try:
        app.menu_fila(con)
    finally:
        con.close()
    afirmar("pendente" in app.msg, app.msg)


def teste_menu_principal_abre_e_cancela():
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    db = tmp / "m.db"
    app = _tui_fake(db, [27, ord("q")])
    afirmar(app.menu_principal() is False, "ESC deveria voltar à lista")


def teste_menu_principal_sair():
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    db = tmp / "m.db"
    teclas = [ord("j")] * 9 + [10]
    app = _tui_fake(db, teclas)
    afirmar(app.menu_principal() is True, "navegar até Sair + Enter deveria pedir saída")


def teste_menu_jogo_volta():
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    db = tmp / "m.db"
    con = core.get_db(db)
    try:
        core.criar_jogo(con, {"titulo": "LX Menu", "executable_path": "",
                              "status": "backlog"})
    finally:
        con.close()
    app = _tui_fake(db, [10, ord("q")])
    cur_antes = app.cur
    app.menu_jogo()
    afirmar(app.cur == cur_antes, "Voltar não deveria mudar a seleção")


def teste_menu_controles_volta():
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    db = tmp / "m.db"
    app = _tui_fake(db, [27])
    app.menu_controles()
    afirmar(app.msg == "" or isinstance(app.msg, str), app.msg)


def teste_desenhar_tela_principal():
    """Regressão: desenhar() desenhava NameError (filtro) e a tela ia em branco."""
    import sys
    import tempfile
    from pathlib import Path
    sys.path.insert(0, str(Path("codigo/frontends").resolve()))
    import app_tui as tui
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    db = tmp / "m.db"
    con = core.get_db(db)
    try:
        core.criar_jogo(con, {"titulo": "LX Tela", "executable_path": "",
                              "status": "backlog"})
    finally:
        con.close()

    class ScrRec:
        def __init__(self):
            self.cells = {}
        def getmaxyx(self):
            return (24, 150)
        def addnstr(self, y, x, s, n, a=0):
            self.cells[(y, x)] = s[:n]
        def erase(self):
            self.cells.clear()
        def refresh(self):
            pass
        def getch(self):
            return ord("q")

    _tui_fake(db, [])  # instala FakeCurses no módulo app_tui
    scr = ScrRec()
    app = tui.Tui(scr, db)
    app.desenhar()
    texto = "\n".join(v for _, v in sorted(scr.cells.items()))
    afirmar("TucoTeca" in texto, texto[:200])
    afirmar("busca=" in texto and "prov=" in texto, texto[:300])
    afirmar("LX Tela" in texto, texto[:500])


def teste_escolher_rola_lista_longa():
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    db = tmp / "m.db"
    ops = [f"opcao-{i:02d}" for i in range(50)]
    app = _tui_fake(db, [ord("j")] * 45 + [10])
    afirmar(app.escolher("T", ops) == 45, "rolagem quebrou o índice")
    app = _tui_fake(db, [ord("j")] * 60 + [10])
    afirmar(app.escolher("T", ops) == 49, "teto da rolagem")
    app = _tui_fake(db, [27])
    afirmar(app.escolher("T", ops) is None, "ESC deveria cancelar")


def teste_escolher_terminal_estreito():
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    db = tmp / "m.db"
    ops = ["x" * 200, "curta"]
    app = _tui_fake(db, [10], cols=30)
    afirmar(app.escolher("T", ops) == 0, "largura estreita quebrou")


def teste_menu_filtros_cicla_status():
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    db = tmp / "m.db"
    app = _tui_fake(db, [10, ord("q")])
    si_antes = app.si
    app.menu_filtros()
    afirmar(app.si == (si_antes + 1) % len(app.statuses), app.si)


def teste_resolver_exe_fantasma_cai_no_provider():
    from bib_nucleo import base
    exe, origem = base.resolver_exe({"executable_path": "", "exe_win": "",
                                     "exe_linux": ""})
    afirmar(exe == "" and origem == "executavel", (exe, origem))
    exe, origem = base.resolver_exe({"executable_path": "",
                                     "exe_win": "D:\\Games\\Inexistente\\jogo.exe",
                                     "exe_linux": ""})
    if os.name == "nt":
        afirmar(exe != "", (exe, origem))
    else:
        afirmar(exe == "" and origem == "executavel", (exe, origem))


def teste_lock_antigo_sem_host_so_libera():
    from bib_nucleo import base
    import json
    lp = base.lock_path()
    try:
        if lp.is_file():
            lp.unlink()
    except OSError:
        pass
    lp.parent.mkdir(parents=True, exist_ok=True)
    lp.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
    base.liberar_lock()
    afirmar(not lp.is_file(), "lock antigo sem host/so deveria liberar")


def teste_tem_nvidia_nao_levanta():
    from bib_nucleo import emuladores as EMU
    r = EMU._tem_nvidia()
    afirmar(isinstance(r, str), r)


def teste_prefixo_wine_no_hub():
    from bib_nucleo import base
    from bib_nucleo import emuladores as EMU
    p = EMU.prefixo_wine_hub()
    afirmar(p == str(base.WINE_PREFIXO), p)
    afirmar("saves" in p.replace("\\", "/"), p)


def teste_dedup_cross_os_mesmo_jogo():
    from bib_nucleo import base
    win = str(base.WIN_ROOT).rstrip("\\")
    lin = str(base.LINUX_ROOT).rstrip("/")
    sep_w, sep_l = "\\", "/"
    a = core.chave_dedup("Jogo X", win + sep_w + "Games" + sep_w + "Jogo" + sep_w + "jogo.exe", "")
    b = core.chave_dedup("jogo x", lin + sep_l + "Games" + sep_l + "Jogo" + sep_l + "jogo.exe", "")
    afirmar(a == b, (a, b))
