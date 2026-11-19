"""qBittorrent como sidecar local: perfil da coleção e Web API em loopback."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from bib_nucleo.arquivos import gravar_atomico
from bib_nucleo.ferramentas import localizar_ferramenta


def perfil_qbit() -> Path:
    from bib_nucleo.base import DADOS_DIR
    return Path(os.environ.get("BIBLIOTECA_QBIT_PROFILE") or DADOS_DIR / "perfis")


def qbit_config_path() -> Path:
    ext = ".ini" if os.name == "nt" or sys.platform == "darwin" else ".conf"
    return perfil_qbit() / "qBittorrent_tucoteca/config" / ("qBittorrent" + ext)


def qbit_backup_local() -> Path:
    return perfil_qbit() / "qBittorrent_tucoteca/data/BT_backup"


def qbit_porta() -> int:
    h = hashlib.sha256(str(perfil_qbit().resolve()).encode("utf-8")).hexdigest()
    return 18000 + int(h[:4], 16) % 20000


def qbit_api_url() -> str:
    env = (os.environ.get("BIBLIOTECA_QBIT_API") or "").rstrip("/")
    if env:
        u = urllib.parse.urlsplit(env)
        if u.scheme not in ("http", "https") or u.hostname not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("A API do qBittorrent deve usar loopback local")
        return env
    if qbit_config_path().is_file():
        return f"http://127.0.0.1:{qbit_porta()}"
    return ""


def qbit_request(endpoint: str, dados: dict | None = None, timeout=1.0):
    base = qbit_api_url()
    if not base:
        raise ValueError("qBittorrent integrado ainda não iniciado")
    req = urllib.request.Request(base + "/api/v2/" + endpoint,
                                data=urllib.parse.urlencode(dados).encode() if dados is not None else None,
                                headers={"Origin": base, "Referer": base + "/"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as r:
        raw = r.read(8_000_000)
    return raw.decode("utf-8", "replace")


def _perfil_texto(destino: Path) -> str:
    salt = os.urandom(16)
    # O GUI exige hash não vazio mesmo com autenticação local dispensada.
    key = hashlib.pbkdf2_hmac("sha512", os.urandom(32), salt, 100000)
    credencial = base64.b64encode(salt).decode() + ":" + base64.b64encode(key).decode()
    return ("[Meta]\nMigrationVersion=8\n[LegalNotice]\nAccepted=true\n\n"
            "[GUI]\nStartUpWindowState=Hidden\n\n"
            "[Preferences]\nWebUI\\Enabled=true\nWebUI\\Address=127.0.0.1\n"
            f"WebUI\\Port={qbit_porta()}\nWebUI\\LocalHostAuth=false\n"
            f"WebUI\\Password_PBKDF2=@ByteArray({credencial})\n"
            "WebUI\\CSRFProtection=true\nWebUI\\HostHeaderValidation=true\n"
            "WebUI\\ServerDomains=127.0.0.1\nAdvanced\\updateCheck=false\n\n"
            "[BitTorrent]\nSession\\DefaultSavePath=" + destino.as_posix() + "\n\n"
            "[AddNewTorrentDialog]\nEnabled=false\n")


def migrar_save_path(texto: str, destino: Path) -> str:
    """Garante DefaultSavePath=Meus Jogos Locais em perfil existente, sem tocar no resto."""
    alvo = "Session\\DefaultSavePath=" + destino.as_posix()
    linhas = texto.splitlines()
    for i, linha in enumerate(linhas):
        if linha.startswith("Session\\DefaultSavePath="):
            linhas[i] = alvo
            return "\n".join(linhas) + ("\n" if texto.endswith("\n") else "")
    for i, linha in enumerate(linhas):
        if linha.strip() == "[BitTorrent]":
            linhas.insert(i + 1, alvo)
            return "\n".join(linhas) + ("\n" if texto.endswith("\n") else "")
    return texto + ("\n" if not texto.endswith("\n") else "") + "[BitTorrent]\n" + alvo + "\n"


def qbit_preparar_perfil() -> Path:
    """Cria o perfil do Hub ou migra o existente (destino sempre Meus Jogos Locais/)."""
    from bib_nucleo.rede.repacks import pasta_jogos
    destino = pasta_jogos().resolve()
    cfg = qbit_config_path()
    destino.mkdir(parents=True, exist_ok=True)
    cfg.parent.mkdir(parents=True, exist_ok=True)
    if not cfg.exists():
        gravar_atomico(cfg, _perfil_texto(destino).encode("utf-8"))
    else:
        try:
            atual = cfg.read_text(encoding="utf-8")
        except OSError:
            return cfg
        novo = migrar_save_path(atual, destino)
        if novo != atual:
            gravar_atomico(cfg.with_suffix(cfg.suffix + ".bak"), atual.encode("utf-8"))
            gravar_atomico(cfg, novo.encode("utf-8"))
    return cfg


def qbit_iniciar(url: str = "") -> dict:
    """Inicia/encaminha ao perfil do Hub; não modifica o perfil do sistema."""
    exe = localizar_ferramenta("qbittorrent")
    if not exe:
        return {"ok": False, "erro": "qBittorrent não encontrado no pacote"}
    from bib_nucleo.rede.repacks import pasta_jogos
    destino = pasta_jogos().resolve()
    try:
        qbit_preparar_perfil()
        cmd = [exe, "--profile=" + str(perfil_qbit().resolve()), "--configuration=tucoteca",
               "--relative-fastresume", "--no-splash", "--confirm-legal-notice",
               "--webui-port=" + str(qbit_porta()), "--save-path=" + str(destino),
               "--skip-dialog=true", "--add-stopped=false", "--category=tucoteca"]
        if url:
            if not url.startswith("magnet:?") and not (Path(url).is_file() and Path(url).suffix == ".torrent"):
                return {"ok": False, "erro": "torrent/magnet inválido"}
            cmd.append(url)
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"ok": True, "pid": proc.pid, "api": f"http://127.0.0.1:{qbit_porta()}",
                "destino": str(destino)}
    except (OSError, ValueError) as e:
        return {"ok": False, "erro": f"qBittorrent: {e}"}


def qbit_listar() -> dict:
    try:
        if not qbit_api_url():
            return {"ok": False, "torrents": [], "erro": "API não configurada"}
        dados = json.loads(qbit_request("torrents/info"))
        if not isinstance(dados, list):
            raise ValueError("resposta da API inválida")
        torrents = []
        finais = {"uploading", "stalledUP", "forcedUP", "queuedUP", "pausedUP", "stoppedUP"}
        for d in dados:
            if not isinstance(d, dict):
                continue
            total = max(0, int(d.get("size") or d.get("total_size") or 0))
            progress = max(0.0, min(1.0, float(d.get("progress") or 0)))
            nome = str(d.get("name") or "")
            estado = str(d.get("state") or "")
            caminho = str(d.get("content_path") or Path(d.get("save_path") or "") / nome)
            torrents.append({"hash": str(d.get("hash") or ""), "nome": nome,
                             "total": total, "feito": int(total * progress), "pct": round(progress * 100, 1),
                             "completo": progress == 1 and estado in finais,
                             "fonte_progresso": "api", "save_path": caminho, "estado": estado,
                             "velocidade": int(d.get("dlspeed") or 0), "eta": int(d.get("eta") or 0)})
        return {"ok": True, "torrents": torrents}
    except Exception as e:
        return {"ok": False, "torrents": [], "erro": str(e)}


def qbit_controlar(hash_torrent: str, acao: str) -> dict:
    """pausar/retomar, ou remover da lista do cliente (os arquivos baixados ficam)."""
    endpoints = {"pausar": "torrents/stop", "retomar": "torrents/start", "remover": "torrents/delete"}
    if acao not in endpoints or not hash_torrent or any(c not in "0123456789abcdefABCDEF" for c in hash_torrent):
        return {"ok": False, "erro": "ação/hash inválido"}
    dados = {"hashes": hash_torrent}
    if acao == "remover":
        dados["deleteFiles"] = "false"
    try:
        qbit_request(endpoints[acao], dados)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "erro": str(e)}


__all__ = ["perfil_qbit", "qbit_config_path", "qbit_backup_local", "qbit_porta",
           "qbit_api_url", "qbit_iniciar", "qbit_listar", "qbit_controlar", "qbit_preparar_perfil", "migrar_save_path"]
