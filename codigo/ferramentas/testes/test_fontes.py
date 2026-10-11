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


def teste_steamrip_hosts_por_dominio_e_fallback():
    from bib_nucleo import fontes as FT
    html = """<meta content='Jogo » SteamRIP' property='og:title'>
        <strong>Descrição anterior que não é host</strong>
        <a href='https://fileditchfiles.me/primeiro.rar'><span>DOWNLOAD HERE</span></a>
        <a href='https://cdn.exemplo/jogo.rar'>DOWNLOAD HERE</a>"""
    tmp = Path(tempfile.mkdtemp(prefix="suite-ft-"))
    velho, chamados = _falso_urlopen([
        ("https://steamrip.com/", (html.encode(), "", {})),
        ("https://fileditchfiles.me/", (b"<html>erro", "", {"Content-Type": "text/html"})),
        ("https://cdn.exemplo/", (b"R" * 1_200_000, "", {"Content-Length": "1200000"})),
    ])
    try:
        det = FT.detalhes_steamrip("https://steamrip.com/jogo/")
        afirmar(det["hosts"][0]["nome"] == "fileditch", det)
        r = FT.baixar_steamrip("https://steamrip.com/jogo/", destino=tmp)
        afirmar(r["ok"] and r["tentados"] == ["fileditch", "cdn"], r)
        afirmar(Path(r["path"]).name == "jogo.rar", r)
        afirmar(len(list(tmp.iterdir())) == 1, "HTML/temporário permaneceu no destino")
    finally:
        urllib.request.urlopen = velho


def teste_steamrip_expirado_e_404():
    import urllib.request

    from bib_nucleo import fontes as FT
    afirmar(FT._mesmo_host("https://a.gofile.io/x", "https://gofile.io/x"))
    afirmar(FT._mesmo_host("https://fileditchfiles.st/f.rar",
                           "https://fileditchfiles.st/f.rar"))
    afirmar(not FT._mesmo_host("https://fileditchfiles.st/f.rar",
                               "https://steamrip.com/"))
    tmp = Path(tempfile.mkdtemp(prefix="suite-ft-"))
    # host redirecionou para fora com HTML = arquivo morto (caso Ball x Pit)
    velho, _ch = _falso_urlopen([
        ("https://fileditchfiles.st/", (b"<html>lixo", "https://steamrip.com/",
                                        {"Content-Type": "text/html"})),
    ])
    try:
        r = FT._descer("https://fileditchfiles.st/a/B.rar", "B", tmp, None)
        afirmar(not r.get("ok") and "expirado" in r.get("erro", ""), r)
        afirmar(list(tmp.iterdir()) == [], "publicou HTML expirado")
    finally:
        urllib.request.urlopen = velho
    # mesmo host com HTML mantém a mensagem antiga
    velho, _ch = _falso_urlopen([
        ("https://host/", (b"<html>lixo", "https://host/jogo.rar",
                           {"Content-Type": "text/html"})),
    ])
    try:
        r = FT._descer("https://host/jogo.rar", "Jogo", tmp, None)
        afirmar(not r.get("ok") and "veio HTML" in r.get("erro", ""), r)
    finally:
        urllib.request.urlopen = velho
    # gofile 404 = conteúdo expirado
    erro404 = urllib.request.HTTPError("https://x/contents/y", 404,
                                       "Not Found", {}, None)
    velho, _ch = _falso_urlopen([("https://api.gofile.io/", erro404)])
    try:
        FT.resolver_gofile("https://gofile.io/d/AbC123")
        afirmar(False, "devia levantar")
    except ValueError as e:
        afirmar("expirado" in str(e) and "404" in str(e), e)
    finally:
        urllib.request.urlopen = velho
    velho, _ch = _falso_urlopen([("https://megadb.net/", erro404)])
    try:
        FT.resolver_megadb("https://megadb.net/xyz9")
        afirmar(False, "devia levantar")
    except ValueError as e:
        afirmar("expirado" in str(e) and "404" in str(e), e)
    finally:
        urllib.request.urlopen = velho


FG_BUSCA_HTML = """
<html><body>
<h1 class="entry-title"><a href="https://fitgirl-repacks.site/ball-x-pit/">BALL x PIT + Bonus OST</a></h1>
<h1 class="entry-title"><a href="/speedball/">Speedball – v1.2.8.0</a></h1>
</body></html>
"""

FG_POST_HTML = """
<html><head><meta property="og:title" content="BALL x PIT + Bonus OST - FitGirl Repacks" /></head>
<body><h3>Download Mirrors (Direct Links)</h3><ul>
<li><a href="https://datanodes.to/abc/jogo.rar" target="_blank">Filehoster: DataNodes</a></li>
<li><a href="https://fuckingfast.co/xyz#jogo.rar" target="_blank">Filehoster: FuckingFast</a></li>
</ul><a href="magnet:?xt=urn:btih:A0AB72E493A3CFA9390F2C551DDFD5BB85B3F16F&dn=Jogo+Demo">magnet</a>
<a href="magnet:?xt=urn:btih:A0AB72E493A3CFA9390F2C551DDFD5BB85B3F16F&dn=Jogo+Demo">magnet</a>
</body></html>
"""


def teste_fitgirl_buscar_e_detalhes():
    import webbrowser

    from bib_nucleo import fontes as FT
    velho, _ch = _falso_urlopen([("https://fitgirl-repacks.site/?s=",
                                  (FG_BUSCA_HTML.encode(), "", {}))])
    try:
        r = FT.buscar_fitgirl("ball pit")
        afirmar(len(r["itens"]) == 2 and not r["erros"], r)
        afirmar(r["itens"][0]["url"] == "https://fitgirl-repacks.site/ball-x-pit/", r)
        afirmar(r["itens"][1]["url"] == "https://fitgirl-repacks.site/speedball/", r)
        afirmar(FT.buscar_fitgirl("   ")["erros"], "vazia devia falhar")
    finally:
        urllib.request.urlopen = velho
    velho, _ch = _falso_urlopen([("https://fitgirl-repacks.site/ball-x-pit/",
                                  (FG_POST_HTML.encode(), "", {}))])
    try:
        d = FT.detalhes_fitgirl("https://fitgirl-repacks.site/ball-x-pit/")
        afirmar(d["titulo"] == "BALL x PIT + Bonus OST", d)
        afirmar([h["nome"] for h in d["espelhos"]] == ["DataNodes", "FuckingFast"], d)
        afirmar(len(d["magnets"]) == 1 and d["magnets"][0].startswith("magnet:?"), d)
        afirmar(FT.nome_magnet(d["magnets"][0]) == "Jogo Demo", d)
        try:
            FT.detalhes_fitgirl("https://fitgirl-repacks.site/x/")
            afirmar(False, "devia levantar")
        except ValueError:
            pass
    finally:
        urllib.request.urlopen = velho
    velho, _ch = _falso_urlopen([("https://", urllib.request.URLError("off"))])
    try:
        r = FT.buscar_fitgirl("x")
        afirmar(r["itens"] == [] and r["erros"], r)
    finally:
        urllib.request.urlopen = velho
    aberto = []
    velho_open = webbrowser.open
    webbrowser.open = lambda url: aberto.append(url) or True
    try:
        afirmar(FT.abrir_url("https://x/y") == {"ok": True})
        afirmar(aberto == ["https://x/y"], aberto)
        afirmar(not FT.abrir_url("  ")["ok"], "vazia devia falhar")
    finally:
        webbrowser.open = velho_open
    afirmar("buscar_fitgirl" in core.__all__ and "detalhes_fitgirl" in core.__all__)
    afirmar("abrir_url" in core.__all__ and "nome_magnet" in core.__all__)


def teste_steamrip_nome_e_download_incompleto():
    from bib_nucleo import fontes as FT
    afirmar(FT._nome_saida("X", "https://host/file.php?f=%2Fa%2FMeu%20Jogo.rar") == "Meu Jogo.rar")
    nome = FT._nome_saida("X", "https://host/%2F..%2F..%2Ffora.rar")
    afirmar(nome == "fora.rar", nome)
    tmp = Path(tempfile.mkdtemp(prefix="suite-ft-"))
    velho, _ch = _falso_urlopen([
        ("https://host/", (b"R" * 1_100_000, "", {"Content-Length": "1300000"})),
    ])
    try:
        r = FT._descer("https://host/jogo.rar", "Jogo", tmp, None)
        afirmar(not r["ok"] and "incompleto" in r["erro"], r)
        afirmar(list(tmp.iterdir()) == [], "publicou download parcial")
    finally:
        urllib.request.urlopen = velho


def teste_wishlist_arquivo():
    from bib_nucleo import fontes as FT
    tmp = Path(tempfile.mkdtemp(prefix="suite-ft-"))
    cru = tmp / "w0.json"
    cru.write_text(json.dumps({"10": {"name": "Alpha"}, "20": {"name": "Beta"}}),
                   encoding="utf-8")
    r = FT.ler_wishlist_arquivo(cru)
    afirmar(not r["erros"] and len(r["itens"]) == 2, r)
    afirmar(r["itens"][0] == {"appid": "10", "titulo": "Alpha"}, r["itens"])
    lista = tmp / "w1.json"
    lista.write_text(json.dumps([{"appid": "30", "titulo": "Gama"}]),
                     encoding="utf-8")
    r = FT.ler_wishlist_arquivo(lista)
    afirmar(len(r["itens"]) == 1 and r["itens"][0]["appid"] == "30", r)
    html = tmp / "w2.json"
    html.write_text("<html>login</html>", encoding="utf-8")
    r = FT.ler_wishlist_arquivo(html)
    afirmar(r["itens"] == [] and r["erros"], r)
    r = FT.ler_wishlist_arquivo(tmp / "falta.json")
    afirmar(r["itens"] == [] and r["erros"], r)
    cru.write_text(json.dumps({"10": "linha inválida", "20": {"name": 123}}), encoding="utf-8")
    r = FT.ler_wishlist_arquivo(cru)
    afirmar(r["itens"] == [{"appid": "20", "titulo": "123"}], r)
    afirmar("ler_wishlist_arquivo" in core.__all__, core.__all__)


def teste_buscar_jogos_steam():
    from bib_nucleo import fontes as FT
    corpo = json.dumps({"total": 2, "items": [
        {"id": 2062430, "name": "BALL x PIT"},
        {"id": 0, "name": ""},
    ]}).encode("utf-8")
    velho, _ch = _falso_urlopen([
        ("https://store.steampowered.com/api/storesearch/",
         (bytes(corpo), "", {})),
    ])
    try:
        r = FT.buscar_jogos_steam("ball x pit")
        afirmar(r["itens"] == [{"appid": "2062430", "titulo": "BALL x PIT"}],
                r)
        r = FT.buscar_jogos_steam("   ")
        afirmar(r["itens"] == [] and r["erros"], r)
    finally:
        urllib.request.urlopen = velho
    velho, _ch = _falso_urlopen([("https://", urllib.request.URLError("off"))])
    try:
        r = FT.buscar_jogos_steam("x")
        afirmar(r["itens"] == [] and r["erros"], r)
    finally:
        urllib.request.urlopen = velho
    afirmar("buscar_jogos_steam" in core.__all__, core.__all__)


def teste_wishlist_resposta_invalida_nao_e_lista_vazia():
    from bib_nucleo import fontes as FT
    for corpo in (b"<html>Homepage</html>", b"[]"):
        velho, _ = _falso_urlopen([("https://store.steampowered.com/", (corpo, "", {}))])
        try:
            r = FT.ler_wishlist("76561199515332932")
            afirmar(r["erros"] and not r["itens"], r)
        finally:
            urllib.request.urlopen = velho
