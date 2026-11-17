"""Catálogo SteamRip: busca, hosts, resolvers e download (mocks, sem rede)."""
import json
import tempfile
import urllib.request
from pathlib import Path
from unittest.mock import patch

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


# ---------------------------------------------------------------- wishlist: leitura, sincronização e fachada

def _resp(dados: bytes, url="https://store.steampowered.com/"):
    class Resp:
        headers = {}
        def __init__(self):
            self._dados = bytes(dados)
        def read(self, n=-1):
            out, self._dados = self._dados[:n], self._dados[n:]
            return out
        def geturl(self):
            return url
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
    return Resp()


def teste_desejos_arquivo_valida_dict_lista_e_dedup():
    from bib_nucleo import fontes as FT
    tmp = Path(tempfile.mkdtemp(prefix="a2-wish-"))
    cru = tmp / "w0.json"
    cru.write_text(json.dumps({"10": {"name": "Alpha"}, "20": {"titulo": "Beta"}}),
                   encoding="utf-8")
    r = FT.ler_wishlist_arquivo(cru)
    afirmar(not r["erros"] and len(r["itens"]) == 2, r)
    afirmar(r["itens"][0] == {"appid": "10", "titulo": "Alpha"}, r["itens"])
    lista = tmp / "w1.json"
    lista.write_text(json.dumps([{"appid": "30", "titulo": "Gama"},
                                 {"appid": 40, "name": "Delta"},
                                 {"appid": "30", "titulo": "Duplicado"},
                                 {"appid": "abc", "titulo": "Inválido"},
                                 {"appid": "50", "titulo": "  "},
                                 "linha solta"]),
                     encoding="utf-8")
    r = FT.ler_wishlist_arquivo(lista)
    afirmar(len(r["itens"]) == 2, r)
    afirmar(r["itens"][0] == {"appid": "30", "titulo": "Gama"}, r["itens"])
    afirmar(r["itens"][1] == {"appid": "40", "titulo": "Delta"}, r["itens"])
    # BOM de editor Windows não pode virar "JSON inválido".
    com_bom = tmp / "w2.json"
    com_bom.write_bytes(b"\xef\xbb\xbf" + json.dumps({"60": {"name": "Com BOM"}}).encode("utf-8"))
    r = FT.ler_wishlist_arquivo(com_bom)
    afirmar(r["itens"] == [{"appid": "60", "titulo": "Com BOM"}], r)


def teste_desejos_arquivo_falha_explicita_html_invalido_ausente():
    from bib_nucleo import fontes as FT
    tmp = Path(tempfile.mkdtemp(prefix="a2-wish-"))
    html = tmp / "login.json"
    html.write_text("<html>login</html>", encoding="utf-8")
    r = FT.ler_wishlist_arquivo(html)
    afirmar(r["itens"] == [] and any("HTML" in e for e in r["erros"]), r)
    ruim = tmp / "ruim.json"
    ruim.write_text("{não-json", encoding="utf-8")
    r = FT.ler_wishlist_arquivo(ruim)
    afirmar(r["itens"] == [] and r["erros"] == ["arquivo não é um JSON válido"], r)
    r = FT.ler_wishlist_arquivo(tmp / "falta.json")
    afirmar(r["itens"] == [] and any("ilegível" in e for e in r["erros"]), r)
    vazio = tmp / "vazio.json"
    vazio.write_text("{}", encoding="utf-8")
    r = FT.ler_wishlist_arquivo(vazio)
    afirmar(r["itens"] == [] and r["erros"] == ["nenhum jogo no arquivo"], r)
    escalar = tmp / "escalar.json"
    escalar.write_text("null", encoding="utf-8")
    r = FT.ler_wishlist_arquivo(escalar)
    afirmar(r["itens"] == [] and r["erros"] == ["nenhum jogo no arquivo"], r)
    grande = tmp / "grande.json"
    grande.write_bytes(b"0" * 8_000_001)
    r = FT.ler_wishlist_arquivo(grande)
    afirmar(r["itens"] == [] and any("grande" in e for e in r["erros"]), r)


def teste_desejos_rede_html_erro_e_paginacao_simulada():
    from bib_nucleo import fontes as FT
    afirmar(FT.ler_wishlist("  ")["erros"] and not FT.ler_wishlist("  ")["itens"])
    with patch.object(FT, "abrir_rede", return_value=_resp(b"<html>Homepage</html>")):
        r = FT.ler_wishlist("76561199515332932")
        afirmar(not r["itens"] and any("página" in e for e in r["erros"]), r)
    with patch.object(FT, "abrir_rede", return_value=_resp(b"{invalido")):
        r = FT.ler_wishlist("76561199515332932")
        afirmar(not r["itens"] and r["erros"] == ["resposta inválida da Steam"], r)
    with patch.object(FT, "abrir_rede", return_value=_resp(b"[]")):
        r = FT.ler_wishlist("76561199515332932")
        afirmar(not r["itens"] and r["erros"] == ["formato inesperado da Steam"], r)

    paginas = [json.dumps({"10": {"name": "Alpha"}, "xx": {"name": "Ruim"},
                           "20": {"name": ""}}).encode(),
               json.dumps({}).encode()]
    chamadas = []

    def roteador(req, timeout=None):
        chamadas.append(req.full_url)
        return _resp(paginas.pop(0))

    with patch.object(FT, "abrir_rede", side_effect=roteador):
        r = FT.ler_wishlist("76561199515332932")
    afirmar(r["itens"] == [{"appid": "10", "titulo": "Alpha"}] and not r["erros"], r)
    afirmar(len(chamadas) == 1 and chamadas[0].endswith("?p=0"), chamadas)

    def quebrado(req, timeout=None):
        raise urllib.request.URLError("rede simulada desligada")
    with patch.object(FT, "abrir_rede", side_effect=quebrado):
        r = FT.ler_wishlist("76561199515332932")
        afirmar(not r["itens"] and any("wishlist falhou" in e for e in r["erros"]), r)


def teste_desejos_sincronizar_preserva_manual_e_obtido():
    tmp = Path(tempfile.mkdtemp(prefix="a2-wish-db-"))
    db = tmp / "colecao.db"
    con = core.get_db(db)
    try:
        afirmar(core.sincronizar_desejos(con, [{"appid": "10", "titulo": "Jogo A"},
                                               {"appid": "xx", "titulo": "Ruim"},
                                               {"appid": "20", "titulo": ""},
                                               {"appid": "10", "titulo": "Jogo A"},
                                               "linha solta"])["novos"] == 1)
        core.adicionar_desejo(con, "99", "Manual")
        did_a = con.execute("SELECT id FROM desejos WHERE appid='10'").fetchone()["id"]
        core.marcar_desejo_obtido(con, did_a)
        # O obtido some da lista remota e o manual não está nela: nenhum dos
        # dois pode ser apagado ou ressuscitado pela sincronização.
        r = core.sincronizar_desejos(con, [{"appid": "30", "titulo": "Jogo C"}])
        afirmar(r == {"novos": 1, "atualizados": 0, "removidos": 0}, r)
        todos = {d["appid"]: d for d in core.listar_desejos(con, incluir_obtidos=True)}
        afirmar(set(todos) == {"10", "99", "30"}, sorted(todos))
        afirmar(todos["10"]["obtido_em"], todos["10"])
        afirmar(todos["99"]["manual"] == 1, todos["99"])
        visiveis = {d["appid"] for d in core.listar_desejos(con)}
        afirmar(visiveis == {"99", "30"}, visiveis)
    finally:
        con.close()


def teste_desejos_backup_antes_de_gravar_e_steam_sem_launcher():
    from bib_nucleo import fontes as FT
    tmp = Path(tempfile.mkdtemp(prefix="a2-wish-bak-"))
    db = tmp / "colecao.db"
    con = core.get_db(db)
    con.close()
    alvo = core.fazer_backup(db)
    afirmar(Path(alvo["db"]).is_file() and Path(alvo["json"]).is_file(), alvo)
    afirmar("ler_wishlist" in core.__all__ and "ler_wishlist_arquivo" in core.__all__)
    afirmar("sincronizar_desejos" in core.__all__ and "listar_desejos" in core.__all__)
    fonte = Path(FT.__file__).read_text(encoding="utf-8")
    afirmar("subprocess" not in fonte and "Popen" not in fonte, "wishlist não executa nada")
    afirmar("wishlistdata" in fonte and "storesearch" in fonte, "endpoints conhecidos")
