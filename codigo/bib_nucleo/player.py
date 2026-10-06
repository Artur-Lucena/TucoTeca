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
import time
from pathlib import Path


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
        r = self._rotear(path)
        if not r.get("ok"):
            return r
        alvo = r["alvo"]
        if r["modo"] == "cache":
            rc = self._decodificar(r["ffmpeg"], path, alvo)
            if not rc.get("ok"):
                return rc
        if not _eh_nt():
            return {"ok": False, "erro": "MCI é só Windows"}
        self.close()
        self.alias = self._novo_alias()
        erro = self._cmd(f'open "{alvo}" type waveaudio alias {self.alias}')
        if erro:
            self.alias = ""
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
            from bib_nucleo.baixar import erro_sem_ffmpeg
            return {"ok": False,
                    "erro": f"mp3 interno exige ffmpeg. {erro_sem_ffmpeg()}"}
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
        if Path(dest).is_file():
            return {"ok": True}
        try:
            r = subprocess.run(
                [ffmpeg, "-y", "-v", "error", "-i", str(src),
                 "-ac", "2", "-ar", "44100", "-f", "wav", str(dest)],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=600)
        except (OSError, subprocess.SubprocessError) as e:
            return {"ok": False, "erro": f"ffmpeg: {e}"}
        if r.returncode != 0 or not Path(dest).is_file():
            detalhe = (r.stderr or "").strip().splitlines()
            msg = detalhe[-1][:200] if detalhe else f"ffmpeg rc={r.returncode}"
            try:
                Path(dest).unlink()
            except OSError:
                pass
            return {"ok": False, "erro": msg}
        return {"ok": True}

    def _podar_cache(self) -> None:
        """LRU: apaga wavs antigos até caber no teto (nunca levanta)."""
        try:
            from bib_nucleo.base import CACHE_WAV_DIR
            arqs = sorted((p for p in CACHE_WAV_DIR.glob("*.wav")
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

    def vivo(self) -> bool:
        return self._modo() in ("playing", "paused")

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
        r = self._sinal(_signal.SIGSTOP)
        if r.get("ok"):
            self._pausado_em = time.monotonic()
        return r

    def resume(self) -> dict:
        r = self._sinal(_signal.SIGCONT)
        if r.get("ok") and self._pausado_em:
            self._pausa_total += time.monotonic() - self._pausado_em
            self._pausado_em = 0.0
        return r

    def stop(self) -> None:
        if self.proc is not None:
            try:
                if self.proc.poll() is None:
                    self.proc.terminate()
                    try:
                        self.proc.wait(timeout=5)
                    except (OSError, subprocess.SubprocessError):
                        try:
                            self.proc.kill()
                        except OSError:
                            pass
            except OSError:
                pass
            self.proc = None

    def vivo(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

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
        self.fila = [f for f in (faixas or []) if f.get("path")]
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

    def _tocar_idx(self, i: int) -> dict:
        if not (0 <= i < len(self.fila)):
            return {"ok": False, "erro": "fora da fila"}
        self.backend.stop()
        try:
            self.backend.close()
        except Exception:
            pass
        r = self.backend.open(self.fila[i]["path"])
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
            return not self.backend.vivo()
        except Exception:
            return False


__all__ = ['NuloBackend', 'MciBackend', 'AfplayBackend', 'LinuxBackend',
           'criar_backend', 'Player']
