"""API de leitura opt-in em 127.0.0.1, protegida por token e sem CORS."""
from __future__ import annotations

import hmac
import json
import secrets
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def autorizado(headers, token, porta):
    host = headers.get("Host", "")
    origem = headers.get("Origin", "")
    if host not in (f"127.0.0.1:{porta}", f"localhost:{porta}"):
        return False  # evita DNS rebinding
    if origem and origem not in (f"http://127.0.0.1:{porta}", f"http://localhost:{porta}"):
        return False
    auth = headers.get("Authorization", "")
    return hmac.compare_digest(auth.encode(), ("Bearer " + token).encode())


def consultar(servico, caminho):
    if caminho not in ("/status", "/jogos", "/musicas", "/desejos"):
        return 404, {"erro": "rota não encontrada"}
    dados = servico.snapshot()
    return 200, dados["sistema"] if caminho == "/status" else dados[caminho[1:]]


class ApiLocal:
    def __init__(self, servico, porta=0, token=""):
        self.servico = servico
        self.token = token or secrets.token_urlsafe(32)
        if len(self.token) < 32:
            raise ValueError("Token precisa de pelo menos 32 caracteres.")
        self.servidor = self.thread = None
        self.porta = int(porta)

    def iniciar(self):
        if self.servidor:
            return self.estado()
        dono = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                self.request.settimeout(3)
                super().setup()

            def log_message(self, *args):
                pass  # não registra token/URLs pessoais

            def responder(self, status, dados):
                raw = json.dumps(dados, ensure_ascii=False).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                if not autorizado(self.headers, dono.token, dono.porta):
                    self.responder(401, {"erro": "não autorizado"})
                    return
                if len(self.path) > 2000:
                    self.responder(414, {"erro": "URL grande demais"})
                    return
                try:
                    status, dados = consultar(dono.servico, urllib.parse.urlsplit(self.path).path)
                    self.responder(status, dados)
                except Exception:
                    self.responder(500, {"erro": "coleção indisponível"})

        self.servidor = ThreadingHTTPServer(("127.0.0.1", self.porta), Handler)
        self.servidor.daemon_threads = True
        self.porta = self.servidor.server_port
        self.thread = threading.Thread(target=self.servidor.serve_forever, daemon=True,
                                       name="tucoteca-api-local")
        self.thread.start()
        return self.estado()

    def estado(self):
        return {"ativa": bool(self.servidor), "url": f"http://127.0.0.1:{self.porta}",
                "token": self.token if self.servidor else ""}

    def fechar(self):
        if self.servidor:
            self.servidor.shutdown()
            self.servidor.server_close()
            self.thread.join(timeout=5)
            self.servidor = self.thread = None
