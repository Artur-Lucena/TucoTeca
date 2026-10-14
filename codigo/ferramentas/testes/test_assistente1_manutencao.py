"""A1-03: saneamento com plano, reparo (religar) e opção UAC no Qt.

Sucesso = plano só-leitura descreve os efeitos; aplicar quarentena sobras;
religar troca só o caminho e preserva horas/notas/saves.
Cancelamento = plano sem aplicar não move nada; religar com campo inválido falha.
Falha = pasta inexistente, caminho vazio e elevação sem jogo falham explícito.
Nenhum jogo real é executado e nenhuma elevação ocorre: UAC é simulado por
patch em core.executar_jogo_dict; testes nunca abrem processo.
Parte Qt usa _qt() e pula sem PySide6.
"""
import tempfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import bib_core as core
from executar import afirmar
from servicos_ui import ServicoBiblioteca


def _servico_tmp():
    tmp = Path(tempfile.mkdtemp(prefix="a1-manut-"))
    db = tmp / "colecao.db"
    svc = ServicoBiblioteca(str(db))
    with closing(core.get_db(str(db))):  # garante o schema antes de contar
        pass
    return svc, tmp, db


def teste_plano_saneamento_so_leitura():
    svc, tmp, _db = _servico_tmp()
    pasta = tmp / "jogo"
    pasta.mkdir(parents=True)
    (pasta / "Aventura.exe").write_bytes(b"MZ-falso")
    (pasta / "setup-helper.exe").write_bytes(b"MZ-falso")
    antes = sorted(p.name for p in pasta.iterdir())
    r = svc.sanear_plano(str(pasta))
    afirmar(r.get("ok") is True, r)
    afirmar(r.get("exe"), r)
    afirmar(r.get("quarentenaveis") == 1, r)
    depois = sorted(p.name for p in pasta.iterdir())
    afirmar(depois == antes, (antes, depois))


def teste_aplicar_saneamento_quarentena_sobras():
    svc, tmp, _db = _servico_tmp()
    pasta = tmp / "jogo2"
    pasta.mkdir(parents=True)
    (pasta / "Aventura.exe").write_bytes(b"MZ-falso")
    (pasta / "setup-instalador.exe").write_bytes(b"MZ-falso")
    r = svc.sanear_pasta(str(pasta))
    afirmar(r.get("ok") is True, r)
    afirmar(r.get("quarentenados") == 1, r)
    afirmar((pasta / ".hub-lixo").is_dir(), "quarentena não apareceu")
    afirmar((pasta / "Aventura.exe").is_file(), "jogo foi afetado")


def teste_plano_pasta_inexistente_falha_explicita():
    svc, tmp, _db = _servico_tmp()
    r = svc.sanear_plano(str(tmp / "nao-existe"))
    afirmar(r.get("ok") is False, r)
    afirmar(r.get("erro"), r)


def teste_diagnostico_religar_preserva_dados_do_jogo():
    svc, tmp, db = _servico_tmp()
    rom_antiga = tmp / "antiga.3ds"
    rom_nova = tmp / "nova.3ds"
    rom_nova.write_bytes(b"3DS-falso")
    with closing(core.get_db(str(db))) as con:
        gid = core.criar_jogo(con, {"titulo": "Jogo de ROM", "origem": "rom-3ds",
                                    "launch_options": str(rom_antiga),
                                    "horas": 7.5, "nota": 9, "observacoes": "capítulo 3"})["id"]
        antes = core.row_to_dict(con.execute("SELECT * FROM jogos WHERE id=?", (gid,)).fetchone())
    d = svc.diagnosticar_jogo(gid)
    afirmar(d["rom"]["estado"] in ("rom-ausente", "ok"), d["rom"])
    r = svc.religar_jogo(gid, "launch_options", str(rom_nova))
    afirmar(bool(r), r)
    with closing(core.get_db(str(db))) as con:
        depois = core.row_to_dict(con.execute("SELECT * FROM jogos WHERE id=?", (gid,)).fetchone())
    afirmar(depois["launch_options"] == str(rom_nova), depois["launch_options"])
    afirmar(float(depois["horas"] or 0) == float(antes["horas"] or 0), "horas perdidas")
    afirmar(depois["nota"] == antes["nota"], "nota perdida")
    afirmar(depois["observacoes"] == antes["observacoes"], "observações perdidas")


def teste_religar_campo_invalido_falha():
    svc, tmp, db = _servico_tmp()
    with closing(core.get_db(str(db))) as con:
        gid = core.criar_jogo(con, {"titulo": "Jogo X", "executable_path": str(tmp / "x.exe")})["id"]
    try:
        svc.religar_jogo(gid, "titulo", str(tmp / "outro.exe"))
    except ValueError as e:
        afirmar("campo" in str(e).lower(), str(e))
    else:
        raise AssertionError("aceitou campo inválido")
    try:
        svc.religar_jogo(gid, "launch_options", "  ")
    except ValueError as e:
        afirmar("caminho" in str(e).lower(), str(e))
    else:
        raise AssertionError("aceitou caminho vazio")


def teste_elevacao_nunca_ocorre_no_teste():
    """O caminho de UAC só é exercido com processo falso: prova que o serviço
    chama executar_jogo_dict(elevar=True) e marca a sessão manual."""
    svc, tmp, db = _servico_tmp()
    chamadas = []
    with closing(core.get_db(str(db))) as con:
        gid = core.criar_jogo(con, {"titulo": "Jogo UAC", "executable_path": str(tmp / "jogo.exe")})["id"]

    def falso(jogo, elevar=False):
        chamadas.append({"elevar": elevar, "jogo": jogo.get("titulo")})
        return {"ok": True, "modo": "runas-uac" if elevar else "normal"}
    with patch.object(core, "executar_jogo_dict", falso), \
            patch.object(core, "preparar_lancamento", lambda j: {"aviso": ""}):
        r = svc.iniciar_jogo_elevado(gid)
    afirmar(r.get("ok") is True and r.get("modo") == "runas-uac", r)
    afirmar(chamadas == [{"elevar": True, "jogo": "Jogo UAC"}], chamadas)


def _sincrono(bridge):
    def executar(rotulo, trabalho, pronto=None, falha=None):
        try:
            r = trabalho()
        except Exception as exc:
            if falha:
                falha(str(exc))
            else:
                bridge.aviso.emit(str(exc), True)
            return
        if pronto:
            pronto(r)
    return patch.object(bridge, "executar", side_effect=executar)


def teste_qt_fluxo_manutencao_e_uac():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    from PySide6.QtCore import QUrl
    tmp = Path(tempfile.mkdtemp(prefix="a1-manut-qt-"))
    pasta = tmp / "jogo3"
    pasta.mkdir(parents=True)
    (pasta / "Aventura.exe").write_bytes(b"MZ-falso")
    (pasta / "setup-instalador.exe").write_bytes(b"MZ-falso")
    gid = bridge.servico.salvar_jogo(
        0, {"titulo": "Jogo Qt", "executable_path": str(pasta / "Aventura.exe")})["id"]
    try:
        with _sincrono(bridge):
            bridge.planejarSaneamento(QUrl.fromLocalFile(str(pasta)))
            plano = bridge.saneamento
            afirmar(plano.get("ok") is True and plano.get("quarentenaveis") == 1, plano)
            bridge.diagnosticarJogo(gid)
            manut = bridge.manutencao
            afirmar(manut.get("gid") == gid, manut)
            afirmar("exe" in manut and "rom" in manut, manut)
            elev = []
            with patch.object(core, "executar_jogo_dict",
                              lambda j, elevar=False: elev.append(elevar) or {"ok": True}):
                bridge.jogarElevado(gid)
            afirmar(elev == [True], elev)
    finally:
        bridge.fechar()


def teste_qt_elevacao_bloqueada_com_sessao_aberta():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    tmp = Path(tempfile.mkdtemp(prefix="a1-manut-qtb-"))
    (tmp / "jogo.exe").write_bytes(b"MZ-falso")
    gid = bridge.servico.salvar_jogo(
        0, {"titulo": "Jogo Qt B", "executable_path": str(tmp / "jogo.exe")})["id"]
    avisos = []
    bridge.aviso.connect(lambda texto, erro: avisos.append((texto, erro)))
    try:
        with _sincrono(bridge):
            bridge._em_jogo = True
            bridge.jogarElevado(gid)
            afirmar(any("sessão" in t.lower() for t, _ in avisos), avisos)
            bridge._em_jogo = False
    finally:
        bridge.fechar()


def teste_qt_religar_preserva():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    tmp = Path(tempfile.mkdtemp(prefix="a1-manut-qtr-"))
    rom = tmp / "nova.3ds"
    rom.write_bytes(b"3DS-falso")
    gid = bridge.servico.salvar_jogo(0, {"titulo": "Jogo Qt ROM",
                                         "launch_options": str(tmp / "velha.3ds"),
                                         "observacoes": "guardar"})["id"]
    try:
        with _sincrono(bridge):
            bridge.diagnosticarJogo(gid)
            bridge.religarJogo(gid, "launch_options", str(rom))
            jogo = bridge.servico.jogo(gid)
            afirmar(jogo["launch_options"] == str(rom), jogo["launch_options"])
            afirmar(jogo.get("observacoes") == "guardar", jogo.get("observacoes"))
    finally:
        bridge.fechar()
