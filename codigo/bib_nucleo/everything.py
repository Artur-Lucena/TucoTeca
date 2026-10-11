"""Everything CLI BYOB, com validação das raízes e fallback para scan normal."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def buscar_executaveis(roots, limite=60_000):
    exe = os.environ.get("BIBLIOTECA_EVERYTHING", "").strip() or shutil.which("es.exe")
    if os.name != "nt" or not exe or not Path(exe).is_file():
        return None
    raizes = [Path(r).resolve() for r in roots if Path(r).is_dir()]
    if not raizes:
        return []
    if any('"' in str(r) for r in raizes):
        return None
    consulta = "ext:exe (" + " | ".join('"' + str(r) + os.sep + '"' for r in raizes) + ")"
    try:
        r = subprocess.run([exe, "-utf8", "-full-path", "-n", str(max(1, int(limite))), consulta],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        if r.returncode or len(r.stdout) > 32_000_000:
            return None
    except (OSError, subprocess.SubprocessError):
        return None
    saida = []
    for linha in r.stdout.splitlines()[:limite]:
        p = Path(linha.strip())
        if p.suffix.lower() != ".exe" or not p.is_file() or p.is_symlink():
            continue
        real = p.resolve()
        if any(raiz in real.parents for raiz in raizes):
            saida.append(str(real))
    # Volume não indexado pode responder com sucesso e lista vazia.
    # Nesse caso a varredura normal continua sendo a fonte da verdade.
    return sorted(set(saida)) if saida else None
