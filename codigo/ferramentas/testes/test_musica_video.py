"""YouTube ↔ Spotify: do título do vídeo à faixa certa no Spotify e o MP3 com os dados dela.

Spotify, yt-dlp e FFmpeg simulados; banco temporário.
"""
import tempfile
from pathlib import Path
from unittest.mock import patch

from bib_nucleo import banco
from bib_nucleo.rede import musica_video
from executar import afirmar
from ponte import Ponte


def _chamar_v(ponte, metodo, **params):
    """Pedido NDJSON pela ponte em processo; devolve a resposta decodificada."""
    import json
    return json.loads(ponte.executar_linha(json.dumps({"id": 1, "metodo": metodo, "params": params})))


def teste_termos_do_video_tira_ruido_do_clipe():
    casos = {
        ("Rick Astley - Never Gonna Give You Up (Official Music Video)", "Rick Astley"):
            ("Rick Astley", "Never Gonna Give You Up"),
        ("Anitta – Envolver [Official Video] | Letra", "Anitta"): ("Anitta", "Envolver"),
        ("Bohemian Rhapsody (Remastered 2011)", "Queen - Topic"): ("Queen", "Bohemian Rhapsody"),
        ("Djavan - Oceano (Ao Vivo)", "DjavanVEVO"): ("Djavan", "Oceano"),
    }
    for (titulo, canal), esperado in casos.items():
        afirmar(musica_video.termos_do_video(titulo, canal) == esperado,
                (titulo, musica_video.termos_do_video(titulo, canal)))


def teste_melhor_faixa_exige_titulo_e_artista():
    candidatos = [
        {"titulo": "Never Gonna Give You Up", "artista": "Cover Band", "duracao_ms": 213000},
        {"titulo": "Never Gonna Give You Up", "artista": "Rick Astley", "duracao_ms": 213573},
        {"titulo": "Together Forever", "artista": "Rick Astley", "duracao_ms": 200000},
    ]
    melhor = musica_video.melhor_faixa(candidatos, "Rick Astley", "Never Gonna Give You Up", 212)
    afirmar(melhor is not None and melhor["artista"] == "Rick Astley" and melhor["nota"] >= 0.9, melhor)
    # artista certo mas outra música: não serve
    afirmar(musica_video.melhor_faixa(candidatos[2:], "Rick Astley", "Never Gonna Give You Up") is None)
    # sem acento/maiúsculas e com "feat." no título do Spotify
    sp = [{"titulo": "Évidemment (feat. X)", "artista": "Ane", "duracao_ms": 0}]
    afirmar(musica_video.melhor_faixa(sp, "ane", "evidemment") is not None)


def teste_versao_spotify_usa_o_cliente_e_avisa_sem_config():
    class Cliente:
        def __init__(self, itens=None, erro=None):
            self.itens, self.erro, self.termos = itens or [], erro, []

        def catalogo(self, modo, termo=""):
            self.termos.append((modo, termo))
            if self.erro:
                raise ValueError(self.erro)
            return {"itens": self.itens}

    faixa = {"titulo": "Envolver", "artista": "Anitta", "album": "Versions of Me", "duracao_ms": 193000,
             "capa_url": "https://i.scdn.co/x.jpg", "url": "https://open.spotify.com/track/abc"}
    c = Cliente([faixa])
    r = musica_video.versao_spotify(c, {"titulo": "Anitta - Envolver (Official Video)", "canal": "Anitta",
                                        "duracao_s": 200})
    afirmar(r["faixa"] and r["faixa"]["album"] == "Versions of Me" and r["aviso"] == "", r)
    afirmar(c.termos == [("busca", "Envolver Anitta")], c.termos)
    r = musica_video.versao_spotify(Cliente(erro="Busca pública exige o Client Secret"), {"titulo": "Ana - Bela"})
    afirmar(r["faixa"] is None and "Client Secret" in r["aviso"], r)
    r = musica_video.versao_spotify(Cliente([]), {"titulo": "A - Bcd"})
    afirmar(r["faixa"] is None and "Spotify" in r["aviso"], r)


def teste_mp3_do_youtube_usa_os_dados_do_spotify():
    from bib_nucleo.rede import videos_youtube as YT
    tmp = Path(tempfile.mkdtemp(prefix="suite-v21-mp3-"))
    con = banco.get_db(tmp / "hub.db")

    def executar(cmd, receber, timeout=0):
        destino = Path(cmd[cmd.index("-o") + 1]).parent / "dQw4w9WgXcQ.mp3"
        destino.write_bytes(b"ID3" + b"x" * 64)
        return 0
    try:
        with patch.object(YT, "_ytdlp", return_value="yt-dlp"), \
                patch("bib_nucleo.baixar.localizar_ffmpeg", return_value="ffmpeg"), \
                patch("bib_nucleo.rede.exigir_rede", lambda *a: None), \
                patch.object(YT, "info_video_youtube", return_value={"titulo": "Rick Astley - NGGYU (Official)", "canal": "RickAstleyVEVO"}), \
                patch.object(YT, "executar_com_progresso", side_effect=executar), \
                patch.object(YT, "_args_js", return_value=[]), \
                patch("bib_nucleo.base.MUSICAS_DIR", tmp / "musicas"):
            r = YT.baixar_audio_youtube(con, "dQw4w9WgXcQ", musica={
                "titulo": "Never Gonna Give You Up", "artista": "Rick Astley", "album": "Whenever You Need Somebody"})
        afirmar(r["ok"] and r["id"], r)
        m = banco.listar_musicas(con)[0]
        afirmar((m["titulo"], m["artista"], m["album"]) ==
                ("Never Gonna Give You Up", "Rick Astley", "Whenever You Need Somebody"), m)
    finally:
        con.close()


def teste_ponte_versao_musica():
    from servicos_ui import ServicoBiblioteca
    servico = ServicoBiblioteca(Path(tempfile.mkdtemp(prefix="suite-mv-")) / "hub.db")
    ponte = Ponte(servico)
    with patch.object(servico.spotify, "catalogo", return_value={"itens": [
            {"titulo": "Oceano", "artista": "Djavan", "album": "Djavan", "duracao_ms": 0, "capa_url": ""}]}):
        r = _chamar_v(ponte, "videos.versao_musica", video={"titulo": "Djavan - Oceano (Ao Vivo)", "canal": "Djavan"})
    afirmar(r["ok"] and r["resultado"]["faixa"]["titulo"] == "Oceano", r)
    afirmar(_chamar_v(ponte, "videos.versao_musica", video={})["ok"] is False)
    afirmar(_chamar_v(ponte, "videos.baixar_mp3", video={"video_id": "abc"}, musica="x")["ok"] is False)
