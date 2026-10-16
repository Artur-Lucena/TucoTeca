#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validação local: um comando reúne os gates que a CI hospedada rodava.

Ordem (mesma da antiga matriz, na medida do possível no SO local):
  1. Ruff (se disponível; senão, substituto: py_compile + espaço em branco)
  2. mypy nos builders (`ferramentas/`; se disponível; senão, pula)
  3. Suíte completa (`testes/executar.py`) — stdlib + Qt offscreen
  4. Cobertura dos subprocessos (`pytest --cobertura`) — opcional
  5. `git diff --check` + árvore suja (informativo)

Diferenças honestas em relação à matriz hospedada: sem gitleaks (a menos que
o binário exista no PATH), sem Ubuntu/Python 3.10 (roda no SO/Python atuais)
e sem macOS (continuaria pulado). Uso:

    python -B codigo/ferramentas/validar.py                 # tudo
    python -B codigo/ferramentas/validar.py --sem-pytest    # rápido (~2 min)
    python -B codigo/ferramentas/validar.py --modulo test_qt --sem-pytest

Saída: resumo no console e JSON em .provas/gates-local-<timestamp>.json.
Código de saída 0 somente se todos os passos executados passarem.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PY = sys.executable


def _agora():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _rodar(nome, cmd, cwd=REPO, env_extra=None):
    """Roda um passo, ecoa a saída e devolve (ok, tail, segundos)."""
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("QT_QUICK_BACKEND", "software")
    env.setdefault("QML_DISABLE_DISK_CACHE", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    if env_extra:
        env.update(env_extra)
    t0 = time.monotonic()
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                       errors="replace")
    seg = round(time.monotonic() - t0, 1)
    tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    for ln in tail[-6:]:
        print("    " + ln)
    return r.returncode == 0, tail, seg, " ".join(map(str, cmd))


def passo_ruff():
    """Ruff completo se existir (venv/PATH/python -m); senão substituto."""
    venv = Path(__file__).resolve().parent.parent / ".provas" / "venv-rel" / "Scripts" / "ruff.exe"
    ruff_exe = shutil.which("ruff")
    if venv.is_file():
        ruff = [str(venv)]
    elif ruff_exe:
        ruff = [ruff_exe]
    elif subprocess.run([PY, "-m", "ruff", "--version"], capture_output=True,
                        cwd=REPO).returncode == 0:
        ruff = [PY, "-m", "ruff"]
    else:
        print("  [aviso] ruff ausente — substituto: py_compile + trailing whitespace")
        import compileall
        ok_c = compileall.compile_dir("codigo", quiet=2, force=False)
        r = subprocess.run(["git", "diff", "--check"], cwd=REPO,
                           capture_output=True, text=True)
        sujo = [ln for ln in (r.stdout or "").splitlines() if ln.strip()]
        return bool(ok_c) and not sujo, {"modo": "substituto",
                                         "compile": bool(ok_c), "trailing": sujo}
    ok, tail, seg, cmd = _rodar("ruff", ruff + ["check", "codigo", "conftest.py",
                                                "--cache-dir", str(REPO / ".provas" / "ruff-cache-local")])
    return ok, {"modo": "ruff", "cmd": cmd,
                "achados": [ln for ln in tail if "Found" in ln or ": " in ln][:8]}


def passo_tipos():
    """mypy nos builders (config em pyproject.toml); pula se ausente."""
    venv = REPO / ".provas" / "venv-tipos" / "Scripts" / "python.exe"
    exe = str(venv) if venv.is_file() else shutil.which("mypy")
    if not exe:
        print("  [pulo] mypy ausente (crie .provas/venv-tipos ou instale no PATH)")
        return True, {"modo": "pulado"}
    cmd = [exe, "-m", "mypy"] if venv.is_file() else [exe]
    ok, tail, seg, c = _rodar("mypy", cmd + ["--cache-dir", str(REPO / ".provas" / "mypy-cache")])
    resumo = next((ln for ln in reversed(tail) if "Success" in ln or "error" in ln), "")
    return ok, {"modo": "mypy", "cmd": c, "segundos": seg, "resumo": resumo}


def passo_suite(modulos):
    cmd = [PY, "-B", "codigo/ferramentas/testes/executar.py"]
    for m in modulos or []:
        cmd += ["--modulo", m]
    ok, tail, seg, c = _rodar("suite", cmd)
    resumo = tail[-1] if tail else ""
    return ok, {"cmd": c, "segundos": seg, "resumo": resumo}


def passo_pytest():
    ok, tail, seg, c = _rodar("pytest", [PY, "-B", "-m", "pytest", "--cobertura"])
    resumo = next((ln for ln in reversed(tail) if "passed" in ln or "failed" in ln), "")
    return ok, {"cmd": c, "segundos": seg, "resumo": resumo}


def passo_git():
    r = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                       capture_output=True, text=True)
    sujo = [ln for ln in (r.stdout or "").splitlines() if ln.strip()]
    d = subprocess.run(["git", "diff", "--check"], cwd=REPO,
                       capture_output=True, text=True)
    ws = [ln for ln in (d.stdout or "").splitlines() if ln.strip()]
    return (not ws), {"sujo": sujo[:10], "whitespace": ws[:10]}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gates locais da TucoTeca")
    ap.add_argument("--sem-ruff", action="store_true")
    ap.add_argument("--sem-tipos", action="store_true", help="pula o mypy dos builders")
    ap.add_argument("--sem-pytest", action="store_true", help="pula a cobertura (leva ~8 min)")
    ap.add_argument("--modulo", action="append", default=[],
                    help="restringe a suíte a módulos (ex.: test_qt)")
    a = ap.parse_args(argv)

    print("== validação local (%s) ==" % _agora())
    rel = {"iniciado_em": _agora(), "python": sys.version.split()[0],
           "so": os.name, "passos": {}, "ok": True}
    t0 = time.monotonic()
    try:
        if not a.sem_ruff:
            print("[1/5] ruff")
            ok, info = passo_ruff()
            rel["passos"]["ruff"] = info
            print("  ->", "ok" if ok else "FALHOU")
            rel["ok"] &= ok
        if not a.sem_tipos:
            print("[2/5] mypy (ferramentas/)")
            ok, info = passo_tipos()
            rel["passos"]["tipos"] = info
            if info.get("modo") == "pulado":
                print("  -> pulado")
            elif info.get("resumo"):
                print("  ->", info["resumo"])
            else:
                print("  ->", "ok" if ok else "FALHOU")
            rel["ok"] &= ok
        print("[3/5] suíte completa" + (" (módulos: %s)" % ",".join(a.modulo) if a.modulo else ""))
        ok, info = passo_suite(a.modulo)
        rel["passos"]["suite"] = info
        print("  ->", info["resumo"] or ("ok" if ok else "FALHOU"))
        rel["ok"] &= ok
        if not a.sem_pytest:
            print("[4/5] pytest --cobertura")
            ok, info = passo_pytest()
            rel["passos"]["pytest"] = info
            print("  ->", info["resumo"] or ("ok" if ok else "FALHOU"))
            rel["ok"] &= ok
        print("[5/5] git")
        ok, info = passo_git()
        rel["passos"]["git"] = info
        print("  ->", "limpo" if ok and not info["sujo"] else
              ("whitespace!" if not ok else "árvore com alterações (informativo)"))
        if not ok:
            rel["ok"] = False
    finally:
        rel["segundos"] = round(time.monotonic() - t0, 1)
        destino = REPO / ".provas" / ("gates-local-%s.json" % _agora())
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(rel, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        print("\n%s — relatório: %s" % ("VERDE" if rel["ok"] else "VERMELHO",
                                        destino))
    return 0 if rel["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
