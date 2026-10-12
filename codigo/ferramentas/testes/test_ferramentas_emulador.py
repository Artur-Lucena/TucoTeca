"""Mods, texturas, cheats e presets do Azahar pelo view-model Qt, com emulador simulado."""
import tempfile
from pathlib import Path
from unittest.mock import patch

from bib_nucleo import emuladores as EMU
from executar import afirmar

TID = "0004000000055D00"


def _sincrono(bridge):
    def executar(rotulo, trabalho, pronto=None, falha=None):
        r = trabalho()
        if pronto:
            pronto(r)
    return patch.object(bridge, "executar", side_effect=executar)


def teste_ferramentas_emulador_mods_cheats_texturas_e_presets_persistem():
    from PySide6.QtCore import QUrl
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    tmp = Path(tempfile.mkdtemp(prefix="emu-ferr-"))
    user = tmp / "azahar-user"
    for pasta in ("cheats", "load/textures", "config"):
        (user / pasta).mkdir(parents=True)
    (user / "config" / "qt-config.ini").write_text("[Utility]\ncustom_textures=true\n", encoding="utf-8")
    origem = tmp / "Mod Teste"
    (origem / "romfs").mkdir(parents=True)
    (origem / "romfs" / "a.bin").write_bytes(b"x")
    textura = tmp / "pack"
    textura.mkdir()
    (textura / "tex.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    try:
        with patch.object(EMU, "title_id_da_rom", return_value=TID), \
                patch.object(EMU, "azahar_user_dir", return_value=str(user)), _sincrono(bridge):
            gid = bridge.servico.salvar_jogo(0, {"titulo": "Jogo 3DS", "launch_options": str(tmp / "jogo.3ds")})["id"]
            emu = bridge.emulacao
            emu.carregar(gid)
            afirmar(emu.dados["tid"] == TID and emu.dados["mods"] == [], emu.dados)
            emu.importarMod(QUrl.fromLocalFile(str(origem)))
            afirmar([m["nome"] for m in emu.dados["mods"]] == ["Mod Teste"], emu.dados["mods"])
            emu.alternarMod("Mod Teste")
            afirmar(emu.dados["mods"][0]["ativo"] is True, emu.dados["mods"])
            emu.alternarModsOff()
            afirmar(emu.dados["mods_off"] is True)
            emu.alternarModsOff()
            emu.removerMod("Mod Teste")
            afirmar(emu.dados["mods"] == [], emu.dados["mods"])
            emu.adicionarCheat("Vida infinita", "00112233 44556677")
            afirmar(emu.dados["cheats"][0]["nome"] == "Vida infinita" and not emu.dados["cheats"][0]["ativo"])
            emu.alternarCheat("Vida infinita")
            afirmar(emu.dados["cheats"][0]["ativo"] is True)
            emu.removerCheat("Vida infinita")
            afirmar(emu.dados["cheats"] == [])
            emu.instalarTextura(QUrl.fromLocalFile(str(textura)))
            afirmar(emu.dados["textura"]["instalado"] and emu.dados["textura"]["ativo"], emu.dados["textura"])
            emu.alternarTextura()
            afirmar(emu.dados["textura"]["instalado"] and not emu.dados["textura"]["ativo"], emu.dados["textura"])
            emu.salvarPreset("Meu preset")
            afirmar("meu-preset" in emu.dados["presets"], emu.dados["presets"])
            emu.aplicarPreset("meu-preset")
            emu.limpar()
            try:
                emu.alternarMod("Mod Teste")
            except ValueError as e:
                afirmar("Escolha um jogo 3DS" in str(e), e)
            else:
                afirmar(False, "aceitou mod sem jogo selecionado")
    finally:
        bridge.fechar()
