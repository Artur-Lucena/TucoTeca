"""Pytest coleta por AST e usa a mesma sandbox por processo do runner stdlib."""
from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent
RUNNER = RAIZ / "codigo/ferramentas/testes/executar.py"


class CasoIsolado(pytest.Item):
    def runtest(self):
        parent = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "Temp/opencode"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="pytest-tucoteca-", dir=parent) as tmp:
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", PYTHONFAULTHANDLER="1")
            cmd = [sys.executable, "-B", str(RUNNER), "--caso", self.path.name, self.name, "--raiz", tmp]
            cobertura = self.config.getoption("--cobertura")
            if cobertura:
                cmd.extend(("--coverage-arquivo", str(Path(tmp) / ".coverage")))
            r = subprocess.run(cmd, env=env, capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=120)
            if cobertura and (Path(tmp) / ".coverage").is_file():
                pasta = self.config._tucoteca_cobertura
                shutil.copy2(Path(tmp) / ".coverage", pasta / f".coverage.{self.path.stem}.{self.name}")
        if r.returncode:
            pytest.fail(f"Processo do caso encerrou com código {r.returncode}.\n" + r.stdout + r.stderr, pytrace=False)
        if re.search(r"\bskip\b|\[pula\]", r.stdout, re.I):
            pytest.skip(r.stdout.strip())

    def reportinfo(self):
        return self.path, 0, self.name


class ModuloIsolado(pytest.Module):
    def collect(self):
        # Não importa módulos no processo compartilhado: constantes HOME e Qt
        # de um caso não podem contaminar o seguinte nem acessar a coleção real.
        tree = ast.parse(self.path.read_text(encoding="utf-8"))
        for no in tree.body:
            if isinstance(no, ast.FunctionDef) and no.name.startswith("teste_"):
                yield CasoIsolado.from_parent(self, name=no.name)


def pytest_pycollect_makemodule(module_path, parent):
    if module_path.parent == RUNNER.parent and module_path.name.startswith("test_"):
        return ModuloIsolado.from_parent(parent, path=module_path)


def pytest_addoption(parser):
    parser.addoption("--cobertura", action="store_true", help="mede cobertura nos processos isolados")


def pytest_sessionstart(session):
    if session.config.getoption("--cobertura"):
        from datetime import datetime
        pasta = RAIZ / ".provas" / "cobertura" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        pasta.mkdir(parents=True)
        session.config._tucoteca_cobertura = pasta


def pytest_sessionfinish(session, exitstatus):
    if not session.config.getoption("--cobertura"):
        return
    import coverage
    pasta = session.config._tucoteca_cobertura
    cov = coverage.Coverage(data_file=str(pasta / ".coverage"), config_file=str(RAIZ / "pyproject.toml"))
    cov.combine(data_paths=[str(pasta)])
    cov.save()
    cov.json_report(outfile=str(pasta / "coverage.json"))
    cov.html_report(directory=str(pasta / "html"))
    cov.report()
    print(f"Relatório de cobertura real dos subprocessos: {pasta}")
