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
    base, mac = _mac()
    win = base._com_barra(str(base.WIN_ROOT)).rstrip("/") + "/Games/Roms 3Ds/x.cci"
    lin = base._com_barra(str(base.LINUX_ROOT)).rstrip("/") + "/Games/Roms 3Ds/x.cci"
    m1 = base.win_para_mac(win)
    afirmar(str(Path(m1)).startswith(str(mac)), (win, m1))
    afirmar(base._com_barra(base.mac_para_win(m1)) == base._com_barra(win), (m1, win))
    m2 = base.linux_para_mac(lin)
    afirmar(str(Path(m2)).startswith(str(mac)), (lin, m2))
    afirmar(base._com_barra(base.mac_para_linux(m2)).lower() == base._com_barra(lin).lower(), (m2, lin))
    fora = "C:\\Outro\\x.exe" if os.name == "nt" else "/tmp/outro/x"
    afirmar(base.win_para_mac(fora) == fora, fora)
    afirmar(base.mac_para_win(fora) == fora, fora)
    afirmar(base.linux_para_mac(fora) == fora, fora)
    afirmar(base.mac_para_linux(fora) == fora, fora)


def teste_traduzir_para_atual_cobre_mac():
    base, mac = _mac()
    m = base._com_barra(str(mac)).rstrip("/") + "/Games/Jogo/jogo"
    if os.name == "nt":
        afirmar(base.traduzir_para_atual(m) == base.mac_para_win(m), m)
    elif base.eh_mac():
        afirmar(base.traduzir_para_atual(m) == m, m)
    else:
        afirmar(base.traduzir_para_atual(m) == base.mac_para_linux(m), m)


def teste_resolver_exe_mac_como_fallback():
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


def teste_extrair_app_mac_dmg_com_hdiutil_mockado():
    from bib_nucleo import atualizacao as ATUAL
    tmp = Path(tempfile.mkdtemp(prefix="suite-mac-"))
    dmg = tmp / "fake.dmg"
    dmg.write_bytes(b"DMGfake")
    stage = tmp / "stage"
    stage.mkdir()
    chamadas = []

    class R:
        def __init__(self, rc):
            self.returncode = rc
            self.stderr = ""

    def fake_run(cmd, **kw):
        chamadas.append(cmd)
        if cmd[1] == "attach":
            mnt = Path(cmd[cmd.index("-mountpoint") + 1])
            macos = mnt / "Fake.app" / "Contents" / "MacOS"
            macos.mkdir(parents=True)
            (macos / "fakebin").write_bytes(b"x" * 2_000_000)
            return R(0)
        return R(0)  # detach

    velho = ATUAL.subprocess.run
    ATUAL.subprocess.run = fake_run
    try:
        nome = ATUAL._extrair_app_mac(dmg, stage)
    finally:
        ATUAL.subprocess.run = velho
    afirmar(nome == "Fake.app", nome)
    afirmar((stage / "Fake.app" / "Contents" / "MacOS" / "fakebin").is_file())
    afirmar(any(c[1] == "detach" for c in chamadas), "não desmontou!")


def teste_extrair_app_mac_zip_rejeita_macosx():
    import zipfile

    from bib_nucleo import atualizacao as ATUAL
    tmp = Path(tempfile.mkdtemp(prefix="suite-mac-"))
    zf = tmp / "fake.zip"
    with zipfile.ZipFile(zf, "w") as z:
        z.writestr("Top/Fake.app/Contents/MacOS/fakebin", b"x" * 2_000_000)
        z.writestr("__MACOSX/lixo", b"meta")
    stage = tmp / "stage"
    stage.mkdir()
    try:
        ATUAL._extrair_app_mac(zf, stage)
        afirmar(False, "aceitou __MACOSX?")
    except ValueError:
        pass


def teste_links_darwin_internos_e_vetos():
    from bib_nucleo import atualizacao as ATUAL
    tmp = Path(tempfile.mkdtemp(prefix="suite-mac-"))
    raiz = tmp / "rt"
    (raiz / "sub").mkdir(parents=True)
    (raiz / "sub" / "real.bin").write_bytes(b"R" * 100)
    try:
        (raiz / "sonda").symlink_to(raiz / "sub" / "real.bin")
    except OSError:
        print("[pula] sem privilégio de symlink (WinError 1314)")
        return
    (raiz / "sonda").unlink()
    fora = tmp / "fora.bin"
    fora.write_bytes(b"F" * 100)
    (raiz / "ok-link").symlink_to(raiz / "sub" / "real.bin")
    arqs = ATUAL._arquivos(raiz, links=True)
    afirmar("ok-link" in arqs and "sub/real.bin" in arqs, sorted(arqs))
    afirmar(ATUAL._manifesto(raiz, links=True)["ok-link"].startswith("link->"))
    (raiz / "externo").symlink_to(fora)
    try:
        ATUAL._arquivos(raiz, links=True)
        afirmar(False, "aceitou link externo?")
    except ValueError:
        pass
    (raiz / "externo").unlink()
    (raiz / "quebrado").symlink_to(raiz / "sumiu.bin")
    try:
        ATUAL._arquivos(raiz, links=True)
        afirmar(False, "aceitou link quebrado?")
    except ValueError:
        pass
    (raiz / "quebrado").unlink()
    (raiz / "loop-a").symlink_to(raiz / "loop-b")
    (raiz / "loop-b").symlink_to(raiz / "loop-a")
    try:
        ATUAL._arquivos(raiz, links=True)
        afirmar(False, "aceitou loop?")
    except ValueError:
        pass
    (raiz / "loop-a").unlink()
    (raiz / "loop-b").unlink()
    try:
        ATUAL._arquivos(raiz)  # links=False: veto clássico
        afirmar(False, "aceitou link sem flag?")
    except ValueError:
        pass


def teste_tocar_musica_cai_no_dados_local():
    from bib_nucleo import base as B
    from bib_nucleo import musicas as MUS
    tmp = Path(tempfile.mkdtemp(prefix="suite-mac-"))
    casa = tmp / "dados" / "musicas"
    casa.mkdir(parents=True)
    (casa / "x.mp3").write_bytes(b"ID3fake")
    chamadas = []
    velho_pop, velho_dir = MUS.subprocess.Popen, B.MUSICAS_DIR
    MUS.subprocess.Popen = lambda *a, **k: chamadas.append(a) or object()
    B.MUSICAS_DIR = casa  # tocar_musica lê base.MUSICAS_DIR ao vivo
    tinha_start = hasattr(os, "startfile")
    if tinha_start:
        velho_start = os.startfile
        os.startfile = lambda p: chamadas.append(p)
    try:
        r = MUS.tocar_musica(str(tmp / "outra-maquina" / "x.mp3"))
        afirmar(r.get("ok") and r.get("path") == str(casa / "x.mp3"), r)
        afirmar(chamadas, "não chamou o player?")
        r2 = MUS.tocar_musica(str(tmp / "sumiu.mp3"))
        afirmar(not r2.get("ok"), r2)
    finally:
        MUS.subprocess.Popen = velho_pop
        B.MUSICAS_DIR = velho_dir
        if tinha_start:
            os.startfile = velho_start


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


def teste_update_dmg_preserva_sufixo_no_download():
    from unittest.mock import patch

    from bib_nucleo import atualizacao as ATUAL
    tmp = Path(tempfile.mkdtemp(prefix="suite-mac-"))

    class Resp:
        headers = {"Content-Length": "4"}
        def __init__(self):
            self.raw = b"DMG!"
        def read(self, _n):
            raw, self.raw = self.raw, b""
            return raw
        def __enter__(self):
            return self
        def __exit__(self, *_exc):
            pass

    def extrair(pacote, stage):
        afirmar(pacote.suffix == ".dmg", "download perdeu a extensão do asset")
        _app_fake(stage, "DeSmuME.app", "desmume")
        return "DeSmuME.app"

    with patch.object(ATUAL.urllib.request, "urlopen", return_value=Resp()), \
            patch.object(ATUAL, "_extrair_app_mac", side_effect=extrair):
        r = ATUAL.instalar({"url": "https://x/emu.dmg", "nome": "emu.dmg", "tag": "v1", "size": 4},
                          tmp / "emu", plataforma="darwin")
    afirmar(r["ok"], r)


def teste_zip_mac_rejeita_link_externo_antes_de_ativar():
    import stat
    import zipfile

    from bib_nucleo import atualizacao as ATUAL
    tmp = Path(tempfile.mkdtemp(prefix="suite-mac-"))
    zip_path = tmp / "app.zip"
    link = zipfile.ZipInfo("Azahar.app/Contents/evil")
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(zip_path, "w") as out:
        out.writestr(link, "../../../../fora")
    stage = tmp / "stage"
    stage.mkdir()
    try:
        ATUAL._extrair_app_mac(zip_path, stage)
        afirmar(False, "aceitou link externo")
    except ValueError as e:
        afirmar("link externo" in str(e), e)
