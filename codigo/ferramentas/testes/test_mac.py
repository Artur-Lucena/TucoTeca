"""Mac: tradução Win/Linux/Mac, exe_mac (migração v8, CRUD, import), .app e erros."""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import bib_core as core
from bib_nucleo import emuladores as EMU
from executar import afirmar


def _app_fake(pasta: Path, nome: str = "Azahar.app", binario: str = "azahar"):
    macos = pasta / nome / "Contents" / "MacOS"
    macos.mkdir(parents=True)
    (macos / binario).write_bytes(b"x" * 2_000_000)
    return pasta / nome


def _mac():
    """MAC_ROOT apontado p/ dentro do sandbox (cada teste roda em processo próprio)."""
    from bib_nucleo import base
    tmp = Path(tempfile.mkdtemp(prefix="suite-mac-"))
    mac = tmp / "macvol"
    (mac / "Games").mkdir(parents=True, exist_ok=True)
    base.MAC_ROOT = str(mac)
    return base, mac


def teste_traducao_mac_ida_e_volta():
    from bib_nucleo import base
    base, mac = _mac()
    win = base._com_barra(str(base.WIN_ROOT)).rstrip("/") + "/Games/Roms 3Ds/x.cci"
    lin = base._com_barra(str(base.LINUX_ROOT)).rstrip("/") + "/Games/Roms 3Ds/x.cci"
    m1 = base.win_para_mac(win)
    afirmar(str(Path(m1)).startswith(str(mac)), (win, m1))
    afirmar(Path(base.mac_para_win(m1)) == Path(win), (m1, win))
    m2 = base.linux_para_mac(lin)
    afirmar(str(Path(m2)).startswith(str(mac)), (lin, m2))
    afirmar(str(Path(base.mac_para_linux(m2))).lower() == str(Path(lin)).lower(), (m2, lin))
    fora = "C:\\Outro\\x.exe" if os.name == "nt" else "/tmp/outro/x"
    afirmar(base.win_para_mac(fora) == fora, fora)
    afirmar(base.mac_para_win(fora) == fora, fora)
    afirmar(base.linux_para_mac(fora) == fora, fora)
    afirmar(base.mac_para_linux(fora) == fora, fora)


def teste_traduzir_para_atual_cobre_mac():
    from bib_nucleo import base
    base, mac = _mac()
    m = base._com_barra(str(mac)).rstrip("/") + "/Games/Jogo/jogo"
    if os.name == "nt":
        afirmar(base.traduzir_para_atual(m) == base.mac_para_win(m), m)
    elif base.eh_mac():
        afirmar(base.traduzir_para_atual(m) == m, m)
    else:
        afirmar(base.traduzir_para_atual(m) == base.mac_para_linux(m), m)


def teste_resolver_exe_mac_como_fallback():
    from bib_nucleo import base
    base, mac = _mac()
    raiz = base.WIN_ROOT if os.name == "nt" else base.LINUX_ROOT
    # no Windows, fallback de outro SO só vale se for executável Win
    # (.AppImage/binário Mac existe no disco mas nunca abre aqui)
    nome = "mac-fallback.exe" if os.name == "nt" else "mac-fallback.bin"
    real = Path(str(raiz).rstrip("\\/")) / "Games" / nome
    real.parent.mkdir(parents=True, exist_ok=True)
    real.write_bytes(b"BIN")
    conv = base.win_para_mac if os.name == "nt" else base.linux_para_mac
    gravado = conv(str(real))
    afirmar(gravado != str(real), (gravado, str(real)))
    exe, origem = base.resolver_exe({"executable_path": "", "exe_win": "",
                                     "exe_linux": "", "exe_mac": gravado})
    afirmar(Path(exe) == real and origem == "exe_mac", (exe, str(real)))
    campo_so = "exe_win" if os.name == "nt" else "exe_linux"
    outro = dict(executable_path="", exe_win="", exe_linux="", exe_mac=gravado)
    outro[campo_so] = str(real)
    exe2, origem2 = base.resolver_exe(outro)
    afirmar(Path(exe2) == real and origem2 == campo_so, (exe2, str(real)))


def teste_resolver_legado_vence_appimage_no_windows():
    if os.name != "nt":
        print("(só Windows: skip)")
        return
    from bib_nucleo import base
    raiz = Path(str(base.WIN_ROOT).rstrip("\\/")) / "Games"
    raiz.mkdir(parents=True, exist_ok=True)
    exe = raiz / "emu-real.exe"
    exe.write_bytes(b"MZ")
    img = raiz / "emu-linux.AppImage"
    img.write_bytes(b"\x7fELF")
    r = {"executable_path": str(exe), "exe_win": "", "exe_linux": str(img), "exe_mac": ""}
    exe_f, origem = base.resolver_exe(r)
    afirmar(exe_f == str(exe) and origem == "executavel", (exe_f, origem))
    r2 = {"executable_path": str(raiz / "sumiu.exe"), "exe_win": "",
          "exe_linux": str(exe), "exe_mac": ""}
    exe_f2, origem2 = base.resolver_exe(r2)
    afirmar(exe_f2 == str(exe) and origem2 == "exe_linux", (exe_f2, origem2))


def teste_exe_mac_crud_e_migracao_v8():
    tmp = Path(tempfile.mkdtemp(prefix="suite-mac-"))
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
    con.commit()
    con.close()
    con = core.get_db(leg)
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(jogos)").fetchall()}
        afirmar("exe_mac" in cols, sorted(cols))
        g = core.criar_jogo(con, {"titulo": "M", "executable_path": "",
                                  "exe_mac": "/Volumes/Games/Games/m",
                                  "status": "backlog"})
        afirmar(g["exe_mac"] == "/Volumes/Games/Games/m", g)
        c = core.atualizar_jogo(con, g["id"], {"nota": 7})  # preserva
        afirmar(c["exe_mac"] == "/Volumes/Games/Games/m", c)
        afirmar("exe_mac" in core.CAMPOS_EDITAVEIS, core.CAMPOS_EDITAVEIS)
    finally:
        con.close()


def teste_importar_lista_leva_exe_mac():
    tmp = Path(tempfile.mkdtemp(prefix="suite-mac-"))
    con = core.get_db(tmp / "t.db")
    try:
        res = core.importar_lista(con, [{"titulo": "Mac Game", "executable_path": "",
                                         "exe_mac": "/Volumes/Games/Games/m",
                                         "origem": "manual"}])
        afirmar(res.get("novos") == 1, res)
        jogos = core.listar_jogos(con, q="Mac Game")
        afirmar(len(jogos) == 1 and jogos[0]["exe_mac"] == "/Volumes/Games/Games/m", jogos)
    finally:
        con.close()


def teste_app_macos_resolve_binario():
    tmp = Path(tempfile.mkdtemp(prefix="suite-mac-"))
    _app_fake(tmp / "Emu", "Azahar.app", "azahar")
    exe = EMU._app_macos(tmp / "Emu")
    afirmar(exe.endswith(os.path.join("Azahar.app", "Contents", "MacOS", "azahar")), exe)
    afirmar(EMU._app_macos(tmp / "vazia-inexistente") == "")
    (tmp / "oco").mkdir()
    afirmar(EMU._app_macos(tmp / "oco") == "")


def teste_default_emu_3ds_no_mac_acha_app():
    base, mac = _mac()
    emu = mac / "Games" / "Emuladores" / "Azahar"
    emu.mkdir(parents=True)
    _app_fake(emu)
    # a sandbox fixa BIBLIOTECA_AZAHAR_DIR: este ramo é o override
    velha, velho_dir = sys.platform, os.environ.get("BIBLIOTECA_AZAHAR_DIR")
    os.environ["BIBLIOTECA_AZAHAR_DIR"] = str(emu)
    sys.platform = "darwin"
    try:
        exe = EMU.default_emu_3ds()
        afirmar(exe.endswith(os.path.join("Azahar.app", "Contents", "MacOS", "azahar")), exe)
        ud = EMU.azahar_user_dir(exe)
        afirmar(ud == "", ud)  # sem user/ ainda: vazio honesto, não lixo do Linux
        (emu / "user").mkdir()
        afirmar(EMU.azahar_user_dir(exe) == str(emu / "user"))
    finally:
        sys.platform = velha
        if velho_dir is None:
            os.environ.pop("BIBLIOTECA_AZAHAR_DIR", None)
        else:
            os.environ["BIBLIOTECA_AZAHAR_DIR"] = velho_dir


def teste_default_emu_3ds_no_mac_ramo_padrao():
    base, mac = _mac()
    emu = mac / "Games" / "Emuladores" / "Azahar"
    emu.mkdir(parents=True)
    _app_fake(emu)
    # sem override: cai no padrão MAC_ROOT (importado por valor no EMU)
    velha, velho_dir, velho_root = (sys.platform,
                                    os.environ.pop("BIBLIOTECA_AZAHAR_DIR", None),
                                    EMU.MAC_ROOT)
    EMU.MAC_ROOT = str(mac)
    sys.platform = "darwin"
    try:
        exe = EMU.default_emu_3ds()
        afirmar(exe.endswith(os.path.join("Azahar.app", "Contents", "MacOS", "azahar")), exe)
    finally:
        sys.platform = velha
        EMU.MAC_ROOT = velho_root
        if velho_dir is not None:
            os.environ["BIBLIOTECA_AZAHAR_DIR"] = velho_dir


def teste_asset_matchers_por_so():
    velha = sys.platform
    try:
        sys.platform = "darwin"
        afirmar(EMU._asset_azahar_ok("azahar-macos-universal-2126.1.2.zip"))
        afirmar(not EMU._asset_azahar_ok("azahar.AppImage"))
        afirmar(not EMU._asset_azahar_ok("azahar-windows-msys2-2126.1.2.zip"))
        afirmar(EMU._asset_desmume_ok("desmume-0.9.13-macOS.dmg"))
        afirmar(not EMU._asset_desmume_ok("desmume-0.9.13-win64.zip"))
    finally:
        sys.platform = velha


def teste_lancar_exe_sem_wine_no_mac_mensagem():
    if os.name == "nt":
        print("(só posix: skip)")
        return
    import shutil
    if shutil.which("wine") or shutil.which("wine64"):
        print("(com wine: skip)")
        return
    from bib_nucleo import emuladores as EMU
    tmp = Path(tempfile.mkdtemp(prefix="suite-mac-"))
    exe = tmp / "jogo.exe"
    exe.write_bytes(b"MZ")
    anterior = sys.platform
    try:
        sys.platform = "darwin"  # eh_mac() lê ao vivo; os.name segue posix
        res, _ = EMU._lancar(str(exe))
    finally:
        sys.platform = anterior
    afirmar(not res.get("ok") and "Mac" in (res.get("erro") or ""), res)
