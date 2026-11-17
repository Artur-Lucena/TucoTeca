"""Pytest coleta por AST e usa a mesma sandbox por processo do runner stdlib."""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent
RUNNER = RAIZ / "codigo/ferramentas/testes/executar.py"
# varredura, ambiente, timeout e regra de pulo vêm do runner (uma fonte só)
_spec = importlib.util.spec_from_file_location("executar_runner", RUNNER)
EXECUTAR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(EXECUTAR)


class CasoIsolado(pytest.Item):
    def runtest(self):
        with tempfile.TemporaryDirectory(prefix="pytest-tucoteca-", dir=EXECUTAR.pasta_dos_casos()) as tmp:
            env = EXECUTAR.ambiente_caso()
            cmd = [sys.executable, "-B", str(RUNNER), "--caso", self.path.name, self.name, "--raiz", tmp]
            cobertura = self.config.getoption("--cobertura")
            if cobertura:
                cmd.extend(("--coverage-arquivo", str(Path(tmp) / ".coverage")))
            r = subprocess.run(cmd, env=env, capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=EXECUTAR.TIMEOUT_CASO)
            if cobertura and (Path(tmp) / ".coverage").is_file():
                pasta = self.config._tucoteca_cobertura
                shutil.copy2(Path(tmp) / ".coverage", pasta / f".coverage.{self.path.stem}.{self.name}")
        if r.returncode:
            pytest.fail(f"Processo do caso encerrou com código {r.returncode}.\n" + r.stdout + r.stderr, pytrace=False)
        if EXECUTAR.PULO.search(r.stdout):
            pytest.skip(r.stdout.strip())

    def reportinfo(self):
        return self.path, 0, self.name


class ModuloIsolado(pytest.Module):
    def collect(self):
        # Não importa módulos no processo compartilhado: constantes HOME
        # de um caso não podem contaminar o seguinte nem acessar a coleção real.
        for nome in EXECUTAR.casos(self.path):
            yield CasoIsolado.from_parent(self, name=nome)


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
