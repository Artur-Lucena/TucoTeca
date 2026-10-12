"""A1-01: remoção só depois de confirmar; cancelar preserva; jogo aberto bloqueia."""
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


def _cena(tmp):
    """Jogo 3DS com um mod e um cheat, emulador e user/ simulados."""
    user = Path(tmp) / "azahar-user"
    for pasta in ("cheats", "load/textures", "config"):
        (user / pasta).mkdir(parents=True, exist_ok=True)
    origem = Path(tmp) / "Mod Teste"
    (origem / "romfs").mkdir(parents=True)
    (origem / "romfs" / "a.bin").write_bytes(b"x")
    return user, origem


def teste_remocao_exige_confirmacao_e_cancelar_preserva():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    from PySide6.QtCore import QUrl
    tmp = tempfile.mkdtemp(prefix="a1-seg-")
    user, origem = _cena(tmp)
    pedidos = []
    try:
        with patch.object(EMU, "title_id_da_rom", return_value=TID), \
                patch.object(EMU, "azahar_user_dir", return_value=str(user)), _sincrono(bridge):
            gid = bridge.servico.salvar_jogo(
                0, {"titulo": "Jogo 3DS", "launch_options": str(Path(tmp) / "jogo.3ds")})["id"]
            emu = bridge.emulacao
            emu.confirmar.connect(lambda t, x, c: pedidos.append((t, x, c)))
            emu.carregar(gid)
            emu.importarMod(QUrl.fromLocalFile(str(origem)))
            emu.adicionarCheat("Vida infinita", "00112233 44556677")
            emu.carregar(gid)
            biblio = EMU.mods_titulo_dir(TID) / "Mod Teste"

            emu.removerMod("Mod Teste")
            afirmar(len(pedidos) == 1, pedidos)
            titulo, texto, chave = pedidos[0]
            afirmar("Remover" in titulo and "não há desfazer" in texto.lower(), (titulo, texto))
            afirmar(biblio.is_dir(), "mod apagado antes da confirmação")
            emu.cancelarAcao(chave)
            emu.carregar(gid)
            afirmar([m["nome"] for m in emu.dados["mods"]] == ["Mod Teste"], emu.dados["mods"])

            emu.removerMod("Mod Teste")
            emu.confirmarAcao(next(iter(emu._pendentes)))
            emu.carregar(gid)
            afirmar(emu.dados["mods"] == [], emu.dados["mods"])
            afirmar(not biblio.exists(), "mod permaneceu após confirmar")

            emu.removerCheat("Vida infinita")
            emu.cancelarAcao(next(iter(emu._pendentes)))
            emu.carregar(gid)
            afirmar([c["nome"] for c in emu.dados["cheats"]] == ["Vida infinita"], emu.dados["cheats"])
            emu.removerCheat("Vida infinita")
            emu.confirmarAcao(next(iter(emu._pendentes)))
            emu.carregar(gid)
            afirmar(emu.dados["cheats"] == [], emu.dados["cheats"])
            emu.limpar()
    finally:
        bridge.fechar()


def teste_jogo_aberto_bloqueia_mudancas():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    from PySide6.QtCore import QUrl
    tmp = tempfile.mkdtemp(prefix="a1-blq-")
    user, origem = _cena(tmp)
    avisos = []
    try:
        with patch.object(EMU, "title_id_da_rom", return_value=TID), \
                patch.object(EMU, "azahar_user_dir", return_value=str(user)), _sincrono(bridge):
            gid = bridge.servico.salvar_jogo(
                0, {"titulo": "Jogo 3DS", "launch_options": str(Path(tmp) / "jogo.3ds")})["id"]
            emu = bridge.emulacao
            bridge.aviso.connect(lambda texto, ruim: avisos.append(texto))
            emu.carregar(gid)
            emu.importarMod(QUrl.fromLocalFile(str(origem)))
            emu.carregar(gid)
            biblio = EMU.mods_titulo_dir(TID) / "Mod Teste"
            afirmar(biblio.is_dir(), biblio)

            bridge._em_jogo = True
            pedidos = []
            emu.confirmar.connect(lambda t, x, c: pedidos.append(c))
            emu.removerMod("Mod Teste")
            emu.alternarMod("Mod Teste")
            emu.instalarTextura(QUrl.fromLocalFile(str(Path(tmp))))
            emu.adicionarCheat("Outro", "00112233 44556677")
            emu.aplicarPreset("x")
            emu.aplicarPresetControle("y")
            afirmar(not pedidos, "pediu confirmação com jogo aberto")
            afirmar(not emu._pendentes, "guardou ação destrutiva com jogo aberto")
            afirmar(biblio.is_dir(), "mod mexido com jogo aberto")
            afirmar(any("Feche o jogo" in a for a in avisos), avisos)
            emu.removerMod("Mod Teste")
            emu.confirmarAcao(emu._pendentes.popitem()[0]) if emu._pendentes else None
            afirmar(biblio.is_dir(), "removeu com jogo aberto")
            emu.limpar()
    finally:
        bridge.fechar()


def teste_instalar_textura_preserva_a_origem():
    """A pasta escolhida pelo usuário não pode desaparecer (A2-04)."""
    import os

    from bib_nucleo import texturas as TEX
    from executar import azahar_fake
    emu = Path(os.environ["BIBLIOTECA_AZAHAR_DIR"])
    (emu / "user").mkdir(parents=True, exist_ok=True)
    azahar_fake(emu)
    pack = emu.parent / "pack"
    (pack / "sub").mkdir(parents=True)
    (pack / "sub" / "tex.png").write_bytes(b"\x89PNG" + b"0" * 64)
    r = TEX.instalar_textura(TID, str(pack))
    afirmar(r.get("ok"), r)
    afirmar(pack.is_dir(), "pasta de origem foi consumida pela instalação")
    est = TEX.estado_textura(TID)
    afirmar(est["instalado"] and est["arquivos"] == 1, est)
    destino = TEX.load_textures_dir() / TID / "sub" / "tex.png"
    afirmar(destino.is_file(), "textura não copiada para o Azahar")
