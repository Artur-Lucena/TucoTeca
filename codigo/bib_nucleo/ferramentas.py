"""Descoberta de executáveis externos, sem iniciar processos ou acessar a rede.

Override explícito → manifesto → ferramentas locais → sistema (no checkout).
Um pacote portátil não usa dependências do PC para esconder componentes ausentes.
No Linux/macOS, executáveis nativos precisam de permissão X; zipapps Python
usam o interpretador do Hub e não precisam de chmod. Ferramentas exclusivas do
Windows não são consideradas nativas nos outros sistemas.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path

MANIFESTO_RUNTIME = "manifesto-runtime.json"
FERRAMENTAS = {
    "7z": ("BIBLIOTECA_7Z", "7zip", ("7z.exe", "7zz", "7z")),
    "ffmpeg": ("BIBLIOTECA_FFMPEG", "ffmpeg", ("ffmpeg.exe", "ffmpeg")),
    "ytdlp": ("BIBLIOTECA_YTDLP", "yt-dlp", ("yt-dlp.pyz", "yt-dlp.exe", "yt-dlp")),
    "qbittorrent": ("BIBLIOTECA_QBITTORRENT", "qbittorrent", ("qbittorrent.exe", "qbittorrent")),
    "deno": ("BIBLIOTECA_DENO", "deno", ("deno.exe", "deno")),
    "quickjs": ("BIBLIOTECA_QUICKJS", "quickjs", ("qjs.exe", "qjs")),
    # 2.0 — edição de imagem open source (BYOB, mesmo molde 7z/emuladores).
    "krita": ("BIBLIOTECA_KRITA", "krita", ("krita.exe", "krita")),
    "gimp": ("BIBLIOTECA_GIMP", "gimp", ("gimp.exe", "gimp", "gimp-2.10.exe")),
    "photodemon": ("BIBLIOTECA_PHOTODEMON", "photodemon", ("PhotoDemon.exe", "photodemon")),
    # 2.0 — áudio: editor + EQ de sistema + GUI de presets.
    "audacity": ("BIBLIOTECA_AUDACITY", "audacity", ("audacity.exe", "tenacity.exe", "audacity", "tenacity")),
    "equalizerapo": ("BIBLIOTECA_EQUALIZERAPO", "equalizerapo", ("Configurator.exe", "Editor.exe")),
    "peace": ("BIBLIOTECA_PEACE", "peace", ("Peace.exe", "peace")),
    # 2.0 — vídeo: 3 reprodutores open source + YouTube via yt-dlp/ffmpeg.
    "vlc": ("BIBLIOTECA_VLC", "vlc", ("vlc.exe", "vlc")),
    "mpv": ("BIBLIOTECA_MPV", "mpv", ("mpv.exe", "mpv")),
    "mpchc": ("BIBLIOTECA_MPCHC", "mpchc", ("mpc-hc64.exe", "mpc-hc.exe", "mpc-hc")),
}

_SOMENTE_WINDOWS = {"photodemon", "equalizerapo", "peace", "mpchc"}
_PADROES_WINDOWS = {
    "qbittorrent": ("qBittorrent/qbittorrent.exe",),
    "krita": ("Krita (x64)/bin/krita.exe", "Krita/bin/krita.exe"),
    "gimp": ("GIMP 3/bin/gimp-3.0.exe", "GIMP 3/bin/gimp.exe",
             "GIMP 2/bin/gimp-2.10.exe", "GIMP 2/bin/gimp.exe"),
    "photodemon": ("PhotoDemon/PhotoDemon.exe",),
    "audacity": ("Audacity/Audacity.exe", "Tenacity/tenacity.exe"),
    "equalizerapo": ("EqualizerAPO/Editor.exe", "EqualizerAPO/Configurator.exe"),
    "peace": ("EqualizerAPO/config/Peace.exe",),
    "vlc": ("VideoLAN/VLC/vlc.exe",),
    "mpchc": ("MPC-HC/mpc-hc64.exe", "MPC-HC/mpc-hc.exe"),
}
_APPS_MAC = {
    "krita": ("krita.app/Contents/MacOS/krita",),
    "gimp": ("GIMP.app/Contents/MacOS/gimp", "GIMP.app/Contents/MacOS/gimp-3.0"),
    "audacity": ("Audacity.app/Contents/MacOS/Audacity",
                 "Tenacity.app/Contents/MacOS/tenacity"),
    "vlc": ("VLC.app/Contents/MacOS/VLC",),
    "mpv": ("mpv.app/Contents/MacOS/mpv",),
}


def _plataforma_atual() -> str:
    # sys.platform é simulável sem alterar os.name global e a classe de Path.
    if sys.platform == "darwin":
        return "darwin"
    if sys.platform.startswith("linux"):
        return "linux"
    return "win32" if os.name == "nt" else sys.platform


def ferramenta_suportada(nome: str) -> bool:
    """Compatibilidade nativa; não presume Wine para ferramentas de mídia."""
    return nome not in _SOMENTE_WINDOWS or _plataforma_atual() == "win32"


def _executavel_valido(caminho) -> bool:
    try:
        p = Path(caminho)
        if not p.is_file():
            return False
        if p.suffix.lower() in (".py", ".pyz"):
            return True
        if _plataforma_atual() != "win32":
            return p.suffix.lower() not in (".exe", ".bat", ".cmd", ".lnk") and os.access(p, os.X_OK)
        return True
    except (OSError, ValueError, TypeError):
        return False


def raiz_runtime() -> Path:
    from bib_nucleo import base
    return base.HOME_DIR


def runtime_portatil() -> bool:
    raiz = raiz_runtime()
    return (raiz / MANIFESTO_RUNTIME).is_file() or (
        (raiz / "app/bib_nucleo/__init__.py").is_file() and (raiz / "python/python.exe").is_file())


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
    """Localiza um executável utilizável neste SO. Override inválido não faz fallback."""
    env, sub, nomes = FERRAMENTAS[nome]
    if not ferramenta_suportada(nome):
        return ""
    explicito = (os.environ.get(env) or "").strip().strip('"')
    if explicito:
        p = Path(explicito)
        return str(p) if _executavel_valido(p) else ""
    componentes = manifesto_runtime().get("componentes", {})
    item = componentes.get(nome, {}) if isinstance(componentes, dict) else {}
    if isinstance(item, dict) and item.get("executavel"):
        if item.get("plataforma", _plataforma_atual()) != _plataforma_atual() and item.get("modo") != "python":
            return ""
        p = _caminho_local(item["executavel"])
        if p is not None and _executavel_valido(p):
            return str(p)
    locais = [pasta_ferramentas() / sub, pasta_ferramentas()]
    portatil = runtime_portatil()
    if not portatil and legado is not None:
        locais.append(Path(legado))
    for pasta in locais:
        for exe in nomes:
            if _plataforma_atual() != "win32" and exe.lower().endswith(".exe"):
                continue
            p = pasta / exe
            if _executavel_valido(p):
                return str(p)
    if portatil:
        return ""  # não mascarar falta de dependência usando o PC de build
    for exe in nomes:
        if _plataforma_atual() != "win32" and exe.lower().endswith(".exe"):
            continue
        achado = shutil.which(exe)
        if achado and _executavel_valido(achado):
            return achado
    if _plataforma_atual() == "win32":
        for env_dir in ("ProgramFiles", "ProgramFiles(x86)"):
            raiz = os.environ.get(env_dir)
            if not raiz:
                continue
            for relativo in _PADROES_WINDOWS.get(nome, ()):
                p = Path(raiz) / relativo
                if _executavel_valido(p):
                    return str(p)
    elif _plataforma_atual() == "darwin":
        for raiz in (Path("/Applications"), Path.home() / "Applications"):
            for relativo in _APPS_MAC.get(nome, ()):
                p = raiz / relativo
                if _executavel_valido(p):
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


__all__ = ["MANIFESTO_RUNTIME", "raiz_runtime", "runtime_portatil", "pasta_ferramentas",
           "manifesto_runtime", "localizar_ferramenta", "emulador_local_dir",
            "comando_externo", "ferramenta_suportada"]
