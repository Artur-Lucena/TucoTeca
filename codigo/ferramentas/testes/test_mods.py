"""Mods Azahar: campo v9, title ID, import, junction, aplicar e menu TUI."""
import os
import sqlite3
import tempfile
import zipfile
from pathlib import Path

import bib_core as core
from executar import afirmar

TID = "0004000000055D00"


def _rom_fake(tmp, nome="t.cci", tid=TID):
    head = bytearray(0x200)
    head[0x100:0x104] = b"NCCH"
    head[0x118:0x120] = bytes.fromhex(tid)[::-1]
    p = Path(tmp) / nome
    p.write_bytes(bytes(head))
    return p


def _mod_dir(tmp, nome="M"):
    d = Path(tmp) / nome
    (d / "romfs" / "a" / "0").mkdir(parents=True, exist_ok=True)
    (d / "romfs" / "a" / "0" / "1").write_bytes(b"x")
    (d / "code.ips").write_bytes(b"PATCH")
    return d


def _mod_zip(tmp, nome="pack.zip", raiz="Pack", nu=False):
    z = Path(tmp) / nome
    with zipfile.ZipFile(z, "w") as zh:
        if nu:
            zh.writestr(f"{raiz}/a/0/1", b"x")
        else:
            zh.writestr(f"{raiz}/romfs/a/0/1", b"x")
            zh.writestr(f"{raiz}/code.ips", b"PATCH")
        zh.writestr(f"{raiz}/notas.txt", b"doc")
    return z


def teste_normalizar_mods():
    afirmar(core.normalizar_mods(None) == "[]")
    afirmar(core.normalizar_mods([]) == "[]")
    afirmar(core.normalizar_mods(["A", "a ", "", "B"]) == '["A", "B"]')
    afirmar(core.normalizar_mods('["X", "Y"]') == '["X", "Y"]')
    afirmar(core.normalizar_mods("Solo") == '["Solo"]')
    afirmar(core.mods_de({"azahar_mods": '["M1"]'}) == ["M1"])
    afirmar(core.mods_de({"azahar_mods": ["M2"]}) == ["M2"])
    afirmar(core.mods_de({}) == [])
    afirmar(core.mods_de({"azahar_mods": "[invalido"}) == [])
    try:
        core.normalizar_mods("[invalido")
        afirmar(False, "devia levantar")
    except ValueError:
        pass
    afirmar(core.normalizar_mods(["a/b", "c\\d"]) == "[]")
    muitos = [f"m{i}" for i in range(30)]
    afirmar(len(core.mods_de({"azahar_mods": core.normalizar_mods(muitos)})) == 20)


def teste_migracao_v9_e_crud():
    tmp = Path(tempfile.mkdtemp(prefix="suite-mods-"))
    leg = tmp / "leg.db"
    con = sqlite3.connect(str(leg))
    con.execute("CREATE TABLE jogos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL,"
                " executable_path TEXT DEFAULT '', exe_win TEXT DEFAULT '', exe_linux TEXT DEFAULT '',"
                " wine_prefix TEXT DEFAULT '', launch_options TEXT DEFAULT '', status TEXT DEFAULT 'backlog',"
                " nota INTEGER, favorito INTEGER DEFAULT 0, horas REAL DEFAULT 0, ultima_execucao TEXT,"
                " observacoes TEXT DEFAULT '', origem TEXT DEFAULT 'manual', shop TEXT DEFAULT '',"
                " object_id TEXT DEFAULT '', game_code TEXT DEFAULT '', regiao TEXT DEFAULT '',"
                " capa TEXT DEFAULT '', confianca REAL DEFAULT 0, criado_em TEXT, atualizado_em TEXT,"
                " UNIQUE(titulo, executable_path))")
    con.commit()
    con.close()
    con = core.get_db(leg)
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(jogos)").fetchall()}
        afirmar("azahar_mods" in cols, sorted(cols))
        afirmar("azahar_mods" in core.CAMPOS_EDITAVEIS, core.CAMPOS_EDITAVEIS)
        g = core.criar_jogo(con, {"titulo": "M", "executable_path": "",
                                  "azahar_mods": ["A", "B"], "status": "backlog"})
        afirmar(g["mods_lista"] == ["A", "B"], g)
        c = core.atualizar_jogo(con, g["id"], {"nota": 5})
        afirmar(c["mods_lista"] == ["A", "B"], c)
        c = core.atualizar_jogo(con, g["id"], {"azahar_mods": []})
        afirmar(c["mods_lista"] == [], c)
    finally:
        con.close()


def teste_title_id_da_rom():
    from bib_nucleo import emuladores as EMU
    tmp = Path(tempfile.mkdtemp(prefix="suite-mods-"))
    rom = _rom_fake(tmp)
    afirmar(EMU.title_id_da_rom(str(rom)) == TID, rom)
    afirmar(EMU.title_id_da_rom(str(rom).strip()) == TID)
    ruim = tmp / "ruim.cci"
    ruim.write_bytes(b"curto")
    afirmar(EMU.title_id_da_rom(str(ruim)) == "")
    afirmar(EMU.title_id_da_rom("") == "")
    afirmar(EMU.title_id_da_rom(str(tmp / "nao-existe.cci")) == "")


def teste_importar_mod_zip_e_pasta():
    from bib_nucleo import emuladores as EMU
    tmp = Path(tempfile.mkdtemp(prefix="suite-mods-"))
    z = _mod_zip(tmp)
    r = EMU.importar_mod(str(z), TID)
    afirmar(r.get("ok"), r)
    afirmar(EMU.listar_mods(TID) == [r["mod"]], r)
    afirmar(r["arquivos"] >= 2, r)
    r2 = EMU.importar_mod(str(z), TID)
    afirmar(not r2.get("ok") and "já existe" in r2["erro"], r2)
    d = _mod_dir(tmp, "Dir")
    r3 = EMU.importar_mod(str(d), TID, "De Pasta")
    afirmar(r3.get("ok") and r3["mod"] == "De Pasta", r3)
    znu = _mod_zip(tmp, "nu.zip", raiz="Nu", nu=True)
    r4 = EMU.importar_mod(str(znu), TID, "Nu")
    afirmar(r4.get("ok"), r4)
    base = EMU.mods_lib_dir() / TID / "Nu"
    afirmar((base / "romfs" / "a" / "0" / "1").is_file(), sorted(p.name for p in base.iterdir()))
    zbad = tmp / "bad.zip"
    with zipfile.ZipFile(zbad, "w") as zh:
        zh.writestr("nada/relevante.txt", b"x")
    r5 = EMU.importar_mod(str(zbad), TID)
    afirmar(not r5.get("ok"), r5)
    r6 = EMU.importar_mod(str(tmp / "falta.zip"), TID)
    afirmar(not r6.get("ok"), r6)
    rr = EMU.remover_mod(TID, "De Pasta")
    afirmar(rr.get("ok") and "De Pasta" not in EMU.listar_mods(TID), rr)
    rr2 = EMU.remover_mod(TID, "../fora")
    afirmar(not rr2.get("ok"), rr2)


def teste_importar_mod_nu_com_code_ips():
    from bib_nucleo import emuladores as EMU
    tmp = Path(tempfile.mkdtemp(prefix="suite-mods-"))
    z = tmp / "nuips.zip"
    with zipfile.ZipFile(z, "w") as zh:
        zh.writestr("M/a/0/1", b"x")
        zh.writestr("M/code.ips", b"PATCH")
        zh.writestr("M/leia.txt", b"doc")
    r = EMU.importar_mod(str(z), TID, "NuIps")
    afirmar(r.get("ok"), r)
    base = EMU.mods_lib_dir() / TID / "NuIps"
    afirmar((base / "code.ips").is_file(), "code.ips saiu da raiz")
    afirmar((base / "romfs" / "a" / "0" / "1").is_file(), "conteúdo não embrulhado")
    afirmar(not (base / "romfs" / "leia.txt").exists(), "txt foi junto")
    afirmar(not (base / "romfs" / "code.ips").exists(), "ips enterrado no romfs")


def teste_remover_link_seguro():
    from bib_nucleo import emuladores as EMU
    tmp = Path(tempfile.mkdtemp(prefix="suite-mods-"))
    real = tmp / "dado.txt"
    real.write_bytes(b"meu")
    EMU.remover_link(str(real))  # pasta/arquivo real: não toca
    afirmar(real.is_file(), "apagou arquivo real!")
    EMU.remover_link(str(tmp / "inexistente"))  # não levanta
    afirmar(not EMU._eh_reparse(tmp / "inexistente"))
    afirmar(not EMU._eh_reparse(real))


def _emu_fake(tmp):
    emu = Path(os.environ.get("BIBLIOTECA_AZAHAR_DIR") or str(Path(tmp) / "emu"))
    (emu / "user").mkdir(parents=True, exist_ok=True)
    from executar import azahar_fake
    azahar_fake(emu)
    return emu


def teste_aplicar_mods_ida_e_volta():
    from bib_nucleo import emuladores as EMU
    tmp = Path(tempfile.mkdtemp(prefix="suite-mods-"))
    _emu_fake(tmp)
    rom = _rom_fake(tmp)
    _mod_dir(tmp, "M1")
    r = EMU.importar_mod(str(tmp / "M1"), TID, "M1")
    afirmar(r.get("ok"), r)
    jogo = {"origem": "rom-3ds", "launch_options": str(rom), "azahar_mods": ["M1"]}
    res = EMU.aplicar_mods(jogo)
    afirmar(res["aplicados"] == ["M1"] and not res["aviso"], res)
    pasta = Path(EMU.azahar_mods_dir()) / TID
    afirmar((pasta / "romfs" / "a" / "0" / "1").is_file(), "romfs não copiou")
    afirmar((pasta / "code.ips").is_file(), "code.ips não copiou")
    afirmar(not EMU._eh_reparse(pasta / "romfs"), "virou link?")
    afirmar((pasta / ".hub-mods.json").is_file(), "sem manifesto")
    mt = (pasta / "code.ips").stat().st_mtime_ns
    res_rep = EMU.aplicar_mods(jogo)
    afirmar(res_rep["aplicados"] == ["M1"], res_rep)
    afirmar((pasta / "code.ips").stat().st_mtime_ns == mt, "recopiou sem precisar")
    res2 = EMU.aplicar_mods({**jogo, "azahar_mods": []})
    afirmar(res2["aplicados"] == [] and not res2["aviso"], res2)
    afirmar(not (pasta / "code.ips").exists(), "cópia ficou após desativar")
    res3 = EMU.aplicar_mods({**jogo, "azahar_mods": ["Fantasma"]})
    afirmar(res3["aplicados"] == [] and res3["aviso"] and "Fantasma" in res3["aviso"], res3)
    res4 = EMU.aplicar_mods({"origem": "manual", "launch_options": "", "azahar_mods": ["M1"]})
    afirmar(res4 == {"aplicados": [], "aviso": None}, res4)
    res5 = EMU.aplicar_mods({**jogo, "azahar_mods_off": 1})
    dest = Path(EMU.azahar_mods_dir()) / TID / "M1"
    afirmar(res5["aplicados"] == [] and not dest.exists(), res5)
    con = core.get_db(tmp / "v10.db")
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(jogos)").fetchall()}
        afirmar("azahar_mods_off" in cols, sorted(cols))
        g = core.criar_jogo(con, {"titulo": "O", "executable_path": "",
                                  "azahar_mods": ["M1"], "azahar_mods_off": 1,
                                  "status": "backlog"})
        afirmar(g["mods_off"] is True and g["mods_lista"] == ["M1"], g)
        c = core.atualizar_jogo(con, g["id"], {"nota": 3})
        afirmar(c["mods_off"] is True, c)
        c = core.atualizar_jogo(con, g["id"], {"azahar_mods_off": 0})
        afirmar(c["mods_off"] is False, c)
    finally:
        con.close()


def teste_aplicar_mods_preserva_arquivo_do_usuario():
    from bib_nucleo import emuladores as EMU
    tmp = Path(tempfile.mkdtemp(prefix="suite-mods-"))
    _emu_fake(tmp)
    rom = _rom_fake(tmp)
    _mod_dir(tmp, "M1")
    r = EMU.importar_mod(str(tmp / "M1"), TID, "M1")
    afirmar(r.get("ok"), r)
    pasta = Path(EMU.azahar_mods_dir()) / TID
    pasta.mkdir(parents=True, exist_ok=True)
    meu = pasta / "meu.txt"
    meu.write_bytes(b"do usuario")
    jogo = {"origem": "rom-3ds", "launch_options": str(rom), "azahar_mods": ["M1"]}
    res = EMU.aplicar_mods(jogo)
    afirmar(res["aplicados"] == ["M1"] and not res["aviso"], res)
    afirmar(meu.is_file(), "comeu arquivo do usuário!")
    res2 = EMU.aplicar_mods({**jogo, "azahar_mods": []})
    afirmar(res2["aplicados"] == [], res2)
    afirmar(meu.is_file(), "comeu arquivo do usuário ao limpar!")
    afirmar(not (pasta / "code.ips").exists(), "cópia ficou")


def teste_aplicar_mods_overlay_ordem():
    from bib_nucleo import emuladores as EMU
    tmp = Path(tempfile.mkdtemp(prefix="suite-mods-"))
    _emu_fake(tmp)
    rom = _rom_fake(tmp)
    a = _mod_dir(tmp, "A")
    (a / "romfs" / "a" / "0" / "1").write_bytes(b"do-A")
    b = _mod_dir(tmp, "B")
    (b / "romfs" / "a" / "0" / "1").write_bytes(b"do-B")
    (b / "code.ips").write_bytes(b"PATCH-B")
    afirmar(EMU.importar_mod(str(a), TID, "A").get("ok"))
    afirmar(EMU.importar_mod(str(b), TID, "B").get("ok"))
    jogo = {"origem": "rom-3ds", "launch_options": str(rom), "azahar_mods": ["A", "B"]}
    res = EMU.aplicar_mods(jogo)
    afirmar(res["aplicados"] == ["A", "B"], res)
    pasta = Path(EMU.azahar_mods_dir()) / TID
    afirmar((pasta / "romfs" / "a" / "0" / "1").read_bytes() == b"do-B",
            "último mod deveria vencer")
    afirmar((pasta / "code.ips").read_bytes() == b"PATCH-B")


def _tui_fake(db, teclas, cols=150):
    import sys
    sys.path.insert(0, str(Path("codigo/frontends").resolve()))
    import app_tui as tui

    class Scr:
        def __init__(self):
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


def teste_tui_menu_mods_alterna():
    from bib_nucleo import emuladores as EMU
    tmp = Path(tempfile.mkdtemp(prefix="suite-mods-"))
    rom = _rom_fake(tmp)
    _mod_dir(tmp, "TM")
    r = EMU.importar_mod(str(tmp / "TM"), TID, "TM")
    afirmar(r.get("ok"), r)
    db = tmp / "m.db"
    con = core.get_db(db)
    try:
        core.criar_jogo(con, {"titulo": "J Mod", "executable_path": "",
                              "launch_options": str(rom),
                              "origem": "rom-3ds", "status": "backlog"})
    finally:
        con.close()
    app = _tui_fake(db, [ord("j"), 10, 27])
    con = core.get_db(db)
    try:
        j = core.listar_jogos(con, q="J Mod")[0]
    finally:
        con.close()
    app.menu_mods(j)
    con = core.get_db(db)
    try:
        mods = core.listar_jogos(con, q="J Mod")[0]["mods_lista"]
    finally:
        con.close()
    afirmar(mods == ["TM"], mods)


def teste_tui_menu_mods_chave():
    from bib_nucleo import emuladores as EMU
    tmp = Path(tempfile.mkdtemp(prefix="suite-mods-"))
    rom = _rom_fake(tmp)
    _mod_dir(tmp, "TK")
    r = EMU.importar_mod(str(tmp / "TK"), TID, "TK")
    afirmar(r.get("ok"), r)
    db = tmp / "m.db"
    con = core.get_db(db)
    try:
        core.criar_jogo(con, {"titulo": "J Chave", "executable_path": "",
                              "launch_options": str(rom),
                              "origem": "rom-3ds", "status": "backlog",
                              "azahar_mods": ["TK"]})
        j = core.listar_jogos(con, q="J Chave")[0]
    finally:
        con.close()
    app = _tui_fake(db, [10, 27])  # alterna a chave + volta
    app.menu_mods(j)
    con = core.get_db(db)
    try:
        row = core.listar_jogos(con, q="J Chave")[0]
    finally:
        con.close()
    afirmar(row["mods_off"] is True and row["mods_lista"] == ["TK"], row)
    res = EMU.aplicar_mods(dict(row, launch_options=str(rom)))
    afirmar(res["aplicados"] == [], res)


def teste_tui_menu_mods_sem_tid():
    tmp = Path(tempfile.mkdtemp(prefix="suite-mods-"))
    db = tmp / "m.db"
    con = core.get_db(db)
    try:
        core.criar_jogo(con, {"titulo": "PC", "executable_path": "x",
                              "status": "backlog"})
        j = core.listar_jogos(con, q="PC")[0]
    finally:
        con.close()
    app = _tui_fake(db, [])
    app.menu_mods(j)
    afirmar("title ID" in (app.msg or ""), app.msg)


def teste_mod_cache_e_colisao_com_arquivo_local():
    from unittest.mock import patch

    from bib_nucleo import emuladores as EMU
    tmp = Path(tempfile.mkdtemp(prefix="suite-mods-"))
    _emu_fake(tmp)
    rom = _rom_fake(tmp)
    src = _mod_dir(tmp, "Cache")
    afirmar(EMU.importar_mod(str(src), TID, "Cache")["ok"])
    jogo = {"origem": "rom-3ds", "launch_options": str(rom), "azahar_mods": ["Cache"]}
    EMU.aplicar_mods(jogo)
    with patch.object(EMU.shutil, "copy2", side_effect=AssertionError("recopiou cache")):
        r = EMU.aplicar_mods(jogo)
        afirmar(r["aplicados"] == ["Cache"] and not r["aviso"], r)
    biblioteca = EMU.mods_lib_dir() / TID / "Cache"
    (biblioteca / "code.ips").write_bytes(b"PATCH-NOVO")
    EMU.aplicar_mods(jogo)
    pasta = Path(EMU.azahar_mods_dir()) / TID
    afirmar((pasta / "code.ips").read_bytes() == b"PATCH-NOVO", "ignorou alteração de fonte")
    EMU.aplicar_mods({**jogo, "azahar_mods": []})
    (pasta / "code.ips").write_bytes(b"PATCH-DO-USUARIO")
    r = EMU.aplicar_mods(jogo)
    afirmar(r["aviso"] and (pasta / "code.ips").read_bytes() == b"PATCH-DO-USUARIO", r)
    EMU.aplicar_mods({**jogo, "azahar_mods": []})
    afirmar((pasta / "code.ips").read_bytes() == b"PATCH-DO-USUARIO")


def teste_mod_tid_invalido_nao_escreve():
    from bib_nucleo import emuladores as EMU
    for tid in ("..", "../../fora", "", "G" * 16):
        afirmar(EMU.listar_mods(tid) == [])
        afirmar(not EMU.remover_mod(tid, "x")["ok"])
        try:
            EMU.mods_titulo_dir(tid)
            afirmar(False, "aceitou title ID inválido")
        except ValueError:
            pass
