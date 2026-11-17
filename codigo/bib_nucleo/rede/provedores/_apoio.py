"""Cache com validade, limite de ritmo por host e HTML → texto, para os provedores."""
from __future__ import annotations

import html
import re
import threading
import time
import unicodedata
from html.parser import HTMLParser

from bib_nucleo.arquivos import gravar_json, ler_json
from bib_nucleo.rede import online

# ---------------------------------------------------------------- cache


def obter(categoria: str, chave: str, validade_s: float, buscar):
    """Resposta em cache se ainda vale; senão `buscar()` e grava. Se a busca
    falhar e houver cache vencido, usa o vencido (melhor que nada)."""
    alvo = online.cache_path(categoria, chave)
    salvo = ler_json(alvo, None)
    if isinstance(salvo, dict) and "dados" in salvo:
        if time.time() - float(salvo.get("em") or 0) < validade_s:
            return salvo["dados"]
    try:
        dados = buscar()
    except ValueError:
        if isinstance(salvo, dict) and "dados" in salvo:
            return salvo["dados"]
        raise
    gravar_json(alvo, {"em": time.time(), "dados": dados})
    return dados


# ---------------------------------------------------------------- ritmo

_ritmo_lock = threading.Lock()
_ultimo: dict[str, float] = {}


def respeitar_ritmo(host: str, intervalo_s: float) -> None:
    """Espera o necessário para não chamar o mesmo host mais rápido que `intervalo_s`."""
    with _ritmo_lock:
        agora = time.monotonic()
        espera = _ultimo.get(host, 0.0) + intervalo_s - agora
        if espera > 0:
            time.sleep(espera)
        _ultimo[host] = time.monotonic()


# ---------------------------------------------------------------- texto

_BLOCOS = {"p", "br", "li", "div", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol"}


class _Texto(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes: list[str] = []
        self._ignorar = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._ignorar += 1
        elif tag in _BLOCOS:
            self.partes.append("\n")
        if tag == "li":
            self.partes.append("• ")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._ignorar:
            self._ignorar -= 1
        elif tag in _BLOCOS:
            self.partes.append("\n")

    def handle_data(self, data):
        if not self._ignorar:
            self.partes.append(data)


def html_para_texto(bruto: str, limite: int = 4000) -> str:
    """HTML de loja → texto simples com parágrafos (nada de marcação chega ao renderer)."""
    leitor = _Texto()
    try:
        leitor.feed(str(bruto or ""))
        leitor.close()
    except Exception:
        return ""
    texto = html.unescape("".join(leitor.partes))
    linhas = [re.sub(r"[ \t ]+", " ", linha).strip() for linha in texto.splitlines()]
    texto = re.sub(r"\n{3,}", "\n\n", "\n".join(linhas)).strip()
    if len(texto) > limite:
        texto = texto[:limite].rsplit(" ", 1)[0] + "…"
    return texto


def normalizar_titulo(titulo: str) -> str:
    """Para casar nomes entre catálogos: minúsculas, sem pontuação/artigos de edição."""
    t = unicodedata.normalize("NFD", str(titulo or "").casefold())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"\(.*?\)|\[.*?\]", " ", t)
    t = re.sub(r"[™®©:'’\-–—_.,!?&]", " ", t)
    t = re.sub(r"\b(the|edition|remastered|definitive|goty)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


__all__ = ["obter", "respeitar_ritmo", "html_para_texto", "normalizar_titulo"]
