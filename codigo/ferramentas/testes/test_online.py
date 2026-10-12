"""Provedores de capas/configuração com HTTP simulado e persistência real no sandbox."""
import base64
import tempfile
from pathlib import Path
from unittest.mock import patch

import bib_core as core
from bib_nucleo import capas, online
from executar import afirmar

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jX1sAAAAASUVORK5CYII=")


def teste_config_provedores_preserva_chaves_e_nao_expoe_segredos():
    online.configurar_provedores({"steam_key": "segredo-steam", "steamgriddb_key": "segredo-grid"})
    online.configurar_provedores({"steam_key": "", "spotify_client_id": "a" * 32,
                                    "spotify_client_secret": "segredo-spotify"})
    afirmar(online.chave_provedor("steam_key") == "segredo-steam")
    estado = online.estado_provedores()
    afirmar(all(isinstance(v, bool) for v in estado.values()) and all(estado.values()), estado)
    afirmar("segredo" not in repr(estado))


def teste_baixar_texto_limites_e_esquema():
    import urllib.error
    for url in ("http://inseguro.example/x", "ftp://a.example/x", "", "https://user:pass@example.com/"):
        try:
            online.baixar_texto(url)
        except ValueError:
            pass
        else:
            raise AssertionError("aceitou URL inválida: " + url)

    class Resp:
        def __init__(self, raw):
            self._raw = raw
        def read(self, _n=-1):
            return self._raw
        def __enter__(self):
            return self
        def __exit__(self, *_a):
            return False

    import urllib.request
    velho = urllib.request.urlopen
    try:
        urllib.request.urlopen = lambda *a, **k: Resp("olá".encode("latin-1"))
        afirmar(online.baixar_texto("https://example.com/") == "olá")
        urllib.request.urlopen = lambda *a, **k: Resp(b"x" * 2_000_001)
        try:
            online.baixar_texto("https://example.com/grande")
        except ValueError:
            pass
        else:
            raise AssertionError("aceitou resposta gigante")
        urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(
            urllib.error.HTTPError("https://example.com/", 429, "limite", {}, None))
        try:
            online.baixar_texto("https://example.com/")
        except ValueError as e:
            afirmar("429" in str(e), e)
        else:
            raise AssertionError("engoliu HTTP 429")
    finally:
        urllib.request.urlopen = velho


def teste_capas_fontes_e_cache_offline_sem_consulta_implicita():
    musica = {"titulo": "Flor", "artista": "Autor", "album": "Luz"}
    respostas = [
        {"results": [{"artistName": "Autor", "collectionName": "Luz", "artworkUrl100": "https://a.example/100x100bb.jpg"}]},
        {"release-groups": [{"id": "12345678-1234-1234-1234-123456789abc", "title": "Luz", "artist-credit": [{"name": "Autor"}]}]},
        {"data": [{"title": "Luz", "artist": {"name": "Autor"}, "cover_xl": "https://b.example/cover.jpg"}]},
    ]
    with patch.object(online, "requisitar_json", side_effect=respostas) as req:
        resultado = capas.buscar_capas("musicas", musica)
        afirmar({i["provedor"] for i in resultado["itens"]} == {"itunes", "musicbrainz", "deezer"}, resultado)
        afirmar(req.call_count == 3)
    with patch.object(online, "requisitar_json", side_effect=AssertionError("offline consultou rede")):
        cache = capas.buscar_capas("musicas", musica)
        afirmar(cache["cache"] and len(cache["itens"]) == 3, cache)
    jogo = {"titulo": "Teste", "shop": "steam", "object_id": "123"}
    with patch.object(online, "requisitar_json", side_effect=[
        {"123": {"success": True, "data": {"name": "Teste", "header_image": "https://a.example/header.jpg"}}},
        {"title": "Teste", "originalimage": {"source": "https://b.example/wiki.jpg"}},
    ]):
        r = capas.buscar_capas("jogos", jogo)
        afirmar({i["provedor"] for i in r["itens"]} == {"steam", "wikipedia"}, r)


def teste_imagem_cache_rejeita_html_e_capas_album_preservam_aspecto():
    class Resp:
        def __enter__(self): return self
        def __exit__(self, *_a): pass
        def read(self, *_a): return PNG
    with patch("urllib.request.urlopen", return_value=Resp()) as req:
        raw, ext, arquivo = online.baixar_imagem("https://example.com/arte")
        afirmar(raw == PNG and ext == ".png" and Path(arquivo).is_file())
        online.baixar_imagem("https://example.com/arte")
        afirmar(req.call_count == 1, "cache baixou a mesma imagem novamente")
    class Html(Resp):
        def read(self, *_a): return b"<!doctype html>" * 100
    with patch("urllib.request.urlopen", return_value=Html()):
        try:
            online.baixar_imagem("https://example.com/nao-imagem")
        except ValueError:
            pass
        else:
            raise AssertionError("publicou HTML como capa")
    db = Path(tempfile.mkdtemp()) / "mus.db"
    con = core.get_db(db)
    try:
        m = core.criar_musica(con, {"titulo": "Faixa", "musica_sha": "a" * 64})
        r = core.salvar_capa_musica_bytes(con, m["id"], "album.png", PNG)
        afirmar(r["ok"], r)
        try:
            from PIL import Image
        except ImportError:
            return
        with Image.open(core.CAPAS_DIR / r["capa"]) as img:
            afirmar(img.width == img.height, "capa de álbum ganhou moldura retrato de jogo")
    finally:
        con.close()


def teste_dicas_provedores_nao_expoem_valor_e_avisam_tamanho():
    """A2-03: aviso de conferência sem jamais expor a credencial."""
    online.configurar_provedores({"spotify_client_id": "a" * 32,
                                  "spotify_client_secret": "x",
                                  "steam_key": "k" * 32})
    dicas = online.dicas_provedores()
    afirmar(dicas["steam_key"]["configurada"] and not dicas["steam_key"]["aviso"], dicas)
    id_spotify = dicas["spotify_client_id"]
    afirmar(id_spotify["configurada"] and not id_spotify["aviso"], dicas)
    segredo = dicas["spotify_client_secret"]
    afirmar(segredo["configurada"] and segredo["tamanho"] == 1, dicas)
    afirmar(segredo["aviso"] and "Confira" in segredo["aviso"], segredo)
    texto = repr(dicas)
    afirmar("x" * 3 not in texto and "aaaa" not in texto, "valor vazou no diagnóstico")
    for chave in ("steamgriddb_key",):
        afirmar(not dicas[chave]["configurada"] and dicas[chave]["aviso"] == "", dicas)
    estado = online.estado_provedores()
    afirmar(estado["steam_key"] and estado["spotify_client_id"] and estado["spotify_client_secret"], estado)


def teste_http_chave_steam_nao_vaza_em_mensagem_de_erro():
    import urllib.error
    erro = urllib.error.HTTPError("https://example.com/?key=segredo", 401, "invalid key", {}, None)
    with patch("urllib.request.urlopen", side_effect=erro):
        try:
            online.requisitar_json("https://example.com/?key=segredo")
        except ValueError as exc:
            afirmar("401" in str(exc) and "segredo" not in str(exc), str(exc))
        else:
            raise AssertionError("erro HTTP ignorado")


def teste_steamgriddb_autorizacao_e_resultados():
    online.configurar_provedores({"steamgriddb_key": "minha-chave"})
    with patch.object(online, "requisitar_json", side_effect=[
            {"data": [{"id": 123, "name": "Aventura"}]},
            {"data": [{"url": "https://example.com/poster.png"}]}]) as req:
        r = capas.buscar_capas("jogos", {"titulo": "Aventura"}, "steamgriddb")
        afirmar(len(r["itens"]) == 1 and r["itens"][0]["fonte"] == "SteamGridDB", r)
        afirmar(all(c.kwargs["headers"]["Authorization"] == "Bearer minha-chave" for c in req.call_args_list))
        afirmar("minha-chave" not in repr(r))
