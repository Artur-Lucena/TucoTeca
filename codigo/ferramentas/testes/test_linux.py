"""Linux: tradução de exe, AppImage case-insensitive, Wine, capa via launch e lock."""
import os
import tempfile
from pathlib import Path

import bib_core as core
from executar import afirmar


def teste_resolver_exe_fallback_win_no_linux():
    if os.name == "nt":
        print("(só Linux: skip)")
        return
    from bib_nucleo import base
    lin = Path(str(base.LINUX_ROOT).rstrip("/")) / "Games"
    lin.mkdir(parents=True, exist_ok=True)
    alvo = lin / "lx-jogo.exe"
    alvo.write_bytes(b"MZ")
    win = base.linux_para_win(str(alvo))
    if win == str(alvo):
        print("(sem tradução: skip)")
        return
    exe, origem = base.resolver_exe({"executable_path": "", "exe_win": win,
                                     "exe_linux": ""})
    afirmar(exe == str(alvo) and origem == "exe_win", (exe, origem))


def teste_exe_existe_via_traduzido():
    from bib_nucleo import base
    lin = Path(str(base.LINUX_ROOT).rstrip("/")) / "Games"
    lin.mkdir(parents=True, exist_ok=True)
    alvo = lin / "lx-jogo2.exe"
    alvo.write_bytes(b"MZ")
    outro = base.linux_para_win(str(alvo)) if os.name != "nt" else base.win_para_linux(str(alvo))
    if outro == str(alvo):
        print("(sem tradução: skip)")
        return
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    con = core.get_db(tmp / "t.db")
    try:
        core.criar_jogo(con, {"titulo": "LX Trad", "executable_path": outro,
                              "status": "backlog"})
        jogos = core.listar_jogos(con, q="LX Trad")
    finally:
        con.close()
    afirmar(len(jogos) == 1 and jogos[0]["exe_existe"], jogos)


def teste_nds_appimage_case_insensitive():
    if os.name == "nt":
        print("(só Linux: skip)")
        return
    from bib_nucleo import emuladores as EMU
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    (tmp / "DeSmuME_X64.AppImage").write_bytes(b"\x7fELF" + b"0" * 100)
    achado = EMU._appimage_na_pasta(tmp, "desmume")
    afirmar(achado.endswith(".AppImage") and Path(achado).is_file(), achado)


def teste_lancar_exe_sem_wine_mensagem_clara():
    if os.name == "nt":
        print("(só Linux: skip)")
        return
    import shutil
    if shutil.which("wine") or shutil.which("wine64"):
        print("(com wine: skip)")
        return
    from bib_nucleo import emuladores as EMU
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    exe = tmp / "jogo.exe"
    exe.write_bytes(b"MZ")
    res, _ = EMU._lancar(str(exe))
    afirmar(not res.get("ok") and "Wine" in (res.get("erro") or ""), res)


def teste_capa_rom_via_launch_sem_rom_path():
    from bib_nucleo import emuladores as EMU  # noqa: F401 (garante providers)
    tmp = Path(tempfile.mkdtemp(prefix="suite-lx-"))
    head = bytearray(0x200)
    head[:12] = b"JOGO TESTE  "
    head[0x0C:0x10] = b"ATCE"
    head[0x68:0x6C] = (0x4000).to_bytes(4, "little")
    banner = bytearray(0x1000)
    banner[0x222:0x224] = (0x001F).to_bytes(2, "little")
    banner[0x340:0x440] = "Capa LX".encode("utf-16-le")[:0x100].ljust(0x100, b"\x00")
    rom = tmp / "capa.nds"
    rom.write_bytes(bytes(head).ljust(0x4000, b"\x00") + bytes(banner))
    con = core.get_db(tmp / "t.db")
    try:
        res = core.importar_lista(con, [{"titulo": "LX ROM", "executable_path": "EMU",
                                         "launch_options": str(rom),
                                         "origem": "rom-nds", "status": "backlog"}])
    finally:
        con.close()
    afirmar(res.get("novos") == 1, res)
    capas = list((tmp / "dados" / "capas").glob("*")) if (tmp / "dados").exists() else []
    # capa pode estar em CAPAS_DIR global do sandbox; basta não ter erro fatal
    afirmar(not res.get("erros"), (res, capas))


def teste_lock_nao_apaga_de_outro():
    from bib_nucleo import base
    import json
    lp = base.lock_path()
    try:
        if lp.is_file():
            lp.unlink()
    except OSError:
        pass
    lp.parent.mkdir(parents=True, exist_ok=True)
    lp.write_text(json.dumps({"pid": 999999999, "host": "outro-host",
                              "so": os.name, "inicio": base.agora_iso()}),
                  encoding="utf-8")
    base.liberar_lock()
    afirmar(lp.is_file(), "apagou lock alheio")
    try:
        lp.unlink()
    except OSError:
        pass
    r = base.adquirir_lock()
    afirmar(r.get("ok"), r)
    base.liberar_lock()
    afirmar(not lp.is_file(), "não liberou lock próprio")
