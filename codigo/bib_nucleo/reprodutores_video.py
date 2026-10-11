#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Players externos da videoteca: VLC/MPV nos três SOs; MPC-HC só no Windows.

A descoberta usa ferramentas.py; MPC-HC nunca é substituído por outro
programa sob o mesmo nome. `auto` escolhe um player disponível. Arquivos
vindos de outra máquina usam tradução de caminho ou dados/videos/<nome>.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from bib_nucleo.ferramentas import ferramenta_suportada, localizar_ferramenta

PROVEDORES_VIDEO = ("vlc", "mpv", "mpchc")

NOMES = {"vlc": "VLC", "mpv": "MPV", "mpchc": "Media Player Classic-HC"}

SITES = {"vlc": "https://www.videolan.org/vlc/",
         "mpv": "https://mpv.io/installation/",
         "mpchc": "https://github.com/clsid2/mpc-hc/releases"}

LICENCAS = {"vlc": "GPL-2.0+ (open source)",
            "mpv": "GPL-2.0+ (open source)",
            "mpchc": "GPL-3.0 (open source, portable)"}

DESCRICOES = {
    "vlc": "Abre tudo (DVD, rede, legendas). Padrão do Hub.",
    "mpv": "Leve e preciso (seek exato, shaders).",
    "mpchc": "Clássico do Windows, duplo-clique e roda.",
}

_ENVS = {"vlc": "BIBLIOTECA_VLC", "mpv": "BIBLIOTECA_MPV",
         "mpchc": "BIBLIOTECA_MPCHC"}


def localizar_reprodutor(nome: str) -> str:
    """Binário do reprodutor ou `''` (env → ferramentas/ → PATH → padrão SO)."""
    nome = (nome or "").strip().lower()
    if nome not in PROVEDORES_VIDEO:
        raise ValueError("Reprodutor de vídeo inválido.")
    return localizar_ferramenta(nome)


def status_reprodutores() -> dict:
    """{nome: {instalado, exe, site}} — só leitura."""
    out = {}
    for nome in PROVEDORES_VIDEO:
        exe = localizar_reprodutor(nome)
        out[nome] = {"nome": NOMES[nome], "instalado": bool(exe), "exe": exe,
                     "site": SITES[nome], "licenca": LICENCAS[nome],
                     "descricao": DESCRICOES[nome], "suportado": ferramenta_suportada(nome)}
    return out


def erro_sem_reprodutor(nome: str) -> str:
    nome = (nome or "").strip().lower()
    if not ferramenta_suportada(nome):
        return f"{NOMES.get(nome, nome)} requer Windows. Use VLC ou MPV neste sistema."
    return (f"{NOMES.get(nome, 'reprodutor')} não encontrado. Baixe gratis em "
            f"{SITES.get(nome, '')} ou aponte {_ENVS.get(nome, '')} p/ o executável.")


def resolver_video(caminho: str) -> str:
    """Arquivo local/traduzido ou basename em dados/videos; só leitura."""
    from bib_nucleo.base import VIDEOS_DIR, nome_arquivo_portatil, traduzir_para_atual
    p = (caminho or "").strip()
    if not p or "\x00" in p:
        return ""
    try:
        for cand in (Path(p), Path(traduzir_para_atual(p)),
                     VIDEOS_DIR / nome_arquivo_portatil(p)):
            if cand.is_file():
                return str(cand)
    except (OSError, ValueError):
        pass
    return ""


def reproduzir_video(caminho: str, reprodutor: str = "auto") -> dict:
    """Abre o vídeo no reprodutor (ação explícita). `auto` = VLC→MPV→MPC-HC."""
    pedido = (reprodutor or "auto").strip().lower()
    if pedido != "auto" and pedido not in PROVEDORES_VIDEO:
        return {"ok": False, "erro": "Reprodutor de vídeo inválido."}
    real = resolver_video(caminho)
    if not real:
        return {"ok": False, "erro": "arquivo não encontrado."}
    ordem = PROVEDORES_VIDEO if pedido == "auto" else (pedido,)
    for nome in ordem:
        exe = localizar_reprodutor(nome)
        if not exe:
            continue
        try:
            subprocess.Popen([exe, str(Path(real).resolve())])
        except (OSError, subprocess.SubprocessError) as e:
            return {"ok": False, "erro": f"falha ao abrir: {e}"}
        return {"ok": True, "reprodutor": nome, "exe": exe, "path": real}
    primeiro = ordem[0] if ordem else "vlc"
    return {"ok": False, "erro": erro_sem_reprodutor(primeiro)}


__all__ = ["PROVEDORES_VIDEO",
           "localizar_reprodutor", "status_reprodutores",
           "erro_sem_reprodutor", "resolver_video", "reproduzir_video"]
