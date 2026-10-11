"""Proteções do audit hook: remoção de links não libera escrita externa."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from executar import afirmar


def _bloqueada(evento, *args):
    try:
        sys.audit(evento, *args)
    except PermissionError:
        return
    afirmar(False, f"sandbox aceitou {evento}: {args}")


def teste_sandbox_unlink_nao_resolve_ultimo_componente():
    alvo = Path(tempfile.mkdtemp(prefix="sandbox-link-")) / "entrada"
    alvo.write_bytes(b"fixture")
    resolver = Path.resolve

    def resolver_loop(p, *a, **kw):
        if p == alvo:
            raise RuntimeError("Symlink loop (comportamento do Python 3.10)")
        return resolver(p, *a, **kw)

    with patch.object(Path, "resolve", resolver_loop):
        alvo.unlink()
    afirmar(not alvo.exists(), "a entrada sintética não foi removida")


def teste_sandbox_escrita_ainda_resolve_alvo_do_link():
    raiz = Path(tempfile.gettempdir())
    alvo = raiz / "link-sintetico"
    fora = raiz.parent / "nao-escrever-fora-do-sandbox"
    resolver = Path.resolve

    def resolver_externo(p, *a, **kw):
        return fora if p == alvo else resolver(p, *a, **kw)

    with patch.object(Path, "resolve", resolver_externo):
        # Emite só o evento: nunca abre/escreve um arquivo fora do sandbox.
        _bloqueada("open", str(alvo), "w", os.O_WRONLY | os.O_CREAT)
        _bloqueada("sqlite3.connect", str(alvo))


def teste_sandbox_operacoes_externas_e_dotdot_seguem_bloqueadas():
    raiz = Path(tempfile.gettempdir())
    fora = raiz.parent / "nao-modificar-fora-do-sandbox"
    for alvo in (fora, raiz / ".."):
        _bloqueada("open", str(alvo), "w", os.O_WRONLY | os.O_CREAT)
        _bloqueada("os.remove", str(alvo), -1)
        _bloqueada("os.rmdir", str(alvo), -1)
        _bloqueada("sqlite3.connect", str(alvo))


def teste_sandbox_remocao_resolve_links_nos_pais():
    raiz = Path(tempfile.gettempdir())
    pasta = raiz / "pasta-link-sintetica"
    fora = raiz.parent / "pasta-fora-do-sandbox"
    resolver = Path.resolve

    def resolver_pasta_externa(p, *a, **kw):
        return fora if p == pasta else resolver(p, *a, **kw)

    with patch.object(Path, "resolve", resolver_pasta_externa):
        _bloqueada("os.remove", str(pasta / "entrada"), -1)
        _bloqueada("os.rmdir", str(pasta / "subpasta"), -1)
