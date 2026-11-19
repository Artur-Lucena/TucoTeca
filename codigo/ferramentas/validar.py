#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validação local: um comando reúne os gates do CI.

  1. Ruff (se disponível; senão, substituto: py_compile + espaço em branco)
  2. mypy nos builders (`ferramentas/`; se disponível; senão, pula)
  3. Suíte (`testes/executar.py`, em paralelo; com cobertura quando o
     `coverage` existe — uma passada só)
  4. Electron: typecheck + vitest (se o npm e as dependências existirem)
  5. `git diff --check` + árvore suja (informativo)

O CI ainda roda Ubuntu, macOS e Python 3.10, gera os instaladores e passa o
gitleaks. Uso:

    python -B codigo/ferramentas/validar.py                 # tudo (~1 min)
    python -B codigo/ferramentas/validar.py --rapido        # só os testes do que mudou
    python -B codigo/ferramentas/validar.py --modulo test_ponte

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
    venv = REPO / ".provas" / "venv-ruff" / "Scripts" / "ruff.exe"  # convenção do AGENTS.md
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
    ok, tail, seg, cmd = _rodar("ruff", ruff + ["check", "codigo",
                                                "--cache-dir", str(REPO / ".provas" / "ruff-cache-local")])
    return ok, {"modo": "ruff", "cmd": cmd,
                "achados": [ln for ln in tail if "Found" in ln or ": " in ln][:8]}


def passo_tipos():
    """mypy nos builders (config em pyproject.toml); pula se ausente.

    `TUCOTECA_MYPY_PY` aponta um Python com mypy fora do repositório (útil quando
    o caminho do projeto é longo demais para as DLLs do mypy no Windows).
    """
    externo = os.environ.get("TUCOTECA_MYPY_PY", "").strip()
    venv = REPO / ".provas" / "venv-tipos" / "Scripts" / "python.exe"
    if externo:
        cmd = [externo, "-m", "mypy"]
    elif venv.is_file():
        cmd = [str(venv), "-m", "mypy"]
    elif shutil.which("mypy"):
        cmd = [shutil.which("mypy")]
    else:
        print("  [pulo] mypy ausente (crie .provas/venv-tipos ou instale no PATH)")
        return True, {"modo": "pulado"}
    ok, tail, seg, c = _rodar("mypy", cmd + ["--cache-dir", str(REPO / ".provas" / "mypy-cache")])
    resumo = next((ln for ln in reversed(tail) if "Success" in ln or "error" in ln), "")
    return ok, {"modo": "mypy", "cmd": c, "segundos": seg, "resumo": resumo}


def passo_suite(modulos, alterados=False, cobertura=True):
    cmd = [PY, "-B", "codigo/ferramentas/testes/executar.py"]
    for m in modulos or []:
        cmd += ["--modulo", m]
    if alterados:
        cmd.append("--alterados")
    tem_coverage = subprocess.run([PY, "-c", "import coverage"], capture_output=True).returncode == 0
    if cobertura and tem_coverage:
        cmd.append("--cobertura")
    ok, tail, seg, c = _rodar("suite", cmd)
    resumo = next((ln for ln in reversed(tail) if "casos sem falha" in ln or "caso(s)" in ln), "")
    total = next((ln for ln in reversed(tail) if ln.startswith("TOTAL")), "")
    return ok, {"cmd": c, "segundos": seg, "resumo": resumo, "cobertura": total.split()[-1] if total else None}


def passo_electron():
    """typecheck + vitest do app Electron; pula sem npm ou sem node_modules."""
    app = REPO / "codigo" / "frontends" / "electron"
    npm = shutil.which("npm")
    if not npm or not (app / "node_modules").is_dir():
        print("  [pulo] npm ou node_modules ausentes (npm --prefix codigo/frontends/electron ci)")
        return True, {"modo": "pulado"}
    ok_t, _, seg_t, _ = _rodar("typecheck", [npm, "run", "typecheck"], cwd=app)
    ok_v, tail, seg_v, _ = _rodar("vitest", [npm, "test"], cwd=app)
    resumo = next((ln.strip() for ln in tail if ln.strip().startswith("Tests")), "")
    return ok_t and ok_v, {"typecheck": ok_t, "vitest": ok_v, "resumo": resumo,
                           "segundos": round(seg_t + seg_v, 1)}


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
    ap.add_argument("--sem-cobertura", "--sem-pytest", dest="sem_cobertura", action="store_true",
                    help="suíte sem medir cobertura")
    ap.add_argument("--rapido", action="store_true",
                    help="só os testes do que mudou (--alterados), sem cobertura nem mypy")
    ap.add_argument("--modulo", action="append", default=[],
                    help="restringe a suíte a módulos (ex.: test_ponte)")
    ap.add_argument("--sem-electron", action="store_true", help="pula typecheck/vitest do Electron")
    a = ap.parse_args(argv)

    print("== validação local (%s) ==" % _agora())
    rel = {"iniciado_em": _agora(), "python": sys.version.split()[0],
           "so": os.name, "passos": {}, "ok": True}
    t0 = time.monotonic()
    try:
        if a.rapido:
            a.sem_tipos = a.sem_cobertura = True
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
        print("[3/5] suíte" + (" (só o que mudou)" if a.rapido else "")
              + (" (módulos: %s)" % ",".join(a.modulo) if a.modulo else ""))
        ok, info = passo_suite(a.modulo, alterados=a.rapido, cobertura=not a.sem_cobertura)
        rel["passos"]["suite"] = info
        print("  ->", (info["resumo"] or ("ok" if ok else "FALHOU"))
              + (f" · cobertura {info['cobertura']}" if info.get("cobertura") else ""))
        rel["ok"] &= ok
        if not a.sem_electron:
            print("[4/5] electron (typecheck + vitest)")
            ok, info = passo_electron()
            rel["passos"]["electron"] = info
            print("  ->", "pulado" if info.get("modo") == "pulado" else
                  (info.get("resumo") or ("ok" if ok else "FALHOU")))
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
