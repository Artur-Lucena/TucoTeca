"""Catálogos SteamRip/FitGirl (busca) e wishlist da Steam (mocks, sem rede)."""
import json
import tempfile
import urllib.request
from pathlib import Path
from unittest.mock import patch

from bib_nucleo import banco, pacotes
from executar import afirmar

BUSCA_HTML = """
<html><body><nav><a href="https://steamrip.com/category/action/">Action</a></nav>
<h2 class="post-title"><a href="https://steamrip.com/ultrakill-free-download-1p/">ULTRAKILL Free Download</a></h2>
<h2><a href="/megabonk-free-download/">MEGABONK Free Download</a></h2>
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


def teste_steamrip_buscar():
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
    velho, _ch = _falso_urlopen([("https://", urllib.request.URLError("off"))])
    try:
        r = FT.buscar_steamrip("x")
        afirmar(r["itens"] == [] and r["erros"], r)
    finally:
        urllib.request.urlopen = velho


FG_BUSCA_HTML = """
<html><body>
<h1 class="entry-title"><a href="https://fitgirl-repacks.site/ball-x-pit/">BALL x PIT + Bonus OST</a></h1>
<h1 class="entry-title"><a href="/speedball/">Speedball – v1.2.8.0</a></h1>
</body></html>
"""


def teste_fitgirl_buscar():
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
    velho, _ch = _falso_urlopen([("https://", urllib.request.URLError("off"))])
    try:
        r = FT.buscar_fitgirl("x")
        afirmar(r["itens"] == [] and r["erros"], r)
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
    con = banco.get_db(db)
    try:
        afirmar(banco.sincronizar_desejos(con, [{"appid": "10", "titulo": "Jogo A"},
                                               {"appid": "xx", "titulo": "Ruim"},
                                               {"appid": "20", "titulo": ""},
                                               {"appid": "10", "titulo": "Jogo A"},
                                               "linha solta"])["novos"] == 1)
        banco.adicionar_desejo(con, "99", "Manual")
        did_a = con.execute("SELECT id FROM desejos WHERE appid='10'").fetchone()["id"]
        banco.marcar_desejo_obtido(con, did_a)
        # O obtido some da lista remota e o manual não está nela: nenhum dos
        # dois pode ser apagado ou ressuscitado pela sincronização.
        r = banco.sincronizar_desejos(con, [{"appid": "30", "titulo": "Jogo C"}])
        afirmar(r == {"novos": 1, "atualizados": 0, "removidos": 0}, r)
        todos = {d["appid"]: d for d in banco.listar_desejos(con, incluir_obtidos=True)}
        afirmar(set(todos) == {"10", "99", "30"}, sorted(todos))
        afirmar(todos["10"]["obtido_em"], todos["10"])
        afirmar(todos["99"]["manual"] == 1, todos["99"])
        visiveis = {d["appid"] for d in banco.listar_desejos(con)}
        afirmar(visiveis == {"99", "30"}, visiveis)
    finally:
        con.close()


def teste_desejos_backup_antes_de_gravar_e_steam_sem_launcher():
    from bib_nucleo import fontes as FT
    tmp = Path(tempfile.mkdtemp(prefix="a2-wish-bak-"))
    db = tmp / "colecao.db"
    con = banco.get_db(db)
    con.close()
    alvo = pacotes.fazer_backup(db)
    afirmar(Path(alvo["db"]).is_file() and Path(alvo["json"]).is_file(), alvo)
    fonte = Path(FT.__file__).read_text(encoding="utf-8")
    afirmar("subprocess" not in fonte and "Popen" not in fonte, "wishlist não executa nada")
    afirmar("wishlistdata" in fonte, "endpoint conhecido")
