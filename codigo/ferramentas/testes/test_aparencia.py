"""Preferências de aparência: defaults, validação e persistência."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from executar import afirmar


def teste_aparencia_default_e_validacao():
    from bib_nucleo import aparencia_usuario as A
    padrao = {"tema": "escuro", "densidade": "conforto", "auto_backup": True, "modo_simples": False}
    with patch.dict(os.environ):
        os.environ.pop("BIBLIOTECA_JOGOS_DIR", None)
        ap = A.ler_aparencia()
        afirmar(ap == padrao, ap)
        afirmar(A.salvar_aparencia("claro", "compacto") ==
                {"tema": "claro", "densidade": "compacto", "auto_backup": True, "modo_simples": False})
        # valor inválido é ignorado campo a campo, o válido é preservado
        afirmar(A.salvar_aparencia("roxo", "") ==
                {"tema": "claro", "densidade": "compacto", "auto_backup": True, "modo_simples": False},
                "tema inválido não pode apagar o tema válido")
        afirmar(A.salvar_aparencia("", "enorme") ==
                {"tema": "claro", "densidade": "compacto", "auto_backup": True, "modo_simples": False},
                "densidade inválida não pode apagar a densidade válida")
        afirmar(A.salvar_aparencia("escuro", "conforto", False) ==
                {"tema": "escuro", "densidade": "conforto", "auto_backup": False, "modo_simples": False},
                "auto_backup deve poder ser desligado")


def teste_aparencia_arquivo_corrompido_cai_no_padrao():
    from bib_nucleo import aparencia_usuario as A
    from bib_nucleo import base
    base.DADOS_DIR.mkdir(parents=True, exist_ok=True)
    (base.DADOS_DIR / "aparencia.json").write_text("{isso não é json", encoding="utf-8")
    padrao = {"tema": "escuro", "densidade": "conforto", "auto_backup": True, "modo_simples": False}
    afirmar(A.ler_aparencia() == padrao)
    afirmar(A.salvar_aparencia("claro", "") ==
            {"tema": "claro", "densidade": "conforto", "auto_backup": True, "modo_simples": False})
