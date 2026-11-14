"""HTTP e configuração dos provedores; dados e credenciais ficam na casa local."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from bib_nucleo import base
from bib_nucleo.arquivos import gravar_atomico, gravar_json, ler_json
from bib_nucleo.versao import user_agent

USER_AGENT = user_agent()
_lock = threading.RLock()
_ENVS = {"steam_key": "BIBLIOTECA_STEAM_API_KEY",
         "steamgriddb_key": "BIBLIOTECA_STEAMGRIDDB_KEY",
         "spotify_client_id": "BIBLIOTECA_SPOTIFY_CLIENT_ID",
         "spotify_client_secret": "BIBLIOTECA_SPOTIFY_CLIENT_SECRET"}


def configurar_provedores(dados: dict):
    alvo = base.DADOS_DIR / "provedores-online.json"
    with _lock:
        config = ler_json(alvo, {})
        config = config if isinstance(config, dict) else {}
        for chave in _ENVS:
            valor = str(dados.get(chave) or "").strip()
            if valor:
                if len(valor) > 256 or any(c in valor for c in "\r\n\x00"):
                    raise ValueError("Configuração de provedor inválida.")
                config[chave] = valor
        gravar_json(alvo, config, backup=True)
    return estado_provedores()


def chave_provedor(chave: str) -> str:
    config = ler_json(base.DADOS_DIR / "provedores-online.json", {})
    return str(os.environ.get(_ENVS.get(chave, "")) or
               (config.get(chave) if isinstance(config, dict) else "") or "").strip()


def estado_provedores() -> dict:
    return {chave: bool(chave_provedor(chave)) for chave in _ENVS}


# Formato usual de cada credencial (para aviso de conferência, não para validar).
_FORMATO = {"steam_key": 32, "steamgriddb_key": 32,
            "spotify_client_id": 32, "spotify_client_secret": 32}


def dicas_provedores() -> dict:
    """Avisos de conferência por credencial, **sem expor nenhum valor**.

    Não valida a chave contra o provedor: apenas compara o tamanho com o
    formato usual e orienta o usuário a regrará-la em "Provedores online".
    Uma chave pode ter tamanho diferente e ainda assim ser válida; por isso
    o texto é de conferência, nunca de reprovação.
    """
    saida = {}
    for chave in _ENVS:
        valor = chave_provedor(chave)
        if not valor:
            saida[chave] = {"configurada": False, "tamanho": 0, "aviso": ""}
            continue
        esperado = _FORMATO[chave]
        divergente = len(valor) != esperado
        saida[chave] = {
            "configurada": True,
            "tamanho": len(valor),
            "aviso": (f"Confira esta credencial: tem {len(valor)} caracteres e o "
                      f"formato usual de {esperado}. Gere uma nova em "
                      f"'Provedores online'.") if divergente else "",
        }
    return saida


def url_https(url: str) -> bool:
    try:
        p = urllib.parse.urlsplit(url)
        return p.scheme == "https" and bool(p.hostname) and not p.username and not p.password
    except (ValueError, TypeError):
        return False


def requisitar_json(url, *, headers=None, dados=None, timeout=15, limite=4_000_000):
    from bib_nucleo.rede import exigir_rede
    exigir_rede("Consultar provedor")
    if not url_https(url):
        raise ValueError("Endereço do provedor inválido.")
    h = {"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=dados, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(limite + 1)
        if len(raw) > limite:
            raise ValueError("Resposta do provedor grande demais.")
        return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise ValueError(f"Provedor indisponível (HTTP {e.code}).") from None
    except (urllib.error.URLError, OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("Provedor indisponível ou resposta inválida.") from None


def baixar_texto(url: str, timeout=20, limite=2_000_000) -> str:
    """HTML/texto público de provedor (ex.: Comunidade Steam). Sem login/chave."""
    from bib_nucleo.rede import exigir_rede
    exigir_rede("Consultar provedor")
    if not url_https(url):
        raise ValueError("Endereço do provedor inválido.")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(limite + 1)
    except urllib.error.HTTPError as e:
        raise ValueError(f"Provedor indisponível (HTTP {e.code}).") from None
    except (urllib.error.URLError, OSError):
        raise ValueError("Provedor indisponível ou resposta inválida.") from None
    if len(raw) > limite:
        raise ValueError("Resposta do provedor grande demais.")
    for cod in ("utf-8", "latin-1"):
        try:
            return raw.decode(cod)
        except UnicodeError:
            continue
    raise ValueError("Resposta do provedor inválida.")


def cache_path(categoria: str, chave: str, ext=".json") -> Path:
    digest = hashlib.sha256(chave.encode("utf-8")).hexdigest()
    return base.DADOS_DIR / "cache-provedores" / categoria / (digest + ext)


def baixar_imagem(url: str, timeout=15) -> tuple[bytes, str, str]:
    if not url_https(url):
        raise ValueError("Endereço de imagem inválido.")
    alvo = cache_path("imagens", url, ".img")
    if alvo.is_file():
        raw = alvo.read_bytes()
    else:
        from bib_nucleo.rede import exigir_rede
        exigir_rede("Baixar imagem")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read(2_000_001)
        except (urllib.error.URLError, OSError):
            raise ValueError("Não foi possível baixar a imagem deste provedor.") from None
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        ext = ".png"
    elif raw.startswith(b"\xff\xd8\xff"):
        ext = ".jpg"
    elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        ext = ".webp"
    elif raw[:6] in (b"GIF87a", b"GIF89a"):
        ext = ".gif"
    else:
        raise ValueError("O provedor retornou conteúdo que não é uma imagem suportada.")
    if len(raw) > 2_000_000 or len(raw) < 32:
        raise ValueError("Imagem vazia ou maior que 2 MB.")
    if not alvo.is_file():
        gravar_atomico(alvo, raw)
    return raw, ext, str(alvo)
