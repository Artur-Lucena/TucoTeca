"""Fronteiras entre as camadas: cada parte funciona e se testa sozinha.

    núcleo (bib_nucleo)  ←  serviços (servicos_ui)  ←  ponte (ponte*.py)  ←  Electron
                                                         renderer só fala por IPC

Uma dependência no sentido contrário faria um teste do núcleo puxar a
interface inteira (e os testes deixariam de ser localizados). Só lê os
fontes; não importa nada.
"""
import ast
import re
from pathlib import Path

from executar import CODIGO, TESTES_DIR, afirmar

PONTE = {"ponte", "ponte_paridade", "ponte_params", "ponte_dominios", "ponte_fontes"}
INTERFACE = PONTE | {"servicos_ui", "desktop"}


def _importados(arquivo: Path) -> set[str]:
    nomes = set()
    for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Import):
            nomes.update(a.name.split(".")[0] for a in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module and not no.level:
            nomes.add(no.module.split(".")[0])
    return nomes


def _violacoes(pasta: Path, proibidos: set[str]) -> list[str]:
    return [f"{p.relative_to(CODIGO).as_posix()} → {sorted(_importados(p) & proibidos)}"
            for p in sorted(pasta.rglob("*.py")) if _importados(p) & proibidos]


def teste_nucleo_nao_depende_da_interface():
    ruins = _violacoes(CODIGO / "bib_nucleo", INTERFACE)
    afirmar(not ruins, "o núcleo não pode importar serviços/ponte: " + "; ".join(ruins))


def teste_servicos_nao_dependem_da_ponte():
    ruins = _violacoes(CODIGO / "frontends" / "servicos_ui", PONTE | {"desktop"})
    afirmar(not ruins, "os serviços não podem importar a ponte: " + "; ".join(ruins))


def teste_renderer_so_fala_por_ipc():
    renderer = CODIGO / "frontends" / "electron" / "src" / "renderer"
    ruins = []
    for p in sorted([*renderer.rglob("*.ts"), *renderer.rglob("*.tsx")]):
        for m in re.finditer(r"""^\s*import[^'"]*['"]([^'"]+)['"]""", p.read_text(encoding="utf-8"), re.M):
            alvo = m.group(1)
            if alvo.startswith("node:") or alvo == "electron" or "/main/" in alvo or "/preload/" in alvo:
                ruins.append(f"{p.relative_to(renderer).as_posix()} → {alvo}")
    afirmar(not ruins, "o renderer só usa window.tucoteca: " + "; ".join(ruins))


def teste_testes_nao_dependem_uns_dos_outros():
    """Cada arquivo de teste roda sozinho: só o runner (afirmar, sandbox) é compartilhado."""
    nossos = {p.stem for p in TESTES_DIR.glob("test_*.py")}
    ruins = [f"{p.name} → {sorted(_importados(p) & nossos)}"
             for p in sorted(TESTES_DIR.glob("test_*.py")) if _importados(p) & nossos]
    afirmar(not ruins, "; ".join(ruins))
