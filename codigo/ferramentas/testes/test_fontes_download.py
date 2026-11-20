"""Fontes de download no formato do Hydra: cadastro, busca e baixar dentro do app.

Fonte, rede e qBittorrent simulados; nenhuma fonte real é consultada.
"""
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from bib_nucleo.rede import fontes_download as FD
from executar import afirmar

MAGNET = "magnet:?xt=urn:btih:A0AB72E493A3CFA9390F2C551DDFD5BB85B3F16F&dn=Hades"
FONTE = {"name": "Minha Fonte", "downloads": [
    {"title": "Hades v1.38 + Bonus Content", "uris": [MAGNET, "https://cdn.exemplo.test/hades.zip", "http://inseguro/x"],
     "fileSize": "8.1 GB", "uploadDate": "2025-02-01T10:00:00Z"},
    {"title": "Hades II (Early Access)", "uris": [MAGNET.replace("A0AB", "B1BC")], "fileSize": "9 GB",
     "uploadDate": "2025-05-06T10:00:00Z"},
    {"title": "Celeste", "uris": ["javascript:alert(1)", "ftp://x/y"]},
    {"title": "", "uris": [MAGNET]},
]}


def _erro(f, *a, **k):
    try:
        f(*a, **k)
    except ValueError as e:
        return str(e)
    raise AssertionError("esperava ValueError")


def teste_formato_do_hydra_e_links_aceitos():
    nome, itens = FD.normalizar_fonte(FONTE)
    afirmar(nome == "Minha Fonte" and [i["titulo"] for i in itens] == ["Hades v1.38 + Bonus Content", "Hades II (Early Access)"], itens)
    afirmar(itens[0]["uris"] == [MAGNET, "https://cdn.exemplo.test/hades.zip"], itens[0])  # http e afins saem
    afirmar(itens[0]["tamanho"] == "8.1 GB" and itens[0]["data"] == "2025-02-01", itens[0])
    afirmar("formato do Hydra" in _erro(FD.normalizar_fonte, {"name": "x"}))
    afirmar("nenhum download" in _erro(FD.normalizar_fonte, {"downloads": [{"title": "A", "uris": ["http://x"]}]}))


def teste_cadastro_busca_atualizacao_e_remocao():
    with patch.object(FD, "_baixar_fonte", return_value=FONTE):
        afirmar("https://" in _erro(FD.adicionar, "http://fonte.test/lista.json"))
        fonte = FD.adicionar("https://fonte.test/lista.json")
    afirmar(fonte["nome"] == "Minha Fonte" and fonte["total"] == 2, fonte)
    afirmar([f["id"] for f in FD.listar()] == [fonte["id"]])
    r = FD.buscar("Hades")
    afirmar(r["fontes"] == 1 and r["itens"][0]["titulo"].startswith("Hades v1.38") and r["itens"][0]["nota"] == 1.0, r)
    afirmar(all(i["fonte"] == "Minha Fonte" for i in r["itens"]))
    afirmar(FD.buscar("Celeste")["itens"] == [], "item sem link aceito não aparece")
    afirmar(FD.buscar("Hollow Knight")["itens"] == [])
    # atualizar com falha mantém a lista anterior e registra o erro
    with patch.object(FD, "_baixar_fonte", side_effect=ValueError("HTTP 500")):
        r = FD.atualizar()
    afirmar(r["atualizadas"] == 0 and "HTTP 500" in r["erros"][0], r)
    afirmar(FD.listar()[0]["erro"] == "HTTP 500" and FD.buscar("Hades")["itens"], FD.listar())
    afirmar(FD.remover(fonte["id"]) == {"ok": True} and FD.listar() == [] and FD.buscar("Hades")["fontes"] == 0)
    afirmar("não encontrada" in _erro(FD.remover, fonte["id"]))


def teste_pontuar_ignora_versao_e_extras():
    afirmar(FD.pontuar("Hades", "Hades v1.38 + Bonus Content") == 1.0)
    afirmar(FD.pontuar("The Witcher 3", "The Witcher 3: Wild Hunt – GOTY Edition (v4.04)") >= 0.75)
    afirmar(FD.pontuar("Hades", "Hades II (Early Access)") < 1.0)
    afirmar(FD.pontuar("Celeste", "Hollow Knight") < 0.75)


class _Resposta:
    def __init__(self, dados=b"", tipo="application/zip", tamanho=None, url="https://cdn.exemplo.test/jogo.zip"):
        self._buf = io.BytesIO(dados)
        self.headers = {"Content-Type": tipo, "Content-Length": str(len(dados) if tamanho is None else tamanho),
                        "Content-Disposition": 'attachment; filename="Jogo Demo.zip"'}
        self._url = url

    def read(self, n=-1):
        return self._buf.read(n)

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def teste_baixar_direto_publica_so_arquivo_inteiro():
    destino = Path(tempfile.mkdtemp(prefix="suite-fd-"))
    pcts = []
    with patch.object(FD, "abrir_rede", return_value=_Resposta(b"Z" * 3_000_000)):
        r = FD.baixar_direto("https://cdn.exemplo.test/jogo.zip", "Jogo Demo", destino, pcts.append)
    afirmar(r["ok"] and Path(r["path"]).name == "Jogo Demo.zip" and r["bytes"] == 3_000_000, r)
    afirmar(pcts and max(pcts) <= 99, pcts)
    with patch.object(FD, "abrir_rede", return_value=_Resposta(b"<html>", tipo="text/html")):
        afirmar("página" in _erro(FD.baixar_direto, "https://x.test/p", "Jogo", destino))
    with patch.object(FD, "abrir_rede", return_value=_Resposta(b"abc", tamanho=10)):
        afirmar("incompleto" in _erro(FD.baixar_direto, "https://x.test/a.zip", "Jogo", destino))
    with patch.object(FD, "abrir_rede", return_value=_Resposta(b"Z" * 2_000_000)):
        afirmar("cancelado" in _erro(FD.baixar_direto, "https://x.test/b.zip", "Jogo", destino, None, lambda: True))
    afirmar(sorted(p.name for p in destino.iterdir()) == ["Jogo Demo.zip"], list(destino.iterdir()))
    afirmar("https" in _erro(FD.baixar_direto, "http://x.test/a.zip", "Jogo", destino))


def teste_ponte_fontes():
    from ponte import Ponte
    from servicos_ui import ServicoBiblioteca
    ponte = Ponte(ServicoBiblioteca(Path(tempfile.mkdtemp(prefix="suite-fd-p-")) / "hub.db"))

    def chamar(metodo, **params):
        return json.loads(ponte.executar_linha(json.dumps({"id": 1, "metodo": metodo, "params": params})))
    afirmar(chamar("fontes.listar")["resultado"] == [])
    with patch.object(FD, "_baixar_fonte", return_value=FONTE):
        fonte = FD.adicionar("https://fonte.test/lista.json")
    r = chamar("fontes.buscar", titulo="Hades")
    afirmar(r["ok"] and r["resultado"]["itens"], r)
    from bib_nucleo import qbit
    enviados = []
    with patch.object(qbit, "qbit_api_url", return_value="http://127.0.0.1:1"), \
            patch.object(qbit, "qbit_request", side_effect=lambda ep, dados=None, **k: enviados.append((ep, dados)) or "Ok."):
        r = chamar("fontes.baixar", uri=MAGNET, titulo="Hades")
    afirmar(r["ok"] and r["resultado"]["modo"] == "torrent", r)
    afirmar(enviados and enviados[0][0] == "torrents/add" and enviados[0][1]["urls"] == MAGNET, enviados)
    afirmar(chamar("fontes.baixar", uri="ftp://x/y", titulo="X")["ok"] is False)
    r = chamar("fontes.baixar", uri="https://cdn.exemplo.test/hades.zip", titulo="Hades")
    afirmar(r["ok"] and "trabalho" in r["resultado"], r)
    afirmar(chamar("fontes.remover", id=fonte["id"])["ok"])
    afirmar(chamar("fontes.adicionar", url="https://fonte.test/x.json")["ok"], "adicionar vira trabalho")
