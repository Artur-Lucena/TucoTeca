#!/usr/bin/env python3
"""Suíte stdlib: cada teste em processo e diretório temporário próprios.

python ferramentas/testes/executar.py
O audit hook bloqueia escrita fora do sandbox, rede e processos externos.
Não depende de monkeypatch para proteger a instalação real.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

TESTES_DIR = Path(__file__).resolve().parent
REPO = TESTES_DIR.parent.parent.parent
CODIGO = REPO / "codigo"
FRONTENDS = CODIGO / "frontends"
sys.dont_write_bytecode = True
sys.path.insert(0, str(CODIGO))
sys.path.insert(0, str(FRONTENDS))


def afirmar(cond, msg=""):
    if not cond:
        raise AssertionError(msg or "afirmação falhou")


def isolar(raiz: Path):
    raiz = raiz.resolve()
    for sub in ("dados", "emu/user", "roms", "appdata", "programdata", "home"):
        (raiz / sub).mkdir(parents=True, exist_ok=True)
    for chave in list(os.environ):
        if chave.startswith("BIBLIOTECA_") or chave == "HYDRA_DB_PATH":
            os.environ.pop(chave)
    os.environ.update({
        "BIBLIOTECA_HOME": str(raiz / "dados"),
        "BIBLIOTECA_AZAHAR_DIR": str(raiz / "emu"),
        "BIBLIOTECA_WIN_ROOT": str(raiz / "win"),
        "BIBLIOTECA_LINUX_ROOT": str(raiz / "linux"),
        "BIBLIOTECA_SCAN_ROOTS": str(raiz / "roms"),
        "BIBLIOTECA_ROMS_ROOTS": str(raiz / "roms"),
        "APPDATA": str(raiz / "appdata"), "LOCALAPPDATA": str(raiz / "appdata"),
        "ProgramData": str(raiz / "programdata"),
        "HOME": str(raiz / "home"), "USERPROFILE": str(raiz / "home"),
        "TMP": str(raiz), "TEMP": str(raiz),
    })
    tempfile.tempdir = str(raiz)

    def dentro(p):
        if isinstance(p, int) or p is None:
            return
        if str(p) == ":memory:":
            return
        alvo = Path(os.fsdecode(p)).resolve()
        if alvo != raiz and raiz not in alvo.parents:
            raise PermissionError(f"Teste tentou escrever fora do sandbox: {alvo}")

    def audit(event, args):
        if event == "open":
            path, mode, flags = args
            if (isinstance(mode, str) and any(x in mode for x in "wax+")) or (
                    isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)):
                dentro(path)
        elif event in ("os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.utime", "sqlite3.connect"):
            dentro(args[0])
        elif event in ("os.rename", "os.link", "os.symlink"):
            dentro(args[0]); dentro(args[1])
        elif event in ("socket.connect", "subprocess.Popen", "os.system", "os.startfile"):
            raise PermissionError(f"Operação externa bloqueada no teste: {event}")
    sys.addaudithook(audit)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--caso", nargs=2)
    ap.add_argument("--raiz")
    args = ap.parse_args()
    if args.caso:
        isolar(Path(args.raiz))
        arq, nome = args.caso
        spec = importlib.util.spec_from_file_location("caso", TESTES_DIR / arq)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            getattr(mod, nome)()
        except Exception:
            traceback.print_exc()
            return 1
        return 0

    total = falhas = 0
    parent = Path(tempfile.gettempdir()) / "opencode"
    parent.mkdir(exist_ok=True)
    for arq in sorted(TESTES_DIR.glob("test_*.py")):
        tree = ast.parse(arq.read_text(encoding="utf-8"))
        for nome in sorted(n.name for n in tree.body if isinstance(n, ast.FunctionDef)
                           and n.name.startswith("teste_")):
            total += 1
            with tempfile.TemporaryDirectory(prefix="hub-teste-", dir=parent) as tmp:
                env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
                env["PYTHONPATH"] = os.pathsep.join(
                    [str(CODIGO), str(FRONTENDS)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
                r = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()),
                                    "--caso", arq.name, nome, "--raiz", tmp],
                                   env=env, capture_output=True, text=True, encoding="utf-8",
                                   timeout=120)
            print(f"{'PASS' if r.returncode == 0 else 'FAIL'} {arq.stem}.{nome}")
            if r.returncode:
                falhas += 1
                print(r.stdout + r.stderr)
    print(f"\n{total - falhas}/{total} testes aprovados (sandbox por teste).")
    return int(bool(falhas))


if __name__ == "__main__":
    raise SystemExit(main())
