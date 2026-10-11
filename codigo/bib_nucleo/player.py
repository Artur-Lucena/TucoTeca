#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Player interno do Hub (sem app externo): transporte + playlist + auto-avançar.

Backends por SO, stdlib só (molde `controles.py`/`emuladores.py`):
- Windows: MCI `waveaudio` via `winmm` (ctypes; `mpegvideo` quebra aqui com
  rc=277, então mp3/m4a decodificam via ffmpeg em cache WAV).
- macOS: `afplay` do sistema (pause via SIGSTOP/SIGCONT).
- Linux: BYOB (`mpv`/`mpg123`/`ffplay`/`play`, o 1º no PATH; pause via sinal).
- Sem backend: `NuloBackend` com erro claro (usar Abrir-externo).

`Player` recebe backend injetável (a suíte usa `FakeBackend`, sem áudio).
Fim de faixa = `terminou()`; a UI avança (`proxima()`) por poll.
"""
from __future__ import annotations

import os
import shutil
import signal as _signal
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

from bib_nucleo.arquivos import destino_temporario


def _eh_nt() -> bool:
    return os.name == "nt"


def _eh_mac() -> bool:
    return sys.platform == "darwin"


class NuloBackend:
    """Sem áudio neste SO: todo play vira erro orientando (fallback externo)."""

    def __init__(self, motivo: str = "sem backend de áudio neste sistema"):
        self.motivo = motivo

    def open(self, _path: str) -> dict:
        return {"ok": False, "erro": self.motivo}

    def play(self) -> dict:
        return {"ok": False, "erro": self.motivo}

    def pause(self) -> dict:
        return {"ok": False, "erro": self.motivo}

    def resume(self) -> dict:
        return {"ok": False, "erro": self.motivo}

    def stop(self) -> None:
        return None

    def vivo(self) -> bool:
        return False

    def pos_ms(self):
        return None

    def dur_ms(self):
        return None

    def close(self) -> None:
        return None


class MciBackend:
    """Windows: MCI (`winmm`) sem nada além do SO.

    O driver `mpegvideo` quebra aqui (rc=277), mas `waveaudio` é sólido
    (provado rc=0): mp3/m4a/ogg entram via ffmpeg em cache WAV
    (`CACHE_WAV_DIR`, teto LRU); `.wav` toca direto, sem ffmpeg.

    Lições de `emuladores.py`: `WinDLL(..., use_last_error=True)` +
    `argtypes`/`restype` declarados (sem `ctypes.windll`).
    """

    _seq = 0
    CACHE_MB = 1024

    def __init__(self):
        self.alias = ""
        self._winmm = None
        self._aberto = ""

    def _dll(self):
        import ctypes
        from ctypes import wintypes
        if self._winmm is None:
            dll = ctypes.WinDLL("winmm", use_last_error=True)
            dll.mciSendStringW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR,
                                           wintypes.UINT, wintypes.HANDLE]
            dll.mciSendStringW.restype = wintypes.UINT
            dll.mciGetErrorStringW.argtypes = [wintypes.UINT, wintypes.LPWSTR,
                                               wintypes.UINT]
            dll.mciGetErrorStringW.restype = wintypes.BOOL
            self._winmm = dll
        return self._winmm

    def _cmd(self, comando: str) -> str:
        """Roda comando MCI; devolve '' ou a mensagem de erro."""
        import ctypes
        try:
            dll = self._dll()
        except (OSError, AttributeError) as e:
            return f"winmm indisponível: {e}"
        buf = ctypes.create_unicode_buffer(256)
        rc = dll.mciSendStringW(comando, buf, 256, None)
        if rc == 0:
            return ""
        try:
            if dll.mciGetErrorStringW(rc, buf, 256):
                return buf.value or f"MCI erro {rc}"
        except (OSError, AttributeError):
            pass
        return f"MCI erro {rc} (0x{ctypes.get_last_error():08X})"

    def _novo_alias(self) -> str:
        MciBackend._seq += 1
        return f"HUBMUS{MciBackend._seq}"

    def open(self, path: str) -> dict:
        """Prepara e abre sincronicamente (TUI); a GUI separa as duas etapas."""
        r = self.preparar(path)
        if not r.get("ok"):
            return r
        return self.open_preparado(r["alvo"])

    def preparar(self, path: str) -> dict:
        """Hash/conversão em segundo plano, sem abrir ou controlar o MCI."""
        if not _eh_nt():
            return {"ok": False, "erro": "MCI é só Windows"}
        r = self._rotear(path)
        if not r.get("ok"):
            return r
        alvo = r["alvo"]
        if r["modo"] == "cache":
            rc = self._decodificar(r["ffmpeg"], path, alvo)
            if not rc.get("ok"):
                return rc
        return self._preparar_caminho_mci(alvo)

    @staticmethod
    def _pasta_mci() -> Path:
        """Cache curto; o TEMP de um bundle profundamente aninhado pode ser longo."""
        pasta = Path(tempfile.gettempdir()) / "TucoTeca-mci"
        if len(str(pasta / ("0" * 16 + ".wav")).encode("utf-16-le")) < 256:
            return pasta
        import ctypes
        from ctypes import wintypes
        # Consulta o diretório real do usuário, sem alterar perfis ou variáveis.
        shell = ctypes.WinDLL("shell32", use_last_error=True)
        shell.SHGetFolderPathW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.HANDLE,
                                         wintypes.DWORD, wintypes.LPWSTR]
        shell.SHGetFolderPathW.restype = wintypes.LONG
        buf = ctypes.create_unicode_buffer(260)
        if shell.SHGetFolderPathW(None, 0x1C, None, 0, buf) != 0 or not buf.value:
            raise OSError("não foi possível localizar o temporário local do usuário")
        pasta = Path(buf.value) / "Temp" / "TucoTeca-mci"
        if len(str(pasta / ("0" * 16 + ".wav")).encode("utf-16-le")) >= 256:
            raise OSError("configure TEMP em uma pasta mais curta para o áudio interno")
        return pasta

    def _preparar_caminho_mci(self, alvo: str) -> dict:
        """MCI waveaudio limita o nome a 127 unidades UTF-16, mesmo sem parser.

        A GUI faz hash/cópia no worker, antes de abrir o dispositivo na UI.
        Cache por conteúdo, publicação atômica e teto LRU evitam alterar o
        original, publicar cópia parcial ou acumular temporários sem limite.
        """
        alvo = str(Path(alvo).resolve())
        if len(alvo.encode("utf-16-le")) < 256:
            return {"ok": True, "alvo": alvo}
        from bib_nucleo.musicas import sha_arquivo
        try:
            pasta = self._pasta_mci()
            pasta.mkdir(parents=True, exist_ok=True)
            self._podar_cache(pasta)
            sha = sha_arquivo(Path(alvo))
            curto = pasta / (sha[:16] + ".wav")
            if not curto.is_file() or sha_arquivo(curto) != sha:
                with destino_temporario(curto) as tmp:
                    shutil.copyfile(alvo, tmp)
                    if sha_arquivo(tmp) != sha:
                        raise ValueError("o áudio mudou durante a cópia temporária")
            os.utime(curto, None)
            return {"ok": True, "alvo": str(curto)}
        except (OSError, ValueError, AttributeError) as e:
            return {"ok": False, "erro": f"caminho de áudio MCI: {e}"}

    def open_preparado(self, alvo: str) -> dict:
        """Abre WAV na thread que fará play/pause/status/close.

        Aliases MCI pertencem à thread de abertura. Consultá-los em outra
        thread dá erro 263 (nome de dispositivo inválido), não fim da faixa.
        """
        if not _eh_nt():
            return {"ok": False, "erro": "MCI é só Windows"}
        if not alvo or not Path(alvo).is_file():
            return {"ok": False, "erro": "arquivo não encontrado."}
        preparado = self._preparar_caminho_mci(alvo)
        if not preparado.get("ok"):
            return preparado
        alvo = preparado["alvo"]
        self.close()
        self.alias = self._novo_alias()
        erro = self._cmd(f'open "{alvo}" type waveaudio alias {self.alias}')
        if erro:
            self.alias = ""
            return {"ok": False, "erro": erro}
        erro = self._cmd(f"set {self.alias} time format milliseconds")
        if erro:
            self.close()
            return {"ok": False, "erro": erro}
        self._aberto = alvo
        return {"ok": True}

    def _rotear(self, path: str) -> dict:
        """Puro (testável sem Win): direto .wav ou cache via ffmpeg."""
        if not path or not Path(path).is_file():
            return {"ok": False, "erro": "arquivo não encontrado."}
        if Path(path).suffix.lower() == ".wav":
            return {"ok": True, "modo": "direto", "alvo": str(path)}
        from bib_nucleo.baixar import localizar_ffmpeg
        ff = localizar_ffmpeg()
        if not ff:
            return {"ok": False,
                    "erro": ("mp3 interno exige ffmpeg"
                             " (https://ffmpeg.org) ou aponte BIBLIOTECA_FFMPEG"
                             " p/ o binário. Sem ele, use Externo… como"
                             " alternativa.")}
        from bib_nucleo.base import CACHE_WAV_DIR
        from bib_nucleo.musicas import sha_arquivo
        try:
            CACHE_WAV_DIR.mkdir(parents=True, exist_ok=True)
            chave = sha_arquivo(Path(path))[:16]
        except OSError as e:
            return {"ok": False, "erro": f"leitura: {e}"}
        self._podar_cache()
        return {"ok": True, "modo": "cache",
                "alvo": str(CACHE_WAV_DIR / f"{chave}.wav"), "ffmpeg": ff}

    def _decodificar(self, ffmpeg: str, src: str, dest: str) -> dict:
        """mp3/m4a → wav (pula se o cache já existe)."""
        if self._wav_valido(Path(dest)):
            return {"ok": True}
        try:
            with destino_temporario(dest) as tmp:
                r = subprocess.run(
                    [ffmpeg, "-y", "-v", "error", "-i", str(src),
                     "-ac", "2", "-ar", "44100", "-f", "wav", str(tmp)],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=600)
                if r.returncode != 0 or not self._wav_valido(tmp):
                    detalhe = (r.stderr or "").strip().splitlines()
                    raise ValueError(detalhe[-1][:200] if detalhe else
                                     f"ffmpeg rc={r.returncode} ou WAV incompleto")
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            return {"ok": False, "erro": f"ffmpeg: {e}"}
        return {"ok": True}

    @staticmethod
    def _wav_valido(path: Path) -> bool:
        try:
            with wave.open(str(path), "rb") as wav:
                tamanho = wav.getnframes() * wav.getsampwidth() * wav.getnchannels()
                return tamanho > 0 and path.stat().st_size >= tamanho + 44
        except (OSError, EOFError, wave.Error):
            return False

    def _podar_cache(self, pasta: Path | None = None) -> None:
        """LRU: apaga wavs antigos até caber no teto (nunca levanta)."""
        try:
            from bib_nucleo.base import CACHE_WAV_DIR
            pasta = pasta if pasta is not None else CACHE_WAV_DIR
            arqs = sorted((p for p in pasta.glob("*.wav")
                           if p.is_file()),
                          key=lambda p: p.stat().st_mtime)
            total = sum(p.stat().st_size for p in arqs)
            teto = self.CACHE_MB * 1048576
            for p in arqs:
                if total <= teto:
                    break
                try:
                    total -= p.stat().st_size
                    p.unlink()
                except OSError:
                    pass
        except OSError:
            pass

    def _modo(self) -> str:
        if not self.alias:
            return ""
        import ctypes
        try:
            dll = self._dll()
        except (OSError, AttributeError):
            return ""
        buf = ctypes.create_unicode_buffer(64)
        rc = dll.mciSendStringW(f"status {self.alias} mode", buf, 64, None)
        if rc != 0:
            return ""
        return (buf.value or "").strip().lower()

    def play(self) -> dict:
        if not self.alias:
            return {"ok": False, "erro": "nada aberto"}
        erro = self._cmd(f"play {self.alias}")
        return {"ok": not erro, "erro": erro or ""}

    def pause(self) -> dict:
        if not self.alias:
            return {"ok": False, "erro": "nada aberto"}
        erro = self._cmd(f"pause {self.alias}")
        return {"ok": not erro, "erro": erro or ""}

    def resume(self) -> dict:
        if not self.alias:
            return {"ok": False, "erro": "nada aberto"}
        erro = self._cmd(f"resume {self.alias}")
        return {"ok": not erro, "erro": erro or ""}

    def stop(self) -> None:
        if self.alias:
            try:
                self._cmd(f"stop {self.alias}")
            except Exception:
                pass

    def vivo(self) -> bool | None:
        modo = self._modo()
        return modo in ("playing", "paused") if modo else None

    def terminou(self) -> bool:
        """Fim natural confirmado: stopped e posição no final do áudio."""
        if self._modo() != "stopped":
            return False
        pos, dur = self.pos_ms(), self.dur_ms()
        return (pos is not None and dur is not None and dur > 0
                and pos >= dur - 50)

    def _posicao(self, o_que: str):
        if not self.alias:
            return None
        import ctypes
        try:
            dll = self._dll()
        except (OSError, AttributeError):
            return None
        buf = ctypes.create_unicode_buffer(64)
        rc = dll.mciSendStringW(f"status {self.alias} {o_que}", buf, 64, None)
        if rc != 0:
            return None
        try:
            return int((buf.value or "").strip())
        except (TypeError, ValueError):
            return None

    def pos_ms(self):
        return self._posicao("position")

    def dur_ms(self):
        return self._posicao("length")

    def close(self) -> None:
        if self.alias:
            try:
                self._cmd(f"close {self.alias}")
            except Exception:
                pass
            self.alias = ""
            self._aberto = ""


class _ProcessoBackend:
    """Base posix: player externo curto (`afplay`/BYOB) com pause por sinal."""

    NOME = ""
    ARGS: tuple = ()

    def __init__(self):
        self.proc = None
        self._aberto = ""

    def _bin(self) -> str:
        return ""

    def _args(self, path: str) -> list[str]:
        return [self._bin(), path]

    def open(self, path: str) -> dict:
        if not path or not Path(path).is_file():
            return {"ok": False, "erro": "arquivo não encontrado."}
        b = self._bin()
        if not b:
            return {"ok": False, "erro": self._sem_bin()}
        self.close()
        try:
            self.proc = subprocess.Popen(
                self._args(path), stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError) as e:
            self.proc = None
            return {"ok": False, "erro": f"falha ao abrir: {e}"}
        self._aberto = path
        self._t0 = time.monotonic()
        self._pausado_em = 0.0
        self._pausa_total = 0.0
        return {"ok": True}

    def _sem_bin(self) -> str:
        return "player indisponível"

    def play(self) -> dict:
        if self.proc is None:
            return {"ok": False, "erro": "nada aberto"}
        # Popen já iniciou a reprodução; SIGCONT só é necessário após pausa.
        if not self._pausado_em:
            return {"ok": self.vivo(), "erro": "" if self.vivo() else "player encerrado"}
        return self.resume()

    def _sinal(self, sig) -> dict:
        if self.proc is None or self.proc.poll() is not None:
            return {"ok": False, "erro": "nada tocando"}
        try:
            self.proc.send_signal(sig)
        except (OSError, ValueError) as e:
            return {"ok": False, "erro": f"sinal: {e}"}
        return {"ok": True}

    def pause(self) -> dict:
        if getattr(self, "_pausado_em", 0):
            return {"ok": self.vivo()}
        r = self._sinal(_signal.SIGSTOP)
        if r.get("ok"):
            self._pausado_em = time.monotonic()
        return r

    def resume(self) -> dict:
        if not getattr(self, "_pausado_em", 0):
            return {"ok": self.vivo()}
        r = self._sinal(_signal.SIGCONT)
        if r.get("ok") and self._pausado_em:
            self._pausa_total += time.monotonic() - self._pausado_em
            self._pausado_em = 0.0
        return r

    def stop(self) -> None:
        if self.proc is not None:
            try:
                if self.proc.poll() is None:
                    # Um processo parado por SIGSTOP não atende SIGTERM até voltar.
                    if getattr(self, "_pausado_em", 0):
                        self.proc.send_signal(_signal.SIGCONT)
                    self.proc.terminate()
                    try:
                        self.proc.wait(timeout=5)
                    except (OSError, subprocess.SubprocessError):
                        try:
                            self.proc.kill()
                            self.proc.wait(timeout=5)
                        except (OSError, subprocess.SubprocessError):
                            pass
            except OSError:
                pass
            self.proc = None
        self._aberto = ""
        self._pausado_em = 0.0

    def vivo(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def terminou(self) -> bool:
        return self.proc is not None and self.proc.poll() == 0

    def pos_ms(self):
        if not self._aberto:
            return None
        fim = self._pausado_em or time.monotonic()
        return int((fim - self._t0 - self._pausa_total) * 1000)

    def dur_ms(self):
        return None

    def close(self) -> None:
        self.stop()
        self._aberto = ""


class AfplayBackend(_ProcessoBackend):
    """macOS: `afplay` vem no SO."""

    def _bin(self) -> str:
        if not _eh_mac():
            return ""
        cand = "/usr/bin/afplay"
        if Path(cand).is_file():
            return cand
        return shutil.which("afplay") or ""

    def _sem_bin(self) -> str:
        return "afplay não encontrado (macOS incompleto?)"


_LINUX_CANDS = (
    ("mpv", ("--no-video", "--really-quiet")),
    ("mpg123", ("-q",)),
    ("ffplay", ("-nodisp", "-autoexit", "-loglevel", "quiet")),
    ("play", ()),
)


class LinuxBackend(_ProcessoBackend):
    """Linux BYOB: 1º player no PATH (molde emuladores)."""

    def _bin(self) -> str:
        for nome, _args in _LINUX_CANDS:
            achado = shutil.which(nome)
            if achado:
                self._args_extra = _args
                return achado
        return ""

    def _args(self, path: str) -> list[str]:
        return [self._bin(), *getattr(self, "_args_extra", ()), path]

    def _sem_bin(self) -> str:
        return ("sem player de áudio (instale mpv/mpg123/ffmpeg ou use"
                " Abrir-externo)")


def criar_backend():
    """Backend do SO atual (nunca levanta; cai em Nulo)."""
    try:
        if _eh_nt():
            return MciBackend()
        if _eh_mac():
            b = AfplayBackend()
            return b if b._bin() else NuloBackend(b._sem_bin())
        if os.name == "posix":
            b = LinuxBackend()
            return b if b._bin() else NuloBackend(b._sem_bin())
    except Exception as e:
        return NuloBackend(f"backend falhou: {e}")
    return NuloBackend()


class Player:
    """Transporte + playlist do Hub (estado puro; áudio no backend).

    `terminou()` = faixa acabou (UI chama `proxima()` → auto-avançar).
    """

    def __init__(self, backend=None):
        self.backend = backend or criar_backend()
        self.fila: list[dict] = []  # {path, titulo}
        self.idx: int | None = None
        self.estado = "parado"  # parado|tocando|pausado

    def carregar(self, faixas: list[dict], inicio: int = 0) -> None:
        self.parar()
        self.fila = [dict(f, path=f.get("path") or "") for f in (faixas or [])]
        self.idx = inicio if 0 <= inicio < len(self.fila) else (
            0 if self.fila else None)

    def atual(self):
        if self.idx is None or not (0 <= self.idx < len(self.fila)):
            return None
        d = dict(self.fila[self.idx])
        d["estado"] = self.estado
        try:
            d["pos_ms"] = self.backend.pos_ms()
            d["dur_ms"] = self.backend.dur_ms()
        except Exception:
            d["pos_ms"] = d["dur_ms"] = None
        return d

    def preparar(self, path: str) -> dict:
        """Prepara arquivo sem alterar fila/estado ou abrir dispositivo de áudio."""
        from bib_nucleo.musicas import resolver_musica
        path = resolver_musica(path) or path
        preparar = getattr(self.backend, "preparar", None)
        if preparar is not None:
            return preparar(path)
        return {"ok": True, "alvo": path}

    def tocar_preparado(self, i: int, preparado: dict) -> dict:
        if not preparado.get("ok"):
            return preparado
        return self._tocar_idx(i, preparado=preparado)

    def _tocar_idx(self, i: int, preparado: dict | None = None) -> dict:
        if not (0 <= i < len(self.fila)):
            return {"ok": False, "erro": "fora da fila"}
        self.estado = "parado"
        self.backend.stop()
        try:
            self.backend.close()
        except Exception:
            pass
        if preparado is None:
            r = self.backend.open(self.fila[i]["path"])
        else:
            abrir = getattr(self.backend, "open_preparado", self.backend.open)
            r = abrir(preparado["alvo"])
        if not r.get("ok"):
            self.estado = "parado"
            return r
        r = self.backend.play()
        self.idx = i
        self.estado = "tocando" if r.get("ok") else "parado"
        return r

    def tocar(self, i: int | None = None) -> dict:
        if i is None:
            if self.estado == "pausado":
                return self.continuar()
            i = self.idx if self.idx is not None else 0
        return self._tocar_idx(i)

    def alternar(self) -> dict:
        """▶↔⏸ (o que o botão principal e a barra de espaço usam)."""
        if self.estado == "tocando":
            return self.pausar()
        if self.estado == "pausado":
            return self.continuar()
        return self.tocar()

    def pausar(self) -> dict:
        if self.estado != "tocando":
            return {"ok": False, "erro": "nada tocando"}
        r = self.backend.pause()
        if r.get("ok"):
            self.estado = "pausado"
        return r

    def continuar(self) -> dict:
        if self.estado != "pausado":
            return self.tocar()
        r = self.backend.resume()
        if r.get("ok"):
            self.estado = "tocando"
        return r

    def parar(self) -> None:
        try:
            self.backend.stop()
        except Exception:
            pass
        self.estado = "parado"

    def proxima(self) -> dict:
        if self.idx is None:
            return self.tocar(0) if self.fila else {"ok": False,
                                                   "erro": "fila vazia"}
        if self.idx + 1 >= len(self.fila):
            self.parar()
            return {"ok": False, "erro": "fim da fila"}
        return self._tocar_idx(self.idx + 1)

    def anterior(self) -> dict:
        if not self.fila:
            return {"ok": False, "erro": "fila vazia"}
        return self._tocar_idx(max(0, (self.idx or 0) - 1))

    def terminou(self) -> bool:
        """A faixa acabou por conta própria (não por parar())?"""
        if self.estado != "tocando":
            return False
        try:
            terminou = getattr(self.backend, "terminou", None)
            if terminou is not None:
                return terminou() is True
            return self.backend.vivo() is False
        except Exception:
            return False


__all__ = ['NuloBackend', 'MciBackend', 'AfplayBackend', 'LinuxBackend',
           'criar_backend', 'Player']
