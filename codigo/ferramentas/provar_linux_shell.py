#!/usr/bin/env python3
"""Provas reais de shell em sandbox; no Windows usa Bash do Git.

Complementa a suíte hermética (que bloqueia subprocessos). Não abre o Hub,
jogos ou dispositivos de áudio. Scripts recebem HOME, PATH e casas descartáveis.
Valida sintaxe POSIX, launchers, instalador .run e desinstalação; opcionalmente
processa WAV sintético com FFmpeg. Bash no Windows não substitui um kernel Linux.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

from montar_linux import DESINSTALAR, DESKTOP, REPO, SH_LAUNCHER, STUB, empacotar_run


def _shell_path(path: Path) -> str:
    texto = path.resolve().as_posix()
    if os.name == "nt" and len(texto) > 2 and texto[1] == ":":
        return "/" + texto[0].lower() + texto[2:]
    return texto


def _rodar(bash, arquivo, args=(), env=None, aceitar_falha=False):
    r = subprocess.run([bash, "--noprofile", "--norc", str(arquivo), *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=30)
    if r.returncode and not aceitar_falha:
        raise AssertionError(f"{arquivo.name}: rc={r.returncode}\n{r.stdout}\n{r.stderr}")
    return r


def provar(bash: str, ffmpeg=False) -> dict:
    parent = Path(tempfile.gettempdir()) / "opencode"
    parent.mkdir(exist_ok=True)
    provas = []
    with tempfile.TemporaryDirectory(prefix="linux-shell-", dir=parent) as pasta:
        tmp = Path(pasta)
        home = tmp / "home"
        home.mkdir()
        env = {k: v for k, v in os.environ.items() if not k.startswith("BIBLIOTECA_")}
        env.update(HOME=_shell_path(home), BASH_ENV="", ENV="")
        launcher_checkout = tmp / "checkout com espaço" / "BibliotecaHub.sh"
        launcher_checkout.parent.mkdir()
        launcher_checkout.write_bytes((REPO / "BibliotecaHub.sh").read_bytes())
        launcher_bundle = tmp / "bundle com espaço" / "BibliotecaHub.sh"
        launcher_bundle.parent.mkdir()
        launcher_bundle.write_text(SH_LAUNCHER, encoding="utf-8", newline="\n")
        for nome, texto in (("instalar.sh", STUB.replace("__OFFSET__", "0").replace("__VERSAO__", "teste")),
                            ("desinstalar.sh", DESINSTALAR)):
            p = tmp / nome
            p.write_text(texto, encoding="utf-8", newline="\n")
            r = subprocess.run([bash, "-n", str(p)], capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
        for p in (launcher_checkout, launcher_bundle):
            r = subprocess.run([bash, "-n", str(p)], capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
        provas.append("4 scripts passam bash -n")

        bin_probe = tmp / "bin-probe"
        bin_probe.mkdir()
        python_probe = bin_probe / "python3"
        python_probe.write_text('#!/bin/sh\nprintf "CASA=%s\\n" "$BIBLIOTECA_HOME"\nprintf "ARG=%s\\n" "$@"\n', encoding="utf-8")
        python_probe.chmod(0o755)
        r_path = subprocess.run([bash, "-c", 'printf "%s" "$PATH"'], env=env,
                                capture_output=True, text=True, timeout=10)
        probe_env = dict(env, PATH=_shell_path(bin_probe) + ":" + r_path.stdout)
        for p in (launcher_checkout, launcher_bundle):
            r = _rodar(bash, p, ["--selftest", "argumento com espaço"], probe_env)
            casas_validas = (_shell_path(p.parent), p.parent.resolve().as_posix())
            assert any("CASA=" + casa in r.stdout for casa in casas_validas), r.stdout
            assert "ARG=argumento com espaço\n" in r.stdout, r.stdout
            override = dict(probe_env, BIBLIOTECA_HOME="casa explícita")
            r = _rodar(bash, p, ["--gui"] if p == launcher_bundle else [], override)
            assert "CASA=casa explícita" in r.stdout, r.stdout
            if p == launcher_bundle:
                assert "app_win.py" in r.stdout and "ARG=--gui" not in r.stdout, r.stdout
        provas.append("2 launchers preservam casa explícita, argumentos e espaços")

        bin_real = tmp / "bin-real"
        bin_real.mkdir()
        python_real = bin_real / "python3"
        python_real.write_text("#!/bin/sh\nexec " + shlex.quote(Path(sys.executable).as_posix()) + ' "$@"\n', encoding="utf-8")
        python_real.chmod(0o755)
        ident = bin_real / "id"
        ident.write_text("#!/bin/sh\nprintf '1000\\n'\n", encoding="utf-8")
        ident.chmod(0o755)
        real_env = dict(env, PATH=_shell_path(bin_real) + ":" + r_path.stdout)
        build = tmp / "build" / "tucoteca"
        build.mkdir(parents=True)
        (build / "BibliotecaHub.sh").write_text(SH_LAUNCHER, encoding="utf-8", newline="\n")
        (build / "desinstalar.sh").write_text(DESINSTALAR, encoding="utf-8", newline="\n")
        (build / "tucoteca.desktop").write_text(DESKTOP, encoding="utf-8", newline="\n")
        (build / "dados").mkdir()
        (build / "dados/prova.txt").write_text("coleção descartável", encoding="utf-8")
        import montar_linux as ML
        with patch.object(ML, "DIST", tmp / "dist"):
            run = empacotar_run(build, "20990101", "payload.tar.xz")
        for args in (["--destino"], ["--opcao-inexistente"]):
            r = _rodar(bash, run, args, real_env, aceitar_falha=True)
            assert r.returncode != 0 and "ERRO:" in r.stderr, (r.stdout, r.stderr)
        provas.append("instalador rejeita opção inválida e destino sem argumento")

        for indice, tudo in enumerate((False, True)):
            # NTFS/Win32 não aceita | e aspas; ext4 será exercitado na CI Linux.
            especiais = " & mais 50% $literal" if os.name == "nt" else ' & mais | 50% $literal "aspas"'
            destino = tmp / (f"Destino {indice}" + especiais)
            args = ["--destino", _shell_path(destino)] if indice == 0 else ["--destino=" + _shell_path(destino)]
            r = _rodar(bash, run, args, real_env)
            hub = destino / "tucoteca"
            assert (hub / "BibliotecaHub.sh").is_file(), r.stdout
            desktop = home / ".local/share/applications/tucoteca.desktop"
            texto = desktop.read_text(encoding="utf-8")
            assert "{dest}" not in texto and '\nExec="' in texto and "50%%" in texto, texto
            assert (hub / "atalho-linux.txt").is_file()
            r = _rodar(bash, hub / "desinstalar.sh", ["--tudo"] if tudo else [], real_env)
            assert not desktop.exists(), r.stdout
            if tudo:
                assert not hub.exists(), r.stdout
            else:
                assert (hub / "dados/prova.txt").is_file(), r.stdout
            provas.append(".run instala/desinstala em caminho especial; " + ("--tudo remove sandbox" if tudo else "dados preservados"))

        if ffmpeg:
            sys.path.insert(0, str(REPO / "codigo"))
            from bib_nucleo import base
            from bib_nucleo import equalizadores as EQ
            from bib_nucleo.baixar import localizar_ffmpeg
            exe = localizar_ffmpeg()
            if not exe:
                raise AssertionError("--ffmpeg solicitado, mas FFmpeg não foi localizado")
            src = tmp / "sintetico.wav"
            with wave.open(str(src), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(44100)
                w.writeframes(b"".join(struct.pack("<h", int(12000 * math.sin(2 * math.pi * 440 * i / 44100)))
                                      for i in range(44100 * 3)))
            antes = src.read_bytes()
            with patch.object(base, "MUSICAS_DIR", tmp / "equalizados"):
                for preset in EQ.PRESETS_EQ:
                    r = EQ.aplicar_eq(str(src), preset, ffmpeg=exe)
                    assert r["ok"], r
                    with wave.open(r["path"], "rb") as w:
                        assert w.getnframes() > 0 and 2.8 <= w.getnframes() / w.getframerate() <= 3.2
                assert src.read_bytes() == antes
            provas.append("6 presets EQ com FFmpeg real, WAV válido e original intacto")
    return {"ok": True, "host": sys.platform, "shell": bash,
            "kernel_linux_testado": sys.platform.startswith("linux"), "provas": provas}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bash", default=shutil.which("bash") or "C:/Program Files/Git/bin/bash.exe")
    ap.add_argument("--ffmpeg", action="store_true")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(provar(args.bash, args.ffmpeg), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
