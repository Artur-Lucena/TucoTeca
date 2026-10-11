#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Edição de áudio e equalização: Audacity/Tenacity, APO, Peace e FFmpeg.

Audacity/Tenacity editam arquivos nos três SOs. APO e Peace são exclusivos
do Windows e ajustam a saída do sistema, não o arquivo musical. Ambos são
GPL-2.0. No Linux, os presets FFmpeg geram uma cópia equalizada: exigem
FFmpeg instalado, preservam o original e não alteram o equalizador do SO.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from bib_nucleo.ferramentas import ferramenta_suportada, localizar_ferramenta

PROVEDORES_EQUALIZADOR = ("audacity", "equalizerapo", "peace")

NOMES = {"audacity": "Audacity", "equalizerapo": "Equalizer APO",
         "peace": "Peace Equalizer"}

SITES = {"audacity": "https://www.audacityteam.org/download/",
         "equalizerapo": "https://sourceforge.net/projects/equalizerapo/",
         "peace": "https://sourceforge.net/projects/peace-equalizer-apo-extension/"}

LICENCAS = {"audacity": "GPL-2.0+ (Tenacity: fork sem telemetria, GPL)",
            "equalizerapo": "GPL-2.0 (open source)",
            "peace": "GPL-2.0 (open source)"}

DESCRICOES = {
    "audacity": "Editor com EQ gráfico/paramétrico (aceita Tenacity).",
    "equalizerapo": "EQ de sistema: vale p/ player interno e jogos.",
    "peace": "Presets e bandas p/ o APO (exige o APO).",
}

_ENVS = {"audacity": "BIBLIOTECA_AUDACITY",
         "equalizerapo": "BIBLIOTECA_EQUALIZERAPO",
         "peace": "BIBLIOTECA_PEACE"}

# Presets ffmpeg (`-af`): do sutil ao "night mode". `flat` = só normaliza.
PRESETS_EQ = {
    "flat": "loudnorm=I=-16:TP=-1.5:LRA=11",
    "bass": "bass=g=6:f=110:w=0.6,loudnorm=I=-16:TP=-1.5:LRA=11",
    "treble": "treble=g=6:f=8000:w=0.6,loudnorm=I=-16:TP=-1.5:LRA=11",
    "vocal": "equalizer=f=1000:t=h:w=1:g=-3,equalizer=f=3000:t=h:w=1:g=3",
    "rock": "equalizer=f=100:t=h:w=0.8:g=5,equalizer=f=10000:t=h:w=0.8:g=4",
    "night": "acompressor=threshold=-20dB:ratio=4:attack=10:release=200,loudnorm=I=-16:TP=-1.5:LRA=11",
}


def localizar_equalizador(nome: str) -> str:
    """Binário do provedor ou `''` (env → ferramentas/ → PATH → Program Files)."""
    nome = (nome or "").strip().lower()
    if nome not in PROVEDORES_EQUALIZADOR:
        raise ValueError("Equalizador inválido.")
    return localizar_ferramenta(nome)


def status_equalizadores() -> dict:
    """{nome: {instalado, exe, site}} — só leitura."""
    out = {}
    for nome in PROVEDORES_EQUALIZADOR:
        exe = localizar_equalizador(nome)
        out[nome] = {"nome": NOMES[nome], "instalado": bool(exe), "exe": exe,
                     "site": SITES[nome], "licenca": LICENCAS[nome],
                     "descricao": DESCRICOES[nome], "suportado": ferramenta_suportada(nome)}
    if out["peace"]["instalado"] and not out["equalizerapo"]["instalado"]:
        out["peace"]["aviso"] = "Peace exige o Equalizer APO instalado."
    return out


def erro_sem_equalizador(nome: str) -> str:
    nome = (nome or "").strip().lower()
    if not ferramenta_suportada(nome):
        return (f"{NOMES.get(nome, nome)} requer Windows. Neste sistema, use Audacity/Tenacity "
                "para editar ou os presets do Hub com FFmpeg instalado.")
    return (f"{NOMES.get(nome, 'equalizador')} não encontrado. Baixe gratis em "
            f"{SITES.get(nome, '')} ou aponte {_ENVS.get(nome, '')} p/ o executável. "
            "Os presets do Hub também exigem FFmpeg instalado.")


def abrir_no_editor_audio(nome: str, caminho: str = "") -> dict:
    """Audacity abre a faixa; APO/Peace abrem o painel de saída do Windows."""
    nome = (nome or "").strip().lower()
    if nome not in PROVEDORES_EQUALIZADOR:
        return {"ok": False, "erro": "Equalizador inválido."}
    exe = localizar_equalizador(nome)
    if not exe:
        return {"ok": False, "erro": erro_sem_equalizador(nome)}
    p = ""
    cmd = [exe]
    if nome == "audacity":
        from bib_nucleo.musicas import resolver_musica
        p = resolver_musica(caminho)
        if not p:
            return {"ok": False, "erro": "arquivo não encontrado."}
        cmd.append(str(Path(p).resolve()))
    try:
        subprocess.Popen(cmd)
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "erro": f"falha ao abrir: {e}"}
    return {"ok": True, "editor": nome, "exe": exe, "path": p}


def _destino_eq(src: Path, preset: str):
    from bib_nucleo.base import MUSICAS_DIR, slugify
    MUSICAS_DIR.mkdir(parents=True, exist_ok=True)
    base = slugify(src.stem + "-eq-" + preset) or "faixa-eq"
    dest = MUSICAS_DIR / f"{base}{src.suffix.lower()}"
    n = 1
    while dest.exists():
        n += 1
        dest = MUSICAS_DIR / f"{base}-{n}{src.suffix.lower()}"
    return dest


def aplicar_eq(caminho: str, preset: str = "bass", ffmpeg: str = "") -> dict:
    """Aplica preset ffmpeg gerando cópia em `musicas/` (nunca sobrescreve).

    Nunca levanta: sem ffmpeg/faixa vira `{"ok": False, "erro": ...}`.
    """
    from bib_nucleo.arquivos import destino_temporario
    from bib_nucleo.baixar import erro_sem_ffmpeg, localizar_ffmpeg
    from bib_nucleo.musicas import resolver_musica
    preset = (preset or "").strip().lower()
    if preset not in PRESETS_EQ:
        return {"ok": False, "erro": f"preset inválido. Use: {sorted(PRESETS_EQ)}"}
    real = resolver_musica(caminho)
    if not real:
        return {"ok": False, "erro": "arquivo não encontrado."}
    src = Path(real)
    binario = (ffmpeg or "").strip() or localizar_ffmpeg()
    if not binario:
        return {"ok": False, "erro": erro_sem_ffmpeg()}
    try:
        dest = _destino_eq(src, preset)
        from bib_nucleo.processos import opcoes_sem_janela
        cmd = [binario, "-y", "-v", "error", "-i", str(src), "-map", "0:a:0",
               "-vn", "-af", PRESETS_EQ[preset], str(dest)]
        with destino_temporario(dest) as tmp:
            cmd[-1] = str(tmp)
            r = subprocess.run(cmd, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=900,
                               stdin=subprocess.DEVNULL, **opcoes_sem_janela())
            if r.returncode != 0 or not tmp.is_file() or tmp.stat().st_size == 0:
                detalhe = (r.stderr or "").strip().splitlines()
                raise ValueError(detalhe[-1][:200] if detalhe else f"ffmpeg rc={r.returncode}")
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        return {"ok": False, "erro": f"EQ ({preset}): {e}"}
    return {"ok": True, "preset": preset, "origem": str(src), "path": str(dest)}


__all__ = ["PROVEDORES_EQUALIZADOR",
           "PRESETS_EQ", "localizar_equalizador", "status_equalizadores",
           "erro_sem_equalizador", "abrir_no_editor_audio", "aplicar_eq"]
