"""Publicação atômica de arquivos: nunca substitui um destino com dados parciais."""
from __future__ import annotations

import os
import json
import threading
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


_JSON_LOCK = threading.RLock()


def ler_json(alvo: Path, padrao=None, limite=8_000_000):
    try:
        with Path(alvo).open("rb") as f:
            raw = f.read(limite + 1)
        if len(raw) > limite:
            raise ValueError("arquivo maior que o limite")
        return json.loads(raw.decode("utf-8-sig"))
    except (OSError, ValueError, UnicodeError):
        return padrao


def gravar_json(alvo: Path, dados, backup=False):
    alvo = Path(alvo)
    raw = json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    with _JSON_LOCK:
        if alvo.is_file():
            antigo = alvo.read_bytes()
            if antigo == raw:
                return
            if backup:
                gravar_atomico(alvo.with_suffix(alvo.suffix + ".bak"), antigo)
        gravar_atomico(alvo, raw)


__all__ = ['destino_temporario', 'gravar_atomico', 'ler_json', 'gravar_json']
