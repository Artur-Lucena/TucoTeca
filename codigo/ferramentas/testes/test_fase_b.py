"""Update com arquivos temporários: falhas, interrupção e rollback verificável."""
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from bib_nucleo import atualizacao as upd, emuladores
from executar import afirmar


def _release(tmp, tag, corpo=b"X", plataforma="nt"):
    payload = (b"MZ" if plataforma == "nt" else b"\x7fELF") + corpo * 10_000_001
    if plataforma == "nt":
        arq = tmp / (tag + ".zip")
        with zipfile.ZipFile(arq, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("azahar.exe", payload)
            for dep in ("Qt6Core.dll", "Qt6Gui.dll", "plugins/platforms/qwindows.dll"):
                z.writestr(dep, corpo * 100)
    else:
        arq = tmp / (tag + ".AppImage")
        arq.write_bytes(payload)
    return {"url": arq.as_uri(), "tag": tag, "size": arq.stat().st_size,
            "sha256": upd._sha(arq)}


def _ambiente():
    tmp = Path(tempfile.mkdtemp())
    dest = tmp / "emu"
    (dest / "user/load/mods").mkdir(parents=True)
    (dest / "user/save.txt").write_text("save intacto")
    (dest / "user/load/mods/code.ips").write_bytes(b"PATCH")
    return tmp, dest


def teste_instala_e_upgrade():
    import os
    tmp, dest = _ambiente()
    if os.name == "nt":
        with patch.object(emuladores, "_emu_dir", return_value=dest):
            r = emuladores.azahar_instalar(_release(tmp, "v1", b"1"))
        afirmar(r["ok"] and r["exe"] == str(dest / "azahar.exe"), r)
    else:
        r = upd.instalar(_release(tmp, "v1", b"1", "posix"), dest, plataforma="posix")
        afirmar(r["ok"] and r["exe"] == str(dest / "azahar.AppImage"), r)
    antes = upd._manifesto(dest)
    r = upd.instalar(_release(tmp, "v2", b"2"), dest, plataforma="nt")
    afirmar(r["ok"], r)
    afirmar(upd._manifesto(Path(r["anterior"]) / "runtime") == antes)
    afirmar((dest / upd.VERSAO).read_text() == "v2")
    afirmar((dest / "user/save.txt").read_text() == "save intacto")


def teste_falha_no_meio_restaura():
    tmp, dest = _ambiente()
    afirmar(upd.instalar(_release(tmp, "v1", b"1"), dest, plataforma="nt")["ok"])
    antes = upd._manifesto(dest)
    copiar = upd._copiar
    def falhar(orig, alvo):
        if alvo == dest / "Qt6Core.dll" and ".azahar-stage-" in str(orig):
            raise OSError("disco cheio")
        copiar(orig, alvo)
    with patch.object(upd, "_copiar", side_effect=falhar):
        r = upd.instalar(_release(tmp, "v2", b"2"), dest, plataforma="nt")
    afirmar(not r["ok"] and r["restaurado"], r)
    afirmar(upd._manifesto(dest) == antes)


def teste_interrupcao_e_recuperacao():
    tmp, dest = _ambiente()
    afirmar(upd.instalar(_release(tmp, "v1"), dest, plataforma="nt")["ok"])
    antes = upd._manifesto(dest)
    copiar = upd._copiar
    def interromper(orig, alvo):
        copiar(orig, alvo)
        if alvo == dest / "azahar.exe" and ".azahar-stage-" in str(orig):
            raise KeyboardInterrupt("simula encerramento abrupto")
    try:
        with patch.object(upd, "_copiar", side_effect=interromper):
            upd.instalar(_release(tmp, "v2", b"2"), dest, plataforma="nt")
    except KeyboardInterrupt:
        pass
    else:
        raise AssertionError("interrupção não ocorreu")
    r = upd.recuperar(dest)
    afirmar(r["ok"] and r["recuperado"], r)
    afirmar(upd._manifesto(dest) == antes)
    afirmar((dest / "user/load/mods/code.ips").read_bytes() == b"PATCH")


def teste_rollback_falho_nao_anuncia_sucesso():
    tmp, dest = _ambiente()
    afirmar(upd.instalar(_release(tmp, "v1"), dest, plataforma="nt")["ok"])
    copiar = upd._copiar
    def falhar(orig, alvo):
        if alvo.parent == dest:
            raise PermissionError("arquivo bloqueado")
        copiar(orig, alvo)
    with patch.object(upd, "_copiar", side_effect=falhar):
        r = upd.instalar(_release(tmp, "v2"), dest, plataforma="nt")
    afirmar(not r["ok"] and not r["restaurado"], r)
    afirmar((Path(r["anterior"]) / "runtime/azahar.exe").is_file())
    afirmar(upd.recuperar(dest)["ok"])


def teste_sha_e_dependencias():
    tmp, dest = _ambiente()
    info = _release(tmp, "v1")
    info["sha256"] = "0" * 64
    r = upd.instalar(info, dest, plataforma="nt")
    afirmar(not r["ok"] and "sha256" in r["erro"], r)
    arq = tmp / "incompleto.zip"
    with zipfile.ZipFile(arq, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("azahar.exe", b"MZ" + b"0" * 10_000_001)
    r = upd.instalar({"tag": "v2", "url": arq.as_uri()}, dest, plataforma="nt")
    afirmar(not r["ok"] and "dependência" in r["erro"], r)
    afirmar(not (dest / "azahar.exe").exists())


def teste_payload_nao_altera_user():
    tmp, dest = _ambiente()
    arq = tmp / "ruim.zip"
    with zipfile.ZipFile(arq, "w") as z:
        z.writestr("user/save.txt", "não pode")
    r = upd.instalar({"tag": "v2", "url": arq.as_uri()}, dest, plataforma="nt")
    afirmar(not r["ok"] and (dest / "user/save.txt").read_text() == "save intacto")


def teste_appimage_mesma_transacao():
    tmp, dest = _ambiente()
    r = upd.instalar(_release(tmp, "v1", plataforma="posix"), dest, plataforma="posix")
    afirmar(r["ok"] and (dest / "azahar.AppImage").is_file(), r)
    antes = upd._manifesto(dest)
    copiar = upd._copiar
    def falhar(orig, alvo):
        if alvo == dest / upd.VERSAO and ".azahar-stage-" in str(orig):
            raise OSError("falha ao escrever versão")
        copiar(orig, alvo)
    with patch.object(upd, "_copiar", side_effect=falhar):
        r = upd.instalar(_release(tmp, "v2", b"2", "posix"), dest, plataforma="posix")
    afirmar(not r["ok"] and r["restaurado"] and upd._manifesto(dest) == antes, r)


def teste_rollback_propaga_permissao_de_links():
    tmp, dest = _ambiente()
    stage = tmp / "stage"
    stage.mkdir()
    (stage / "novo.bin").write_bytes(b"novo")
    (dest / "antigo.bin").write_bytes(b"antigo")
    original = upd._copiar

    def copiar(orig, alvo):
        if orig == stage / "novo.bin":
            raise OSError("falha na atualização")
        return original(orig, alvo)

    with patch.object(upd, "_copiar", side_effect=copiar), \
            patch.object(upd, "recuperar", wraps=upd.recuperar) as recuperar:
        r = upd._aplicar(stage, dest, "v1", links=True)
    afirmar(not r["ok"] and r["restaurado"], r)
    afirmar(recuperar.call_args_list[-1].args == (dest, True), recuperar.call_args_list)
    afirmar((dest / "antigo.bin").read_bytes() == b"antigo")
