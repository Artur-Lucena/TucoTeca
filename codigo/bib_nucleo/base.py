#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caminhos canônicos, tradução Win<->Linux<->Mac, dirs, texto e tempo."""
from __future__ import annotations

import datetime
import json
import os
import re
import socket
import sys
import time
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


# --------------------------------------------------------------------------
# Casa canônica + tradução determinística de caminhos (Win <-> Linux)
# --------------------------------------------------------------------------

WIN_ROOT = os.environ.get("BIBLIOTECA_WIN_ROOT", "D:\\")

LINUX_ROOT = os.environ.get("BIBLIOTECA_LINUX_ROOT", "/run/media/tuco/Games")

MAC_ROOT = os.environ.get("BIBLIOTECA_MAC_ROOT", "/Volumes/Games")


def eh_mac() -> bool:
    """True no macOS (Intel ou Apple Silicon), independente de os.name."""
    return sys.platform == "darwin"

REL_HOME = Path("Tuco-Compartilhado") / "Jogos" / "biblioteca"


def resolve_home() -> Path:
    env = os.environ.get("BIBLIOTECA_HOME")
    if env:
        return Path(env)
    # Um pacote real sempre vence a instalação canônica do PC de build.
    if (BASE_DIR / "manifesto-runtime.json").is_file() or (
            (BASE_DIR / "app/bib_core.py").is_file() and (BASE_DIR / "python/python.exe").is_file()):
        return BASE_DIR
    # Pasta única do projeto: coleção dentro da própria árvore de fontes
    # (dev/uso no repo) vence a instalação canônica de build.
    if (BASE_DIR / "dados").is_dir():
        return BASE_DIR
    if os.name == "nt":
        cand = Path(WIN_ROOT) / REL_HOME
        if cand.is_dir():
            return cand
    elif eh_mac():
        for raiz in (MAC_ROOT, LINUX_ROOT):
            cand = Path(raiz) / REL_HOME
            if cand.is_dir():
                return cand
    else:
        cand = Path(LINUX_ROOT) / REL_HOME
        if cand.is_dir():
            return cand
    return BASE_DIR


HOME_DIR = resolve_home()

DADOS_DIR = HOME_DIR / "dados"

DEFAULT_DB = DADOS_DIR / "biblioteca.db"

BACKUP_DIR = DADOS_DIR / "backups"

CAPAS_DIR = DADOS_DIR / "capas"

PRESETS_DIR = DADOS_DIR / "presets"

SESSOES_DIR = DADOS_DIR / "sessoes"

# Pasta-mãe de saves do HUB: todo jogo aberto pelo app grava aqui dentro.
# PC (Wine): prefixo único do HUB; emuladores: dirs compartilhados na partilha.
SAVES_DIR = DADOS_DIR / "saves"

WINE_PREFIXO = SAVES_DIR / "wine"

# Biblioteca de mods por provider: mods/<prov>/<title-id>/<mod>/ (LayeredFS
# extraído e normalizado). O play copia o overlay ativo para o emulador;
# arquivos que não pertencem ao Hub são preservados.
MODS_DIR = DADOS_DIR / "mods"

# Catálogo de áudio independente dos jogos; arquivos importados por conteúdo.
# Fora do git e do scanner; áudio final viaja no pacote de coleção.
MUSICAS_DIR = DADOS_DIR / "musicas"

# Rascunhos brutos da fila CSV → mp3 (Fase B baixa aqui; Fase C importa
# p/ `musicas/`). Fora do git, do scanner (SKIP) e dos pacotes.
BAIXAR_DIR = DADOS_DIR / "baixados"

# WAVs decodificados p/ o player interno (MCI-waveaudio; mp3/m4a via
# ffmpeg em cache com teto LRU). Fora do git, do scanner e dos pacotes.
CACHE_WAV_DIR = DADOS_DIR / "cache-wav"

# Texturas HD por jogo (Azahar custom textures): texturas/<title-id>/ com PNGs.
# Toggle por rename (<tid> ativo, <tid>.off desligado — sem privilégio, sem
# cópia, vale nos 3 SOs). Fora do git, do scanner e dos instaladores
# (GBs — mesmo trato dos mods: pacote portátil não inclui).
TEXTURAS_DIR = DADOS_DIR / "texturas"

# Videoteca local da 2.0: filmes/vídeos pesquisados e baixados do YouTube
# (yt-dlp BYOB) + arquivos locais importados. Fora do git e do scanner de
# jogos (SKIP). O pacote de coleção v4 ainda não transporta vídeos.
VIDEOS_DIR = DADOS_DIR / "videos"


def garantir_dirs() -> None:
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    DADOS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    CAPAS_DIR.mkdir(parents=True, exist_ok=True)
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    SESSOES_DIR.mkdir(parents=True, exist_ok=True)
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
    MODS_DIR.mkdir(parents=True, exist_ok=True)
    MUSICAS_DIR.mkdir(parents=True, exist_ok=True)
    BAIXAR_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_WAV_DIR.mkdir(parents=True, exist_ok=True)
    TEXTURAS_DIR.mkdir(parents=True, exist_ok=True)
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)


def _com_barra(p: str) -> str:
    return p.replace("\\", "/")


def _trocar_prefixo(p: str, origem: str, destino: str, para_win: bool = False) -> str:
    """Troca o prefixo origem pelo destino (sem caixa). Fora da origem, devolve igual.

    Compacta os 6 win/linux/mac_para_* sem mudar comportamento: ida sempre
    com barra (/), volta p/ Win com contrabarra (\\).
    """
    n = _com_barra(p)
    ori = _com_barra(origem).rstrip("/") + "/"
    if n[: len(ori)].lower() != ori.lower():
        return p
    resto = n[len(ori):]
    if para_win:
        return destino.rstrip("\\") + "\\" + resto.replace("/", "\\")
    return _com_barra(destino).rstrip("/") + "/" + resto


def win_para_linux(p: str) -> str:
    """D:\\Games\\X -> /run/media/tuco/Games/Games/X. Fora de D:\\, devolve igual."""
    return _trocar_prefixo(p, WIN_ROOT, LINUX_ROOT)


def linux_para_win(p: str) -> str:
    return _trocar_prefixo(p, LINUX_ROOT, WIN_ROOT, para_win=True)


def win_para_mac(p: str) -> str:
    """D:\\Games\\X -> /Volumes/Games/Games/X. Fora de D:\\, devolve igual."""
    return _trocar_prefixo(p, WIN_ROOT, MAC_ROOT)


def mac_para_win(p: str) -> str:
    return _trocar_prefixo(p, MAC_ROOT, WIN_ROOT, para_win=True)


def linux_para_mac(p: str) -> str:
    """Troca o prefixo do mount Linux pelo do Mac; fora dele, devolve igual."""
    return _trocar_prefixo(p, LINUX_ROOT, MAC_ROOT)


def mac_para_linux(p: str) -> str:
    return _trocar_prefixo(p, MAC_ROOT, LINUX_ROOT)


def _sob(p: str, raiz: str) -> bool:
    """p está dentro de raiz? (compara com barra, sem caixa)."""
    n = _com_barra(p).lower()
    r = _com_barra(raiz).rstrip("/") + "/"
    return n.startswith(r.lower())


# Sufixos que o Windows executa de verdade (fallback de outro SO com
# outra extensão — ex.: .AppImage — existe no disco mas nunca abre aqui).
_WIN_EXEC = (".exe", ".bat", ".cmd", ".lnk", ".com")


def traduzir_para_atual(p: str) -> str:
    """Converte um caminho gravado para o equivalente neste SO (ou igual)."""
    if not p:
        return p
    if os.name == "nt":
        if _sob(p, MAC_ROOT):
            return mac_para_win(p)
        return linux_para_win(p)
    if eh_mac():
        t = win_para_mac(p)
        if t != p:
            return t
        return linux_para_mac(p)
    if _sob(p, MAC_ROOT):
        return mac_para_linux(p)
    return win_para_linux(p)


def existe_aqui_ou_traduzido(p: str) -> tuple[bool, str]:
    """(existe, caminho_que_existe_ou_traduzido). Para exibir e executar."""
    if not p:
        return False, ""
    if Path(p).exists():
        return True, p
    t = traduzir_para_atual(p)
    if t != p and Path(t).exists():
        return True, t
    return False, t


def resolver_exe(d: dict) -> tuple[str, str]:
    """(executável final neste SO, origem). exe_win/exe_linux/exe_mac vencem o legado.

    O campo do outro SO só vale como fallback se existir aqui ou traduzido;
    senão o legado (mesmo vazio) prevalece para o provider completar.
    No Mac, exe_mac vence; .exe/.AppImage de Win/Linux nunca executam lá.
    """
    if os.name == "nt":
        esp = (d.get("exe_win") or "").strip()
        if esp:
            return esp, "exe_win"
        legado = traduzir_para_atual((d.get("executable_path") or "").strip())
        if legado and existe_aqui_ou_traduzido(legado)[0]:
            return legado, "executavel"
        for campo in ("exe_linux", "exe_mac"):
            alt = traduzir_para_atual((d.get(campo) or "").strip())
            if alt and Path(alt).suffix.lower() in _WIN_EXEC and existe_aqui_ou_traduzido(alt)[0]:
                return alt, campo
        return legado, "executavel"
    if eh_mac():
        esp = (d.get("exe_mac") or "").strip()
        if esp:
            return esp, "exe_mac"
        legado = traduzir_para_atual((d.get("executable_path") or "").strip())
        if legado:
            return legado, "executavel"
        for campo in ("exe_linux", "exe_win"):
            alt = traduzir_para_atual((d.get(campo) or "").strip())
            if alt and existe_aqui_ou_traduzido(alt)[0]:
                return alt, campo
        return "", "executavel"
    esp = (d.get("exe_linux") or "").strip()
    if esp:
        return esp, "exe_linux"
    legado = traduzir_para_atual((d.get("executable_path") or "").strip())
    if legado:
        return legado, "executavel"
    for campo in ("exe_win", "exe_mac"):
        alt = traduzir_para_atual((d.get(campo) or "").strip())
        if alt and existe_aqui_ou_traduzido(alt)[0]:
            return alt, campo
    return "", "executavel"


def agora_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def log_erro(contexto: str, detalhe: str) -> None:
    """Anexa uma linha em dados/erros.log. Nunca levanta; diagnóstico local.

    Usa DADOS_DIR (patchável em testes). Em produção é HOME/dados;
    na suíte, isolar() fixa BIBLIOTECA_HOME antes do import, então
    DADOS_DIR já aponta p/ sandbox e nada vaza p/ instalação real.
    """
    try:
        DADOS_DIR.mkdir(parents=True, exist_ok=True)
        with open(DADOS_DIR / "erros.log", "a", encoding="utf-8") as fh:
            fh.write(f"{agora_iso()} [{contexto}] {detalhe}\n")
    except OSError:
        pass


def lock_path() -> Path:
    return HOME_DIR / ".biblioteca.lock"


def _processo_vivo(pid) -> bool | None:
    try:
        pid = int(pid)
        if pid <= 0:
            return None
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            dll = ctypes.WinDLL("kernel32", use_last_error=True)
            dll.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            dll.OpenProcess.restype = wintypes.HANDLE
            dll.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            dll.GetExitCodeProcess.restype = wintypes.BOOL
            dll.CloseHandle.argtypes = [wintypes.HANDLE]
            dll.CloseHandle.restype = wintypes.BOOL
            handle = dll.OpenProcess(0x1000, False, pid)
            if not handle:
                return True if ctypes.get_last_error() == 5 else False
            try:
                codigo = wintypes.DWORD()
                return codigo.value == 259 if dll.GetExitCodeProcess(handle, ctypes.byref(codigo)) else None
            finally:
                dll.CloseHandle(handle)
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def adquirir_lock(ignorar: bool = False) -> dict:
    """Impede 2 instâncias (Win+Linux juntos corrompem o SQLite).

    Retorna {"ok": True} ou {"ok": False, "erro": ...}. Com ignorar=True,
    sobrescreve lock existente (uso: --ignorar-lock após crash).
    Criação exclusiva impede duas aberturas simultâneas. Lock antigo
    (>24h) pode ser recuperado; PID vivo no mesmo host nunca expira.
    """
    lp = lock_path()
    info_atual = {"pid": os.getpid(),
                  "host": socket.gethostname(),
                  "so": sys.platform,
                  "inicio": agora_iso()}
    try:
        lp.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(3):
            try:
                fd = os.open(lp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                try:
                    antigo = json.loads(lp.read_text(encoding="utf-8"))
                    antigo = antigo if isinstance(antigo, dict) else {}
                except (OSError, ValueError):
                    antigo = {}
                try:
                    idade_h = (datetime.datetime.now().astimezone() -
                               datetime.datetime.fromisoformat(str(antigo.get("inicio") or ""))).total_seconds() / 3600.0
                except (ValueError, TypeError):
                    # Pode ser o intervalo entre criação e gravação por outra instância.
                    try:
                        idade_h = (time.time() - lp.stat().st_mtime) / 3600.0
                    except FileNotFoundError:
                        continue
                mesmo_host = antigo.get("host") == info_atual["host"]
                mesmo_so = antigo.get("so") in (sys.platform, os.name)
                vivo = mesmo_host and mesmo_so and _processo_vivo(antigo.get("pid")) is True
                if not ignorar and (idade_h < 24 or vivo):
                    return {"ok": False, "lock": antigo,
                            "erro": (f"Biblioteca já aberta em {antigo.get('host', '?')} "
                                     f"(pid {antigo.get('pid', '?')}, desde {antigo.get('inicio', '?')}). "
                                     "Feche lá primeiro ou use --ignorar-lock (após crash).")}
                try:
                    lp.unlink()
                except FileNotFoundError:
                    pass
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
                json.dump(info_atual, arquivo, ensure_ascii=False, indent=2)
            return {"ok": True, "lock": info_atual}
        return {"ok": False, "erro": "Outra instância está abrindo a biblioteca."}
    except OSError as e:
        return {"ok": False, "erro": f"não consegui gravar lock: {e}"}


def liberar_lock() -> None:
    """Remove lock da instância atual (não remove lock de outro pid/host/SO)."""
    import json as _json
    import socket as _socket
    lp = lock_path()
    try:
        if not lp.is_file():
            return
        try:
            dono = _json.loads(lp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(dono, dict):
            return
        try:
            host_atual = _socket.gethostname()
        except OSError:
            host_atual = ""
        # campos ausentes = lock de versão antiga: aceita como próprio
        so_ok = dono.get("so") in (None, "", os.name, sys.platform)
        host_ok = dono.get("host") in (None, "") or dono.get("host") == host_atual
        if (int(dono.get("pid") or -1) == os.getpid() and so_ok and host_ok):
            try:
                lp.unlink()
            except OSError:
                pass
    except (OSError, ValueError, TypeError):
        pass


def _txt(v) -> str:
    """Texto limpo: sem NUL (quebra Path/SQLite) e sem espaços nas bordas."""
    if v is None:
        return ""
    return (v if isinstance(v, str) else str(v)).replace("\x00", "").strip()


def _desaspas(s: str) -> str:
    """Remove um par de aspas duplas coladas (colo de 'copiar como caminho')."""
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s


def slugify(s: str) -> str:
    n = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    n = re.sub(r"[^a-zA-Z0-9]+", "-", n.lower()).strip("-")
    return n or "capa"


def nome_arquivo_portatil(caminho: str) -> str:
    """Basename de caminhos Windows/POSIX, independentemente do SO atual."""
    return Path(str(caminho or "").replace("\\", "/")).name


# Extensões de ROM por provider (aqui p/ scans e emuladores usarem sem ciclo).
ROM_EXTS_3DS = {".cci", ".cxi", ".3ds", ".3dsx", ".elf", ".app", ".axf"}

# Áudio do catálogo: inclui Opus nativo quando a conversão não está disponível.
MUSICA_EXTS = {".mp3", ".ogg", ".opus", ".m4a", ".flac", ".wav"}

# Vídeo da 2.0: contêineres que os 3 reprodutores (VLC/MPV/MPC-HC) abrem.
VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".m4v", ".ogv"}

__all__ = ['BASE_DIR', 'WIN_ROOT', 'LINUX_ROOT', 'MAC_ROOT', 'eh_mac', 'REL_HOME', 'resolve_home', 'HOME_DIR', 'DADOS_DIR', 'DEFAULT_DB', 'BACKUP_DIR', 'CAPAS_DIR', 'PRESETS_DIR', 'SESSOES_DIR', 'SAVES_DIR', 'WINE_PREFIXO', 'MODS_DIR', 'MUSICAS_DIR', 'BAIXAR_DIR', 'CACHE_WAV_DIR', 'TEXTURAS_DIR', 'VIDEOS_DIR', 'garantir_dirs', 'win_para_linux', 'linux_para_win', 'win_para_mac', 'mac_para_win', 'linux_para_mac', 'mac_para_linux', 'traduzir_para_atual', 'existe_aqui_ou_traduzido', 'resolver_exe', 'agora_iso', 'log_erro', 'lock_path', 'adquirir_lock', 'liberar_lock', 'slugify',
 'ROM_EXTS_3DS', 'MUSICA_EXTS', 'VIDEO_EXTS', 'nome_arquivo_portatil']
