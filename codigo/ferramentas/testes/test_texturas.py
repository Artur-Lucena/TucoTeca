"""Texturas HD: toggle por rename (<tid>/ <-> <tid>.off), sem banco, sem rede."""
import os
import tempfile
from pathlib import Path

import bib_core as core  # noqa: F401  (garante import do núcleo no sandbox)
from executar import afirmar

TID = "000400000011C400"


def _emu_fake():
    emu = Path(os.environ.get("BIBLIOTECA_AZAHAR_DIR"))
    (emu / "user").mkdir(parents=True, exist_ok=True)
    (emu / "azahar.exe").write_bytes(b"MZ" + b"0" * 64)
    return emu


def _pack(tmp, nome="pack", n=3):
    d = Path(tempfile.mkdtemp(prefix="suite-tex-", dir=str(tmp))) / nome
    (d / "sub").mkdir(parents=True)
    for i in range(n):
        (d / "sub" / f"tex{i}.png").write_bytes(b"\x89PNG" + b"0" * 64)
    (d / "notas.txt").write_bytes(b"doc")
    return d


def teste_texturas_base_e_skip():
    from bib_nucleo import base
    from bib_nucleo import scans
    afirmar("texturas" in scans.SKIP_DIRS, sorted(scans.SKIP_DIRS))
    afirmar("TEXTURAS_DIR" in base.__all__, base.__all__)
    base.garantir_dirs()
    afirmar(Path(str(base.TEXTURAS_DIR)).is_dir(), str(base.TEXTURAS_DIR))


def teste_texturas_instalar_listar_alternar():
    from bib_nucleo import texturas as TEX
    tmp = Path(tempfile.mkdtemp(prefix="suite-tex-"))
    _emu_fake()
    afirmar(TEX.load_textures_dir() is not None)
    afirmar(TEX.listar_texturas() == [])
    r = TEX.instalar_textura("curto", str(_pack(tmp, "a")))
    afirmar(not r.get("ok"), r)
    r = TEX.instalar_textura(TID, str(tmp / "nao-existe"))
    afirmar(not r.get("ok"), r)
    vazio = Path(tmp) / "vazio"
    vazio.mkdir()
    r = TEX.instalar_textura(TID, str(vazio))
    afirmar(not r.get("ok") and "png" in r["erro"], r)
    r = TEX.instalar_textura(TID, str(_pack(tmp, "hd")))
    afirmar(r.get("ok") and r["arquivos"] == 3, r)
    lst = TEX.listar_texturas()
    afirmar(len(lst) == 1 and lst[0]["ativo"] and lst[0]["arquivos"] == 4, lst)
    afirmar(TEX.tem_textura(TID))
    r = TEX.definir_textura(TID, False)
    afirmar(r.get("ok") and not r["ativo"], r)
    afirmar(not TEX.tem_textura(TID))
    lst = TEX.listar_texturas()
    afirmar(len(lst) == 1 and not lst[0]["ativo"], lst)
    r = TEX.alternar_textura(TID)
    afirmar(r.get("ok") and r["ativo"], r)
    afirmar(TEX.tem_textura(TID))
    r = TEX.instalar_textura(TID, str(_pack(tmp, "outra")))
    afirmar(not r.get("ok") and "instalado" in r["erro"], r)
    r = TEX.alternar_textura("0004000000999999")
    afirmar(not r.get("ok"), r)


def teste_texturas_ignora_lixo():
    from bib_nucleo import texturas as TEX
    tmp = Path(tempfile.mkdtemp(prefix="suite-tex-"))
    _emu_fake()
    base = TEX.load_textures_dir()
    (base / "leia-me.txt").write_bytes(b"x")
    (base / "123").mkdir()
    link = base / "000400000011C500"
    try:
        link.symlink_to(base / "123")
    except OSError:
        pass  # sem privilégio: pula a parte do link
    lst = TEX.listar_texturas()
    afirmar(lst == [], lst)


def teste_texturas_estado_e_flag():
    import configparser
    from bib_nucleo import texturas as TEX
    tmp = Path(tempfile.mkdtemp(prefix="suite-tex-"))
    emu = _emu_fake()
    afirmar(TEX.flag_custom_textures() is None)
    est = TEX.estado_textura(TID)
    afirmar(est == {"tid": TID, "instalado": False, "ativo": False,
                    "arquivos": 0, "mb": 0.0}, est)
    est = TEX.estado_textura("curto")
    afirmar(not est["instalado"], est)
    cfgdir = emu / "user" / "config"
    cfgdir.mkdir(parents=True, exist_ok=True)
    ini = configparser.ConfigParser()
    ini.optionxform = str
    ini["Utility"] = {"custom_textures": "true"}
    with open(cfgdir / "qt-config.ini", "w", encoding="utf-8") as fh:
        ini.write(fh)
    afirmar(TEX.flag_custom_textures() is True)
    ini["Utility"] = {"custom_textures": "false"}
    with open(cfgdir / "qt-config.ini", "w", encoding="utf-8") as fh:
        ini.write(fh)
    afirmar(TEX.flag_custom_textures() is False)


def teste_preparar_lancamento_avisa_hd_sem_flag():
    import configparser
    from bib_nucleo import emuladores as EMU
    from bib_nucleo import texturas as TEX
    tmp = Path(tempfile.mkdtemp(prefix="suite-tex-"))
    emu = _emu_fake()
    head = bytearray(0x200)
    head[0x100:0x104] = b"NCCH"
    head[0x118:0x120] = bytes.fromhex(TID)[::-1]
    rom = Path(tmp) / "t.cci"
    rom.write_bytes(bytes(head))
    jogo = {"origem": "rom-3ds", "launch_options": str(rom),
            "azahar_preset": "", "azahar_mods": []}
    r = EMU.preparar_lancamento(jogo)
    afirmar("hd2x" not in (r["aviso"] or ""), r)
    base = TEX.load_textures_dir()
    (base / TID).mkdir(parents=True)
    (base / TID / "tex1_1x1_AAAAAAAAAAAAAAAA_1.png").write_bytes(b"\x89PNG")
    r = EMU.preparar_lancamento(jogo)
    afirmar("hd2x" not in (r["aviso"] or ""), r)  # sem ini: flag None
    cfgdir = emu / "user" / "config"
    cfgdir.mkdir(parents=True, exist_ok=True)
    ini = configparser.ConfigParser()
    ini.optionxform = str
    ini["Utility"] = {"custom_textures": "false"}
    with open(cfgdir / "qt-config.ini", "w", encoding="utf-8") as fh:
        ini.write(fh)
    r = EMU.preparar_lancamento(jogo)
    afirmar(r["aviso"] is not None and "hd2x" in r["aviso"], r)
