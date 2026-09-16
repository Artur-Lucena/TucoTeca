"""Fase B: update com stage + backup + rollback (file:// fake, dest fake)."""
import hashlib
import tempfile
import zipfile
from pathlib import Path

import bib_core as core
from executar import afirmar


def _release(tmp, tag, corpo=b"X", extra=None):
    src = tmp / f"rel-{tag}"
    src.mkdir()
    (src / "azahar.exe").write_bytes(corpo * (12_000_000 // len(corpo) + 1))
    (src / "nota.txt").write_text("oi", encoding="utf-8")
    if extra:
        for nome, dados in extra.items():
            (src / nome).write_bytes(dados)
    zp = tmp / f"{tag}.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for arq in src.rglob("*"):
            if arq.is_file():
                z.write(arq, arq.relative_to(src))
    raw = zp.read_bytes()
    return {"url": zp.as_uri(), "tag": tag, "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def _com_dest(tmp):
    dest = tmp / "emu"
    dest.mkdir()
    (dest / "user").mkdir()
    (dest / "user" / "save.txt").write_text("meu save", encoding="utf-8")
    velho = core._emu_dir
    core._emu_dir = lambda: dest
    return dest, velho


def teste_instala_limpo():
    tmp = Path(tempfile.mkdtemp(prefix="suite-b1-"))
    info = _release(tmp, "v1")
    dest, velho = _com_dest(tmp)
    try:
        res = core.azahar_instalar(info)
        afirmar(res.get("ok"), res)
        afirmar((dest / "azahar.exe").is_file(), res)
        afirmar((dest / "versao-azahar.txt").read_text(encoding="utf-8") == "v1")
        afirmar((dest / "user" / "save.txt").read_text(encoding="utf-8") == "meu save")
        afirmar(res.get("anterior") is None, res)  # limpa: nada a preservar
    finally:
        core._emu_dir = velho


def teste_upgrade_guarda_anterior():
    tmp = Path(tempfile.mkdtemp(prefix="suite-b2-"))
    dest, velho = _com_dest(tmp)
    try:
        r1 = core.azahar_instalar(_release(tmp, "v1", corpo=b"1"))
        afirmar(r1.get("ok"), r1)
        r2 = core.azahar_instalar(_release(tmp, "v2", corpo=b"2"))
        afirmar(r2.get("ok"), r2)
        ant = Path(r2["anterior"])
        afirmar(ant.is_dir(), r2)
        velho_exe = (ant / "azahar.exe").read_bytes()[:8]
        novo_exe = (dest / "azahar.exe").read_bytes()[:8]
        afirmar(velho_exe == b"11111111" and novo_exe == b"22222222",
                (velho_exe, novo_exe))
        afirmar((dest / "user" / "save.txt").is_file(), "user sumiu")
    finally:
        core._emu_dir = velho


def teste_falha_no_meio_restaura():
    tmp = Path(tempfile.mkdtemp(prefix="suite-b3-"))
    dest, velho = _com_dest(tmp)
    afirmar(core.azahar_instalar(_release(tmp, "v1", corpo=b"1")).get("ok"))
    orig_fundir = core._fundir
    core._fundir = lambda o, d: (_ for _ in ()).throw(OSError("disco cheio"))
    try:
        res = core.azahar_instalar(_release(tmp, "v2", corpo=b"2"))
    finally:
        core._fundir = orig_fundir
        core._emu_dir = velho
    afirmar(res.get("ok") is False and "restaurada" in res.get("erro", ""), res)
    afirmar((dest / "azahar.exe").read_bytes()[:8] == b"11111111", "exe trocou!")
    afirmar((dest / "user" / "save.txt").is_file(), "user sumiu")


def teste_pacote_sem_exe():
    tmp = Path(tempfile.mkdtemp(prefix="suite-b4-"))
    zp = tmp / "ruim.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("leia.txt", "nada")
    raw = zp.read_bytes()
    info = {"url": zp.as_uri(), "tag": "vx", "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}
    dest, velho = _com_dest(tmp)
    try:
        res = core.azahar_instalar(info)
    finally:
        core._emu_dir = velho
    afirmar(res.get("ok") is False and "não encontrado" in res.get("erro", ""), res)
    afirmar(not (dest / "azahar.exe").exists(), "criou exe do nada")


def teste_sha_divergente():
    tmp = Path(tempfile.mkdtemp(prefix="suite-b5-"))
    info = _release(tmp, "v1")
    info["sha256"] = "0" * 64
    dest, velho = _com_dest(tmp)
    try:
        res = core.azahar_instalar(info)
    finally:
        core._emu_dir = velho
    afirmar(res.get("ok") is False and "sha256" in res.get("erro", ""), res)


def teste_fundir_conta_falhas():
    tmp = Path(tempfile.mkdtemp(prefix="suite-b6-"))
    orig = tmp / "o"
    dst = tmp / "d"
    orig.mkdir()
    dst.mkdir()
    (orig / "a.txt").write_text("a", encoding="utf-8")
    (orig / "conflito").write_text("novo", encoding="utf-8")
    (dst / "conflito").mkdir()  # dir no caminho: unlink+move falham
    n = core._fundir(orig, dst)
    afirmar(n >= 1, n)
    afirmar((dst / "a.txt").read_text(encoding="utf-8") == "a", "ok não copiou")
