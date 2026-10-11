"""Bibliotecas de música sem chave: fixtures, limites, cache e ida à fila."""
import tempfile
from pathlib import Path
from unittest.mock import patch

from bib_nucleo import musica_online as MO
from bib_nucleo import online
from executar import afirmar
from servicos_ui import ServicoBiblioteca

DEEZER = {"data": [{"id": 1, "title": "Faixa", "duration": 200,
                    "link": "https://www.deezer.com/track/1",
                    "artist": {"name": "Artista"}, "album": {"title": "Álbum", "cover_xl": "https://cdn.example/xl.jpg"}}]}
ITUNES = {"results": [{"trackId": 2, "trackName": "Faixa", "artistName": "Artista",
                       "collectionName": "Álbum", "trackTimeMillis": 180000,
                       "artworkUrl100": "https://a.example/100x100bb.jpg",
                       "trackViewUrl": "https://music.example/t"}]}
MB = {"recordings": [{"id": "12345678-1234-1234-1234-123456789abc", "title": "Faixa",
                      "artist-credit": [{"name": "Artista"}],
                      "releases": [{"title": "Álbum"}]}]}


def teste_musica_online_faixas_normalizadas_e_sem_chave():
    with patch.object(online, "requisitar_json", return_value=DEEZER):
        d = MO.buscar_deezer("artista faixa")
        afirmar(d[0]["duracao_ms"] == 200000 and d[0]["fonte"] == "deezer", d)
        afirmar(d[0]["uri"] == "deezer:track:1")
    with patch.object(online, "requisitar_json", return_value=ITUNES):
        i = MO.buscar_itunes("artista faixa")
        afirmar(i[0]["capa_url"] == "https://a.example/600x600bb.jpg", i)
        afirmar(i[0]["duracao_ms"] == 180000)
    with patch.object(online, "requisitar_json", return_value=MB):
        m = MO.buscar_musicbrainz("artista faixa")
        afirmar(m[0]["url"].startswith("https://musicbrainz.org/recording/"), m)
    for fn in (MO.buscar_deezer, MO.buscar_itunes, MO.buscar_musicbrainz):
        try:
            fn("x")
        except ValueError:
            pass
        else:
            raise AssertionError("buscou com termo curto")
    afirmar(MO._faixa("deezer", "   ", "Artista") is None)
    afirmar(MO._faixa("itunes", "T", "A", capa_url="http://inseguro/x.jpg")["capa_url"] == "")


def teste_musica_online_todas_cache_dedup_e_falha_parcial():
    with patch.object(online, "requisitar_json", side_effect=[DEEZER, ITUNES, MB]):
        r = MO.buscar_musicas("artista faixa")
        afirmar(len(r["itens"]) == 1 and not r["erros"] and not r["cache"], r)
    with patch.object(online, "requisitar_json", side_effect=AssertionError("rede com cache")):
        r = MO.buscar_musicas("artista faixa")
        afirmar(r["cache"] and len(r["itens"]) == 1, r)
    with patch.object(online, "requisitar_json", side_effect=[DEEZER, ValueError("iTunes fora"), MB]):
        r = MO.buscar_musicas("artista faixa", atualizar=True)
        afirmar(len(r["itens"]) == 1 and len(r["erros"]) == 1 and "iTunes" in r["erros"][0], r)
    try:
        MO.buscar_musicas("artista faixa", "napster")
    except ValueError:
        pass
    else:
        raise AssertionError("aceitou biblioteca inválida")


def teste_musica_online_rate_limit_musicbrainz_e_ids():
    chamadas = []

    def fake(url, **_kw):
        chamadas.append(url)
        return MB

    with patch.object(online, "requisitar_json", side_effect=fake):
        MO.buscar_musicbrainz("a b")
        MO.buscar_musicbrainz("c d")
    afirmar(len(chamadas) == 2 and all("musicbrainz.org" in u for u in chamadas))
    with patch.object(online, "requisitar_json", return_value={"data": [
            {"id": 1, "title": "T", "artist": {"name": "A"}, "album": {}}]}):
        d = MO.buscar_deezer("a b")
        afirmar(d[0]["album"] == "" and d[0]["capa_url"] == "" and d[0]["duracao_ms"] == 0, d)


def teste_musica_online_ponte_fila_e_mensagem():
    db = Path(tempfile.mkdtemp()) / "colecao.db"
    servico = ServicoBiblioteca(db)
    faixas = [{"titulo": "Faixa", "artista": "Artista", "album": "Álbum",
               "url": "https://www.deezer.com/track/1", "uri": "deezer:track:1",
               "fonte": "deezer", "nome_fonte": "Deezer"}]
    with patch.object(MO, "buscar_musicas", return_value={"itens": faixas, "erros": [], "cache": False}):
        r = servico.buscar_musicas_online("artista faixa", "deezer")
        afirmar(len(r["itens"]) == 1, r)
    r = servico.enfileirar_musicas([{"titulo": f["titulo"], "artista": f["artista"],
                                     "album": f["album"], "uri": f["url"]} for f in faixas])
    afirmar(r["novos"] == 1, r)
    fila = servico.snapshot()["fila_musicas"]
    afirmar(fila[0]["uri"] == "https://www.deezer.com/track/1", fila)
    with patch.object(servico.spotify, "consultar",
                      return_value={"itens": [{"titulo": "S", "uri": "spotify:track:" + "a" * 22}],
                                    "cache": True, "aviso": "offline, catálogo preservado"}):
        r = servico.buscar_musicas_online("x", "spotify")
        afirmar(r["itens"][0]["nome_fonte"] == "Spotify" and r["cache"] and "offline" in r["aviso"], r)
