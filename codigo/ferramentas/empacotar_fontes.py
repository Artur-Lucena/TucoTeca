#!/usr/bin/env python3
"""Entrega reproduzível dos fontes/documentação, independente de Git e dados pessoais."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import stat
import sys
import zipfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
IGNORADAS = {"__pycache__", ".cache", ".build", "historico", ".git", ".provas",
             ".pytest_cache", ".ruff_cache", ".venv"}
RAIZ_ARQUIVOS = {"README.md", "CONTRIBUTING.md", "LICENSE", ".gitignore", ".gitattributes",
                 "BibliotecaHub.bat", "BibliotecaHub.sh", "BibliotecaHubMac.command",
                  "Montar-Universal.bat", "requirements-ui.txt"}
RAIZ_ARQUIVOS.update({"TucoTeca.bat", "VERSION", "CHANGELOG.md", "SECURITY.md",
                      "pyproject.toml", "conftest.py", "requirements-extras.txt"})
EXTENSOES = {"codigo": {".py", ".iss", ".qml"}, "docs": {".md"},
              ".github": {".yml", ".yaml", ".md"}, "midia": {".png", ".jpg", ".jpeg"}}


def _link(path: Path) -> bool:
    st = path.lstat()
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & 0x400)


def listar_fontes(repo: Path = REPO) -> list[Path]:
    """Allowlist explícita: dados/dist/ROMs/cache/atalhos nunca entram."""
    repo = Path(repo)
    arquivos = [repo / nome for nome in RAIZ_ARQUIVOS
                if (repo / nome).is_file() and not _link(repo / nome)]
    for nome, extensoes in EXTENSOES.items():
        base = repo / nome
        if not base.is_dir() or _link(base):
            continue
        for pasta, dirs, nomes in os.walk(base, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in IGNORADAS and not _link(Path(pasta, d)))
            for fn in sorted(nomes):
                path = Path(pasta, fn)
                if (path.suffix.lower() in extensoes or fn == "qmldir") and not _link(path):
                    arquivos.append(path)
    return sorted(arquivos, key=lambda p: p.relative_to(repo).as_posix())


def empacotar_fontes(destino: Path, repo: Path = REPO, revisao: str | None = None) -> dict:
    """Inclui a árvore de trabalho atual, inclusive módulos ainda não commitados."""
    repo, destino = Path(repo), Path(destino)
    if revisao is not None and (len(revisao) != 40 or any(c not in "0123456789abcdef" for c in revisao)):
        raise ValueError("A revisão deve ser o SHA Git completo (40 caracteres hexadecimais).")
    arquivos = listar_fontes(repo)
    if not (repo / "codigo/bib_core.py").is_file():
        raise ValueError("pasta não contém os fontes da TucoTeca")
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Empacotar não deve executar módulos da árvore de entrada.
    sys.path.insert(0, str(REPO / "codigo"))
    from bib_nucleo.arquivos import destino_temporario
    manifesto: dict[str, Any] = {"esquema": 1, "projeto": "TucoTeca", "origem": "árvore de trabalho",
                  "gerado_em": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "arquivos": {}}
    if (repo / "VERSION").is_file():
        manifesto["versao"] = (repo / "VERSION").read_text(encoding="utf-8").strip()
    if revisao is not None:
        manifesto["revisao_git"] = revisao
    with destino_temporario(destino) as tmp, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for path in arquivos:
            relativo = path.relative_to(repo).as_posix()
            dados = path.read_bytes()
            manifesto["arquivos"][relativo] = {"bytes": len(dados),
                                                "sha256": hashlib.sha256(dados).hexdigest()}
            info = zipfile.ZipInfo(relativo)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            modo = 0o755 if path.suffix in (".sh", ".command") else 0o644
            info.external_attr = (stat.S_IFREG | modo) << 16
            out.writestr(info, dados)
        out.writestr("MANIFESTO-FONTES.json", json.dumps(manifesto, ensure_ascii=False, indent=2))
    return {"ok": True, "destino": str(destino), "arquivos": len(arquivos),
            "bytes": destino.stat().st_size}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Empacota fontes para colaboração técnica.")
    ap.add_argument("--saida", type=Path, default=REPO / "dist/fontes/tucoteca-fontes-revisadas.zip")
    ap.add_argument("--revisao", help="SHA completo do checkout limpo/congelado; não valida o Git por conta própria")
    args = ap.parse_args(argv)
    try:
        r = empacotar_fontes(args.saida, revisao=args.revisao)
    except (OSError, ValueError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    print(f"[ok] {r['destino']} — {r['arquivos']} arquivos, {r['bytes'] / 1048576:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
