#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apps externos de mídia: editores de imagem, áudio/equalização e players.

- Imagem: Krita e GIMP (três SOs); PhotoDemon (só Windows, projeto
  independente, não uma descompilação do Photoshop).
- Áudio: Audacity/Tenacity editam arquivos nos três SOs; Equalizer APO e
  Peace (só Windows) ajustam a saída do sistema, não o arquivo. Os presets
  FFmpeg do Hub geram uma cópia equalizada e preservam o original.
- Vídeo: VLC/MPV nos três SOs; MPC-HC só no Windows.

A descoberta (env → ferramentas/ → PATH → padrão do SO) é a de
ferramentas.py. Nada aqui instala programas nem toca a rede; abrir é sempre
uma ação explícita da UI e nunca levanta (erro vira `{"ok": False}`).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from bib_nucleo.ferramentas import ferramenta_suportada, localizar_ferramenta

# nome: (rótulo, site, licença, descrição)
APPS = {
    "krita": ("Krita", "https://krita.org/pt-br/download/", "GPL-3.0 (open source)",
              "Pintura digital e retoque (PSD, PNG, JPG). Ideal p/ criar capas."),
    "gimp": ("GIMP", "https://www.gimp.org/downloads/", "GPL-3.0+ (open source)",
             "Edição fotográfica completa (camadas, filtros, XCF/PSD)."),
    "photodemon": ("PhotoDemon", "https://photodemon.org/", "BSD-3-Clause (open source, portátil)",
                   "Leve e instantâneo: abrir/converter/exportar sem instalar."),
    "audacity": ("Audacity", "https://www.audacityteam.org/download/",
                 "GPL-2.0+ (Tenacity: fork sem telemetria, GPL)",
                 "Editor com EQ gráfico/paramétrico (aceita Tenacity)."),
    "equalizerapo": ("Equalizer APO", "https://sourceforge.net/projects/equalizerapo/",
                     "GPL-2.0 (open source)", "EQ de sistema: vale p/ player interno e jogos."),
    "peace": ("Peace Equalizer", "https://sourceforge.net/projects/peace-equalizer-apo-extension/",
              "GPL-2.0 (open source)", "Presets e bandas p/ o APO (exige o APO)."),
    "vlc": ("VLC", "https://www.videolan.org/vlc/", "GPL-2.0+ (open source)",
            "Abre tudo (DVD, rede, legendas). Padrão do Hub."),
    "mpv": ("MPV", "https://mpv.io/installation/", "GPL-2.0+ (open source)",
            "Leve e preciso (seek exato, shaders)."),
    "mpchc": ("Media Player Classic-HC", "https://github.com/clsid2/mpc-hc/releases",
              "GPL-3.0 (open source, portable)", "Clássico do Windows, duplo-clique e roda."),
}

PROVEDORES_IMAGEM = ("krita", "gimp", "photodemon")
PROVEDORES_EQUALIZADOR = ("audacity", "equalizerapo", "peace")
PROVEDORES_VIDEO = ("vlc", "mpv", "mpchc")

# Presets ffmpeg (`-af`): do sutil ao "night mode". `flat` = só normaliza.
PRESETS_EQ = {
    "flat": "loudnorm=I=-16:TP=-1.5:LRA=11",
    "bass": "bass=g=6:f=110:w=0.6,loudnorm=I=-16:TP=-1.5:LRA=11",
    "treble": "treble=g=6:f=8000:w=0.6,loudnorm=I=-16:TP=-1.5:LRA=11",
    "vocal": "equalizer=f=1000:t=h:w=1:g=-3,equalizer=f=3000:t=h:w=1:g=3",
    "rock": "equalizer=f=100:t=h:w=0.8:g=5,equalizer=f=10000:t=h:w=0.8:g=4",
    "night": "acompressor=threshold=-20dB:ratio=4:attack=10:release=200,loudnorm=I=-16:TP=-1.5:LRA=11",
}


def _norm(nome: str) -> str:
    return (nome or "").strip().lower()


def _rotulo(nome: str, padrao: str) -> str:
    return APPS[nome][0] if nome in APPS else padrao


def _localizar(nome: str, familia: tuple, erro: str) -> str:
    nome = _norm(nome)
    if nome not in familia:
        raise ValueError(erro)
    return localizar_ferramenta(nome)


def _status(familia: tuple, localizar) -> dict:
    """{nome: {nome, instalado, exe, site, licenca, descricao, suportado}} — só leitura."""
    out = {}
    for nome in familia:
        exe = localizar(nome)
        rotulo, site, licenca, descricao = APPS[nome]
        out[nome] = {"nome": rotulo, "instalado": bool(exe), "exe": exe, "site": site,
                     "licenca": licenca, "descricao": descricao,
                     "suportado": ferramenta_suportada(nome)}
    return out


def _sem_app(nome: str, padrao: str, extra: str = "") -> str:
    site = APPS[nome][1] if nome in APPS else ""
    return (f"{_rotulo(nome, padrao)} não encontrado. Baixe gratis em {site} ou aponte "
            f"BIBLIOTECA_{nome.upper()} p/ o executável.{extra}")


def _abrir(cmd: list, **extra) -> dict:
    try:
        subprocess.Popen(cmd)
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "erro": f"falha ao abrir: {e}"}
    return {"ok": True, **extra}


# ---------------------------------------------------------------- imagem

def localizar_editor(nome: str) -> str:
    """Binário do editor de imagem ou `''`."""
    return _localizar(nome, PROVEDORES_IMAGEM, "Editor de imagem inválido.")


def status_editores() -> dict:
    return _status(PROVEDORES_IMAGEM, localizar_editor)


def erro_sem_editor(nome: str) -> str:
    nome = _norm(nome)
    if not ferramenta_suportada(nome):
        return (f"{_rotulo(nome, 'editor')} tem integração nativa apenas no Windows. "
                "Use Krita ou GIMP neste sistema.")
    return _sem_app(nome, "editor")


def abrir_no_editor(nome: str, caminho: str) -> dict:
    """Abre imagem/capa no editor."""
    nome = _norm(nome)
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
    return _abrir([exe, p], editor=nome, exe=exe, path=p)


# ---------------------------------------------------------------- áudio

def localizar_equalizador(nome: str) -> str:
    """Binário do editor de áudio/equalizador ou `''`."""
    return _localizar(nome, PROVEDORES_EQUALIZADOR, "Equalizador inválido.")


def status_equalizadores() -> dict:
    out = _status(PROVEDORES_EQUALIZADOR, localizar_equalizador)
    if out["peace"]["instalado"] and not out["equalizerapo"]["instalado"]:
        out["peace"]["aviso"] = "Peace exige o Equalizer APO instalado."
    return out


def erro_sem_equalizador(nome: str) -> str:
    nome = _norm(nome)
    if not ferramenta_suportada(nome):
        return (f"{_rotulo(nome, nome)} requer Windows. Neste sistema, use Audacity/Tenacity "
                "para editar ou os presets do Hub com FFmpeg instalado.")
    return _sem_app(nome, "equalizador", " Os presets do Hub também exigem FFmpeg instalado.")


def abrir_no_editor_audio(nome: str, caminho: str = "") -> dict:
    """Audacity abre a faixa; APO/Peace abrem o painel de saída do Windows."""
    nome = _norm(nome)
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
    return _abrir(cmd, editor=nome, exe=exe, path=p)


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
    """Aplica preset ffmpeg gerando cópia em `musicas/` (nunca sobrescreve)."""
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


# ---------------------------------------------------------------- vídeo

def localizar_reprodutor(nome: str) -> str:
    """Binário do player de vídeo ou `''`."""
    return _localizar(nome, PROVEDORES_VIDEO, "Reprodutor de vídeo inválido.")


def status_reprodutores() -> dict:
    return _status(PROVEDORES_VIDEO, localizar_reprodutor)


def erro_sem_reprodutor(nome: str) -> str:
    nome = _norm(nome)
    if not ferramenta_suportada(nome):
        return f"{_rotulo(nome, nome)} requer Windows. Use VLC ou MPV neste sistema."
    return _sem_app(nome, "reprodutor")


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
    """Abre o vídeo no player. `auto` = primeiro instalado de VLC→MPV→MPC-HC."""
    pedido = _norm(reprodutor) or "auto"
    if pedido != "auto" and pedido not in PROVEDORES_VIDEO:
        return {"ok": False, "erro": "Reprodutor de vídeo inválido."}
    real = resolver_video(caminho)
    if not real:
        return {"ok": False, "erro": "arquivo não encontrado."}
    ordem = PROVEDORES_VIDEO if pedido == "auto" else (pedido,)
    for nome in ordem:
        exe = localizar_reprodutor(nome)
        if exe:
            return _abrir([exe, str(Path(real).resolve())], reprodutor=nome, exe=exe, path=real)
    return {"ok": False, "erro": erro_sem_reprodutor(ordem[0])}


__all__ = ["APPS", "PROVEDORES_IMAGEM", "PROVEDORES_EQUALIZADOR", "PROVEDORES_VIDEO", "PRESETS_EQ",
           "localizar_editor", "status_editores", "erro_sem_editor", "abrir_no_editor",
           "localizar_equalizador", "status_equalizadores", "erro_sem_equalizador",
           "abrir_no_editor_audio", "aplicar_eq",
           "localizar_reprodutor", "status_reprodutores", "erro_sem_reprodutor",
           "resolver_video", "reproduzir_video"]
