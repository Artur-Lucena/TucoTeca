"""Instaladores: dieta, .tar.xz, stub .run (offset) e conteúdo do .iss."""
import io
import re
import sys
import tarfile
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # ferramentas/
import montar_linux as ML
import montar_portatil as MP
from executar import afirmar


def _fake(arvore: Path) -> Path:
    (arvore / "app").mkdir(parents=True)
    (arvore / "app" / "app_tui.py").write_bytes(b"# tui")
    (arvore / "BibliotecaHub.sh").write_bytes(b"#!/bin/sh\n")
    (arvore / "VERSAO.txt").write_bytes(b"fake")
    return arvore


def teste_dieta_poda_pycache():
    tmp = Path(tempfile.mkdtemp(prefix="suite-inst-"))
    build = _fake(tmp / "hub")
    pc = build / "app" / "__pycache__"
    pc.mkdir()
    (pc / "x.pyc").write_bytes(b"0" * 100)
    (build / "solto.pyc").write_bytes(b"1" * 50)
    (build / "_sqlite3.pyd").write_bytes(b"extensao nativa")
    (build / "_tkinter.pyd").write_bytes(b"extensao nativa")
    livres = MP.podar_dieta(build)
    afirmar(livres == 150, livres)
    afirmar(not pc.exists() and not (build / "solto.pyc").exists())
    afirmar((build / "app" / "app_tui.py").is_file(), "comeu arquivo real!")
    afirmar((build / "_sqlite3.pyd").is_file() and (build / "_tkinter.pyd").is_file(),
            "dieta apagou extensões nativas")


def teste_tarxz_roundtrip():
    tmp = Path(tempfile.mkdtemp(prefix="suite-inst-"))
    build = _fake(tmp / "hub")
    velho, MP.DIST = MP.DIST, tmp / "dist"
    try:
        saida = MP.empacotar_tarxz(build, "prova.tar.xz")
        afirmar(saida.is_file() and saida.stat().st_size > 0)
        with tarfile.open(saida, "r:xz") as t:
            nomes = t.getnames()
        for alvo in ("app/app_tui.py", "BibliotecaHub.sh", "VERSAO.txt"):
            afirmar(alvo in nomes, nomes)
    finally:
        MP.DIST = velho


def teste_run_offset_e_payload():
    tmp = Path(tempfile.mkdtemp(prefix="suite-inst-"))
    build = _fake(tmp / "tucoteca")
    velho, ML.DIST = ML.DIST, tmp / "dist"
    (tmp / "dist").mkdir()
    try:
        saida = ML.empacotar_run(build, "20990101", "_tmp.tar.xz")
        raw = saida.read_bytes()
        marc = b"__PAYLOAD_SEGUE__\n"
        i = raw.index(marc) + len(marc)
        stub = raw[:i].decode("utf-8")
        afirmar("__OFFSET__" not in stub and "__VERSAO__" not in stub, "placeholder vazou")
        afirmar("tar -xJf" in stub and "tail -c +" in stub, "stub sem extração?")
        off = int(re.search(r"^OFFSET=(\d+)$", stub, re.M).group(1))
        afirmar(off == i, (off, i))
        with tarfile.open(fileobj=io.BytesIO(raw[off:]), mode="r:xz") as t:
            nomes = t.getnames()
        for alvo in ("tucoteca/app/app_tui.py", "tucoteca/BibliotecaHub.sh",
                     "tucoteca/VERSAO.txt"):
            afirmar(alvo in nomes, nomes)
    finally:
        ML.DIST = velho


def teste_iss_classico():
    iss = Path(montar_iss())
    txt = iss.read_text(encoding="utf-8")
    afirmar("Compression=lzma2" in txt, "sem LZMA2?")
    afirmar("AppName={#AppNome}" in txt, "sem AppName?")
    afirmar("/DBuildDir" in txt and "/DVersao" in txt, "sem defines?")
    afirmar("PrivilegesRequired=lowest" in txt, "pedindo admin?")
    afirmar('Excludes: "dados\\*"' in txt, "dados vai pro setup?")
    afirmar("UninstallDelete" in txt, "sem limpeza?")


def montar_iss() -> str:
    return str(Path(__file__).resolve().parent.parent / "instalador.iss")


def teste_mac_payload_e_instalador():
    import montar_mac as MM
    tmp = Path(tempfile.mkdtemp(prefix="suite-inst-"))
    cache = tmp / "cache"
    cache.mkdir()
    (cache / "f.bin").write_bytes(b"0" * 10)
    velhos = (MM.DIST, MM.MAC_CACHE, MM.MAC_ARQS, MM.MAC_NAVIO)
    MM.DIST = tmp / "dist"
    MM.MAC_CACHE, MM.MAC_ARQS, MM.MAC_NAVIO = (
        cache, (("f.bin", "http://x", 1, ""),), ("f.bin",))
    try:
        base, v = MM.montar_base_mac(tmp / "trab")
        payload, inst = MM.empacotar_mac(base, "20990101")
        afirmar(payload.is_file() and inst.is_file())
        afirmar(payload.name in inst.read_text(encoding="utf-8"),
                "instalador não aponta o payload")
        afirmar((MM.DIST / "mac" / "f.bin").is_file(), "oficial não embarcou")
        with tarfile.open(payload, "r:xz") as t:
            nomes = t.getnames()
        for alvo in ("tucoteca/VERSAO.txt",
                     "tucoteca/BibliotecaHubMac.command",
                     "tucoteca/app/app_win.py"):
            afirmar(alvo in nomes, nomes)
    finally:
        MM.DIST, MM.MAC_CACHE, MM.MAC_ARQS, MM.MAC_NAVIO = velhos


def teste_universal_junta_tres():
    import montar_universal as MU
    tmp = Path(tempfile.mkdtemp(prefix="suite-inst-"))
    dist = tmp / "dist"
    dist.mkdir()
    (dist / "TucoTeca-Setup-20990101.exe").write_bytes(b"MZfake")
    (dist / "tucoteca-setup-20990101.run").write_bytes(b"#!/bin/sh\n")
    mac = dist / "mac"
    mac.mkdir()
    (mac / "tucoteca-mac-20990101.tar.xz").write_bytes(b"xzfake")
    (mac / "Instalar-Mac.command").write_bytes(b"#!/bin/sh\n")
    (mac / "LEIA-ME-MAC.txt").write_bytes(b"mac")
    velho_dist, velho_mac = MU.DIST, MU.montar_mac
    MU.DIST = dist
    MU.montar_mac = lambda leve=False: (
        mac / "tucoteca-mac-20990101.tar.xz", mac / "Instalar-Mac.command")
    try:
        saida = MU.montar(sem_zip=True)
        for alvo in ("windows/TucoTeca-Setup-20990101.exe",
                     "linux/tucoteca-setup-20990101.run",
                     "mac/Instalar-Mac.command",
                     "INSTALAR.html", "LEIA-ME.txt"):
            afirmar((saida / alvo).is_file(), alvo)
        html = (saida / "INSTALAR.html").read_text(encoding="utf-8")
        afirmar("TucoTeca-Setup-20990101.exe" in html, "html sem exe?")
        afirmar("tucoteca-setup-20990101.run" in html, "html sem run?")
        afirmar("__EXE__" not in html and "__RUN__" not in html, "placeholder vazou")
        afirmar("navigator.platform" in html, "sem detecção de SO?")
    finally:
        MU.DIST, MU.montar_mac = velho_dist, velho_mac


def teste_builders_copiam_despacho_e_volume():
    import montar_mac as MM
    tmp = Path(tempfile.mkdtemp(prefix="suite-inst-"))
    MP.copiar_app(tmp / "win")
    mac, _ = MM.montar_base_mac(tmp / "mac")
    from unittest.mock import patch
    with patch.object(ML, "incluir_azahar_linux", return_value="fake"):
        linux, _ = ML.montar_base_linux(tmp / "linux")
    for app in (tmp / "win", mac / "app", linux / "app"):
        afirmar((app / "despacho.py").is_file(), app)
        afirmar((app / "aparencia.py").is_file(), "tema ausente no pacote offline")
        afirmar((app / "bib_nucleo/volume.py").is_file(), app)
        afirmar((app / "bib_nucleo/arquivos.py").is_file(), app)
    afirmar('shift\n' in ML.SH_LAUNCHER)
    afirmar('BIBLIOTECA_HOME="$HUB"' in ML.SH_LAUNCHER)
    afirmar("%*" in MP.BAT_GUI)


def teste_desmume_origem_do_bundle_resolve():
    import os
    tmp = Path(tempfile.mkdtemp(prefix="suite-inst-"))
    exe = tmp / "desmume.exe"
    exe.write_bytes(b"MZfake")
    from unittest.mock import patch
    with patch.dict(os.environ, {"BIBLIOTECA_EMULADOR_NDS": str(exe)}):
        afirmar(MP.desmume_instalado_dir() == tmp)


def teste_mac_leve_nao_baixa_e_preserva_user():
    import montar_mac as MM
    from unittest.mock import patch
    tmp = Path(tempfile.mkdtemp(prefix="suite-inst-"))
    base, _ = MM.montar_base_mac(tmp / "build")
    with patch.object(MM, "DIST", tmp / "dist"), \
            patch.object(MM, "garantir_mac", side_effect=AssertionError("leve baixou oficiais")):
        payload, inst = MM.empacotar_mac(base, "20990101", leve=True)
    texto = inst.read_text(encoding="utf-8")
    afirmar(payload.is_file() and inst.is_file())
    afirmar('rm -rf "$2"' not in texto, "reinstalação apagaria o user do emulador")
    afirmar("ditto" in texto and "pacote leve" in texto)
