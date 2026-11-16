"""Casa arquivos indexados com títulos do Cinemeta (nome + ano + tipo → id IMDb).

Uma busca por grupo (mesmo nome/ano/tipo), pontuação 0–1 e limiar 0,85:
abaixo disso o arquivo vai para "Revisar correspondência" com a melhor
sugestão. Correções manuais (`manual=1`) nunca são refeitas.
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from difflib import SequenceMatcher

from bib_nucleo.midia.banco import garantir_tabelas_midia, gravar_titulo

LIMIAR = 0.85


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFD", str(texto or "").casefold())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.replace("&", " and ")
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"^(the|a|an|o|a|os|as)\s+", "", t.strip())
    return re.sub(r"\s+", " ", t).strip()


def pontuar(nome_lido: str, ano_lido, candidato: dict, posicao: int = 0) -> float:
    """Semelhança do nome + ano batendo (±1) − pequena penalidade por posição na busca."""
    a, b = _norm(nome_lido), _norm(candidato.get("name") or "")
    if not a or not b:
        return 0.0
    nome = 1.0 if a == b else SequenceMatcher(None, a, b).ratio()
    ano_c = re.match(r"\d{4}", str(candidato.get("releaseInfo") or candidato.get("year") or ""))
    if ano_lido and ano_c:
        diff = abs(int(ano_lido) - int(ano_c.group(0)))
        ano = 0.15 if diff == 0 else 0.05 if diff == 1 else -0.25
    else:
        ano = 0.0
    return max(0.0, min(1.0, nome * 0.9 + ano + 0.1 - 0.03 * posicao))


def melhor_candidato(nome_lido: str, ano_lido, candidatos: list[dict]) -> tuple[dict | None, float]:
    melhor, nota = None, 0.0
    for i, c in enumerate(candidatos[:8]):
        n = pontuar(nome_lido, ano_lido, c, i)
        if n > nota:
            melhor, nota = c, n
    return melhor, round(nota, 3)


def casar_pendentes(con: sqlite3.Connection, buscar, buscar_meta, ids=None, cancelado=lambda: False) -> dict:
    """Casa os arquivos sem id (ou só `ids`). `buscar(tipo, termo)` e
    `buscar_meta(tipo, imdb)` vêm do Cinemeta (injetados para testar sem rede)."""
    garantir_tabelas_midia(con)
    filtro = "imdb_id IS NULL AND manual=0 AND ausente=0"
    params: list = []
    if ids:
        filtro += f" AND id IN ({','.join('?' * len(ids))})"
        params = list(ids)
    linhas = [dict(r) for r in con.execute(f"SELECT * FROM midia_arquivos WHERE {filtro}", params)]
    grupos: dict[tuple, list[dict]] = {}
    for r in linhas:
        grupos.setdefault((_norm(r["nome_lido"]), r["ano_lido"], r["tipo_lido"]), []).append(r)
    casados = revisar = 0
    titulos: set[tuple[str, str]] = set()
    erros: list[str] = []
    for (_, ano, tipo), itens in grupos.items():
        if cancelado():
            break
        nome = itens[0]["nome_lido"]
        try:
            candidatos = buscar(tipo, nome)
        except ValueError as e:
            erros.append(f"{nome}: {e}")
            continue
        c, nota = melhor_candidato(nome, ano, candidatos)
        imdb = str((c or {}).get("imdb_id") or (c or {}).get("id") or "")
        for r in itens:
            if c is not None and nota >= LIMIAR:
                con.execute("UPDATE midia_arquivos SET imdb_id=?, confianca=?, sugestao='' WHERE id=?",
                            (imdb, nota, r["id"]))
                casados += 1
                titulos.add((tipo, imdb))
            else:
                con.execute("UPDATE midia_arquivos SET confianca=?, sugestao=? WHERE id=?",
                            (nota, imdb, r["id"]))
                revisar += 1
    con.commit()
    for tipo, imdb in titulos:
        if cancelado():
            break
        if con.execute("SELECT 1 FROM midia_titulos WHERE imdb_id=?", (imdb,)).fetchone():
            continue
        try:
            gravar_titulo(con, buscar_meta(tipo, imdb))
        except ValueError as e:
            erros.append(f"{imdb}: {e}")
    return {"casados": casados, "revisar": revisar, "erros": erros}


def corrigir(con: sqlite3.Connection, arquivo_id: int, imdb: str, tipo: str, temporada=None, episodio=None) -> None:
    """Correspondência escolhida pelo usuário (trava contra o casamento automático)."""
    garantir_tabelas_midia(con)
    if not str(imdb).startswith("tt"):
        raise ValueError("Escolha um título do catálogo.")
    if tipo == "series" and (temporada is None or episodio is None):
        raise ValueError("Informe temporada e episódio.")
    con.execute("UPDATE midia_arquivos SET imdb_id=?, tipo_lido=?, temporada=?, episodio=?, confianca=1, "
                "sugestao='', manual=1 WHERE id=?",
                (imdb, tipo, temporada if tipo == "series" else None, episodio if tipo == "series" else None,
                 int(arquivo_id)))
    con.commit()


__all__ = ["LIMIAR", "pontuar", "melhor_candidato", "casar_pendentes", "corrigir"]
