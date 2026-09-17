"""Fase C: uuid, restore, relatório, diagnosticar, procurar, relink."""
import sqlite3
import tempfile
import zipfile
from pathlib import Path

import bib_core as core
from bib_nucleo import emuladores
from executar import afirmar


def _nova_db(nome="t.db"):
    tmp = Path(tempfile.mkdtemp(prefix="suite-c-"))
    db = tmp / nome
    return core.get_db(db), tmp


def teste_uuid_backfill_legado():
    tmp = Path(tempfile.mkdtemp(prefix="suite-cl-"))
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
    con.execute("INSERT INTO jogos (titulo) VALUES ('A'), ('B')")
    con.commit()
    con.close()
    con = core.get_db(leg)
    try:
        rows = con.execute("SELECT uuid FROM jogos ORDER BY id").fetchall()
        uuids = [r["uuid"] for r in rows]
        afirmar(all(u and len(u) == 32 for u in uuids), uuids)
        afirmar(len(set(uuids)) == 2, uuids)
        ix = con.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_jogos_uuid'").fetchone()
        afirmar(ix is not None, "sem índice único")
    finally:
        con.close()


def teste_criar_e_atualizar_uuid():
    con, _tmp = _nova_db()
    try:
        a = core.criar_jogo(con, {"titulo": "A", "executable_path": "", "status": "backlog"})
        afirmar(len(a["uuid"]) == 32, a)
        b = core.criar_jogo(con, {"titulo": "B", "executable_path": "", "status": "backlog",
                                  "uuid": "fixo123"})
        afirmar(b["uuid"] == "fixo123", b)
        c = core.atualizar_jogo(con, a["id"], {"nota": 8})
        afirmar(c["uuid"] == a["uuid"], (a["uuid"], c["uuid"]))
    finally:
        con.close()


def teste_restore_por_uuid():
    con, _tmp = _nova_db()
    try:
        g = core.criar_jogo(con, {"titulo": "R", "executable_path": "", "status": "jogando"})
        uid = g["uuid"]
        res = core.importar_lista(con, [{"uuid": uid, "titulo": "R TROCA?",
                                         "executable_path": "/outro",
                                         "status": "zerado", "horas": 5.5,
                                         "ultima_execucao": "2026-01-01T00:00:00",
                                         "nota": 9, "favorito": True,
                                         "observacoes": "obs"}])
        afirmar(res["atualizados"] == 1 and res["novos"] == 0, res)
        row = con.execute("SELECT * FROM jogos WHERE uuid=?", (uid,)).fetchone()
        d = core.row_to_dict(row)
        afirmar(d["horas"] == 5.5 and d["ultima_execucao"] == "2026-01-01T00:00:00"
                and d["status"] == "zerado" and d["nota"] == 9
                and d["titulo"] == "R" and d["executable_path"] == "", d)
    finally:
        con.close()


def teste_relatorio_import():
    con, _tmp = _nova_db()
    try:
        res = core.importar_lista(con, [{"titulo": "Ok", "executable_path": ""},
                                        {"titulo": ""}, "lixo",
                                        {"titulo": "Ruim", "nota": "xx"}])
        afirmar(res["novos"] == 1 and res["ignorados"] == 3, res)
        afirmar(len(res["erros"]) == 3, res["erros"])
        afirmar(res["total_no_banco"] == 1, res)
    finally:
        con.close()


def teste_pacote_uuid_e_ultima():
    tmp = Path(tempfile.mkdtemp(prefix="suite-cp-"))
    db1 = tmp / "p1.db"
    con = core.get_db(db1)
    try:
        g1 = core.criar_jogo(con, {"titulo": "MESMO", "executable_path": "a",
                                   "status": "jogando", "game_code": "C1"})
        g2 = core.criar_jogo(con, {"titulo": "MESMO", "executable_path": "b",
                                   "status": "backlog", "game_code": "C2"})
        core.salvar_capa_bytes(con, g1["id"], "um.png", b"PNG-UM")
        core.salvar_capa_bytes(con, g2["id"], "dois.png", b"PNG-DOIS")
        con.execute("UPDATE jogos SET ultima_execucao='2026-02-02T02:02:02', horas=3 WHERE id=?",
                    (g1["id"],))
        con.commit()
        uid1 = con.execute("SELECT uuid FROM jogos WHERE id=?", (g1["id"],)).fetchone()["uuid"]
    finally:
        con.close()
    zp = tmp / "pack.zip"
    r = core.exportar_pacote(zp, db_path=db1, incluir_saves=False)
    afirmar(r.get("ok"), r)
    with zipfile.ZipFile(zp) as z:
        import json
        man = json.loads(z.read("capas-manifesto.json").decode("utf-8"))
    afirmar(set(man.values()) == {uid1,
            [u for u in man.values() if u != uid1][0]} and len(man) == 2, man)
    db2 = tmp / "p2.db"
    res = core.importar_pacote(zp, db_path=db2, restaurar_saves=False)
    afirmar(res.get("ok") and res["novos"] == 2 and res["capas"] == 2, res)
    for k in ("atualizados", "ignorados", "erros"):
        afirmar(k in res, res)
    con = core.get_db(db2)
    try:
        rows = con.execute("SELECT * FROM jogos ORDER BY id").fetchall()
        por_code = {dict(r)["game_code"]: dict(r) for r in rows}
        c1 = core.caminho_capa(por_code["C1"]["capa"])
        c2 = core.caminho_capa(por_code["C2"]["capa"])
        afirmar(c1 is not None and c1.read_bytes() == b"PNG-UM", por_code["C1"]["capa"])
        afirmar(c2 is not None and c2.read_bytes() == b"PNG-DOIS", por_code["C2"]["capa"])
        afirmar(por_code["C1"]["ultima_execucao"] == "2026-02-02T02:02:02"
                and por_code["C1"]["horas"] == 3, por_code["C1"])
        # reimportar o mesmo pacote: atualiza, não duplica
        res2 = core.importar_pacote(zp, db_path=db2, restaurar_saves=False)
        afirmar(res2["novos"] == 0 and res2["atualizados"] == 2, res2)
    finally:
        con.close()


def teste_diagnosticar():
    exe_real = str(Path(tempfile.mkdtemp(prefix="suite-cd-")) / "j.exe")
    Path(exe_real).write_bytes(b"x")
    base = {"executable_path": exe_real, "exe_win": "", "exe_linux": "",
            "wine_prefix": "", "launch_options": "", "origem": "manual"}
    afirmar(core.diagnosticar_exe(dict(base))["estado"] == "ok")
    afirmar(core.diagnosticar_exe({**base, "executable_path": ""})["estado"] == "sem-exe")
    rom_falso = {**base, "origem": "rom-3ds", "exe_win": "D:\\nao\\existe\\azahar.exe",
                 "executable_path": ""}
    d = core.diagnosticar_exe(rom_falso)
    if core.default_emu_3ds():
        afirmar(d["estado"] == "trocou-emulador" and d["atual"] == core.default_emu_3ds(), d)
    afirmar(core.diagnosticar_exe({**base, "executable_path": "D:\\falta.exe"})["estado"] == "ausente")
    afirmar(core.diagnosticar_rom({**base, "launch_options": "--fullscreen"})["estado"] == "nao-rom")
    afirmar(core.diagnosticar_rom({**base, "launch_options": exe_real})["estado"] == "nao-rom")


def teste_procurar_rom():
    tmp = Path(tempfile.mkdtemp(prefix="suite-cr-"))
    sub = tmp / "sub"
    sub.mkdir()
    alvo = sub / "Meu Jogo.3ds"
    alvo.write_bytes(b"0")
    r = core.procurar_rom("meu jogo.3DS", roots=[str(tmp)])
    afirmar(r == [str(alvo)], r)
    afirmar(core.procurar_rom("falta.3ds", roots=[str(tmp)]) == [])
    afirmar(core.procurar_rom("", roots=[str(tmp)]) == [])


def teste_tui_relink():
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
    tmp = Path(tempfile.mkdtemp(prefix="suite-ct-"))
    cand = tmp / "jogo.3ds"
    cand.write_bytes(b"0")
    db = tmp / "u.db"
    t = tui.Tui(FakeScr(), db)
    con = core.get_db(db)
    try:
        gid = core.criar_jogo(con, {"titulo": "RL", "executable_path": "",
                                    "status": "backlog", "origem": "rom-3ds",
                                    "launch_options": "D:\\sumiu\\jogo.3ds"})["id"]
    finally:
        con.close()
    t.recarregar()
    t.cur = 0
    orig_proc, orig_lancar = emuladores.procurar_rom, emuladores._lancar_jogo_dict

    class FP:
        def wait(self):
            return 0

    emuladores.procurar_rom = lambda base, roots=None, max_resultados=20: [str(cand)]
    emuladores._lancar_jogo_dict = lambda j, e=False: ({"ok": True, "modo": "fake"}, FP())
    t.perguntar = lambda *a, **k: "j"
    t.confirmar = lambda *a, **k: True
    try:
        t.jogar()
        afirmar("Executando" in t.msg, t.msg)
    finally:
        emuladores.procurar_rom, emuladores._lancar_jogo_dict = orig_proc, orig_lancar
    con = core.get_db(db)
    try:
        launch = con.execute("SELECT launch_options FROM jogos WHERE id=?", (gid,)).fetchone()["launch_options"]
    finally:
        con.close()
    afirmar(launch == str(cand), launch)
