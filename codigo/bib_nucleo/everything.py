"""Everything CLI, com cliente local opcional, raízes restritas e fallback seguro."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .base import BASE_DIR, HOME_DIR
from .processos import opcoes_sem_janela


def _cliente():
    configurado = os.environ.get("BIBLIOTECA_EVERYTHING", "").strip()
    instancia = os.environ.get("BIBLIOTECA_EVERYTHING_INSTANCIA", "").strip()
    if configurado:
        return configurado, instancia
    exe = shutil.which("es.exe")
    if exe:
        return exe, instancia
    for raiz in (HOME_DIR, BASE_DIR):
        local = raiz / "programa/ferramentas/everything/cli/es.exe"
        if local.is_file():
            return str(local), instancia or "TucoTeca"
    return "", instancia


def buscar_executaveis(roots, limite=60_000):
    exe, instancia = _cliente()
    if os.name != "nt" or not exe or not Path(exe).is_file():
        return None
    raizes = [Path(r).resolve() for r in roots if Path(r).is_dir()]
    if not raizes:
        return []
    if any('"' in str(r) for r in raizes):
        return None
    # < > são os agrupadores padrão; parênteses podem ser nomes de arquivo.
    consulta = "ext:exe <" + " | ".join('path:"' + str(r) + '"' for r in raizes) + ">"
    try:
        limite = max(1, int(limite))
        # ES 1.1.0.38 não aceita -utf8. Exportação com BOM independe da página
        # de código do console e preserva caminhos Unicode no Windows.
        with tempfile.TemporaryDirectory(prefix="tucoteca-everything-") as tmp:
            exportado = Path(tmp) / "resultados.txt"
            comando = [exe, "-timeout", "15000", "-full-path-and-name", "-n", str(limite),
                       "-export-txt", str(exportado), "-utf8-bom"]
            if instancia:
                comando.extend(["-instance", instancia])
            # ES tem parser próprio: -search remove aspas mesmo em -argv.
            # -search* recebe a expressão literal. Não há shell: < > e | são
            # operadores da busca, jamais redirecionamentos/comandos do Windows.
            linha_comando = subprocess.list2cmdline(comando) + " -search* " + consulta
            r = subprocess.run(linha_comando, shell=False, capture_output=True, stdin=subprocess.DEVNULL,
                               timeout=30, **opcoes_sem_janela())
            if r.returncode or not exportado.is_file() or exportado.stat().st_size > 32_000_000:
                return None
            linhas = exportado.read_text(encoding="utf-8-sig").splitlines()
            if len(linhas) > limite:
                return None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    saida = []
    for linha in linhas:
        p = Path(linha.strip())
        if p.suffix.lower() != ".exe" or not p.is_file() or p.is_symlink():
            continue
        real = p.resolve()
        if any(raiz in real.parents for raiz in raizes):
            saida.append(str(real))
    # Volume não indexado pode responder com sucesso e lista vazia.
    # Nesse caso a varredura normal continua sendo a fonte da verdade.
    return sorted(set(saida)) if saida else None
