"""Processos com saída de progresso e prazo total, inclusive quando ficam mudos.

Ler stdout diretamente no worker pode bloquear antes de proc.wait(timeout).
Um leitor separado alimenta uma fila limitada; a thread chamadora controla o
prazo e aguarda o processo. Toda interrupção encerra e recolhe o filho antes
de fechar os pipes. Não usa shell e não executa nada durante o import.
"""
from __future__ import annotations

import os
import queue
import signal
import subprocess
import threading
import time


def opcoes_sem_janela() -> dict:
    """Kwargs p/ processo de FUNDO (yt-dlp, ffmpeg, 7z…) sem console visível.

    Um console-app iniciado por uma GUI sem console (pythonw, launcher) abre
    uma janela de terminal própria; CREATE_NO_WINDOW evita isso no Windows.
    Não use em programas que o usuário deve ver (emuladores, editores).
    """
    if os.name != "nt":
        return {}
    return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}


def executar_com_progresso(comando, ao_ler=None, timeout=1800) -> int:
    """Executa argv e entrega linhas ao callback; timeout conta desde Popen.

    Erro do callback de UI é ignorado. Falha de leitura/execução propaga para
    o chamador registrar seu estado; TimeoutExpired garante o fim do filho.
    """
    proc = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace",
                            start_new_session=os.name == "posix", **opcoes_sem_janela())
    eventos = queue.Queue(maxsize=128)
    parar = threading.Event()
    prazo = time.monotonic() + timeout

    def enviar(item):
        while not parar.is_set():
            try:
                eventos.put(item, timeout=0.05)
                return
            except queue.Full:
                pass

    def ler():
        try:
            for linha in proc.stdout or []:
                if parar.is_set():
                    break
                enviar(("linha", linha))
        except (OSError, ValueError) as e:
            enviar(("erro", e))
        finally:
            enviar(("fim", None))

    leitor = threading.Thread(target=ler, name="hub-saida-processo", daemon=True)
    try:
        leitor.start()
        while True:
            restante = prazo - time.monotonic()
            if restante <= 0:
                raise subprocess.TimeoutExpired(comando, timeout)
            try:
                tipo, item = eventos.get(timeout=min(restante, 0.1))
            except queue.Empty:
                continue
            if tipo == "erro":
                raise OSError(f"leitura da saída: {item}")
            if tipo == "fim":
                return proc.wait(timeout=max(0.001, prazo - time.monotonic()))
            if ao_ler:
                try:
                    ao_ler(item)
                except Exception:
                    pass
    except BaseException:
        # Recolher também após kill evita zumbis no Linux e handles vazando no Win.
        try:
            pid = getattr(proc, "pid", None)
            grupo = os.name == "posix" and isinstance(pid, int) and pid > 0
            if proc.poll() is None or grupo:
                if grupo:
                    os.killpg(pid, signal.SIGTERM)
                else:
                    proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    if grupo:
                        os.killpg(pid, signal.SIGKILL)
                    else:
                        proc.kill()
                    proc.wait(timeout=2)
                if grupo:
                    # wait recolhe o pai, mas FFmpeg pode ainda herdar o pipe do grupo.
                    try:
                        os.killpg(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        except (OSError, subprocess.SubprocessError):
            pass
        raise
    finally:
        parar.set()
        if getattr(proc.stdout, "close", None):
            try:
                proc.stdout.close()
            except (OSError, ValueError):
                pass
        if leitor.ident is not None:
            leitor.join(timeout=2)
