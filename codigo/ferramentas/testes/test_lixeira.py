"""Lixeira local: arquivar/desfazer (jogos com capa, desejos, vídeos) e serviço.

Sem rede; a ponte roda só no venv. Música fica fora da lixeira por design —
o arquivo de áudio é apagado junto na exclusão (comportamento preservado).
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from executar import afirmar


def _banco_tmp():
    from bib_nucleo import banco as B
    tmp = Path(tempfile.mkdtemp(prefix="lixeira-"))
    con = B.get_db(tmp / "b.db")
    return con, tmp


def teste_lixeira_jogo_com_capa_volta_igual():
    from bib_nucleo import banco as B
    from bib_nucleo import lixeira as L
    con, _tmp = _banco_tmp()
    j = B.criar_jogo(con, {"titulo": "Volta", "executable_path": "jogo.exe",
                           "horas": 3.5, "nota": 8, "etiquetas": "rpg"})
    capa = B.salvar_capa_bytes(con, j["id"], "arte.png", b"\x89PNG" + b"z" * 128)
    afirmar(capa["ok"], capa)
    recibo = L.arquivar(con, "jogos", j["id"])
    afirmar(recibo["titulo"] == "Volta", recibo)
    B.excluir_jogo(con, j["id"])
    afirmar(B.listar_jogos(con, q="Volta") == [], "jogo deveria ter saído")
    afirmar(L.ultima()["titulo"] == "Volta", L.ultima())
    r = L.restaurar_ultimo(con)
    afirmar(r["ok"] and r["tipo"] == "jogos", r)
    voltou = B.listar_jogos(con, q="Volta")[0]
    afirmar(voltou["horas"] == 3.5 and voltou["nota"] == 8, voltou)
    afirmar(voltou["uuid"] == j["uuid"], "uuid deveria ser preservado")
    afirmar(voltou["etiquetas"] == "rpg", voltou)
    afirmar(voltou.get("capa") and int(voltou["capa"].split("-")[0]) == voltou["id"],
            voltou.get("capa"))
    afirmar(L.ultima() is None, "arquivo deveria ser consumido")
    con.close()


def teste_lixeira_desejos_e_videos_voltam_com_identidade():
    from bib_nucleo import banco as B
    from bib_nucleo import lixeira as L
    con, _tmp = _banco_tmp()
    B.adicionar_desejo(con, "111", "Alfa")
    did = [d for d in B.listar_desejos(con) if d["appid"] == "111"][0]["id"]
    L.arquivar(con, "desejos", did)
    B.remover_desejo(con, did)
    r = L.restaurar_ultimo(con)
    afirmar(r["tipo"] == "desejos", r)
    afirmar(any(d["appid"] == "111" for d in B.listar_desejos(con)), "desejo não voltou")
    v = B.criar_video(con, {"titulo": "Clipe", "video_id": "yt123", "duracao_s": 90})
    L.arquivar(con, "videos", v["id"])
    B.excluir_video(con, v["id"])
    r2 = L.restaurar_ultimo(con)
    afirmar(r2["tipo"] == "videos", r2)
    voltou = B.listar_videos(con)[0]
    afirmar(voltou["video_id"] == "yt123" and voltou["duracao_s"] == 90, voltou)
    con.close()


def teste_lixeira_recusa_invalido_e_vazio():
    from bib_nucleo import lixeira as L
    con, _tmp = _banco_tmp()
    for ruim in ("musicas", "outra"):
        try:
            L.arquivar(con, ruim, 1)
        except ValueError:
            pass
        else:
            afirmar(False, f"categoria aceita: {ruim}")
    try:
        L.arquivar(con, "jogos", 999)
    except LookupError:
        pass
    else:
        afirmar(False, "arquivou linha inexistente")
    try:
        L.restaurar_ultimo(con)
    except ValueError:
        pass
    else:
        afirmar(False, "desfez sem nada na lixeira")
    con.close()


def teste_servico_excluir_desfazer_e_musica_fora_da_lixeira():
    from bib_nucleo import banco as B
    from bib_nucleo import lixeira as L
    from servicos_ui import ServicoBiblioteca
    tmp = Path(tempfile.mkdtemp(prefix="lixeira-svc-"))
    db = tmp / "col.db"
    svc = ServicoBiblioteca(str(db))
    con = B.get_db(db)
    j = B.criar_jogo(con, {"titulo": "Some", "executable_path": "s.exe"})
    v = B.criar_video(con, {"titulo": "Clipe", "video_id": "abc"})
    con.close()
    svc.excluir("videos", v["id"])
    afirmar(L.ultima()["tipo"] == "videos", L.ultima())
    r = svc.desfazer_exclusao()
    afirmar(r["tipo"] == "videos", r)
    afirmar(L.ultima() is None, "lixeira deveria estar vazia")
    svc.excluir("jogos", j["id"])
    afirmar(L.ultima()["titulo"] == "Some", L.ultima())
    afirmar(svc.desfazer_exclusao()["tipo"] == "jogos")
    # Música: fluxo antigo (arquivo apagado junto) e sem lixeira.
    from bib_nucleo.base import MUSICAS_DIR
    MUSICAS_DIR.mkdir(parents=True, exist_ok=True)
    audio = MUSICAS_DIR / "faixa-lixeira-test.mp3"
    audio.write_bytes(b"ID3" + b"0" * 64)
    con = B.get_db(db)
    m = B.criar_musica(con, {"titulo": "Faixa", "musica_sha": "deadbeef01",
                             "musica_path": str(audio)})
    con.close()
    svc.excluir("musicas", m["id"])
    afirmar(L.ultima() is None, "música não entra na lixeira")
    afirmar(not audio.exists(), "áudio é apagado junto (por design)")


def teste_qml_tem_botao_desfazer():
    qml = Path(__file__).resolve().parents[2] / "frontends" / "qml" / "Main.qml"
    main = qml.read_text(encoding="utf-8")
    for trecho in ('objectName: "desfazerButton"', "hub.lixeira.disponivel",
                   "hub.desfazerExclusao()", '"Desfazer remoção"'):
        afirmar(trecho in main, "Main sem: " + trecho)


def teste_qt_bridge_desfazer_remocao():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    from bib_nucleo import banco as B
    try:
        con = B.get_db(bridge.servico.db_path)
        v = B.criar_video(con, {"titulo": "Clipe", "video_id": "qq1"})
        con.close()

        def sincrono(rotulo, trabalho, pronto=None, falha=None):
            pronto(trabalho())

        with patch.object(bridge, "executar", side_effect=sincrono):
            bridge.excluir("videos", v["id"])
            afirmar(bool(bridge.lixeira.get("disponivel")), bridge.lixeira)
            afirmar(bridge.lixeira.get("titulo") == "Clipe", bridge.lixeira)
            bridge.desfazerExclusao()
        afirmar(not bridge.lixeira.get("disponivel"), bridge.lixeira)
    finally:
        bridge.fechar()
