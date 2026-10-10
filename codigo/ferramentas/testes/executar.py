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
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.parse
import urllib.request
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


def azahar_fake(emu):
    """Binário falso do Azahar que o SO atual detecta (exe no Win, AppImage no Linux)."""
    from pathlib import Path as _P
    emu = _P(emu)
    if sys.platform == "darwin":
        binario = emu / "Azahar.app" / "Contents" / "MacOS"
        binario.mkdir(parents=True, exist_ok=True)
        (binario / "azahar").write_bytes(b"MachO-fake")
    elif os.name == "nt":
        (emu / "azahar.exe").write_bytes(b"MZ" + b"0" * 64)
    else:
        (emu / "azahar.AppImage").write_bytes(b"\x7fELF" + b"0" * 64)
    return emu


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
        "BIBLIOTECA_MAC_ROOT": str(raiz / "mac"),
        "BIBLIOTECA_SCAN_ROOTS": str(raiz / "roms"),
        "BIBLIOTECA_ROMS_ROOTS": str(raiz / "roms"),
        "APPDATA": str(raiz / "appdata"), "LOCALAPPDATA": str(raiz / "appdata"),
        "ProgramData": str(raiz / "programdata"),
        "HOME": str(raiz / "home"), "USERPROFILE": str(raiz / "home"),
        "TMP": str(raiz), "TEMP": str(raiz),
    })
    tempfile.tempdir = str(raiz)

    def dentro(p, dir_fd=-1):
        if isinstance(p, int) or p is None:
            return
        if str(p) == ":memory:":
            return
        pp = Path(os.fsdecode(p))
        if not pp.is_absolute() and isinstance(dir_fd, int) and dir_fd >= 0:
            try:
                base = os.readlink(f"/proc/self/fd/{dir_fd}")
            except OSError:
                return
            pp = Path(base) / pp
        alvo = pp.resolve()
        if alvo != raiz and raiz not in alvo.parents:
            raise PermissionError(f"Teste tentou escrever fora do sandbox: {alvo}")

    def audit(event, args):
        if event == "open":
            path, mode, flags = args
            if (isinstance(mode, str) and any(x in mode for x in "wax+")) or (
                    isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)):
                dentro(path)
        elif event in ("os.remove", "os.unlink", "os.rmdir"):
            dentro(args[0], args[1] if len(args) > 1 else -1)
        elif event in ("os.mkdir", "os.chmod"):
            dentro(args[0], args[2] if len(args) > 2 else -1)
        elif event == "os.utime":
            dentro(args[0], args[3] if len(args) > 3 else -1)
        elif event == "os.open":
            path, flags = args[0], args[1] if len(args) > 1 else 0
            if isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
                dentro(path, args[3] if len(args) > 3 else -1)
        elif event == "sqlite3.connect":
            path = os.fsdecode(args[0])
            if path.startswith("file:"):
                parsed = urllib.parse.urlsplit(path)
                path = urllib.request.url2pathname(parsed.path)
            dentro(path)
        elif event in ("os.rename", "os.replace", "os.link"):
            dentro(args[0], args[2] if len(args) > 2 else -1)
            dentro(args[1], args[3] if len(args) > 3 else -1)
        elif event == "os.symlink":
            dentro(args[0])
            dentro(args[1], args[2] if len(args) > 2 else -1)
        elif event in ("socket.connect", "subprocess.Popen", "os.system", "os.startfile"):
            raise PermissionError(f"Operação externa bloqueada no teste: {event}")
    sys.addaudithook(audit)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--caso", nargs=2)
    ap.add_argument("--raiz")
    ap.add_argument("--modulo", action="append", default=[],
                    help="executa só este módulo, ex.: test_baixar (repetível)")
    ap.add_argument("--json", metavar="ARQUIVO", help="salva relatório estruturado")
    args = ap.parse_args()
    if args.caso and args.raiz:
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

    total = falhas = pulados = 0
    resultados = []
    parent = Path(tempfile.gettempdir()) / "opencode"
    parent.mkdir(exist_ok=True)
    for arq in sorted(TESTES_DIR.glob("test_*.py")):
        if args.caso and arq.name != args.caso[0]:
            continue
        if args.modulo and arq.stem not in {m.removesuffix(".py") for m in args.modulo}:
            continue
        tree = ast.parse(arq.read_text(encoding="utf-8"))
        for nome in sorted(n.name for n in tree.body if isinstance(n, ast.FunctionDef)
                            and n.name.startswith("teste_")):
            if args.caso and nome != args.caso[1]:
                continue
            total += 1
            inicio = time.monotonic()
            with tempfile.TemporaryDirectory(prefix="hub-teste-", dir=parent) as tmp:
                env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
                env["PYTHONPATH"] = os.pathsep.join(
                    [str(CODIGO), str(FRONTENDS)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
                try:
                    r = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()),
                                        "--caso", arq.name, nome, "--raiz", tmp],
                                       env=env, capture_output=True, text=True, encoding="utf-8",
                                       timeout=120)
                except subprocess.TimeoutExpired:
                    r = subprocess.CompletedProcess([], 1, "", "Teste excedeu 120 segundos.")
            pulo = r.returncode == 0 and bool(re.search(r"\bskip\b|\[pula\]", r.stdout, re.I))
            status = "FAIL" if r.returncode else "SKIP" if pulo else "PASS"
            pulados += int(pulo)
            resultados.append({"teste": f"{arq.stem}.{nome}", "status": status,
                               "segundos": round(time.monotonic() - inicio, 3),
                               "saida": r.stdout + r.stderr if r.returncode or pulo else ""})
            print(f"{status} {arq.stem}.{nome}")
            if r.returncode:
                falhas += 1
                try:
                    print(r.stdout + r.stderr)
                except UnicodeEncodeError:
                    sys.stdout.buffer.write(
                        (r.stdout + r.stderr).encode("utf-8", "replace"))
    if not total:
        ap.error("nenhum teste corresponde à seleção")
    print(f"\n{total - falhas}/{total} casos sem falha; {pulados} pulado(s) por ambiente.")
    if args.json:
        destino = Path(args.json)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps({"python": sys.version.split()[0], "plataforma": sys.platform,
                                       "total": total, "falhas": falhas, "pulados": pulados,
                                       "resultados": resultados}, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    return int(bool(falhas))


if __name__ == "__main__":
    raise SystemExit(main())
