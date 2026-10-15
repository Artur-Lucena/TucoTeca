"""Preferências de aparência: defaults, validação e persistência."""
from __future__ import annotations

import os
from unittest.mock import patch

from executar import afirmar


def _esperado(tema, densidade, auto_backup=True, modo_simples=False, escala=None):
    """Dict completo devolvido por ler/salvar_aparencia (contrato com escala)."""
    from bib_nucleo import aparencia_usuario as A
    return {"tema": tema, "densidade": densidade,
            "escala_texto": A.ESCALA_PADRAO if escala is None else escala,
            "auto_backup": auto_backup, "modo_simples": modo_simples}


def teste_aparencia_default_e_validacao():
    from bib_nucleo import aparencia_usuario as A
    with patch.dict(os.environ):
        os.environ.pop("BIBLIOTECA_JOGOS_DIR", None)
        ap = A.ler_aparencia()
        afirmar(ap == _esperado("escuro", "conforto"), ap)
        afirmar(A.salvar_aparencia("claro", "compacto") ==
                _esperado("claro", "compacto"))
        # valor inválido é ignorado campo a campo, o válido é preservado
        afirmar(A.salvar_aparencia("roxo", "") ==
                _esperado("claro", "compacto"),
                "tema inválido não pode apagar o tema válido")
        afirmar(A.salvar_aparencia("", "enorme") ==
                _esperado("claro", "compacto"),
                "densidade inválida não pode apagar a densidade válida")
        afirmar(A.salvar_aparencia("escuro", "conforto", False) ==
                _esperado("escuro", "conforto", auto_backup=False),
                "auto_backup deve poder ser desligado")


def teste_aparencia_arquivo_corrompido_cai_no_padrao():
    from bib_nucleo import aparencia_usuario as A
    from bib_nucleo import base
    base.DADOS_DIR.mkdir(parents=True, exist_ok=True)
    (base.DADOS_DIR / "aparencia.json").write_text("{isso não é json", encoding="utf-8")
    afirmar(A.ler_aparencia() == _esperado("escuro", "conforto"))
    afirmar(A.salvar_aparencia("claro", "") ==
            _esperado("claro", "conforto"))
