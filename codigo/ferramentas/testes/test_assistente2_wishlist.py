"""A2-02 (Assistente 2): wishlist JSON com validação e falha explícita no Steam.

Steam é catálogo/referência, não launcher nem sync de conquistas: os casos
abaixo usam rede/subprocessos simulados e banco sintético. Não toca
test_controle_e_desejos.py (A1); este é o módulo próprio do A2.
"""
import json
import tempfile
import urllib.request
from pathlib import Path
from unittest.mock import patch

import bib_core as core
from executar import afirmar


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


def teste_assistente2_wishlist_arquivo_valida_dict_lista_e_dedup():
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


def teste_assistente2_wishlist_arquivo_falha_explicita_html_invalido_ausente():
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


def teste_assistente2_wishlist_rede_html_erro_e_paginacao_simulada():
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


def teste_assistente2_wishlist_sincronizar_preserva_manual_e_obtido():
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


def teste_assistente2_wishlist_backup_antes_de_gravar_e_steam_sem_launcher():
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
