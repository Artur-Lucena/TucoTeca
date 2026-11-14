#!/usr/bin/env python3
"""Prepara o Python embutido do instalador (programa/windows-x64/python).

Baixa o "Windows embeddable package (64-bit)" oficial do python.org, confere
o SHA-256 fixado abaixo (publicado na página da release), extrai num staging
e só então troca a pasta final. O núcleo é stdlib pura, então o pacote
embeddable basta: nada de pip nem site-packages.

    py -3.14 -B codigo/ferramentas/preparar_runtime_python.py
    py -3.14 -B codigo/ferramentas/preparar_runtime_python.py --zip caminho/python-embed.zip

Para trocar de versão, atualize VERSAO e SHA256 juntos, copiando o hash da
página https://www.python.org/downloads/release/python-<versao>/.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_utils import baixar_verificado, sha_arquivo  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
VERSAO = "3.14.10"
SHA256 = "90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159"
URL = f"https://www.python.org/ftp/python/{VERSAO}/python-{VERSAO}-embed-amd64.zip"
NOME = f"python-{VERSAO}-embed-amd64.zip"
CACHE = REPO / "codigo/ferramentas/.cache"
DESTINO = REPO / "programa/windows-x64/python"
MARCADOR = "TUCOTECA-RUNTIME.json"


def instalar(zip_path: Path, destino: Path = DESTINO, sha256: str = SHA256) -> dict:
    """Extrai o embeddable conferido em `destino` (troca atômica por renomeação)."""
    zip_path, destino = Path(zip_path), Path(destino)
    obtido = sha_arquivo(zip_path)
    if obtido != sha256:
        raise ValueError(f"SHA-256 divergente: esperado {sha256}, obtido {obtido}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".python-staging-", dir=destino.parent))
    try:
        with zipfile.ZipFile(zip_path) as z:
            for info in z.infolist():
                partes = Path(info.filename).parts
                if info.filename.startswith(("/", "\\")) or ".." in partes or ":" in info.filename:
                    raise ValueError(f"caminho inseguro no pacote: {info.filename!r}")
            z.extractall(staging)
        if not (staging / "python.exe").is_file():
            raise ValueError("pacote sem python.exe: não é o embeddable do Windows")
        (staging / MARCADOR).write_text(json.dumps(
            {"versao": VERSAO, "origem": URL, "sha256_zip": sha256}, indent=2) + "\n",
            encoding="utf-8")
        antigo = None
        if destino.exists():
            antigo = destino.with_name(destino.name + ".antigo")
            if antigo.exists():
                shutil.rmtree(antigo)
            destino.rename(antigo)
        staging.rename(destino)
        if antigo is not None:
            shutil.rmtree(antigo, ignore_errors=True)
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    return {"ok": True, "versao": VERSAO, "destino": str(destino)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--zip", type=Path, help="embeddable já baixado (pula o download)")
    ap.add_argument("--destino", type=Path, default=DESTINO)
    args = ap.parse_args(argv)
    try:
        zip_path = args.zip or baixar_verificado(URL, NOME, CACHE, sha256=SHA256, minimo=5_000_000)
        r = instalar(zip_path, args.destino)
    except (OSError, ValueError, zipfile.BadZipFile) as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        return 1
    print(f"[ok] Python {r['versao']} embutido em {r['destino']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
