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
    from pathlib import Path as _P

    from bib_nucleo import repacks as RP
    pir = RP.pasta_jogos()
    if _os.name == "nt":
        afirmar("\\Games\\Meus Jogos Locais" in str(pir), pir)
    else:
        afirmar(str(pir).endswith("/Games/Meus Jogos Locais"), pir)
    velho = _os.environ.get("BIBLIOTECA_PIRATAS")
    _os.environ["BIBLIOTECA_PIRATAS"] = str(_P("x"))
    try:
        afirmar(RP.pasta_jogos() == _P("x"))
    finally:
        if velho is None:
            _os.environ.pop("BIBLIOTECA_PIRATAS", None)
        else:
            _os.environ["BIBLIOTECA_PIRATAS"] = velho


def teste_repack_organizar_no_destino_padrao_todos():
    import os as _os
    from pathlib import Path as _P

    from bib_nucleo import repacks as RP
    tmp = _P(tempfile.mkdtemp(prefix="suite-rp-org-"))
    pir = tmp / "Meus Jogos Locais"
    velho = _os.environ.get("BIBLIOTECA_PIRATAS")
    _os.environ["BIBLIOTECA_PIRATAS"] = str(pir)
    try:
        fora = tmp / "Downloads" / "Hell Clock [FitGirl Repack]"
        fora.mkdir(parents=True)
        (fora / "setup.exe").write_bytes(b"S")
        afirmar(not RP.dentro_do_destino(fora))
        r = RP.organizar_no_destino(fora)
        afirmar(r["ok"] and r["movido"] and not fora.exists(), r)
        afirmar((_P(r["path"]) / "setup.exe").is_file())
        afirmar(RP.dentro_do_destino(r["path"]))
        r2 = RP.organizar_no_destino(r["path"])
        afirmar(r2["ok"] and not r2["movido"], r2)
        outra = tmp / "outra" / "Hell Clock [FitGirl Repack]"
        outra.mkdir(parents=True)
        r3 = RP.organizar_no_destino(outra)
        afirmar(r3["ok"] and _P(r3["path"]).name == "Hell Clock [FitGirl Repack]-2", r3)
        r4 = RP.organizar_no_destino(tmp / "sumiu")
        afirmar(not r4["ok"], r4)
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
    falso = _P(tmp) / ("meu7z.exe" if _os.name == "nt" else "meu7z")
    falso.write_bytes(b"7z")
    velho = _os.environ.get("BIBLIOTECA_7Z")
    _os.environ["BIBLIOTECA_7Z"] = str(falso)
    falso.chmod(0o755)
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
    from pathlib import Path as _P

    from bib_nucleo import repacks as RP
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
        afirmar(r["apagou_arquivo"] and r["setups_quarentena"] == 1, r)
        quar = Path(r["pasta"]) / ".hub-lixo" / "setup_coolgame.exe"
        afirmar(quar.is_file(), "setup devia ir p/ quarentena, não sumir")
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

        def read(self, n=-1):
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


def teste_repack_symlink_nao_vaza():
    from bib_nucleo import repacks as RP
    tmp = Path(tempfile.mkdtemp(prefix="suite-rp-"))
    arq = tmp / "evil.zip"
    with zipfile.ZipFile(arq, "w") as zh:
        zh.writestr("jogo/jogo.exe", b"MZ")
        zh.writestr("C:/evil.exe", b"x")
    r = RP.extrair_arquivo(arq, tmp / "out")
    afirmar(not r.get("ok"), r)
    afirmar(not (tmp / "out").exists(), "destino devia ser limpo")
    base = tmp / "arm"
    (base / "sub").mkdir(parents=True)
    (base / "sub" / "jogo.exe").write_bytes(b"MZ")
    try:
        (base / "link.exe").symlink_to(base / "sub" / "jogo.exe")
    except OSError:
        return  # sem privilégio p/ symlink: pula
    ach = RP.achar_exe(base)
    afirmar(ach.get("ok") and ach["candidatos"] == 1, ach)
    real = tmp / "fora.exe"
    real.write_bytes(b"MZ")
    (base / "ext.exe").symlink_to(real)
    ach = RP.achar_exe(base)
    afirmar(ach.get("ok") and ach["candidatos"] == 1
            and "ext.exe" not in ach["exe"], ach)


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


def teste_sanear_pasta_acha_e_limpa():
    from bib_nucleo import repacks as RP
    tmp = Path(tempfile.mkdtemp(prefix="suite-rp-"))
    jogo = tmp / "JogoX"
    (jogo / "Wrapper").mkdir(parents=True)
    (jogo / "Wrapper" / "GameX.exe").write_bytes(b"MZ" + b"0" * 5000)
    (jogo / "Wrapper" / "setup_gamex.exe").write_bytes(b"S" * 500)
    (jogo / "Wrapper" / "Read_Me.txt").write_bytes(b"leia")
    (jogo / "Wrapper" / "site.url").write_bytes(b"[x]")
    (jogo / "Wrapper" / "_CommonRedist").mkdir()
    res = RP.sanear_pasta(jogo)
    afirmar(res.get("ok") and not res.get("precisa_instalar"), res)
    afirmar(Path(res["pasta"]).name == "Wrapper", res)
    afirmar(res["exe"].endswith("GameX.exe"), res)
    afirmar(res["quarentenados"] == 1, res)
    certa = Path(res["pasta"])
    afirmar(not (certa / "Read_Me.txt").exists(), "lixo ficou")
    afirmar(not (certa / "site.url").exists(), "url ficou")
    afirmar(not (certa / "setup_gamex.exe").exists(), "setup ficou")
    afirmar((certa / ".hub-lixo" / "setup_gamex.exe").is_file(),
            "quarentena sumiu")
    so_setup = tmp / "so-setup"
    so_setup.mkdir()
    (so_setup / "setup_jogo.exe").write_bytes(b"S")
    res = RP.sanear_pasta(so_setup)
    afirmar(res.get("ok") and res.get("precisa_instalar"), res)
    afirmar((so_setup / "setup_jogo.exe").is_file(), "setup sumiu!")
    res = RP.sanear_pasta(tmp / "sumiu")
    afirmar(not res.get("ok"), res)
    afirmar("sanear_pasta" in core.__all__)


def teste_sanear_preserva_instaladores_e_redist_distinto():
    from bib_nucleo import repacks as RP
    tmp = Path(tempfile.mkdtemp(prefix="suite-rp-"))
    instalador = tmp / "instalador"
    instalador.mkdir()
    (instalador / "setup.exe").write_bytes(b"setup")
    (instalador / "Read_Me.txt").write_text("Instruções", encoding="utf-8")
    r = RP.sanear_pasta(instalador)
    afirmar(r.get("precisa_instalar"), r)
    afirmar((instalador / "Read_Me.txt").exists(), "limpou antes de localizar um jogo")
    jogo = tmp / "Jogo"
    a, b = jogo / "_CommonRedist", jogo / "Dados/_CommonRedist"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    (jogo / "Jogo.exe").write_bytes(b"MZ" + b"G" * 5000)
    (a / "runtime.dll").write_bytes(b"AAAA")
    (b / "runtime.dll").write_bytes(b"BBBB")
    RP.organizar_extraido(jogo)
    afirmar(a.is_dir() and b.is_dir(), "mesmo nome/tamanho foi confundido com duplicata")
    (b / "runtime.dll").write_bytes(b"AAAA")
    RP.organizar_extraido(jogo)
    afirmar(not a.exists() and b.is_dir(), "não preservou a cópia dentro do jogo")


def teste_canonizar_steam_exato():
    import json as _json
    import urllib.request

    from bib_nucleo import scans as S

    class _Resp:
        def __init__(self, dados):
            self._d = dados

        def read(self, n=-1):
            return _json.dumps(self._d).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    payload = {"items": [{"id": 7, "name": "Outro Jogo"},
                         {"id": 2062430, "name": "BALL x PIT"}]}
    orig = urllib.request.urlopen
    urllib.request.urlopen = lambda *a, **k: _Resp(payload)
    try:
        afirmar(S.canonizar_steam("Balls", "BALL x PIT")
                == ("2062430", "BALL x PIT"))
        afirmar(S.canonizar_steam("zzz") == ("", ""))
        afirmar(S._appid_steam_por_titulo("BALL x PIT") == "2062430")
    finally:
        urllib.request.urlopen = orig
    urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(
        OSError("rede-x"))
    try:
        afirmar(S.canonizar_steam("BALL x PIT") == ("", ""))
    finally:
        urllib.request.urlopen = orig


def teste_repack_nome_canonico_e_capa():
    import urllib.request

    from bib_nucleo import banco as B
    from bib_nucleo import repacks as RP
    from bib_nucleo import scans as S
    tmp = Path(tempfile.mkdtemp(prefix="suite-rp-"))
    arq = tmp / "ballpit.zip"
    with zipfile.ZipFile(arq, "w") as zh:
        zh.writestr("BALL x PIT/Balls.exe", b"MZ" + b"0" * 5000)
    payload = {"items": [{"id": 2062430, "name": "BALL x PIT"}]}

    class _Resp:
        def read(self, n=-1):
            import json as _j
            return _j.dumps(payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    con = core.get_db(tmp / "c.db")
    orig_open, orig_capa = urllib.request.urlopen, S._capa_steam
    orig_appid = S._appid_steam_por_titulo
    orig_salvar_b, orig_salvar_s = B.salvar_capa_bytes, S.salvar_capa_bytes
    chamadas = []
    urllib.request.urlopen = lambda *a, **k: _Resp()
    S._capa_steam = lambda a, timeout=15: b"x" * 2000
    def fake_salvar(c, g, f, d):
        chamadas.append((g, f))
        return {"ok": True}
    B.salvar_capa_bytes = fake_salvar
    S.salvar_capa_bytes = fake_salvar
    try:
        r = RP.importar_repack(con, arq, destino_raiz=tmp / "pir")
        afirmar(r.get("ok") and r["titulo"] == "BALL x PIT", r)
        got = B.listar_jogos(con, q="BALL x PIT")
        afirmar(len(got) == 1 and got[0]["shop"] == "steam"
                and got[0]["object_id"] == "2062430", got)
        afirmar(chamadas and chamadas[0][1].endswith(".jpg"), chamadas)
    finally:
        urllib.request.urlopen = orig_open
        S._capa_steam = orig_capa
        S._appid_steam_por_titulo = orig_appid
        B.salvar_capa_bytes = orig_salvar_b
        S.salvar_capa_bytes = orig_salvar_s
        con.close()


def teste_repack_pasta_jogos_env_legado_e_migracao():
    import os
    import tempfile
    from pathlib import Path
    from unittest.mock import patch

    from bib_nucleo.rede import repacks as RP
    tmp = Path(tempfile.mkdtemp(prefix="suite-jogos-"))
    with patch.dict(os.environ, {"BIBLIOTECA_JOGOS_DIR": str(tmp / "novo"),
                                 "BIBLIOTECA_PIRATAS": str(tmp / "legado")}):
        afirmar(RP.pasta_jogos() == tmp / "novo", "a env nova deve vencer a legada")
    with patch.dict(os.environ, {"BIBLIOTECA_PIRATAS": str(tmp / "legado")}):
        os.environ.pop("BIBLIOTECA_JOGOS_DIR", None)
        afirmar(RP.pasta_jogos() == tmp / "legado", "a env legada continua valendo")
    base = tmp / "Games"
    base.mkdir()
    with patch.dict(os.environ):
        os.environ.pop("BIBLIOTECA_JOGOS_DIR", None)
        os.environ.pop("BIBLIOTECA_PIRATAS", None)
        with patch.object(RP, "_raiz_padrao_jogos", return_value=base):
            afirmar(RP.pasta_jogos() == base / "Meus Jogos Locais", "padrão novo")
            (base / "Piratas").mkdir()
            afirmar(RP.pasta_jogos() == base / "Piratas", "pasta antiga existente é mantida")
            (base / "Meus Jogos Locais").mkdir()
            afirmar(RP.pasta_jogos() == base / "Meus Jogos Locais", "pasta nova existente vence")
            afirmar(RP.pasta_piratas() == RP.pasta_jogos(), "alias legado aponta para a mesma pasta")
