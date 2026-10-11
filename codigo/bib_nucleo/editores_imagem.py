#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integração externa de imagem: Krita, GIMP e PhotoDemon.

Krita/GIMP têm versões nativas para Windows, Linux e macOS. PhotoDemon
é um projeto independente para Windows, não uma descompilação do Photoshop.
A descoberta comum em ferramentas.py verifica SO e permissão de execução.
Este módulo não instala programas; abrir uma imagem é uma ação explícita.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from bib_nucleo.ferramentas import ferramenta_suportada, localizar_ferramenta

PROVEDORES_IMAGEM = ("krita", "gimp", "photodemon")

NOMES = {"krita": "Krita", "gimp": "GIMP", "photodemon": "PhotoDemon"}

SITES = {"krita": "https://krita.org/pt-br/download/",
         "gimp": "https://www.gimp.org/downloads/",
         "photodemon": "https://photodemon.org/"}

LICENCAS = {"krita": "GPL-3.0 (open source)",
            "gimp": "GPL-3.0+ (open source)",
            "photodemon": "BSD-3-Clause (open source, portátil)"}

DESCRICOES = {
    "krita": "Pintura digital e retoque (PSD, PNG, JPG). Ideal p/ criar capas.",
    "gimp": "Edição fotográfica completa (camadas, filtros, XCF/PSD).",
    "photodemon": "Leve e instantâneo: abrir/converter/exportar sem instalar.",
}

_ENVS = {"krita": "BIBLIOTECA_KRITA", "gimp": "BIBLIOTECA_GIMP",
         "photodemon": "BIBLIOTECA_PHOTODEMON"}


def localizar_editor(nome: str) -> str:
    """Binário do editor ou `''`. Ordem: env → ferramentas/ → PATH → padrão SO."""
    nome = (nome or "").strip().lower()
    if nome not in PROVEDORES_IMAGEM:
        raise ValueError("Editor de imagem inválido.")
    return localizar_ferramenta(nome)


def status_editores() -> dict:
    """{nome: {instalado, exe, site}} — só leitura, sem rede, sem processo."""
    out = {}
    for nome in PROVEDORES_IMAGEM:
        exe = localizar_editor(nome)
        out[nome] = {"nome": NOMES[nome], "instalado": bool(exe), "exe": exe,
                     "site": SITES[nome], "licenca": LICENCAS[nome],
                     "descricao": DESCRICOES[nome], "suportado": ferramenta_suportada(nome)}
    return out


def erro_sem_editor(nome: str) -> str:
    nome = (nome or "").strip().lower()
    site = SITES.get(nome, "")
    rotulo = NOMES.get(nome, "editor")
    if not ferramenta_suportada(nome):
        return f"{rotulo} tem integração nativa apenas no Windows. Use Krita ou GIMP neste sistema."
    return (f"{rotulo} não encontrado. Baixe gratis em {site} ou aponte "
            f"{_ENVS.get(nome, '')} p/ o executável.")


def abrir_no_editor(nome: str, caminho: str) -> dict:
    """Abre imagem/capa no editor (ação explícita da UI). Nunca levanta."""
    nome = (nome or "").strip().lower()
    if nome not in PROVEDORES_IMAGEM:
        return {"ok": False, "erro": "Editor de imagem inválido."}
    exe = localizar_editor(nome)
    if not exe:
        return {"ok": False, "erro": erro_sem_editor(nome)}
    p = (caminho or "").strip()
    if not p or "\x00" in p:
        return {"ok": False, "erro": "imagem não informada."}
    try:
        from bib_nucleo.base import existe_aqui_ou_traduzido
        ok, p = existe_aqui_ou_traduzido(p)
        if not ok or not Path(p).is_file():
            return {"ok": False, "erro": "arquivo não encontrado."}
        p = str(Path(p).resolve())
    except (OSError, ValueError) as e:
        return {"ok": False, "erro": f"caminho inválido: {e}"}
    try:
        subprocess.Popen([exe, p])
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "erro": f"falha ao abrir: {e}"}
    return {"ok": True, "editor": nome, "exe": exe, "path": p}


def editar_capa_caminho(capa_nome: str, editor: str = "auto") -> dict:
    """Atalho p/ capas do Hub (`dados/capas/<nome>`). `auto` = 1º instalado."""
    from bib_nucleo.base import CAPAS_DIR
    from bib_nucleo.base import nome_arquivo_portatil
    alvo = (CAPAS_DIR / nome_arquivo_portatil(capa_nome)) if capa_nome else None
    if alvo is None or not alvo.is_file():
        return {"ok": False, "erro": "capa não encontrada."}
    ordem = PROVEDORES_IMAGEM if editor == "auto" else ((editor or "").strip().lower(),)
    for nome in ordem:
        if nome not in PROVEDORES_IMAGEM:
            return {"ok": False, "erro": "Editor de imagem inválido."}
        if localizar_editor(nome):
            return abrir_no_editor(nome, str(alvo))
    return {"ok": False, "erro": erro_sem_editor(ordem[0] if ordem else "gimp")}


__all__ = ["PROVEDORES_IMAGEM",
           "localizar_editor", "status_editores", "erro_sem_editor",
           "abrir_no_editor", "editar_capa_caminho"]
