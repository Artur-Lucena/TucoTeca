#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Torrents no Hub: último estado salvo pelo qBittorrent, sem rede.

Lê `BT_backup/` (.torrent/.fastresume) e calcula peças recebidas pelo
cliente. Tamanho de arquivo não prova download concluído (pré-alocação).
Sem peças disponíveis, mostra estimativa de ocupação e não autoriza importar.
Sem banco (derivado ao vivo, como cheats/texturas), darwin-safe
(só caminhos; nada executa).
"""
from __future__ import annotations

import os
from pathlib import Path

QBIT_DIR_ENV = "BIBLIOTECA_QBIT_DIR"


def _bdecodificar(buf: bytes, i: int = 0, _nivel: int = 0):
    """(objeto, próxima posição). Levanta ValueError em dado truncado."""
    if i >= len(buf) or _nivel > 64:
        raise ValueError("bencode truncado")
    c = buf[i:i + 1]
    if c == b"i":
        j = buf.index(b"e", i)
        return int(buf[i + 1:j]), j + 1
    if c == b"l" or c == b"d":
        out = [] if c == b"l" else {}
        i += 1
        while buf[i:i + 1] != b"e":
            chave, i = _bdecodificar(buf, i, _nivel + 1)
            if c == b"l":
                out.append(chave)
            else:
                if not isinstance(chave, bytes):
                    raise ValueError("chave bencode inválida")
                valor, i = _bdecodificar(buf, i, _nivel + 1)
                out[chave] = valor
        return out, i + 1
    if b"0" <= c <= b"9":
        j = buf.index(b":", i)
        n = int(buf[i:j])
        ini = j + 1
        fim = ini + n
        if n < 0 or fim > len(buf):
            raise ValueError("bencode truncado")
        return buf[ini:fim], fim
    raise ValueError(f"byte inválido em {i}")


def _u(x) -> str:
    """bytes do bencode → str (nunca levanta)."""
    if isinstance(x, bytes):
        return x.decode("utf-8", "replace")
    return str(x or "")


def bt_backup_dir(incluir_gerenciado: bool = True) -> Path | None:
    """Pasta BT_backup do qBittorrent (override `BIBLIOTECA_QBIT_DIR`)."""
    env = (os.environ.get(QBIT_DIR_ENV) or "").strip()
    if env:
        p = Path(env)
        return p if p.is_dir() else None
    casa = Path.home()
    from bib_nucleo.ferramentas import runtime_portatil
    from bib_nucleo.qbit import qbit_backup_local
    gerenciado = qbit_backup_local()
    if incluir_gerenciado and gerenciado.is_dir():
        return gerenciado
    if runtime_portatil():
        return None
    if sys_mac():
        cands = [casa / "Library/Application Support/qBittorrent/BT_backup"]
    elif os.name == "nt":
        cands = [Path(os.environ.get(k) or casa / "AppData" / sub)
                 / "qBittorrent" / "BT_backup"
                 for k, sub in (("LOCALAPPDATA", "Local"), ("APPDATA", "Roaming"))]
    else:
        cands = [casa / ".local/share/qBittorrent/BT_backup"]
    for c in cands:
        try:
            if c.is_dir():
                return c
        except OSError:
            continue
    return None


def sys_mac() -> bool:
    """Darwin sem importar base (evita ciclo)."""
    import sys
    return sys.platform == "darwin"


def _arquivos_info(info: dict) -> tuple[str, list[tuple[str, int]]]:
    """(nome, [(caminho_rel, tamanho)]) do dict `info` do .torrent."""
    nome = _u(info.get(b"name", b""))
    if not nome or nome in (".", "..") or any(c in nome for c in "/\\:"):
        raise ValueError("nome de torrent inválido")
    arquivos = info.get(b"files")
    if isinstance(arquivos, list) and arquivos:
        out = []
        for f in arquivos:
            if not isinstance(f, dict):
                continue
            try:
                tam = int(f.get(b"length", 0))
            except (TypeError, ValueError):
                continue
            partes = f.get(b"path", [])
            rel = "/".join(_u(p) for p in partes) if isinstance(
                partes, list) else _u(partes)
            if any(p in ("", ".", "..") or ":" in p
                   for p in rel.replace("\\", "/").split("/")):
                raise ValueError("caminho de torrent inválido")
            if tam > 0 and rel:
                out.append((rel, tam))
        if out:
            return nome, out
    try:
        tam = int(info.get(b"length", 0))
    except (TypeError, ValueError):
        tam = 0
    if tam > 0 and nome:
        return nome, [(nome, tam)]
    return nome, []


def _save_path_de(resume: dict) -> str:
    """Pasta de destino no .fastresume (best-effort, pode ser '')."""
    for chave in (b"qBt-savePath", b"savePath", b"save_path"):
        val = resume.get(chave)
        if isinstance(val, bytes) and val.strip():
            return _u(val).strip()
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _progresso_no_disco(base: Path, arquivos: list[tuple[str, int]]) -> tuple[int, int]:
    """(bytes prontos, bytes totais). Nunca levanta."""
    feito = total = 0
    for rel, tam in arquivos:
        total += tam
        try:
            atual = (base / rel).stat().st_size if tam > 0 else 0
        except OSError:
            atual = 0
        feito += min(atual, tam)
    return feito, total


def _progresso_resume(info: dict, resume: dict, total: int) -> int | None:
    """Bytes em peças completas; formatos libtorrent v1 e v2 documentados."""
    pecas = resume.get(b"pieces")
    tamanho = info.get(b"piece length", 0)
    if not isinstance(pecas, bytes) or not isinstance(tamanho, int) or tamanho <= 0:
        return None
    qtd = (total + tamanho - 1) // tamanho
    versao = resume.get(b"file-version", 1)
    if versao == 1 and len(pecas) == qtd:
        presentes = [bool(p & 1) for p in pecas]
    elif versao == 2 and len(pecas) == (qtd + 7) // 8:
        presentes = [bool(pecas[i // 8] & (0x80 >> (i % 8))) for i in range(qtd)]
    else:
        return None
    return sum(min(tamanho, total - i * tamanho) for i, pronto in enumerate(presentes) if pronto)


def _listar_torrents_arquivos(pasta: Path | None = None) -> dict:
    """Torrents conhecidos do qBittorrent + % medido em disco.

    Sem o BT_backup (cliente sem torrent): lista vazia, sem erro.
    """
    pasta = pasta if pasta is not None else bt_backup_dir()
    if pasta is None:
        return {"torrents": [], "erros": []}
    saida: list[dict] = []
    try:
        mets = sorted(pasta.glob("*.torrent"))
    except OSError as e:
        return {"torrents": [], "erros": [f"BT_backup ilegível: {e}"]}
    for met in mets:
        h = met.stem.lower()
        if len(h) not in (40, 64) or any(c not in "0123456789abcdef" for c in h):
            continue
        try:
            doc, _pos = _bdecodificar(met.read_bytes())
            info = doc.get(b"info", {}) if isinstance(doc, dict) else {}
            nome, arquivos = _arquivos_info(
                info if isinstance(info, dict) else {})
        except (OSError, ValueError):
            continue
        if not nome or not arquivos:
            continue
        total = sum(t for _r, t in arquivos)
        spa = ""
        resume = {}
        try:
            raw = (pasta / (h + ".fastresume")).read_bytes()
            resume, _p2 = _bdecodificar(raw)
            resume = resume if isinstance(resume, dict) else {}
            spa = _save_path_de(resume)
            if spa:
                # O .fastresume pode ter sido gravado no Windows antes do dual boot.
                from bib_nucleo.base import traduzir_para_atual
                spa = traduzir_para_atual(spa)
        except (OSError, ValueError):
            spa = ""
        base = Path(spa) / nome if spa else None
        if base is not None:
            # Single-file usa save_path/nome, não save_path/nome/nome.
            disco, total = _progresso_no_disco(base if info.get(b"files") else Path(spa), arquivos)
        else:
            disco = 0
        recebido = _progresso_resume(info, resume, total)
        feito = recebido if recebido is not None else disco
        pct = (100.0 * feito / total) if total > 0 else 0.0
        saida.append({"hash": h, "nome": nome, "total": total,
                      "feito": feito, "pct": round(min(pct, 100.0), 1),
                      "completo": bool(total > 0 and recebido == total and disco == total),
                      "fonte_progresso": "resume" if recebido is not None else "estimativa",
                      "save_path": str(base) if base is not None else ""})
    saida.sort(key=lambda t: t["nome"].casefold())
    return {"torrents": saida, "erros": []}


def listar_torrents() -> dict:
    from bib_nucleo.qbit import qbit_listar
    from bib_nucleo.ferramentas import runtime_portatil
    remoto = qbit_listar()
    if remoto.get("ok"):
        todos = {}
        # No checkout, manter o histórico instalado ao lado do perfil integrado.
        # O runtime distribuído não consulta perfis externos.
        if not runtime_portatil():
            legado = bt_backup_dir(incluir_gerenciado=False)
            if legado is not None:
                todos.update({t["hash"]: t for t in _listar_torrents_arquivos(legado)["torrents"]})
        todos.update({t["hash"]: t for t in remoto["torrents"]})
        return {"torrents": sorted(todos.values(), key=lambda t: t["nome"].casefold()),
                "erros": [], "fonte": "api"}
    return _listar_torrents_arquivos()


def encontrar_torrents(termo: str) -> list[dict]:
    """Filtra listar_torrents() por todas as palavras do termo."""
    palavras = (termo or "").casefold().split()
    todos = listar_torrents().get("torrents") or []
    if not palavras:
        return todos
    return [t for t in todos
            if all(p in t["nome"].casefold() for p in palavras)]


def formatar_tamanho(n: float) -> str:
    """123456789 → '117,7 MB' (pt-BR, sem locale)."""
    try:
        n = float(n or 0)
    except (TypeError, ValueError):
        return "0 B"
    for un in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or un == "TB":
            txt = f"{n:.1f}".replace(".", ",")
            return f"{txt} {un}"
        n /= 1024
    return f"{n:.1f} TB".replace(".", ",")


__all__ = ['bt_backup_dir', 'listar_torrents', 'encontrar_torrents',
           'formatar_tamanho']
