"""Catálogo Spotify via OAuth PKCE. Áudio é obtido pelo downloader do Hub.

Nenhuma senha Spotify é recebida pelo Hub. Callback somente em loopback;
tokens e catálogo ficam em dados/spotify, fora do Git.
"""
from __future__ import annotations

import base64
import hashlib
import re
import secrets
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from bib_nucleo import base, online

REDIRECT_URI = "http://127.0.0.1:43827/callback"
SCOPES = "playlist-read-private playlist-read-collaborative user-library-read"
API = "https://api.spotify.com/v1/"
CLIENT_ID_RE = re.compile(r"[A-Za-z0-9]{32}")
MODOS_USUARIO = ("playlists", "salvas")
MODOS_PUBLICOS = ("busca", "faixa", "album", "playlist")


def normalizar_faixa(item):
    if not isinstance(item, dict):
        return None
    faixa = item.get("item") or item.get("track") or item
    if not isinstance(faixa, dict) or faixa.get("type", "track") != "track" or faixa.get("is_local"):
        return None
    ident = str(faixa.get("id") or "")
    if not re.fullmatch(r"[A-Za-z0-9]{22}", ident):
        return None
    album = faixa.get("album") or {}
    imagens = album.get("images") or []
    return {"id": ident, "uri": "spotify:track:" + ident, "titulo": str(faixa.get("name") or ""),
            "artista": "; ".join(a.get("name") or "" for a in faixa.get("artists", []) if isinstance(a, dict)),
            "album": str(album.get("name") or ""), "duracao_ms": faixa.get("duration_ms") or 0,
            "capa_url": (imagens[0].get("url") or "") if imagens and isinstance(imagens[0], dict) else "",
            "url": "https://open.spotify.com/track/" + ident,
            "isrc": (faixa.get("external_ids") or {}).get("isrc") or ""}


def extrair_codigo_retorno(texto: str) -> str:
    """Extrai o código de uma URL de retorno ou aceita um token puro inteiro."""
    texto = str(texto or "").strip()
    if not texto or any(c in texto for c in "\r\n\x00"):
        return ""
    if "://" in texto:
        try:
            url = urllib.parse.urlsplit(texto)
            esperado = urllib.parse.urlsplit(REDIRECT_URI)
            if (url.scheme, url.hostname, url.port, url.path) != (
                    esperado.scheme, esperado.hostname, esperado.port, esperado.path):
                return ""
            valores = urllib.parse.parse_qs(url.query).get("code", [])
            texto = valores[0] if len(valores) == 1 else ""
        except ValueError:
            return ""
    return texto if 0 < len(texto) <= 500 and not any(c.isspace() for c in texto) else ""


def identificar_spotify(texto):
    texto = str(texto or "").strip()
    m = re.fullmatch(r"spotify:(track|playlist|album):([A-Za-z0-9]{22})", texto)
    if m:
        return m.groups()
    p = urllib.parse.urlsplit(texto)
    if p.hostname == "open.spotify.com" and p.scheme == "https":
        partes = p.path.strip("/").split("/")
        if partes and partes[0].startswith("intl-"):
            partes.pop(0)
        if len(partes) == 2 and partes[0] in ("track", "playlist", "album") and re.fullmatch(r"[A-Za-z0-9]{22}", partes[1]):
            return tuple(partes)
    return None


class ClienteSpotify:
    def __init__(self):
        self._cancelar = threading.Event()
        self._thread = None
        self._resposta = None
        self._verifier = ""
        self._state = ""
        self._cliente = ""
        self._lock = threading.RLock()

    @property
    def token_path(self):
        return base.DADOS_DIR / "spotify/token.json"

    @property
    def app_token_path(self):
        return base.DADOS_DIR / "spotify/app-token.json"

    def estado(self):
        token = online.ler_json(self.token_path, {})
        return {"configurado": bool(online.chave_provedor("spotify_client_id")),
                "busca_publica": bool(online.chave_provedor("spotify_client_id")
                                      and online.chave_provedor("spotify_client_secret")),
                "conectado": bool(isinstance(token, dict) and token.get("refresh_token")),
                "aguardando": bool(self._thread and self._thread.is_alive()), "redirect": REDIRECT_URI}

    def _validar_client_id(self):
        cliente = online.chave_provedor("spotify_client_id")
        if not CLIENT_ID_RE.fullmatch(cliente):
            raise ValueError("Client ID Spotify inválido: use o App ID de 32 caracteres do "
                             "painel https://developer.spotify.com/dashboard e registre o redirect "
                             + REDIRECT_URI)
        return cliente

    def iniciar_login(self):
        from bib_nucleo.rede import exigir_rede
        exigir_rede("Conectar Spotify")
        cliente = self._validar_client_id()
        if self._thread and self._thread.is_alive():
            raise ValueError("A autorização Spotify já está aguardando no navegador.")
        self._cliente = cliente
        self._verifier = secrets.token_urlsafe(64)
        self._state = secrets.token_urlsafe(32)
        self._cancelar.clear()
        self._resposta = None
        dono = self

        class Callback(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                p = urllib.parse.urlsplit(self.path)
                q = urllib.parse.parse_qs(p.query)
                valido = p.path == "/callback" and secrets.compare_digest(q.get("state", [""])[0], dono._state)
                if valido:
                    with dono._lock:
                        dono._resposta = {"code": q.get("code", [""])[0], "error": q.get("error", [""])[0]}
                    dono._cancelar.set()
                self.send_response(200 if valido else 400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(("Autorizacao recebida. Volte ao TucoTeca." if valido else
                                  "Callback invalido. Volte ao login do TucoTeca.").encode("utf-8"))

        try:
            servidor = HTTPServer(("127.0.0.1", 43827), Callback)
        except OSError:
            raise ValueError("Porta 43827 em uso (outro Hub aberto?). Feche a outra sessão "
                             "ou libere a porta e tente Conectar Spotify de novo.") from None
        servidor.timeout = 0.5

        def ouvir():
            try:
                fim = time.monotonic() + 180
                while not self._cancelar.is_set() and time.monotonic() < fim:
                    servidor.handle_request()
                if not self._cancelar.is_set():
                    with self._lock:
                        self._resposta = {"error": "tempo esgotado"}
            finally:
                servidor.server_close()

        self._thread = threading.Thread(target=ouvir, name="spotify-callback", daemon=True)
        self._thread.start()
        challenge = base64.urlsafe_b64encode(hashlib.sha256(self._verifier.encode()).digest()).rstrip(b"=").decode()
        return "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(
            {"client_id": cliente, "response_type": "code", "redirect_uri": REDIRECT_URI,
             "scope": SCOPES, "state": self._state, "code_challenge_method": "S256", "code_challenge": challenge})

    def receber_callback(self):
        with self._lock:
            resposta, self._resposta = self._resposta, None
            return resposta

    def finalizar_login(self, resposta):
        self.fechar()
        if resposta.get("error") or not resposta.get("code"):
            raise ValueError("Autorização Spotify cancelada ou expirada.")
        token = online.requisitar_json("https://accounts.spotify.com/api/token", dados=urllib.parse.urlencode(
            {"grant_type": "authorization_code", "code": resposta["code"], "redirect_uri": REDIRECT_URI,
             "client_id": self._cliente, "code_verifier": self._verifier}).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        self._verifier = ""
        self._guardar_token(token)
        return self.estado()

    def trocar_codigo(self, codigo):
        """Troca código colado da URL de retorno (fallback se o loopback falhar).

        Aceita o código puro OU a URL inteira (`.../callback?code=...`);
        colar a URL era o erro do print (virava "código inválido").
        """
        entrada = str(codigo or "").strip()
        if "://" in entrada and self._state:
            state = urllib.parse.parse_qs(urllib.parse.urlsplit(entrada).query).get("state", [""])[0]
            if not secrets.compare_digest(state, self._state):
                raise ValueError("O retorno pertence a outra autorização. Conecte novamente.")
        codigo = extrair_codigo_retorno(entrada)
        if not codigo or len(codigo) > 500 or any(c in codigo for c in "\r\n\x00 "):
            raise ValueError("Cole o código 'code=…' da URL de retorno do Spotify "
                             "(vale a URL inteira http://127.0.0.1:43827/callback?...).")
        if not self._verifier:
            raise ValueError("Clique em Conectar Spotify primeiro e autorize no navegador.")
        return self.finalizar_login({"code": codigo})

    def _token_app(self, atualizar=False):
        """Token só-aplicativo (Client Credentials): busca pública sem login do usuário."""
        with self._lock:
            app = online.ler_json(self.app_token_path, {})
            if (not atualizar and isinstance(app, dict) and app.get("access_token")
                    and time.time() < app.get("expires_at", 0)):
                return app["access_token"]
            cliente = self._validar_client_id()
            segredo = online.chave_provedor("spotify_client_secret")
            if not segredo:
                raise ValueError("Busca pública exige o Client Secret em Provedores online "
                                 "(ou conecte sua conta Spotify).")
            basic = base64.b64encode((cliente + ":" + segredo).encode()).decode()
            token = online.requisitar_json(
                "https://accounts.spotify.com/api/token",
                dados=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
                headers={"Authorization": "Basic " + basic,
                         "Content-Type": "application/x-www-form-urlencoded"})
            if not isinstance(token, dict) or not token.get("access_token"):
                raise ValueError("Spotify não retornou um token de busca válido.")
            online.gravar_json(self.app_token_path,
                               {"access_token": token["access_token"],
                                "expires_at": time.time() + max(0, int(token.get("expires_in") or 0)) - 30})
            return token["access_token"]

    def _guardar_token(self, token, antigo=None):
        if not isinstance(token, dict) or not token.get("access_token"):
            raise ValueError("Spotify não retornou um token válido.")
        antigo = antigo or {}
        dados = {"access_token": token["access_token"],
                 "refresh_token": token.get("refresh_token") or antigo.get("refresh_token") or "",
                 "expires_at": time.time() + max(0, int(token.get("expires_in") or 0)) - 30,
                 "client_id": self._cliente or antigo.get("client_id") or online.chave_provedor("spotify_client_id")}
        online.gravar_json(self.token_path, dados)

    def _token(self, atualizar=False):
        with self._lock:
            token = online.ler_json(self.token_path, {})
            if not isinstance(token, dict) or not token.get("refresh_token"):
                raise ValueError("Conecte sua conta Spotify para consultar o catálogo.")
            if atualizar or time.time() >= token.get("expires_at", 0):
                novo = online.requisitar_json("https://accounts.spotify.com/api/token", dados=urllib.parse.urlencode(
                    {"grant_type": "refresh_token", "refresh_token": token["refresh_token"],
                     "client_id": token.get("client_id") or online.chave_provedor("spotify_client_id")}).encode(),
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
                self._guardar_token(novo, token)
                token = online.ler_json(self.token_path, {})
            return token["access_token"]

    def _get(self, caminho):
        url = caminho if caminho.startswith(API) else API + caminho
        if not url.startswith(API) or urllib.parse.urlsplit(url).hostname != "api.spotify.com":
            raise ValueError("Página Spotify inválida.")
        try:
            return online.requisitar_json(url, headers={"Authorization": "Bearer " + self._token()})
        except ValueError as e:
            if "HTTP 401" not in str(e):
                raise
            return online.requisitar_json(url, headers={"Authorization": "Bearer " + self._token(True)})

    def _usuario_conectado(self):
        token = online.ler_json(self.token_path, {})
        return isinstance(token, dict) and bool(token.get("refresh_token"))

    def _get_publico(self, caminho):
        """GET com token de aplicativo; playlist privada cai p/ conta conectada."""
        url = caminho if caminho.startswith(API) else API + caminho
        if not url.startswith(API) or urllib.parse.urlsplit(url).hostname != "api.spotify.com":
            raise ValueError("Página Spotify inválida.")
        try:
            return online.requisitar_json(url, headers={"Authorization": "Bearer " + self._token_app()})
        except ValueError as e:
            if "HTTP 401" in str(e):
                try:
                    return online.requisitar_json(
                        url, headers={"Authorization": "Bearer " + self._token_app(True)})
                except ValueError:
                    pass
            if self._usuario_conectado():
                return self._get(url)
            raise

    def catalogo(self, modo, termo="", pagina=""):
        if pagina:
            with self._lock:
                publica = getattr(self, "_pagina_publica", True)
                modo = getattr(self, "_contexto_modo", "busca") or "busca"
            get = self._get_publico if publica else self._get
            dados = get(pagina)
        elif modo == "playlists":
            with self._lock:
                self._pagina_publica = False
                self._contexto_modo = modo
            dados = self._get("me/playlists?limit=50")
        elif modo == "salvas":
            with self._lock:
                self._pagina_publica = False
                self._contexto_modo = modo
            dados = self._get("me/tracks?limit=50")
        elif modo == "playlist":
            if not re.fullmatch(r"[A-Za-z0-9]{22}", termo):
                raise ValueError("ID de playlist inválido: cole o link Spotify da playlist.")
            with self._lock:
                self._pagina_publica = True
                self._contexto_modo = modo
            dados = self._get_publico(f"playlists/{termo}/items?limit=50")
        elif modo == "album":
            if not re.fullmatch(r"[A-Za-z0-9]{22}", termo):
                raise ValueError("ID de álbum inválido: cole o link Spotify do álbum.")
            with self._lock:
                self._pagina_publica = True
                self._contexto_modo = modo
            album = self._get_publico(f"albums/{termo}")
            dados = album.get("tracks") or {}
            online.gravar_json(online.cache_path("spotify-albuns", termo),
                               {"name": album.get("name"), "images": album.get("images")})
        elif modo == "faixa":
            with self._lock:
                self._pagina_publica = True
                self._contexto_modo = modo
            dados = {"items": [self._get_publico("tracks/" + termo)]}
        else:
            if len(termo.strip()) < 2:
                raise ValueError("Digite um artista/faixa ou cole um link Spotify.")
            with self._lock:
                self._pagina_publica = True
                self._contexto_modo = modo
            try:
                dados = self._get_publico("search?" + urllib.parse.urlencode({"q": termo, "type": "track", "limit": 10}))
            except ValueError as e:
                msg = str(e)
                if "Client Secret" in msg or "conta Spotify" in msg:
                    raise ValueError(msg + " Configure em Provedores online "
                                     "(Client ID + Secret) ou conecte a conta.") from None
                raise
            dados = dados.get("tracks") or {}
        if modo == "album":
            album = online.ler_json(online.cache_path("spotify-albuns", termo), {})
            for track in dados.get("items", []):
                if isinstance(track, dict):
                    track["album"] = album
        if modo == "playlists":
            itens = [{"id": p["id"], "titulo": p.get("name") or "Playlist", "tipo": "playlist",
                      "url": "https://open.spotify.com/playlist/" + p["id"],
                      "capa_url": ((p.get("images") or [{}])[0] or {}).get("url") or ""}
                     for p in dados.get("items", []) if isinstance(p, dict) and p.get("id")]
        else:
            itens = [f for i in dados.get("items", []) if (f := normalizar_faixa(i)) and f["titulo"]]
        resultado = {"itens": itens, "next": dados.get("next") or "", "modo": modo, "cache": False}
        online.gravar_json(online.cache_path("spotify", repr((modo, termo, pagina))), resultado)
        return resultado

    def consultar(self, modo, termo="", pagina=""):
        try:
            resultado = self.catalogo(modo, termo, pagina)
            modo_efetivo = resultado.get("modo") or modo
        except ValueError as e:
            with self._lock:
                contexto = getattr(self, "_contexto_modo", modo) or modo
            chaves = [repr((modo, termo, pagina))]
            if pagina and contexto != modo:
                chaves.append(repr((contexto, termo, pagina)))
            cache = None
            for chave in chaves:
                cache = online.ler_json(online.cache_path("spotify", chave))
                if isinstance(cache, dict):
                    break
            if not isinstance(cache, dict):
                raise
            resultado = dict(cache, cache=True, aviso=str(e) + " Catálogo local preservado.")
            modo_efetivo = resultado.get("modo") or contexto
        if modo_efetivo != "playlists":
            caminho = base.DADOS_DIR / "spotify/faixas.json"
            faixas = online.ler_json(caminho, {})
            faixas = faixas if isinstance(faixas, dict) else {}
            faixas.update({f["uri"]: f for f in resultado["itens"]})
            online.gravar_json(caminho, faixas)
        return resultado

    def desconectar(self):
        self.fechar()
        self.token_path.unlink(missing_ok=True)

    def fechar(self):
        self._cancelar.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
