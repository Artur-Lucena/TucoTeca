#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cheats Gateway do Azahar com liga/desliga por jogo, tal qual os mods.

Arquivo live: `user/cheats/<TITLE-ID>.txt` (HEX maiúsculo). Bloco ativo tem
`*citra_enabled` logo após o `[Nome]`; sem ele o cheat existe mas não
aplica. Azahar lê no boot — alternar exige reiniciar o jogo.
Sem banco, stdlib só, darwin-safe (texto puro, sem privilégio).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

CHEAT_MAX_NOME = 64
CHEATS_MAX_QTD = 64
CHEAT_MAX_LINHAS = 1024

_TID_RE = re.compile(r"^[0-9A-Fa-f]{16}$")
_LINHA_COD = re.compile(r"^[0-9A-Fa-f]{8} [0-9A-Fa-f]{8}$")
_ATIVO = "*citra_enabled"


def titulo_ok(tid: str) -> str:
    """Normaliza e valida o title ID (16 hex). '' se inválido."""
    tid = (tid or "").strip().upper()
    return tid if _TID_RE.match(tid) else ""


def cheats_path(tid: str) -> Path | None:
    """Caminho do `.txt` deste jogo (None se sem user/ ou TID inválido)."""
    tid = titulo_ok(tid)
    if not tid:
        return None
    from bib_nucleo import emuladores as EMU
    try:
        ud = EMU.azahar_user_dir()
    except (OSError, ValueError):
        return None
    if not ud:
        return None
    d = Path(ud) / "cheats"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    return d / f"{tid}.txt"


def _ler_blocos(texto: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """(preâmbulo, [(nome, linhas)]) preservando ordem e comentários."""
    pre, blocos = [], []
    atual = None
    for linha in texto.splitlines():
        m = re.match(r"^\[(.+)\]$", linha.strip())
        if m:
            atual = (m.group(1), [])
            blocos.append(atual)
        elif atual is None:
            pre.append(linha)
        else:
            atual[1].append(linha)
    return pre, blocos


def _escrever(pre: list[str], blocos: list[tuple[str, list[str]]]) -> str:
    out = list(pre)
    for nome, linhas in blocos:
        out.append(f"[{nome}]")
        out.extend(linhas)
    text = "\n".join(out)
    return text + ("\n" if text and not text.endswith("\n") else "")


def listar_cheats(tid: str) -> list[dict]:
    """Cheats do jogo: [{nome, ativo, linhas}]. [] se ausente/ilegível."""
    arq = cheats_path(tid)
    if arq is None or not arq.is_file():
        return []
    try:
        _, blocos = _ler_blocos(arq.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for nome, linhas in blocos:
        corpo = [l for l in linhas if l.strip()]
        ativo = bool(corpo) and corpo[0].strip() == _ATIVO
        out.append({"nome": nome, "ativo": ativo, "linhas": len(corpo)})
    return out


def cheats_ativos(tid: str) -> list[str]:
    """Nomes ativos (para exibir no detalhe)."""
    return [c["nome"] for c in listar_cheats(tid) if c["ativo"]]


def _gravar(arq: Path, pre, blocos) -> dict:
    try:
        tmp = arq.with_name(arq.name + ".hub-tmp")
        tmp.write_text(_escrever(pre, blocos), encoding="utf-8")
        os.replace(tmp, arq)
    except OSError as e:
        return {"ok": False, "erro": f"falha ao gravar: {e}"}
    return {"ok": True}


def definir_cheat(tid: str, nome: str, ativo: bool) -> dict:
    """Liga/desliga preservando o resto do arquivo byte a byte."""
    tid = titulo_ok(tid)
    arq = cheats_path(tid)
    if arq is None:
        return {"ok": False, "erro": "title ID inválido ou sem user/."}
    if not arq.is_file():
        return {"ok": False, "erro": f"sem cheats p/ {tid}."}
    try:
        pre, blocos = _ler_blocos(arq.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return {"ok": False, "erro": f"falha ao ler: {e}"}
    for i, (n, linhas) in enumerate(blocos):
        if n == nome:
            corpo = [l for l in linhas if l.strip()]
            tem = bool(corpo) and corpo[0].strip() == _ATIVO
            if ativo and not tem:
                blocos[i] = (n, [_ATIVO] + linhas)
            elif not ativo and tem:
                resto = list(linhas)
                for j, l in enumerate(resto):
                    if l.strip():
                        del resto[j]
                        break
                blocos[i] = (n, resto)
            r = _gravar(arq, pre, blocos)
            if not r.get("ok"):
                return r
            return {"ok": True, "tid": tid, "nome": nome, "ativo": ativo}
    return {"ok": False, "erro": f"cheat '{nome}' não achado."}


def alternar_cheat(tid: str, nome: str) -> dict:
    """Alterna o estado atual."""
    atual = [c for c in listar_cheats(tid) if c["nome"] == nome]
    if not atual:
        return {"ok": False, "erro": f"cheat '{nome}' não achado."}
    return definir_cheat(tid, nome, not atual[0]["ativo"])


def _nome_ok(nome: str) -> str:
    nome = (nome or "").strip()
    if not nome or len(nome) > CHEAT_MAX_NOME or "\n" in nome:
        return ""
    if nome.startswith("[") or nome.endswith("]"):
        return ""
    return nome


def adicionar_cheat(tid: str, nome: str, codigo: str) -> dict:
    """Anexa bloco NOVO sempre desligado (seguro: usuário liga depois).

    Código: linhas `XXXXXXXX YYYYYYYY`, `*comentário` ou vazio. Rejeita
    duplicata de nome e lixo (endereço fora do par hex).
    """
    tid = titulo_ok(tid)
    arq = cheats_path(tid)
    if arq is None:
        return {"ok": False, "erro": "title ID inválido ou sem user/."}
    nome = _nome_ok(nome)
    if not nome:
        return {"ok": False, "erro": "nome inválido."}
    linhas, ruins = [], []
    for bruta in (codigo or "").splitlines():
        l = bruta.strip()
        if not l or l.startswith("*"):
            if l and l != _ATIVO:
                linhas.append(l)
            continue
        if _LINHA_COD.match(l):
            linhas.append(l.upper())
        else:
            ruins.append(bruta.strip()[:24])
    if not linhas:
        return {"ok": False, "erro": "código vazio ou sem linha válida."}
    if ruins:
        return {"ok": False,
                "erro": f"linha inválida: {ruins[0]} (use XXXXXXXX YYYYYYYY)."}
    if len(linhas) > CHEAT_MAX_LINHAS:
        return {"ok": False, "erro": "cheat grande demais."}
    if arq.is_file():
        try:
            pre, blocos = _ler_blocos(arq.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            return {"ok": False, "erro": f"falha ao ler: {e}"}
    else:
        pre, blocos = [], []
    if any(n == nome for n, _ in blocos):
        return {"ok": False, "erro": f"cheat '{nome}' já existe."}
    if len(blocos) >= CHEATS_MAX_QTD:
        return {"ok": False, "erro": "arquivo cheio (64 cheats)."}
    blocos.append((nome, linhas))
    r = _gravar(arq, pre, blocos)
    if not r.get("ok"):
        return r
    return {"ok": True, "tid": tid, "nome": nome, "linhas": len(linhas)}


def remover_cheat(tid: str, nome: str) -> dict:
    """Remove o bloco. Arquivo vazio é apagado (Azahar ignora ausente)."""
    tid = titulo_ok(tid)
    arq = cheats_path(tid)
    if arq is None:
        return {"ok": False, "erro": "title ID inválido ou sem user/."}
    if not arq.is_file():
        return {"ok": False, "erro": f"sem cheats p/ {tid}."}
    try:
        pre, blocos = _ler_blocos(arq.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return {"ok": False, "erro": f"falha ao ler: {e}"}
    novos = [(n, l) for n, l in blocos if n != nome]
    if len(novos) == len(blocos):
        return {"ok": False, "erro": f"cheat '{nome}' não achado."}
    if not novos and not [l for l in pre if l.strip()]:
        try:
            arq.unlink()
        except OSError as e:
            return {"ok": False, "erro": f"falha ao apagar: {e}"}
        return {"ok": True, "tid": tid, "nome": nome, "apagado": True}
    r = _gravar(arq, pre, novos)
    if not r.get("ok"):
        return r
    return {"ok": True, "tid": tid, "nome": nome}


__all__ = ['CHEAT_MAX_NOME', 'CHEATS_MAX_QTD', 'CHEAT_MAX_LINHAS',
           'titulo_ok', 'cheats_path', 'listar_cheats', 'cheats_ativos',
           'definir_cheat', 'alternar_cheat', 'adicionar_cheat',
           'remover_cheat']
