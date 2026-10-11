"""OAuth/catálogo Spotify e pipeline local: sem Spotify/YouTube/processos reais."""
import base64
import hashlib
import io
import tempfile
import threading
import time
import urllib.parse
import wave
from pathlib import Path
from unittest.mock import patch

import bib_core as core
from bib_nucleo import online, spotify
from executar import afirmar
from servicos_ui import ServicoBiblioteca


def _track(ident="a" * 22, nome="Faixa"):
    return {"id": ident, "type": "track", "name": nome, "artists": [{"name": "Artista"}],
            "duration_ms": 123000, "album": {"name": "Álbum", "images": []}}


def teste_spotify_metadados_nulos_episodios_e_links():
    f = spotify.normalizar_faixa({"item": _track()})
    afirmar(f["titulo"] == "Faixa" and f["artista"] == "Artista" and f["album"] == "Álbum", f)
    afirmar(f["uri"] == "spotify:track:" + "a" * 22)
    for item in (None, {"track": None}, {"item": {"id": "a" * 22, "type": "episode"}},
                 dict(_track(), is_local=True)):
        afirmar(spotify.normalizar_faixa(item) is None, item)
    afirmar(spotify.identificar_spotify("https://open.spotify.com/intl-pt/playlist/" + "b" * 22 + "?si=xyz") == ("playlist", "b" * 22))
    afirmar(spotify.identificar_spotify("https://example.com/track/" + "a" * 22) is None)


def teste_spotify_pkce_loopback_state_e_token_nao_exposto():
    online.configurar_provedores({"spotify_client_id": "a" * 32})
    cliente = spotify.ClienteSpotify()
    criados = []

    class Servidor:
        def __init__(self, endereco, handler):
            criados.append((endereco, handler))
        def handle_request(self): time.sleep(0.01)
        def server_close(self): pass

    try:
        with patch.object(spotify, "HTTPServer", Servidor):
            url = cliente.iniciar_login()
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(cliente._verifier.encode()).digest()).rstrip(b"=").decode()
        afirmar(q["code_challenge"] == [challenge] and q["code_challenge_method"] == ["S256"])
        afirmar(q["redirect_uri"] == [spotify.REDIRECT_URI] and cliente._verifier not in url)
        afirmar(criados[0][0] == ("127.0.0.1", 43827))
        handler = object.__new__(criados[0][1])
        handler.wfile = io.BytesIO()
        status = []
        handler.send_response = status.append
        handler.send_header = lambda *_a: None
        handler.end_headers = lambda: None
        handler.path = "/callback?code=teste&state=forjado"
        handler.do_GET()
        afirmar(status[-1] == 400 and cliente.receber_callback() is None)
        handler.path = "/callback?" + urllib.parse.urlencode({"code": "autorizado", "state": cliente._state})
        handler.do_GET()
        resposta = cliente.receber_callback()
        afirmar(status[-1] == 200 and resposta["code"] == "autorizado")
        with patch.object(online, "requisitar_json", return_value={"access_token": "segredo-access", "refresh_token": "segredo-refresh", "expires_in": 3600}) as req:
            estado = cliente.finalizar_login(resposta)
            body = urllib.parse.parse_qs(req.call_args.kwargs["dados"].decode())
            afirmar(body["grant_type"] == ["authorization_code"] and "code_verifier" in body)
            afirmar(estado["conectado"] and "segredo" not in repr(estado))
    finally:
        cliente.fechar()


def teste_spotify_refresh_paginacao_cache_preserva_catalogo():
    cliente = spotify.ClienteSpotify()
    online.gravar_json(cliente.token_path, {"access_token": "velho", "refresh_token": "refresh", "expires_at": 0, "client_id": "a" * 32})
    pagina = {"items": [{"item": _track()}, {"track": None}], "next": "https://api.spotify.com/v1/me/tracks?offset=50"}
    with patch.object(online, "requisitar_json", side_effect=[{"access_token": "novo", "expires_in": 3600}, pagina]) as req:
        r = cliente.consultar("salvas")
        afirmar(len(r["itens"]) == 1 and r["next"], r)
        afirmar(req.call_args.kwargs["headers"]["Authorization"] == "Bearer novo")
        afirmar(online.ler_json(cliente.token_path)["refresh_token"] == "refresh")
    with patch.object(online, "requisitar_json", side_effect=ValueError("offline")):
        r = cliente.consultar("salvas")
        afirmar(r["cache"] and len(r["itens"]) == 1 and "preservado" in r["aviso"])
    metas = online.ler_json(core.DADOS_DIR / "spotify/faixas.json")
    afirmar("spotify:track:" + "a" * 22 in metas and "access_token" not in repr(metas))
    try:
        cliente.consultar("salvas", pagina="https://example.com/roubar-token")
    except ValueError:
        pass
    else:
        raise AssertionError("paginação enviou o token para outro host")


def teste_spotify_busca_publica_sem_login_e_codigo_manual():
    online.configurar_provedores({"spotify_client_id": "Z" * 32, "spotify_client_secret": "segredo"})
    cliente = spotify.ClienteSpotify()
    cliente.token_path.unlink(missing_ok=True)
    chamadas = []

    def fake(url, headers=None, dados=None, timeout=15, limite=4000000):
        chamadas.append((url, (headers or {}).get("Authorization", "")))
        if url.endswith("/api/token"):
            corpo = dados.decode()
            assert "grant_type=client_credentials" in corpo, corpo
            assert "segredo" not in (headers or {}).get("Authorization", "")
            return {"access_token": "token-app", "expires_in": 3600}
        return {"tracks": {"items": [_track()], "next": ""}}

    try:
        with patch.object(online, "requisitar_json", side_effect=fake):
            r = cliente.consultar("busca", "alguma faixa")
            afirmar(len(r["itens"]) == 1 and not r.get("cache"), r)
            api = [(u, a) for u, a in chamadas if "api.spotify.com" in u]
            afirmar(api and all(auth == "Bearer token-app" for _, auth in api), chamadas)
            afirmar("segredo" not in repr(r))
        try:
            cliente.trocar_codigo("codigo-qualquer")
        except ValueError as e:
            afirmar("Conectar Spotify" in str(e), e)
        else:
            raise AssertionError("trocou código sem verifier")
        cliente._verifier = "verificador-fake"
        with patch.object(online, "requisitar_json", return_value={"access_token": "a", "refresh_token": "r", "expires_in": 10}):
            cliente.trocar_codigo("codigo-valido")
            afirmar(cliente.estado()["conectado"])
    finally:
        cliente.fechar()
        cliente.token_path.unlink(missing_ok=True)
        cliente.app_token_path.unlink(missing_ok=True)


def teste_spotify_modos_de_conta_sem_login_orientam():
    online.configurar_provedores({"spotify_client_id": "a" * 32, "spotify_client_secret": ""})
    cliente = spotify.ClienteSpotify()
    cliente.token_path.unlink(missing_ok=True)
    cliente.app_token_path.unlink(missing_ok=True)
    try:
        cliente.consultar("playlists")
    except ValueError as e:
        afirmar("Conecte sua conta" in str(e), e)
    else:
        raise AssertionError("listou playlists sem login nem secret")
    try:
        cliente.consultar("busca", "alguma faixa")
    except ValueError as e:
        afirmar("Client Secret" in str(e) or "conta Spotify" in str(e), e)
    else:
        raise AssertionError("buscou sem credencial alguma")
    try:
        online.configurar_provedores({"spotify_client_id": "curto"})
        cliente.iniciar_login()
    except ValueError as e:
        afirmar("dashboard" in str(e) and "redirect" in str(e), e)
    else:
        raise AssertionError("aceitou client id inválido")
    finally:
        cliente.fechar()


def teste_spotify_codigo_invalido_e_fallback_conta_privada():
    online.configurar_provedores({"spotify_client_id": "b" * 32, "spotify_client_secret": "s"})
    cliente = spotify.ClienteSpotify()
    try:
        for codigo in ("", "   ", "a" * 501, "code com espaço"):
            try:
                cliente.trocar_codigo(codigo)
            except ValueError:
                pass
            else:
                raise AssertionError("aceitou código inválido")
        chamadas = []

        def fake(url, headers=None, dados=None, timeout=15, limite=4000000):
            auth = (headers or {}).get("Authorization", "")
            chamadas.append((url, auth))
            if url.endswith("/api/token"):
                return {"access_token": "app", "expires_in": 3600}
            if auth == "Bearer u":
                return {"items": [], "next": ""}
            raise ValueError("Provedor indisponível (HTTP 401).")

        with patch.object(online, "requisitar_json", side_effect=fake):
            online.gravar_json(cliente.token_path, {"access_token": "u", "refresh_token": "r",
                                                    "expires_at": 9999999999.0, "client_id": "b" * 32})
            r = cliente._get_publico("playlists/" + "c" * 22 + "/items?limit=50")
            afirmar(r == {"items": [], "next": ""}, r)
            afirmar(chamadas[-1][1] == "Bearer u", chamadas)
    finally:
        cliente.fechar()
        cliente.token_path.unlink(missing_ok=True)
        cliente.app_token_path.unlink(missing_ok=True)


def teste_pipeline_spotify_importa_no_hub_cancela_e_retoma_com_dedup():
    db = Path(tempfile.mkdtemp()) / "colecao.db"
    servico = ServicoBiblioteca(db)
    fila = [spotify.normalizar_faixa(_track("a" * 22, "Uma")), spotify.normalizar_faixa(_track("b" * 22, "Duas"))]
    r = servico.enfileirar_musicas(fila)
    afirmar(r["novos"] == 2)
    afirmar(servico.enfileirar_musicas(fila)["ignorados"] == 2)
    parar = threading.Event()
    chamadas = []

    def baixar(con, did, progresso=None):
        chamadas.append(did)
        arq = core.BAIXAR_DIR / (str(did) + ".wav")
        arq.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(arq), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(bytes([did % 255, 0]) * 800)
        core.marcar_download(con, did, "baixado", video_id="teste", musica_path=str(arq))
        if progresso:
            progresso(did, 100)
        parar.set()
        return {"ok": True}

    with patch.object(core, "localizar_ytdlp", return_value="fake-ytdlp"), \
            patch.object(core, "baixar_faixa", side_effect=baixar), \
            patch.object(core.baixar, "localizar_ffmpeg", return_value=""), \
            patch.object(core, "baixar_capa_album", return_value={"ok": False}):
        r = servico.baixar_musicas(parar)
        afirmar(r["novas"] == 1 and r["cancelado"], r)
        snap = servico.snapshot()
        afirmar(len(snap["musicas"]) == 1 and snap["musicas"][0]["origem"] == "spotify-catalogo")
        afirmar(Path(snap["musicas"][0]["musica_path"]).is_file())
        afirmar([d["estado"] for d in snap["fila_musicas"]] == ["pronta", "pendente"])
        parar.clear()
        r = servico.baixar_musicas(parar)
        afirmar(r["novas"] == 1 and len(servico.snapshot()["musicas"]) == 2, r)
        afirmar(len(chamadas) == 2, "rebaixou uma faixa pronta")


def teste_conversao_atomica_falha_preserva_staging_e_retoma_sem_ytdlp():
    import subprocess
    db = Path(tempfile.mkdtemp()) / "colecao.db"
    servico = ServicoBiblioteca(db)
    servico.enfileirar_musicas([{"titulo": "Falha de conversão", "artista": "Teste"}])
    con = core.get_db(db)
    try:
        did = core.listar_downloads(con)[0]["id"]
        staging = core.BAIXAR_DIR / "audio.wav"
        staging.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(staging), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(b"\x00\x00" * 800)
        core.marcar_download(con, did, "baixado", video_id="teste", musica_path=str(staging))
        def falhar(cmd, **_kwargs):
            Path(cmd[-1]).write_bytes(b"mp3-incompleto")
            return subprocess.CompletedProcess(cmd, 1, "", "conversão interrompida")
        with patch.object(core.baixar, "localizar_ffmpeg", return_value="fake-ffmpeg"), \
                patch.object(core.baixar.subprocess, "run", side_effect=falhar):
            r = core.converter_faixa(con, did, capa_auto=False)
        afirmar(not r["ok"] and staging.is_file() and not list(core.MUSICAS_DIR.glob("*.mp3")), r)
        afirmar(core.listar_downloads(con)[0]["estado"] == "falha")
    finally:
        con.close()
    with patch.object(core, "localizar_ytdlp", return_value=""), \
            patch.object(core, "baixar_faixa", side_effect=AssertionError("rebaixou áudio completo")), \
            patch.object(core.baixar, "localizar_ffmpeg", return_value=""), \
            patch.object(core, "baixar_capa_album", return_value={"ok": False}):
        r = servico.baixar_musicas(threading.Event())
    afirmar(r["novas"] == 1 and len(servico.snapshot()["musicas"]) == 1, r)
