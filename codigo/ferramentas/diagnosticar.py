#!/usr/bin/env python3
"""Diagnóstico somente-leitura: fontes, dependências, mapa de pastas e SQLite."""
from __future__ import annotations

import argparse
import ast
import collections
import importlib.util
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from empacotar_fontes import REPO, listar_fontes


def resumo_fontes(repo: Path = REPO) -> dict:
    grupos = collections.defaultdict(lambda: {"arquivos": 0, "bytes": 0, "linhas_python": 0})
    erros = []
    testes = total_py = 0
    for arq in listar_fontes(repo):
        rel = arq.relative_to(repo)
        grupo = rel.parent.as_posix()
        dados = arq.read_bytes()
        grupos[grupo]["arquivos"] += 1
        grupos[grupo]["bytes"] += len(dados)
        if arq.suffix != ".py":
            continue
        total_py += 1
        try:
            texto = dados.decode("utf-8-sig")
            grupos[grupo]["linhas_python"] += len(texto.splitlines())
            arvore = ast.parse(texto, filename=str(rel), feature_version=(3, 10))
            compile(arvore, str(rel), "exec")
            testes += sum(isinstance(n, ast.FunctionDef) and n.name.startswith("teste_")
                          for n in arvore.body)
        except SyntaxError as e:
            erros.append(f"{rel}:{e.lineno}: {e.msg}")
        except UnicodeDecodeError as e:
            erros.append(f"{rel}: fonte não está em UTF-8: {e}")
    return {"python": total_py, "testes_descobertos": testes,
            "pastas": dict(sorted(grupos.items())), "erros_sintaxe": erros}


def diagnosticar_banco(db: Path) -> dict:
    """Nunca cria/migra/limpa o banco nem seus backups."""
    db = Path(db)
    if not db.is_file():
        return {"estado": "ausente", "mensagem": "Coleção ainda não criada."}
    try:
        uri = db.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as con:
            con.execute("PRAGMA query_only=ON")
            integridade = [r[0] for r in con.execute("PRAGMA quick_check")]
            tabelas = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            contagens, colunas = {}, {}
            for nome in ("jogos", "musicas", "downloads", "desejos"):
                if nome in tabelas:
                    contagens[nome] = con.execute(f"SELECT COUNT(*) FROM {nome}").fetchone()[0]
                    colunas[nome] = [r[1] for r in con.execute(f"PRAGMA table_info({nome})")]
            return {"estado": "ok" if integridade == ["ok"] else "erro",
                    "integridade": integridade, "contagens": contagens, "colunas": colunas}
    except sqlite3.Error as e:
        return {"estado": "erro", "mensagem": str(e)}


def diagnosticar(repo: Path = REPO, db: Path | None = None) -> dict:
    sys.path.insert(0, str(repo / "codigo"))
    import bib_core as core
    fonte = resumo_fontes(repo)
    ausentes = [n for n in core.__all__ if not hasattr(core, n)]
    deps = {"tkinter": importlib.util.find_spec("tkinter") is not None,
            "pillow_opcional": importlib.util.find_spec("PIL") is not None,
            "ffmpeg": bool(core.ffmpeg_pronto()), "yt-dlp": bool(core.ytdlp_pronto()),
            "7z": core.ferramenta_7z() is not None,
            "azahar": bool(core.default_emu_3ds()), "desmume": bool(core.default_emu_nds())}
    banco = diagnosticar_banco(db if db is not None else core.DEFAULT_DB)
    return {"ok": not fonte["erros_sintaxe"] and not ausentes and banco["estado"] != "erro",
            "python": sys.version.split()[0], "plataforma": sys.platform,
            "somente_leitura": True, "fontes": fonte, "exports_ausentes": ausentes,
            "dependencias": deps, "banco": banco}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Diagnóstico local sem alterar a coleção.")
    ap.add_argument("--db", type=Path, help="banco a inspecionar (somente-leitura)")
    ap.add_argument("--json", action="store_true", help="saída estruturada")
    args = ap.parse_args(argv)
    r = diagnosticar(db=args.db)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"TucoTeca — Python {r['python']} / {r['plataforma']} — somente-leitura")
        print(f"Fontes: {r['fontes']['python']} arquivos Python; {r['fontes']['testes_descobertos']} testes")
        for nome, resumo in r["fontes"]["pastas"].items():
            print(f"  {nome:38} {resumo['arquivos']:3} arquivos  {resumo['bytes'] / 1024:7.1f} KB")
        print("Dependências:", ", ".join(f"{k}={'presente' if v else 'ausente'}" for k, v in r["dependencias"].items()))
        print("Banco:", r["banco"].get("estado"), r["banco"].get("contagens", {}))
        for erro in r["fontes"]["erros_sintaxe"] + r["exports_ausentes"]:
            print("ERRO:", erro)
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
