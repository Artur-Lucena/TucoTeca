"""Preços da Steam para Desejos: parsing, cache 24h, serviço e exibição.

Rede 100% simulada (urlopen fake, como em test_fontes); nada acessa a loja.
O bridge roda só com PySide6 (gate do venv); domínio/QML rodam na stdlib.
"""
from __future__ import annotations

import json
import tempfile
import urllib.request
from pathlib import Path
from unittest.mock import patch

from executar import afirmar

QML = Path(__file__).resolve().parents[2] / "frontends" / "qml"


def _falso_urlopen(corpo_json: dict):
    """Fake de urllib.request.urlopen: conta chamadas e serve o JSON dado."""
    chamadas: list[str] = []

    class Resp:
        def __init__(self, dados):
            self._dados = dados

        def read(self, n=-1):
            return self._dados[:n]

        def geturl(self):
            return ""

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def falso(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        chamadas.append(url)
        return Resp(json.dumps(corpo_json).encode("utf-8"))

    return falso, chamadas


def _corpo(com_preco: dict, sem_preco=()):
    corpo = {}
    for appid, (final, inicial, pct, moeda) in com_preco.items():
        corpo[str(appid)] = {"success": True, "data": {"price_overview": {
            "currency": moeda, "initial": inicial, "final": final,
            "discount_percent": pct}}}
    for appid in sem_preco:
        corpo[str(appid)] = {"success": True, "data": {}}
    return corpo


def teste_preco_steam_parse_gratis_e_recusas():
    from bib_nucleo.rede import metadados as M
    falso, chamadas = _falso_urlopen(_corpo({111: (3490, 6990, 50, "BRL")}, sem_preco=[222]))
    velho = urllib.request.urlopen
    urllib.request.urlopen = falso
    try:
        p = M.preco_steam("111")
        afirmar(p["final"] == 3490 and p["inicial"] == 6990 and p["desconto_pct"] == 50, p)
        afirmar(p["moeda"] == "BRL" and p["gratis"] is False, p)
        afirmar(len(chamadas) == 1 and "appdetails" in chamadas[0] and "cc=br" in chamadas[0],
                chamadas)
        g = M.preco_steam("222")
        afirmar(g and g["gratis"] is True and g["final"] == 0, g)
    finally:
        urllib.request.urlopen = velho
    afirmar(M.preco_steam("abc") is None)
    afirmar(M.preco_steam("") is None)
    with patch.object(M, "rede_ativa", return_value=False):
        afirmar(M.preco_steam("111") is None, "rede desligada não consulta")


def teste_precos_steam_cache_24h_e_vencimento():
    from bib_nucleo import base
    from bib_nucleo.rede import metadados as M
    falso, chamadas = _falso_urlopen(_corpo({111: (1000, 1000, 0, "BRL"),
                                             222: (2000, 2500, 20, "BRL")}))
    velho = urllib.request.urlopen
    urllib.request.urlopen = falso
    arquivo = base.DADOS_DIR / "precos-steam.json"
    try:
        r = M.precos_steam(["111", "222"], "br")
        afirmar(set(r) == {"111", "222"} and r["222"]["desconto_pct"] == 20, r)
        afirmar(len(chamadas) == 1, "deveria consultar uma vez (lote)")
        r2 = M.precos_steam(["111", "222"], "br")
        afirmar(r2 == r and len(chamadas) == 1, "cache não evitou a segunda consulta")
        cache = json.loads(arquivo.read_text(encoding="utf-8"))
        cache["br"]["111"]["em"] = 0  # vence só um appid
        arquivo.write_text(json.dumps(cache), encoding="utf-8")
        r3 = M.precos_steam(["111", "222"], "br")
        afirmar(len(chamadas) == 2 and r3["111"]["final"] == 1000, (chamadas, r3))
    finally:
        urllib.request.urlopen = velho
    # Rede desligada: entrega o cache local e não consulta.
    with patch.object(M, "rede_ativa", return_value=False):
        r4 = M.precos_steam(["111", "222"], "br")
    afirmar(r4["111"]["final"] == 1000 and len(chamadas) == 2, r4)


def teste_precos_desejos_servico_consulta_so_nao_obtidos():
    from bib_nucleo import banco as B
    from bib_nucleo.rede import metadados as MM
    from servicos_ui import ServicoBiblioteca
    tmp = Path(tempfile.mkdtemp(prefix="precos-svc-"))
    db = tmp / "col.db"
    svc = ServicoBiblioteca(str(db))
    con = B.get_db(db)
    try:
        B.adicionar_desejo(con, "111", "Alfa")
        B.adicionar_desejo(con, "222", "Beta")
        obtido = [x for x in B.listar_desejos(con, incluir_obtidos=True)
                  if x["appid"] == "222"][0]["id"]
        B.marcar_desejo_obtido(con, obtido)
    finally:
        con.close()
    visto = {}

    def fake(appids, regiao="br", validade_h=24):
        visto["appids"] = list(appids)
        visto["regiao"] = regiao
        return {"111": {"final": 999, "gratis": False}}

    with patch.object(MM, "precos_steam", side_effect=fake):
        r = svc.precos_desejos()
    afirmar(visto["appids"] == ["111"], visto)
    afirmar(visto["regiao"] == "br", visto)
    afirmar(r["111"]["final"] == 999, r)


def teste_qml_mostra_preco_e_botao_sob_demanda():
    colecao = (QML / "secoes" / "Colecao.qml").read_text(encoding="utf-8")
    main = (QML / "Main.qml").read_text(encoding="utf-8")
    for trecho in ("function preco(appid)", "hub.precosDesejos", "desconto_pct", '"Grátis"'):
        afirmar(trecho in colecao, "Colecao sem: " + trecho)
    afirmar('"Ver preços"' in main and "hub.consultarPrecosDesejos()" in main
            and "cache local por 24h" in main, "Main sem botão de preços")


def teste_qt_bridge_precos_desejos():
    from test_qt import _qt
    app, bridge = _qt()
    if app is None:
        return
    try:
        with patch.object(bridge.servico, "precos_desejos",
                          return_value={"111": {"final": 1234}}) as _f:

            def sincrono(rotulo, trabalho, pronto=None, falha=None):
                pronto(trabalho())

            with patch.object(bridge, "executar", side_effect=sincrono):
                bridge.consultarPrecosDesejos()
            afirmar(bridge.precosDesejos.get("111", {}).get("final") == 1234,
                    bridge.precosDesejos)
    finally:
        bridge.fechar()
