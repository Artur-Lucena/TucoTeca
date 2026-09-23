"""Fase D: etiquetas, dedup, splitter, skip-junk, appid, lock e selos."""
import tempfile
import urllib.request
from pathlib import Path

import bib_core as core
from bib_nucleo import scans as SC
from executar import afirmar


def _nova_db(nome="d.db"):
    tmp = Path(tempfile.mkdtemp(prefix="suite-d-"))
    db = tmp / nome
    return core.get_db(db), tmp


def teste_etiquetas_normaliza():
    afirmar(core.normalizar_etiquetas("RPG, rpg;  Acao ") == "Acao, RPG")
    afirmar(core.normalizar_etiquetas("") == "")
    afirmar(core.normalizar_etiquetas(None) == "")
    longa = "x" * 50
    afirmar(len(core.normalizar_etiquetas(longa).split(", ")[0]) == 30)
    muitas = ", ".join(f"t{i}" for i in range(30))
    afirmar(len(core.normalizar_etiquetas(muitas).split(", ")) == 20)
    afirmar(core.etiquetas_de({"etiquetas": "b, A"}) == ["A", "b"])
    afirmar(core.etiquetas_de({}) == [])
    afirmar(core.plataforma_de_origem("rom-3ds") == "3DS")
    afirmar(core.plataforma_de_origem("rom-nds") == "NDS")
    afirmar(core.plataforma_de_origem("manual") == "PC")


def teste_etiquetas_crud():
    con, _tmp = _nova_db()
    try:
        g = core.criar_jogo(con, {"titulo": "E", "executable_path": "",
                                  "status": "backlog", "etiquetas": "rpg, Souls"})
        afirmar(g["etiquetas_lista"] == ["rpg", "Souls"], g)
        c = core.atualizar_jogo(con, g["id"], {"nota": 7})  # sem etiquetas = preserva
        afirmar(c["etiquetas"] == g["etiquetas"], (c, g))
        assert core.listar_etiquetas(con)[0]["n"] == 1
    finally:
        con.close()


def teste_chave_dedup():
    a = core.chave_dedup("Jogo", r"D:\Games\j.exe", "")
    b = core.chave_dedup("jogo", "D:/Games/j.exe", "")
    afirmar(a == b, (a, b))
    afirmar(a != core.chave_dedup("Outro", r"D:\Games\j.exe", ""))


def teste_import_dedup_barra():
    con, _tmp = _nova_db()
    try:
        r1 = core.importar_lista(con, [{"titulo": "J", "executable_path": r"D:\G\j.exe"}])
        afirmar(r1["novos"] == 1, r1)
        r2 = core.importar_lista(con, [{"titulo": "J", "executable_path": "D:/G/j.exe"}])
        afirmar(r2["novos"] == 0 and r2["total_no_banco"] == 1, r2)
    finally:
        con.close()


def teste_import_mesmo_exe_outro_titulo():
    con, _tmp = _nova_db()
    try:
        core.importar_lista(con, [{"titulo": "Hades II",
                                   "executable_path": r"D:\G\Hades2.exe"}])
        r = core.importar_lista(con, [{"titulo": "Hades 2",
                                       "executable_path": r"D:\G\Hades2.exe"}])
        afirmar(r["novos"] == 0 and r["total_no_banco"] == 1, r)
    finally:
        con.close()


def teste_criar_duplicata_barra():
    con, _tmp = _nova_db()
    try:
        core.criar_jogo(con, {"titulo": "J", "executable_path": r"D:\G\j.exe",
                              "status": "backlog"})
        try:
            core.criar_jogo(con, {"titulo": "j", "executable_path": "D:/G/j.exe",
                                  "status": "backlog"})
        except ValueError:
            return
        raise AssertionError("criar aceitou variante de barra")
    finally:
        con.close()


def teste_splitter_titulos():
    afirmar(SC._titulo_de_exe(Path("HowManyDudes.exe")) == "How Many Dudes")
    afirmar(SC._titulo_de_exe(Path("Hades2.exe")) == "Hades 2")
    afirmar(SC._titulo_de_exe(Path("meu_jogo-win64.exe")) == "meu jogo")


def teste_skip_junk():
    for exe in ("stockfish-windows-x86-64.exe", "cgef.exe", "F10.exe"):
        afirmar(SC.SKIP_EXE_RE.search(exe), exe)
    for exe in ("Hades2.exe", "ULTRAKILL.exe", "Mewgenics.exe"):
        afirmar(not SC.SKIP_EXE_RE.search(exe), exe)


def teste_appid_manifest():
    afirmar(SC._appid_de_manifest("appmanifest_12345.acf") == "12345")
    afirmar(SC._appid_de_manifest("outro.acf") == "")
    it = SC._item_steam_manifest('"name" "Nome"\n"installdir" "Pasta"', "/x", "12345")
    afirmar(it is not None and it["object_id"] == "12345", it)


def teste_capa_steam_falha_rede():
    orig = urllib.request.urlopen
    urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(OSError("rede-x"))
    try:
        try:
            SC._capa_steam("123")
        except Exception:
            return  # falha alta: quem chama (importar) trata e avisa
        raise AssertionError("capa engoliu erro de rede")
    finally:
        urllib.request.urlopen = orig


def teste_lock_segunda_instancia():
    r1 = core.adquirir_lock()
    afirmar(r1.get("ok"), r1)
    try:
        r2 = core.adquirir_lock()
        afirmar(not r2.get("ok"), r2)
    finally:
        core.liberar_lock()
    r3 = core.adquirir_lock()
    afirmar(r3.get("ok"), r3)
    core.liberar_lock()


def teste_backup_pre_import_e_selo():
    con, tmp = _nova_db()
    db = tmp / "d.db"
    con.close()
    res = core.backup_pre_import(db)
    afirmar(res is None or "db" in res, res)
    idade = core.idade_ultimo_backup_dias()
    afirmar(idade is None or isinstance(idade, float), idade)
    afirmar(core.selo_confianca({"confianca": 0.85}) == " · ◎0.85")
    afirmar(core.selo_confianca({"confianca": 0}) == "")
