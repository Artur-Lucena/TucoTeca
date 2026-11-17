"""Calendário das séries seguidas (episódios recentes e próximos) a partir do meta salvo."""
from __future__ import annotations

import datetime as dt
import json
import sqlite3

from bib_nucleo.midia.banco import garantir_tabelas_midia, progresso


def _data(texto) -> dt.date | None:
    try:
        return dt.datetime.fromisoformat(str(texto).replace("Z", "+00:00")).date()
    except (TypeError, ValueError):
        return None


def calendario(con: sqlite3.Connection, hoje: dt.date | None = None, antes: int = 14, depois: int = 60) -> list[dict]:
    """Episódios das séries seguidas com estreia entre hoje−`antes` e hoje+`depois`."""
    garantir_tabelas_midia(con)
    hoje = hoje or dt.date.today()
    saida = []
    for r in con.execute("SELECT imdb_id, nome, poster, meta_json FROM midia_titulos WHERE seguindo=1"):
        try:
            videos = json.loads(r["meta_json"] or "{}").get("videos") or []
        except ValueError:
            continue
        for v in videos:
            if not isinstance(v, dict) or not v.get("season"):
                continue
            quando = _data(v.get("released"))
            if quando is None or not (hoje - dt.timedelta(days=antes) <= quando <= hoje + dt.timedelta(days=depois)):
                continue
            saida.append({"imdb_id": r["imdb_id"], "serie": r["nome"], "poster": r["poster"],
                          "chave": f"{r['imdb_id']}:{int(v['season'])}:{int(v.get('episode') or 0)}",
                          "temporada": int(v["season"]), "episodio": int(v.get("episode") or 0),
                          "nome": str(v.get("name") or v.get("title") or ""), "data": quando.isoformat(),
                          "lancado": quando <= hoje})
    vistos = progresso(con, [e["chave"] for e in saida])
    for e in saida:
        e["assistido"] = bool(vistos.get(e["chave"], {}).get("assistido"))
    saida.sort(key=lambda e: (e["data"], e["serie"], e["temporada"], e["episodio"]))
    return saida


__all__ = ["calendario"]
