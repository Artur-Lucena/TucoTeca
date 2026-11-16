"""Indexa as pastas de vídeo escolhidas pelo usuário — só lê, nunca copia nem move.

Pula links simbólicos e junções (não seguimos atalhos para fora da pasta),
pastas ocultas/de sistema e arquivos de amostra. O "hash rápido" lê só o
primeiro e o último 1 MB, e só quando tamanho ou data mudaram.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path

from bib_nucleo.base import agora_iso
from bib_nucleo.midia.banco import garantir_tabelas_midia
from bib_nucleo.midia.nomes import eh_video, legendas_vizinhas, ler_nome

BLOCO = 1024 * 1024
PULAR_PASTAS = {"$recycle.bin", "system volume information", "@eadir", ".trash", "sample", "samples",
                "extras", "featurettes", "trailers"}
MIN_BYTES = 20 * 1024 * 1024  # menor que isso é amostra/trailer


def hash_rapido(caminho: Path, tamanho: int) -> str:
    h = hashlib.sha1(str(tamanho).encode())
    with open(caminho, "rb") as f:
        h.update(f.read(BLOCO))
        if tamanho > 2 * BLOCO:
            f.seek(-BLOCO, os.SEEK_END)
            h.update(f.read(BLOCO))
    return h.hexdigest()


def _eh_link(entrada: os.DirEntry) -> bool:
    if entrada.is_symlink():
        return True
    try:
        return Path(entrada.path).is_junction()
    except (OSError, AttributeError):
        return False


def _varrer_disco(raiz: Path, cancelado):
    """Gera (caminho, tamanho, mtime, irmaos) de cada vídeo sob a raiz."""
    pilha = [raiz]
    while pilha:
        if cancelado():
            return
        pasta = pilha.pop()
        try:
            entradas = list(os.scandir(pasta))
        except OSError:
            continue
        nomes = [e.name for e in entradas]
        for e in entradas:
            try:
                if _eh_link(e):
                    continue
                if e.is_dir(follow_symlinks=False):
                    if not e.name.startswith(".") and e.name.casefold() not in PULAR_PASTAS:
                        pilha.append(Path(e.path))
                elif e.is_file(follow_symlinks=False) and eh_video(e.name):
                    st = e.stat(follow_symlinks=False)
                    if st.st_size >= MIN_BYTES and "sample" not in e.name.casefold():
                        yield Path(e.path), st.st_size, st.st_mtime, nomes
            except OSError:
                continue


def indexar_pasta(con: sqlite3.Connection, pasta_id: int, raiz: str, cancelado=lambda: False,
                  progresso=None) -> dict:
    """Atualiza o índice de uma pasta. Devolve contagens e os ids novos/alterados."""
    garantir_tabelas_midia(con)
    raiz_p = Path(raiz)
    if not raiz_p.is_dir():
        con.execute("UPDATE midia_arquivos SET ausente=1 WHERE pasta_id=?", (int(pasta_id),))
        con.commit()
        return {"novos": 0, "alterados": 0, "iguais": 0, "ausentes": -1, "ids": [],
                "aviso": f"Pasta inacessível: {raiz} (os itens ficaram como ausentes)."}
    atuais = {r["caminho"]: dict(r) for r in con.execute(
        "SELECT id, caminho, tamanho, mtime, hash FROM midia_arquivos WHERE pasta_id=?", (int(pasta_id),))}
    vistos: set[str] = set()
    novos = alterados = iguais = 0
    ids: list[int] = []
    for n, (caminho, tamanho, mtime, irmaos) in enumerate(_varrer_disco(raiz_p, cancelado)):
        chave = str(caminho)
        vistos.add(chave)
        legendas = json.dumps([{**leg, "arquivo": str(caminho.parent / leg["arquivo"])}
                               for leg in legendas_vizinhas(chave, irmaos)], ensure_ascii=False)
        velho = atuais.get(chave)
        if velho and velho["tamanho"] == tamanho and abs(float(velho["mtime"]) - mtime) < 1:
            con.execute("UPDATE midia_arquivos SET ausente=0, legendas=? WHERE id=?", (legendas, velho["id"]))
            iguais += 1
            continue
        try:
            dig = hash_rapido(caminho, tamanho)
        except OSError:
            continue
        lido = ler_nome(chave)
        if velho:
            con.execute("UPDATE midia_arquivos SET tamanho=?, mtime=?, hash=?, legendas=?, ausente=0, "
                        "indexado_em=? WHERE id=?", (tamanho, mtime, dig, legendas, agora_iso(), velho["id"]))
            alterados += 1
            ids.append(int(velho["id"]))
        else:
            cur = con.execute(
                "INSERT INTO midia_arquivos(caminho, pasta_id, tamanho, mtime, hash, nome_lido, ano_lido, tipo_lido, "
                "temporada, episodio, legendas, ausente, indexado_em) VALUES (?,?,?,?,?,?,?,?,?,?,?,0,?)",
                (chave, int(pasta_id), tamanho, mtime, dig, lido["titulo"], lido["ano"], lido["tipo"],
                 lido["temporada"], lido["episodio"], legendas, agora_iso()))
            novos += 1
            ids.append(int(cur.lastrowid))
        if progresso and n % 25 == 0:
            progresso(n)
    ausentes = 0
    if not cancelado():
        for caminho, velho in atuais.items():
            if caminho not in vistos:
                con.execute("UPDATE midia_arquivos SET ausente=1 WHERE id=?", (velho["id"],))
                ausentes += 1
    con.commit()
    return {"novos": novos, "alterados": alterados, "iguais": iguais, "ausentes": ausentes, "ids": ids}


__all__ = ["hash_rapido", "indexar_pasta", "MIN_BYTES"]
