"""Descoberta portátil de sidecars: caminhos locais, manifesto e overrides."""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from functools import lru_cache

MANIFESTO_RUNTIME = "manifesto-runtime.json"
FERRAMENTAS = {
    "7z": ("BIBLIOTECA_7Z", "7zip", ("7z.exe", "7zz", "7z")),
    "ffmpeg": ("BIBLIOTECA_FFMPEG", "ffmpeg", ("ffmpeg.exe", "ffmpeg")),
    "ytdlp": ("BIBLIOTECA_YTDLP", "yt-dlp", ("yt-dlp.pyz", "yt-dlp.exe", "yt-dlp")),
    "qbittorrent": ("BIBLIOTECA_QBITTORRENT", "qbittorrent", ("qbittorrent.exe", "qbittorrent")),
    "deno": ("BIBLIOTECA_DENO", "deno", ("deno.exe", "deno")),
    "quickjs": ("BIBLIOTECA_QUICKJS", "quickjs", ("qjs.exe", "qjs")),
}


def raiz_runtime() -> Path:
    from bib_nucleo import base
    return base.HOME_DIR


def runtime_portatil() -> bool:
    raiz = raiz_runtime()
    return (raiz / MANIFESTO_RUNTIME).is_file() or (
        (raiz / "app/bib_core.py").is_file() and (raiz / "python/python.exe").is_file())


def pasta_ferramentas() -> Path:
    return raiz_runtime() / "ferramentas"


def manifesto_runtime() -> dict:
    try:
        arq = raiz_runtime() / MANIFESTO_RUNTIME
        st = arq.stat()
        if st.st_size > 5_000_000:
            return {}
        return _ler_manifesto(arq, st.st_mtime_ns, st.st_size)
    except (OSError, ValueError):
        return {}


@lru_cache(maxsize=8)
def _ler_manifesto(arq: Path, mtime_ns: int, tamanho: int) -> dict:
    d = json.loads(arq.read_text(encoding="utf-8"))
    return d if isinstance(d, dict) else {}


def _caminho_local(relativo: str) -> Path | None:
    """Manifesto editável, restrito à casa do Hub. BYOB absoluto usa env."""
    try:
        raiz = raiz_runtime().resolve()
        p = (raiz / relativo).resolve()
        return p if p != raiz and raiz in p.parents else None
    except (OSError, ValueError, TypeError):
        return None


def localizar_ferramenta(nome: str, legado: Path | None = None) -> str:
    env, sub, nomes = FERRAMENTAS[nome]
    explicito = (os.environ.get(env) or "").strip().strip('"')
    if explicito:
        p = Path(explicito)
        return str(p) if p.is_file() else ""
    componentes = manifesto_runtime().get("componentes", {})
    item = componentes.get(nome, {}) if isinstance(componentes, dict) else {}
    if isinstance(item, dict) and item.get("executavel"):
        if item.get("plataforma", sys.platform) != sys.platform and item.get("modo") != "python":
            return ""
        p = _caminho_local(item["executavel"])
        if p is not None and p.is_file():
            return str(p)
    locais = [pasta_ferramentas() / sub, pasta_ferramentas()]
    portatil = runtime_portatil()
    if not portatil and legado is not None:
        locais.append(Path(legado))
    for pasta in locais:
        for exe in nomes:
            if (os.name != "nt" or sys.platform == "darwin") and exe.endswith(".exe"):
                continue
            p = pasta / exe
            if p.is_file():
                return str(p)
    if portatil:
        return ""  # não mascarar falta de dependência usando o PC de build
    for exe in nomes:
        achado = shutil.which(exe)
        if achado:
            return achado
    if nome == "qbittorrent" and os.name == "nt":
        for env_dir in ("ProgramFiles", "ProgramFiles(x86)"):
            p = Path(os.environ.get(env_dir, "")) / "qBittorrent/qbittorrent.exe"
            if p.is_file():
                return str(p)
    return ""


def emulador_local_dir(nome: str) -> Path | None:
    p = raiz_runtime() / "emuladores" / nome
    return p if p.is_dir() or runtime_portatil() else None


def comando_externo(executavel: str) -> list[str]:
    """Zipapps reutilizam o Python local, sem outro interpretador empacotado."""
    if Path(executavel).suffix.lower() in (".pyz", ".py"):
        python = Path(sys.executable)
        if python.name.lower() == "pythonw.exe" and python.with_name("python.exe").is_file():
            python = python.with_name("python.exe")
        return [str(python), executavel]
    return [executavel]


def resumo_ferramentas() -> list[dict]:
    return [{"nome": nome, "executavel": localizar_ferramenta(nome),
             "incluido": bool(localizar_ferramenta(nome))} for nome in FERRAMENTAS]


__all__ = ["MANIFESTO_RUNTIME", "raiz_runtime", "runtime_portatil", "pasta_ferramentas",
           "manifesto_runtime", "localizar_ferramenta", "emulador_local_dir", "resumo_ferramentas",
           "comando_externo"]
