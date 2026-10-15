"""A1-02: importação Qt com preview e seleção.

Sucesso = preview só-leitura lista achados e importar selecionados grava só os marcados.
Cancelamento = limpar preview / nada selecionado não altera a coleção.
Falha = seleção vazia/inválida falha explícita; caminho inexistente não importa.
Sem jogos reais, sem elevação, sem rede: fixtures sintéticas em pasta descartável.
Parte Qt usa _qt() e pula sem PySide6; domínio roda em stdlib.
"""
import tempfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import bib_core as core
from executar import afirmar
from servicos_ui import ServicoBiblioteca


def _servico_tmp():
    tmp = Path(tempfile.mkdtemp(prefix="a1-imp-"))
    db = tmp / "colecao.db"
    svc = ServicoBiblioteca(str(db))
    with closing(core.get_db(str(db))):  # garante o schema antes de contar
        pass
    return svc, tmp, db


def _contar(db):
    import sqlite3
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    try:
        return con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()["n"]
    finally:
        con.close()


def _cena_pasta(tmp):
    pasta = tmp / "pasta-jogo"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "Jogo Alfa.exe").write_bytes(b"MZ-falso")
    (pasta / "aventura.3ds").write_bytes(b"3DS-falso")
    return pasta


def teste_preview_pasta_so_leitura_nao_importa():
    svc, tmp, db = _servico_tmp()
    pasta = _cena_pasta(tmp)
    antes = _contar(db)
    r = svc.prever_pasta(str(pasta))
    afirmar(r.get("ok") is True, r)
    afirmar(len(r.get("itens") or []) >= 1, r)
    afirmar(_contar(db) == antes, "preview mutou a coleção")
    afirmar(isinstance(r.get("info"), dict), r)


def teste_preview_selecao_importa_so_marcados():
    svc, tmp, db = _servico_tmp()
    pasta = _cena_pasta(tmp)
    r = svc.prever_pasta(str(pasta))
    itens = r["itens"]
    afirmar(len(itens) >= 1, r)
    antes = _contar(db)
    sel = [itens[0]]
    res = svc.importar_selecionados(sel)
    afirmar(_contar(db) == antes + 1, (res, antes))
    # importar o mesmo de novo não duplica (dedup do domínio)
    res2 = svc.importar_selecionados(sel)
    afirmar(_contar(db) == antes + 1, res2)


def teste_cancelar_limpa_sem_importar():
    svc, tmp, db = _servico_tmp()
    pasta = _cena_pasta(tmp)
    antes = _contar(db)
    r = svc.prever_pasta(str(pasta))
    afirmar(r.get("ok") is True, r)
    # cancelar = simplesmente não chamar importar_selecionados
    afirmar(_contar(db) == antes, "cancelar mutou a coleção")


def teste_analisar_arquivo_classifica_sem_mutar():
    svc, tmp, db = _servico_tmp()
    exe = tmp / "Solo Beta.exe"
    exe.write_bytes(b"MZ-falso")
    rom = tmp / "zelda.3ds"
    rom.write_bytes(b"3DS-falso")
    antes = _contar(db)
    a_exe = svc.analisar_arquivo(str(exe))
    a_rom = svc.analisar_arquivo(str(rom))
    afirmar(a_exe.get("ok") is True and a_exe.get("tipo") == "jogo", a_exe)
    afirmar(a_rom.get("ok") is True and a_rom.get("tipo") == "rom", a_rom)
    afirmar(isinstance(a_rom.get("item"), dict), a_rom)
    afirmar(_contar(db) == antes, "análise mutou a coleção")
    a_vazio = svc.analisar_arquivo(str(tmp / "nao-existe.exe"))
    afirmar(a_vazio.get("tipo") == "desconhecido", a_vazio)


def teste_importar_sem_selecao_falha_explicita():
    svc, tmp, db = _servico_tmp()
    antes = _contar(db)
    for invalida in ([], None, [{"sem": "campos"}]):
        try:
            svc.importar_selecionados(invalida)
        except ValueError as e:
            afirmar("selecionado" in str(e).lower(), str(e))
        else:
            raise AssertionError(f"aceitou seleção inválida: {invalida!r}")
    afirmar(_contar(db) == antes, "falha mutou a coleção")


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


def teste_qt_preview_e_importacao_selecionada():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    from PySide6.QtCore import QUrl
    tmp = Path(tempfile.mkdtemp(prefix="a1-imp-qt-"))
    (tmp / "Aventura Alfa.3ds").write_bytes(b"3DS-falso")
    try:
        with _sincrono(bridge):
            bridge.preverPasta(QUrl.fromLocalFile(str(tmp)))
            itens = list(bridge.previewImportacao.get("itens") or [])
            afirmar(len(itens) >= 1, bridge.previewImportacao)
            bridge.importarSelecionados([0])
            afirmar(bridge.previewImportacao.get("itens") == [], bridge.previewImportacao)
    finally:
        bridge.fechar()


def teste_qt_cancelar_preserva():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    from PySide6.QtCore import QUrl
    tmp = Path(tempfile.mkdtemp(prefix="a1-imp-qtc-"))
    (tmp / "Beta.exe").write_bytes(b"MZ-falso")
    import sqlite3
    db = Path(bridge.servico.db_path)
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    try:
        antes = con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()["n"]
    finally:
        con.close()
    try:
        with _sincrono(bridge):
            bridge.preverPasta(QUrl.fromLocalFile(str(tmp)))
            afirmar(len(bridge.previewImportacao.get("itens") or []) >= 1,
                    bridge.previewImportacao)
            bridge.limparPreview()
            afirmar(bridge.previewImportacao.get("itens") == [], bridge.previewImportacao)
            bridge.importarSelecionados([])
    finally:
        bridge.fechar()
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    try:
        depois = con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()["n"]
    finally:
        con.close()
    afirmar(depois == antes, (antes, depois))


def teste_drag_drop_reutiliza_o_mesmo_preview():
    """Arrastar pasta/arquivo abre o MESMO preview (estático, roda sem PySide6).

    O drop não importa direto: reusa `analisarArquivo` + `importPreview`, então
    a seleção da lista continua sendo o único caminho que grava na coleção.
    """
    from pathlib import Path as _P
    main = (_P(__file__).resolve().parents[2] / "frontends" / "qml" / "Main.qml"
            ).read_text(encoding="utf-8")
    for trecho in ("DropArea {", "id: dropGlobal", "onDropped:", "drop.hasUrls",
                   "hub.analisarArquivo(alvo)", "importPreview.open()",
                   "dropGlobal.containsDrag"):
        afirmar(trecho in main, "drag&drop ausente: " + trecho)
    afirmar("importarSelecionados(drop" not in main and "importarJogos(drop" not in main,
            "drop não pode importar direto, sem preview")
