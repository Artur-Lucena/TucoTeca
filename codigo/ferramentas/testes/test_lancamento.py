"""Lançamento de jogos e presets de emulador: caminhos do Windows, sessão rastreada e diagnóstico.

Processo, UAC (ShellExecute) e GPU são simulados: nenhum jogo roda e nenhum
prompt de administrador abre. Os caminhos de Linux/Mac ficam em
test_linux_portabilidade e test_mac.
"""
import ctypes
import os
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

from bib_nucleo import emuladores as EMU
from bib_nucleo.emuladores import lancamento as L
from bib_nucleo.emuladores import presets as P
from executar import afirmar


def _pasta() -> Path:
    return Path(tempfile.mkdtemp())


class _Proc:
    pid = 77

    def __init__(self, espera=None):
        self.espera = espera

    def wait(self):
        if self.espera is not None:
            self.espera.wait(5)


def teste_lancar_no_windows_popen_atalho_e_elevacao():
    if os.name != "nt":
        afirmar(L.executar_elevado("x.exe") == {"ok": False, "erro": "elevação só existe no Windows"})
        return
    raiz = _pasta()
    exe = raiz / "Jogo Bom" / "jogo.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"MZ")
    chamadas = []
    with patch.object(L.subprocess, "Popen", side_effect=lambda cmd, **k: chamadas.append((cmd, k)) or _Proc()):
        r, proc = L._lancar(str(exe), wine_prefix="C:/vinho", launch_options='"C:\\com espaco\\a.cci" -f')
    afirmar(r == {"ok": True, "modo": "popen-windows"} and isinstance(proc, _Proc), r)
    cmd, k = chamadas[0]
    afirmar(cmd == [str(exe), "C:\\com espaco\\a.cci", "-f"] and k["cwd"] == str(exe.parent), cmd)
    afirmar(k["env"]["WINEPREFIX"] == "C:/vinho")
    atalho = raiz / "jogo.lnk"
    atalho.write_bytes(b"L")
    abertos = []
    with patch.object(L._E.os, "startfile", side_effect=abertos.append, create=True):
        afirmar(L._lancar(str(atalho)) == ({"ok": True, "modo": "startfile"}, None))
    afirmar(abertos == [str(atalho)])
    erro = OSError("requer elevação")
    erro.winerror = 740
    with patch.object(L.subprocess, "Popen", side_effect=erro):
        r, proc = L._lancar(str(exe))
    afirmar(r["requer_elevacao"] and proc is None and "administrador" in r["erro"], r)
    with patch.object(L.subprocess, "Popen", side_effect=ValueError("ruim")):
        afirmar(L._lancar(str(exe))[0] == {"ok": False, "erro": "ValueError: ruim"})
    afirmar(L._lancar("")[0]["erro"] == "Jogo sem caminho de executável cadastrado.")
    afirmar(L._lancar(str(raiz / "sumiu.exe"))[0]["erro"].startswith("Executável não encontrado"))


def teste_executar_elevado_simulado():
    if os.name != "nt":
        return
    exe = _pasta() / "jogo.exe"
    exe.write_bytes(b"MZ")

    class Shell:
        def __init__(self, rc):
            self.rc = rc
            self.ShellExecuteW = self

        def __call__(self, *args):
            self.args = args
            return self.rc

    with patch.object(ctypes, "WinDLL", lambda nome, use_last_error=False: Shell(42), create=True):
        afirmar(L.executar_elevado(str(exe), "-x") == {"ok": True, "modo": "runas-uac"})
        afirmar(L._lancar(str(exe), elevar=True)[0] == {"ok": True, "modo": "runas-uac"})
    with patch.object(ctypes, "WinDLL", lambda nome, use_last_error=False: Shell(5), create=True):
        afirmar(L.executar_elevado(str(exe))["erro"] == "UAC recusou/falhou (código 5)")
    afirmar(L.executar_elevado(str(exe.parent / "nao.exe"))["erro"].startswith("Executável não encontrado"))


def teste_gpu_nvidia_e_prefixo_wine():
    class Saida:
        returncode, stdout = 0, "NVIDIA GeForce RTX 4060\n"

    with patch("shutil.which", return_value="nvidia-smi"), patch("subprocess.run", return_value=Saida()):
        afirmar(L._tem_nvidia() == "NVIDIA GeForce RTX 4060")
    with patch("shutil.which", return_value=None), patch.object(L.Path, "is_file", return_value=False):
        afirmar(L._tem_nvidia() == "")
    prefixo = Path(L.prefixo_wine_hub())
    afirmar(prefixo.is_dir() and prefixo.name == "wine", prefixo)


def teste_sessao_rastreada_e_manual():
    fim = threading.Event()
    vistos = []
    libera = threading.Event()
    with patch.object(EMU, "_lancar_jogo_dict", return_value=({"ok": True}, _Proc(libera))):
        r = L.executar_monitorado({"id": 1}, lambda h, rast: (vistos.append((h, rast)), fim.set()), limiar_s=0)
        libera.set()
        afirmar(fim.wait(5) and r["rastreado"] and vistos[0][1] is True, vistos)
    manuais = []
    with patch.object(EMU, "_lancar_jogo_dict", return_value=({"ok": True, "modo": "startfile"}, None)), \
            patch.object(L, "iniciar_sessao_manual", side_effect=lambda i, t: manuais.append((i, t))):
        fins = []
        r = L.executar_monitorado({"id": 3, "titulo": "Hades"}, lambda h, rast: fins.append((h, rast)))
        afirmar(not r["rastreado"] and fins == [(0.0, False)] and manuais == [(3, "Hades")], (r, fins, manuais))
        afirmar(L.executar_monitorado({"id": 4, "titulo": "Sem vigia"})["rastreado"] is False)
        afirmar(manuais[-1] == (4, "Sem vigia"))
    curtos = []
    L._vigiar_processo(_Proc(), 3600, lambda h, rast: curtos.append((h, rast)))
    afirmar(curtos == [(0.0, True)])  # abaixo do limiar não conta horas


def teste_diagnostico_de_exe_e_rom():
    raiz = _pasta()
    exe = raiz / "jogo.exe"
    exe.write_bytes(b"MZ")
    afirmar(L.diagnosticar_exe({})["estado"] == "sem-exe")
    afirmar(L.diagnosticar_exe({"executable_path": str(exe)})["estado"] == "ok")
    afirmar(L.diagnosticar_exe({"executable_path": str(raiz / "x.exe")})["estado"] == "ausente")
    prov = {"exe": lambda: str(exe), "chave": "azahar", "nome": "Azahar"}
    with patch.object(L, "provedor_por_origem", return_value=prov):
        d = L.diagnosticar_exe({"executable_path": str(raiz / "antigo" / "azahar.exe"), "origem": "rom-3ds"})
    afirmar(d["estado"] == "trocou-emulador" and d["atual"] == str(exe), d)

    roms = raiz / "roms" / "3ds"
    roms.mkdir(parents=True)
    (roms / "Zelda.3DS").write_bytes(b"x")
    afirmar(L.diagnosticar_rom({"origem": "pc", "launch_options": "x.3ds"})["estado"] == "nao-rom")
    afirmar(L.diagnosticar_rom({"origem": "rom-3ds", "launch_options": "-fullscreen"})["estado"] == "nao-rom")
    afirmar(L.diagnosticar_rom({"origem": "rom-3ds", "launch_options": str(roms / "Zelda.3DS")})["estado"] == "ok")
    with patch.object(EMU, "procurar_rom", side_effect=lambda nome: L.procurar_rom(nome, [str(raiz / "roms")])):
        d = L.diagnosticar_rom({"origem": "rom-3ds", "launch_options": '"D:\\velho\\zelda.3ds"'})
    afirmar(d["estado"] == "rom-ausente" and d["candidatos"] == [str((roms / "Zelda.3DS").resolve())], d)
    afirmar(L.procurar_rom("") == [] and L.procurar_rom("zelda.3ds", [str(raiz / "nada")]) == [])


def teste_launch_da_rom_e_rom_criptografada():
    prov = {"flags": lambda: ["-f"]}
    afirmar(L.montar_launch_rom(prov, "D:/com espaco/a.3ds") == '-f "D:/com espaco/a.3ds"')
    afirmar(L.montar_launch_rom({"flags": lambda: []}, "a.3ds") == "a.3ds")
    raiz = _pasta()
    ncch = bytearray(0x200)
    ncch[0x100:0x104] = b"NCCH"
    cripto = raiz / "cripto.3ds"
    cripto.write_bytes(bytes(ncch))
    afirmar(L.rom_parece_criptografada(str(cripto)))
    ncch[0x18F] = 0x04  # NoCrypto
    ncsd = bytearray(0x200)
    ncsd[0x100:0x104] = b"NCSD"
    ncsd[0x120:0x124] = (1).to_bytes(4, "little")
    limpa = raiz / "limpa.3ds"
    limpa.write_bytes(bytes(ncsd) + bytes(ncch))
    afirmar(not L.rom_parece_criptografada(str(limpa)))
    afirmar(not L.rom_parece_criptografada(str(raiz / "sumiu.3ds")) and not L.rom_parece_criptografada(""))


def _prov_falso(user_dir: str):
    return {"teste": {"nome": "Teste", "user_dir": lambda: user_dir, "saves_subs": ["sdmc", "nand"]}}


def teste_backup_de_saves_do_emulador():
    ud = _pasta()
    with patch.object(P, "provedores", return_value=_prov_falso(str(ud))):
        afirmar(P.backup_saves_emu("teste")["erro"] == "sem saves ainda (saves vazios ou ausentes)")
        (ud / "sdmc" / "a").mkdir(parents=True)
        (ud / "sdmc" / "a" / "save.bin").write_bytes(b"1")
        (ud / "nand" / "b.bin").parent.mkdir()
        (ud / "nand" / "b.bin").write_bytes(b"2")
        r = P.backup_saves_emu("teste", manter=1)
        afirmar(r["ok"] and r["arquivos"] == 2 and Path(r["arquivo"]).is_file(), r)
    with patch.object(P, "provedores", return_value=_prov_falso("")):
        afirmar(P.backup_saves_emu("teste")["erro"] == "Teste não instalado")
    afirmar("desconhecido" in P.backup_saves_emu("nenhum")["erro"])


def teste_presets_salvar_listar_e_mesclar():
    cfg = _pasta() / "qt-config.ini"
    cfg.write_text("[Renderer]\nresolution_factor=1\nUseVsync=true\n[UI]\nx=1\n", encoding="utf-8")
    with patch.object(P, "config_atual_emu", return_value=None):
        afirmar("config não encontrada" in P.salvar_preset_de_atual("hd")["erro"])
        afirmar(P.aplicar_preset("hd")["erro"] == "preset 'hd' não existe.")
    with patch.object(P, "config_atual_emu", return_value=cfg):
        afirmar(P.salvar_preset_de_atual("  ")["erro"] == "nome de preset vazio.")
        r = P.salvar_preset_de_atual("HD 2x")
        afirmar(r["ok"] and r["preset"] in P.listar_presets(), (r, P.listar_presets()))
        Path(r["arquivo"]).write_text("[Renderer]\nresolution_factor=2\n[Novo]\nChave=1\n", encoding="utf-8")
        (P.presets_dir() / "legado.ini").write_text("[UI]\nx=9\n", encoding="utf-8")
        afirmar("legado" in P.listar_presets("azahar") and "legado" not in P.listar_presets("desmume"))
        m = P.aplicar_preset(r["preset"])
        afirmar(m["ok"] and cfg.with_name(cfg.name + ".bak").is_file(), m)
        texto = cfg.read_text(encoding="utf-8")
        afirmar("resolution_factor = 2" in texto and "UseVsync = true" in texto and "Chave = 1" in texto, texto)
        afirmar(P.aplicar_preset("legado.ini")["ok"] and "x = 9" in cfg.read_text(encoding="utf-8"))
        afirmar(P.aplicar_preset("../fora")["ok"] is False and P.aplicar_preset("")["erro"] == "sem preset")
        cfg.write_text("lixo sem seção\n", encoding="utf-8")
        afirmar(P.aplicar_preset(r["preset"])["erro"].startswith("falha ao mesclar"))
