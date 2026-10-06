"""Catálogo SteamRip: busca, hosts, resolvers e download (mocks, sem rede)."""
import json
import tempfile
import urllib.request
from pathlib import Path

import bib_core as core
from executar import afirmar

BUSCA_HTML = """
<html><body><nav><a href="https://steamrip.com/category/action/">Action</a></nav>
<h2 class="post-title"><a href="https://steamrip.com/ultrakill-free-download-1p/">ULTRAKILL Free Download</a></h2>
<h2><a href="/megabonk-free-download/">MEGABONK Free Download</a></h2>
</body></html>
"""

POST_HTML = """
<html><head><meta property="og:title" content="ULTRAKILL Free Download (Build 1) » SteamRIP" /></head>
<body><p><strong>GOFILE</strong><br/> <a href="//gofile.io/d/AbC123" rel="nofollow">DOWNLOAD HERE</a>
<p><strong>MegaDB</strong><br/><a href="//megadb.net/xyz9" rel="nofollow">DOWNLOAD HERE</a>
<p><strong>FileDitch</strong><br/> <a href="//fileditchfiles.me/file.php?f=/a/GAME.rar" rel="nofollow">DOWNLOAD HERE</a>
</body></html>
"""


def _falso_urlopen(mapa):
    chamadas = []

    class Resp:
        def __init__(self, dados, url="", headers=None):
            self._dados = dados
            self._url = url
            self.headers = headers or {}
        def read(self, n=-1):
            if not self._dados:
                return b""
            out, self._dados = self._dados[:n], self._dados[n:]
            return out
        def geturl(self):
            return self._url
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def falso(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        chamadas.append(url)
        for prefixo, item in mapa:
            if url.startswith(prefixo):
                if isinstance(item, Exception):
                    raise item
                dados, final, heads = item
                return Resp(bytes(dados), final or url, heads)
        raise AssertionError(f"fora do roteiro: {url}")
    velho = urllib.request.urlopen
    urllib.request.urlopen = falso
    return velho, chamadas


def teste_steamrip_buscar_e_detalhes():
    from bib_nucleo import fontes as FT
    velho, ch = _falso_urlopen([("https://steamrip.com/?", (BUSCA_HTML.encode(), "", {}))])
    try:
        r = FT.buscar_steamrip("ultra")
        afirmar(len(r["itens"]) == 2 and not r["erros"], r)
        afirmar(r["itens"][0]["url"].endswith("ultrakill-free-download-1p/"), r)
        afirmar(r["itens"][1]["url"] == "https://steamrip.com/megabonk-free-download/", r)
        afirmar(FT.buscar_steamrip("")["erros"], "vazia devia falhar")
    finally:
        urllib.request.urlopen = velho
    velho, _ch = _falso_urlopen([("https://steamrip.com/u", (POST_HTML.encode(), "", {}))])
    try:
        d = FT.detalhes_steamrip("https://steamrip.com/ultrakill-free-download-1p/")
        afirmar(d["titulo"].startswith("ULTRAKILL"), d)
        afirmar([h["nome"] for h in d["hosts"]] == ["gofile", "megadb", "fileditch"], d)
        afirmar(d["hosts"][0]["url"] == "https://gofile.io/d/AbC123", d)
        try:
            FT.detalhes_steamrip("https://steamrip.com/x/")
            afirmar(False, "devia levantar")
        except ValueError:
            pass
    finally:
        urllib.request.urlopen = velho
    velho, _ch = _falso_urlopen([("https://", urllib.request.URLError("off"))])
    try:
        r = FT.buscar_steamrip("x")
        afirmar(r["itens"] == [] and r["erros"], r)
    finally:
        urllib.request.urlopen = velho


def teste_steamrip_ordem_hosts():
    import os
    from bib_nucleo import fontes as FT
    afirmar(FT.ordem_hosts()[0] == "fileditch")
    velho = os.environ.get("BIBLIOTECA_STEAMRIP_HOSTS")
    os.environ["BIBLIOTECA_STEAMRIP_HOSTS"] = "gofile, megadb"
    try:
        afirmar(FT.ordem_hosts() == ("gofile", "megadb"), FT.ordem_hosts())
    finally:
        if velho is None:
            os.environ.pop("BIBLIOTECA_STEAMRIP_HOSTS", None)
        else:
            os.environ["BIBLIOTECA_STEAMRIP_HOSTS"] = velho


def teste_steamrip_gofile_e_megadb():
    import urllib.request
    from bib_nucleo import fontes as FT
    conta = json.dumps({"data": {"token": "tok"}}).encode()
    servs = json.dumps({"data": {"servers": [{"name": "store1"}]}}).encode()
    cont = json.dumps({"data": {"children": {
        "a": {"type": "file", "name": "g.rar", "link": "https://store1/dl/g.rar",
              "size": 500},
        "b": {"type": "folder", "children": {
            "c": {"type": "file", "name": "h.rar",
                  "link": "https://store1/dl/h.rar", "size": 900}}}}}}).encode()
    velho, ch = _falso_urlopen([
        ("https://api.gofile.io/accounts", (conta, "", {})),
        ("https://api.gofile.io/servers", (servs, "", {})),
        ("https://store1.gofile.io/contents", (cont, "", {})),
    ])
    try:
        arqs = FT.resolver_gofile("https://gofile.io/d/AbC123")
        afirmar(len(arqs) == 2, arqs)
        afirmar(all(a["url"].startswith("https://store1/") for a in arqs), arqs)
        try:
            FT.resolver_gofile("https://x.com/y")
            afirmar(False, "devia levantar")
        except ValueError:
            pass
    finally:
        urllib.request.urlopen = velho
    velho, _ch = _falso_urlopen([
        ("https://megadb.net/", (b"", "https://cdn.x/f.rar",
                                 {"Content-Type": "application/x-rar",
                                  "Content-Disposition": "attachment"})),
    ])
    try:
        r = FT.resolver_megadb("https://megadb.net/xyz9")
        afirmar(r == {"url": "https://cdn.x/f.rar"}, r)
    finally:
        urllib.request.urlopen = velho
    velho, _ch = _falso_urlopen([
        ("https://megadb.net/", (b"<html>", "https://megadb.net/xyz9",
                                 {"Content-Type": "text/html"})),
    ])
    try:
        FT.resolver_megadb("https://megadb.net/xyz9")
        afirmar(False, "devia levantar")
    except ValueError:
        pass
    finally:
        urllib.request.urlopen = velho


def teste_steamrip_baixar_fileditch():
    import urllib.request
    from bib_nucleo import fontes as FT
    tmp = Path(tempfile.mkdtemp(prefix="suite-ft-"))
    corpo = b"R" * 1_200_000
    velho, ch = _falso_urlopen([
        ("https://steamrip.com/ultrakill", (POST_HTML.encode(), "", {})),
        ("https://fileditchfiles.me/", (corpo, "", {"Content-Length": str(len(corpo))})),
    ])
    try:
        vistos = []
        r = FT.baixar_steamrip("https://steamrip.com/ultrakill-free-download-1p/",
                               destino=tmp, host="fileditch",
                               progresso=lambda f, t: vistos.append((f, t)))
        afirmar(r.get("ok") and r["path"].endswith("GAME.rar"), r)
        afirmar(Path(r["path"]).stat().st_size == len(corpo), r)
        afirmar(vistos, "sem progresso?")
    finally:
        urllib.request.urlopen = velho
    # HTML em vez de arquivo + tudo falhando
    velho, _ch = _falso_urlopen([
        ("https://steamrip.com/ultrakill", (POST_HTML.encode(), "", {})),
        ("https://", (b"<html>lixo", "", {})),
    ])
    try:
        r = FT.baixar_steamrip("https://steamrip.com/ultrakill-free-download-1p/",
                               destino=tmp, host="fileditch")
        afirmar(not r.get("ok") and "HTML" in r.get("erro", ""), r)
    finally:
        urllib.request.urlopen = velho
    afirmar("steamrip" in FT.__all__ or "buscar_steamrip" in FT.__all__)
    afirmar("buscar_steamrip" in core.__all__)
