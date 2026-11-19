"""2.1: vídeo do YouTube ↔ música do Spotify, gêneros da loja Steam e limpezas.

Tudo hermético: Spotify, Steam e qBittorrent simulados; banco temporário.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from bib_nucleo import banco
from bib_nucleo.rede import loja_steam, musica_video
from executar import afirmar
from ponte import Ponte


def _chamar(ponte, metodo, **params):
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


HTML_BUSCA = """
<a href="https://store.steampowered.com/app/367520/" data-ds-appid="367520" class="search_result_row">
 <div class="search_name"><span class="title">Hollow Knight</span></div>
 <div class="discount_block" data-price-final="4699"><div class="discount_pct">-50%</div></div></a>
<a href="https://store.steampowered.com/app/730/" data-ds-appid="730" class="search_result_row">
 <span class="title">Counter-Strike 2</span><div data-price-final="0"></div></a>
<a href="https://store.steampowered.com/app/367520/" data-ds-appid="367520"><span class="title">dup</span></a>
"""


def teste_loja_por_genero_le_a_busca_da_steam():
    cartoes = loja_steam._cartoes_da_busca(HTML_BUSCA)
    afirmar([c["appid"] for c in cartoes] == ["367520", "730"], cartoes)
    afirmar(cartoes[0]["nome"] == "Hollow Knight" and cartoes[0]["preco"]["final"] == 4699
            and cartoes[0]["preco"]["desconto_pct"] == 50, cartoes[0])
    afirmar(cartoes[1]["preco"]["gratis"] is True, cartoes[1])
    afirmar(cartoes[0]["capa"].endswith("/367520/library_600x900.jpg"), cartoes[0])
    pedidos = []

    def falso(url, **kw):
        pedidos.append(url)
        return {"total_count": 99, "results_html": HTML_BUSCA}
    with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"BIBLIOTECA_HOME": tmp}), \
            patch.object(loja_steam.online, "requisitar_json", side_effect=falso), \
            patch.object(loja_steam, "respeitar_ritmo", lambda *a: None):
        r = loja_steam.por_genero("rpg", 1)
    afirmar(r["nome"] == "RPG" and r["total"] == 99 and len(r["itens"]) == 2, r)
    afirmar("tags=122" in pedidos[0] and "start=24" in pedidos[0] and "filter=topsellers" in pedidos[0], pedidos)
    try:
        loja_steam.por_genero("nao-existe")
        afirmar(False, "gênero desconhecido passou")
    except ValueError:
        pass
    afirmar(len({g[2] for g in loja_steam.GENEROS}) == len(loja_steam.GENEROS), "tag repetida")


def teste_qbit_remover_mantem_arquivos():
    from bib_nucleo import qbit
    chamadas = []
    with patch.object(qbit, "qbit_request", side_effect=lambda ep, dados=None, **kw: chamadas.append((ep, dados))):
        afirmar(qbit.qbit_controlar("ABCDEF0123", "remover")["ok"])
        afirmar(not qbit.qbit_controlar("xyz", "remover")["ok"])
        afirmar(not qbit.qbit_controlar("ABCDEF0123", "apagar")["ok"])
    afirmar(chamadas == [("torrents/delete", {"hashes": "ABCDEF0123", "deleteFiles": "false"})], chamadas)


def teste_ponte_limpezas_e_versao_musica():
    from servicos_ui import ServicoBiblioteca
    tmp = Path(tempfile.mkdtemp(prefix="suite-v21-"))
    servico = ServicoBiblioteca(tmp / "hub.db")
    ponte = Ponte(servico)
    con = banco.get_db(servico.db_path)
    try:
        banco.enfileirar_downloads(con, [{"titulo": "A", "artista": "X"}, {"titulo": "B", "artista": "Y"}])
        ids = [d["id"] for d in banco.listar_downloads(con)]
        banco.marcar_download(con, ids[0], "pronta")
    finally:
        con.close()
    r = _chamar(ponte, "musicas.limpar_fila")
    afirmar(r["ok"] and r["resultado"]["removidas"] == 1, r)
    con = banco.get_db(servico.db_path)
    try:
        afirmar([d["titulo"] for d in banco.listar_downloads(con)] == ["B"])
    finally:
        con.close()
    # torrents: só os concluídos saem da lista do cliente
    lista = {"torrents": [{"hash": "AA11", "nome": "pronto", "pct": 100.0, "completo": True},
                          {"hash": "BB22", "nome": "baixando", "pct": 40.0, "completo": False}], "erros": []}
    from bib_nucleo import qbit
    removidos = []
    with patch("bib_nucleo.rede.torrents.listar_torrents", return_value=lista), \
            patch.object(qbit, "qbit_controlar", side_effect=lambda h, a: removidos.append((h, a)) or {"ok": True}):
        r = _chamar(ponte, "torrents.limpar_concluidos")
    afirmar(r["ok"] and r["resultado"] == {"removidos": 1, "erros": []}, r)
    afirmar(removidos == [("AA11", "remover")], removidos)
    afirmar(_chamar(ponte, "torrents.controlar", ident="AA11", acao="apagar")["ok"] is False)
    # vídeo → música no Spotify (cliente simulado)
    with patch.object(servico.spotify, "catalogo", return_value={"itens": [
            {"titulo": "Oceano", "artista": "Djavan", "album": "Djavan", "duracao_ms": 0, "capa_url": ""}]}):
        r = _chamar(ponte, "videos.versao_musica", video={"titulo": "Djavan - Oceano (Ao Vivo)", "canal": "Djavan"})
    afirmar(r["ok"] and r["resultado"]["faixa"]["titulo"] == "Oceano", r)
    afirmar(_chamar(ponte, "videos.versao_musica", video={})["ok"] is False)
    # loja: gêneros vêm da lista fixa, sem rede
    r = _chamar(ponte, "loja.generos")
    afirmar(r["ok"] and {"chave": "rpg", "nome": "RPG"} in r["resultado"], r)
    afirmar(_chamar(ponte, "loja.genero", genero="rpg", pagina=-1)["ok"] is False)
    afirmar(_chamar(ponte, "videos.baixar_mp3", video={"video_id": "abc"}, musica="x")["ok"] is False)


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
