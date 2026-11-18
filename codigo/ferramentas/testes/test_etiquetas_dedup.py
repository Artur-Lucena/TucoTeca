"""Etiquetas, deduplicação, separador de títulos, filtro de lixo, appid, lock e selos."""
import tempfile
import urllib.request
from pathlib import Path

from bib_nucleo import banco, base, pacotes
from bib_nucleo import scans as SC
from executar import afirmar


def _nova_db(nome="d.db"):
    tmp = Path(tempfile.mkdtemp(prefix="suite-d-"))
    db = tmp / nome
    return banco.get_db(db), tmp


def teste_etiquetas_normaliza():
    afirmar(banco.normalizar_etiquetas("RPG, rpg;  Acao ") == "Acao, RPG")
    afirmar(banco.normalizar_etiquetas("") == "")
    afirmar(banco.normalizar_etiquetas(None) == "")
    longa = "x" * 50
    afirmar(len(banco.normalizar_etiquetas(longa).split(", ")[0]) == 30)
    muitas = ", ".join(f"t{i}" for i in range(30))
    afirmar(len(banco.normalizar_etiquetas(muitas).split(", ")) == 20)
    afirmar(banco.etiquetas_de({"etiquetas": "b, A"}) == ["A", "b"])
    afirmar(banco.etiquetas_de({}) == [])
    afirmar(banco.plataforma_de_origem("rom-3ds") == "3DS")
    afirmar(banco.plataforma_de_origem("rom-nds") == "NDS")
    afirmar(banco.plataforma_de_origem("manual") == "PC")


def teste_etiquetas_crud():
    con, _tmp = _nova_db()
    try:
        g = banco.criar_jogo(con, {"titulo": "E", "executable_path": "",
                                  "status": "backlog", "etiquetas": "rpg, Souls"})
        afirmar(g["etiquetas_lista"] == ["rpg", "Souls"], g)
        c = banco.atualizar_jogo(con, g["id"], {"nota": 7})  # sem etiquetas = preserva
        afirmar(c["etiquetas"] == g["etiquetas"], (c, g))
        assert banco.listar_etiquetas(con)[0]["n"] == 1
    finally:
        con.close()


def teste_chave_dedup():
    a = banco.chave_dedup("Jogo", r"D:\Games\j.exe", "")
    b = banco.chave_dedup("jogo", "D:/Games/j.exe", "")
    afirmar(a == b, (a, b))
    afirmar(a != banco.chave_dedup("Outro", r"D:\Games\j.exe", ""))


def teste_import_dedup_barra():
    con, _tmp = _nova_db()
    try:
        r1 = SC.importar_lista(con, [{"titulo": "J", "executable_path": r"D:\G\j.exe"}])
        afirmar(r1["novos"] == 1, r1)
        r2 = SC.importar_lista(con, [{"titulo": "J", "executable_path": "D:/G/j.exe"}])
        afirmar(r2["novos"] == 0 and r2["total_no_banco"] == 1, r2)
    finally:
        con.close()


def teste_import_mesmo_exe_outro_titulo():
    con, _tmp = _nova_db()
    try:
        SC.importar_lista(con, [{"titulo": "Hades II",
                                   "executable_path": r"D:\G\Hades2.exe"}])
        r = SC.importar_lista(con, [{"titulo": "Hades 2",
                                       "executable_path": r"D:\G\Hades2.exe"}])
        afirmar(r["novos"] == 0 and r["total_no_banco"] == 1, r)
    finally:
        con.close()


def teste_criar_duplicata_barra():
    con, _tmp = _nova_db()
    try:
        banco.criar_jogo(con, {"titulo": "J", "executable_path": r"D:\G\j.exe",
                              "status": "backlog"})
        try:
            banco.criar_jogo(con, {"titulo": "j", "executable_path": "D:/G/j.exe",
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
    r1 = base.adquirir_lock()
    afirmar(r1.get("ok"), r1)
    try:
        r2 = base.adquirir_lock()
        afirmar(not r2.get("ok"), r2)
    finally:
        base.liberar_lock()
    r3 = base.adquirir_lock()
    afirmar(r3.get("ok"), r3)
    base.liberar_lock()


def teste_backup_pre_import_e_selo():
    con, tmp = _nova_db()
    db = tmp / "d.db"
    con.close()
    res = pacotes.backup_pre_import(db)
    afirmar(res is None or "db" in res, res)
    idade = pacotes.idade_ultimo_backup_dias()
    afirmar(idade is None or isinstance(idade, float), idade)
    afirmar(banco.selo_confianca({"confianca": 0.85}) == " · ◎0.85")
    afirmar(banco.selo_confianca({"confianca": 0}) == "")


def teste_lock_abertura_concorrente():
    import threading
    barreira = threading.Barrier(8)
    resultados = []

    def adquirir():
        barreira.wait(5)
        resultados.append(base.adquirir_lock())

    threads = [threading.Thread(target=adquirir) for _ in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join(5)
    try:
        afirmar(len(resultados) == 8 and sum(r["ok"] for r in resultados) == 1, resultados)
    finally:
        base.liberar_lock()


def teste_lock_vivo_nao_expira_e_json_invalido():
    import json
    import os
    import socket
    import sys

    from bib_nucleo import base
    lp = base.lock_path()
    lp.parent.mkdir(parents=True, exist_ok=True)
    lp.write_text(json.dumps({"pid": os.getpid(), "host": socket.gethostname(),
                              "so": sys.platform, "inicio": "2000-01-01T00:00:00+00:00"}))
    try:
        afirmar(not base.adquirir_lock()["ok"], "lock com PID vivo expirou")
    finally:
        base.liberar_lock()
    lp.write_text("[]")
    afirmar(not base.adquirir_lock()["ok"], "arquivo recém-criado foi atropelado")
    base.liberar_lock()  # não levanta em JSON não-objeto
    lp.unlink()


def teste_save_path():
    con, _tmp = _nova_db()
    try:
        g = banco.criar_jogo(con, {"titulo": "S", "executable_path": "",
                                  "status": "backlog",
                                  "save_path": r"C:\Saves\Jogo"})
        afirmar(g["save_path"] == r"C:\Saves\Jogo", g)
        c = banco.atualizar_jogo(con, g["id"], {"nota": 5})  # preserva
        afirmar(c["save_path"] == r"C:\Saves\Jogo", c)
        c = banco.atualizar_jogo(con, g["id"], {"save_path": ""})
        afirmar(c["save_path"] == "", c)
    finally:
        con.close()
