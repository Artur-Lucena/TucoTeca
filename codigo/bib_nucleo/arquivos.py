"""Publicação atômica de arquivos: nunca substitui um destino com dados parciais."""
from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def destino_temporario(destino: str | os.PathLike):
    """Caminho temporário no mesmo disco; publica só se o bloco terminar bem.

    O chamador fecha seu writer antes de sair do bloco. Em falha, o arquivo
    anterior fica intacto e o temporário é removido. Não substitui backups.
    """
    alvo = Path(destino)
    alvo.parent.mkdir(parents=True, exist_ok=True)
    fd, nome = tempfile.mkstemp(prefix=f".{alvo.stem}-", suffix=alvo.suffix or ".tmp",
                                dir=alvo.parent)
    os.close(fd)
    tmp = Path(nome)
    try:
        yield tmp
        os.replace(tmp, alvo)
    finally:
        tmp.unlink(missing_ok=True)


def gravar_atomico(destino: str | os.PathLike, dados: bytes) -> None:
    with destino_temporario(destino) as tmp:
        tmp.write_bytes(dados)


__all__ = ['destino_temporario', 'gravar_atomico']
