"""Repacks: extração zip, organização, exe, import ponta a ponta."""
import os
import tempfile
import zipfile
from pathlib import Path

import bib_core as core
from executar import afirmar


def _repack_zip(tmp, nome="CoolGame-repack.zip"):
    arq = Path(tmp) / nome
    with zipfile.ZipFile(arq, "w") as zh:
        zh.writestr("CoolGame/CoolGame.exe", b"MZ" + b"0" * 1000)
        zh.writestr("CoolGame/_CommonRedist/vcredist.exe", b"R" * 100)
        zh.writestr("CoolGame/Read_Me.txt", b"leia")
        zh.writestr("CoolGame/site.url", b"[x]")
        zh.writestr("CoolGame/setup_coolgame.exe", b"S" * 100)
    return arq


def teste_repack_zip_extracao_e_classificacao():
    from bib_nucleo import repacks as RP
    tmp = Path(tempfile.mkdtemp(prefix="suite-rp-"))
    arq = _repack_zip(tmp)
    dest = tmp / "out"
    r = RP.extrair_arquivo(arq, dest)
    afirmar(r.get("ok"), r)
    afirmar((dest / "CoolGame" / "CoolGame.exe").is_file())
    afirmar(not RP.eh_pacote_hub(arq))
    (tmp / "p.zip").write_bytes(b"nao-zip")
    r = RP.extrair_arquivo(tmp / "p.zip", tmp / "out2")
    afirmar(not r.get("ok"), r)
    r = RP.extrair_arquivo(tmp / "sumiu.zip", tmp / "out3")
    afirmar(not r.get("ok") and "encontrado" in r["erro"], r)


def teste_repack_pacote_hub_preservado():
    import json
    from bib_nucleo import repacks as RP
    tmp = Path(tempfile.mkdtemp(prefix="suite-rp-"))
    arq = tmp / "pack.zip"
    with zipfile.ZipFile(arq, "w") as zh:
        zh.writestr("biblioteca.json", json.dumps({"jogos": []}))
    afirmar(RP.eh_pacote_hub(arq))
    ana = core.analisar_arquivo(str(arq))
    afirmar(ana["tipo"] == "pacote", ana)


def teste_repack_organizar_e_achar_exe():
    from bib_nucleo import repacks as RP
    tmp = Path(tempfile.mkdtemp(prefix="suite-rp-"))
    dest = tmp / "out"
    RP.extrair_arquivo(_repack_zip(tmp), dest)
    org = RP.organizar_extraido(dest)
    pasta = Path(org["pasta"])
    afirmar(pasta.name == "CoolGame", org)
    afirmar(not (pasta / "Read_Me.txt").exists(), "lixo ficou")
    afirmar(not (pasta / "site.url").exists(), "url ficou")
    afirmar((pasta / "_CommonRedist").is_dir(), "redist do jogo sumiu!")
    ach = RP.achar_exe(pasta)
    afirmar(ach.get("ok") and ach["exe"].endswith("CoolGame.exe"), ach)
    afirmar(ach["candidatos"] == 1, ach)
    vazia = tmp / "vazia"
    vazia.mkdir()
    r = RP.achar_exe(vazia)
    afirmar(not r.get("ok") and "precisa_instalar" not in r, r)
    so_setup = tmp / "so-setup"
    so_setup.mkdir()
    (so_setup / "setup_jogo.exe").write_bytes(b"S")
    r = RP.achar_exe(so_setup)
    afirmar(not r.get("ok") and r.get("precisa_instalar"), r)


def teste_repack_caminhos_padrao_win():
    import os as _os
    from bib_nucleo import repacks as RP
    from pathlib import Path as _P
    pir = RP.pasta_piratas()
    if _os.name == "nt":
        afirmar("\\Games\\Piratas" in str(pir), pir)
    else:
        afirmar(str(pir).endswith("/Games/Piratas"), pir)
    velho = _os.environ.get("BIBLIOTECA_PIRATAS")
    _os.environ["BIBLIOTECA_PIRATAS"] = str(_P("x"))
    try:
        afirmar(RP.pasta_piratas() == _P("x"))
    finally:
        if velho is None:
            _os.environ.pop("BIBLIOTECA_PIRATAS", None)
        else:
            _os.environ["BIBLIOTECA_PIRATAS"] = velho


def teste_repack_7z_override():
    import os as _os
    import tempfile as _tf
    from bib_nucleo import repacks as RP
    tmp = _tf.mkdtemp(prefix="suite-rp7z-")
    from pathlib import Path as _P
    falso = _P(tmp) / "meu7z.exe"
    falso.write_bytes(b"7z")
    velho = _os.environ.get("BIBLIOTECA_7Z")
    _os.environ["BIBLIOTECA_7Z"] = str(falso)
    try:
        afirmar(RP.ferramenta_7z() == falso)
        _os.environ["BIBLIOTECA_7Z"] = str(_P(tmp) / "inexistente.exe")
        afirmar(RP.ferramenta_7z() is None)
    finally:
        if velho is None:
            _os.environ.pop("BIBLIOTECA_7Z", None)
        else:
            _os.environ["BIBLIOTECA_7Z"] = velho
    r = RP.ferramenta_7z()
    afirmar(r is None or str(r).lower().endswith(("7z.exe", "7z", "7zr")), r)


def teste_repack_titulo_pasta_limpa():
    from bib_nucleo import repacks as RP
    from pathlib import Path as _P
    afirmar(RP._titulo_pasta(_P("Hades II [FitGirl Repack]")) == "Hades II")
    afirmar(RP._titulo_pasta(_P("CoolGame")) == "Cool Game")
    afirmar(RP._titulo_pasta(_P("Mewgenics-SteamRIP.com")) == "Mewgenics")
    afirmar(RP._titulo_pasta(_P("Sephiria-SteamRIP.com")) == "Sephiria")
    afirmar(RP._titulo_pasta(_P("Wanderburg-DODI")) == "Wanderburg")


def teste_repack_import_ponta_a_ponta():
    from bib_nucleo import repacks as RP
    tmp = Path(tempfile.mkdtemp(prefix="suite-rp-"))
    arq = _repack_zip(tmp)
    dest_root = tmp / "piratas"
    con = core.get_db(tmp / "r.db")
    try:
        r = RP.importar_repack(con, arq, destino_raiz=dest_root)
        afirmar(r.get("ok"), r)
        afirmar(r["novos"] == 1 and r["titulo"] == "Cool Game", r)
        afirmar(Path(r["exe"]).is_file(), r)
        afirmar(not arq.exists(), "archive devia ser apagado")
        afirmar(r["apagou_arquivo"] and r["setups_apagados"] == 1, r)
        afirmar(r["capa_pendente"] is True, r)
        jogos = core.listar_jogos(con, q="Cool Game")
        afirmar(len(jogos) == 1 and jogos[0]["origem"] == "repack", jogos)
        arq2 = _repack_zip(tmp, "outro.zip")
        r2 = RP.importar_repack(con, arq2, destino_raiz=dest_root)
        afirmar(r2.get("ok") and r2["novos"] == 1, r2)
        afirmar(r2["pasta"] != r["pasta"], r2)
    finally:
        con.close()


def teste_repack_capa_automatica_padrao():
    import urllib.request
    from bib_nucleo import banco as B
    from bib_nucleo import repacks as RP
    from bib_nucleo import scans as S
    tmp = Path(tempfile.mkdtemp(prefix="suite-rp-"))
    arq = _repack_zip(tmp, "auto.zip")
    con = core.get_db(tmp / "a.db")
    orig_appid, orig_capa = S._appid_steam_por_titulo, S._capa_steam
    orig_salvar = B.salvar_capa_bytes
    S._appid_steam_por_titulo = lambda t, timeout=15: "123"
    S._capa_steam = lambda a, timeout=15: b"x" * 2000
    B.salvar_capa_bytes = lambda c, g, f, d: {"ok": True}
    try:
        r = RP.importar_repack(con, arq, destino_raiz=tmp / "pir")
        afirmar(r.get("ok") and r["capa_auto"] and not r["capa_pendente"], r)
        afirmar("capa Steam" in " ".join(r["avisos"]), r)
    finally:
        S._appid_steam_por_titulo, S._capa_steam = orig_appid, orig_capa
        B.salvar_capa_bytes = orig_salvar
        con.close()
    con = core.get_db(tmp / "b.db")
    S._appid_steam_por_titulo = lambda t, timeout=15: (_ for _ in ()).throw(
        OSError("rede-x"))
    try:
        r = RP.importar_repack(con, _repack_zip(tmp, "off.zip"),
                               destino_raiz=tmp / "pir2")
        afirmar(r.get("ok") and r["capa_pendente"] and not r["capa_auto"], r)
    finally:
        S._appid_steam_por_titulo = orig_appid
        con.close()


def teste_repack_appid_casa_nome_exato():
    import json as _json
    import urllib.request
    from bib_nucleo import scans as S

    class _Resp:
        def __init__(self, dados):
            self._d = dados

        def read(self):
            return _json.dumps(self._d).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    payload = {"items": [{"id": 9, "name": "Outro Jogo"},
                         {"id": 7, "name": "Cool Game"}]}
    orig = urllib.request.urlopen
    urllib.request.urlopen = lambda *a, **k: _Resp(payload)
    try:
        afirmar(S._appid_steam_por_titulo("cool game") == "7")
        afirmar(S._appid_steam_por_titulo("jogo xx") == "")
        afirmar(S._appid_steam_por_titulo("") == "")
    finally:
        urllib.request.urlopen = orig
    urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(
        OSError("rede-x"))
    try:
        afirmar(S._appid_steam_por_titulo("cool game") == "")
    finally:
        urllib.request.urlopen = orig


def teste_repack_7z_ausente_orienta():
    from bib_nucleo import repacks as RP
    tmp = Path(tempfile.mkdtemp(prefix="suite-rp-"))
    arq = tmp / "jogo.rar"
    arq.write_bytes(b"Rar!\x1a\x07\x00")
    velho = os.environ.get("BIBLIOTECA_7Z")
    os.environ["BIBLIOTECA_7Z"] = str(tmp / "sem-7z.exe")
    try:
        r = RP.extrair_arquivo(arq, tmp / "out")
        afirmar(not r.get("ok") and "BIBLIOTECA_7Z" in r["erro"], r)
        ana = core.analisar_arquivo(str(arq))
        afirmar(ana["tipo"] == "arquivo-jogo", ana)
        iso = tmp / "jogo.iso"
        iso.write_bytes(b"ISO")
        ana = core.analisar_arquivo(str(iso))
        afirmar(ana["tipo"] == "arquivo-jogo", ana)
        ana = core.analisar_arquivo(str(tmp / "sumiu.rar"))
        afirmar(ana["tipo"] == "desconhecido", ana)
    finally:
        if velho is None:
            os.environ.pop("BIBLIOTECA_7Z", None)
        else:
            os.environ["BIBLIOTECA_7Z"] = velho
