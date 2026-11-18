#!/usr/bin/env python3
"""Prepara o Python embutido do app (programa/<plataforma>/python).

- windows-x64: "Windows embeddable package (64-bit)" oficial do python.org.
- macos-x64 / macos-arm64: build `install_only` do python-build-standalone
  (o mesmo CPython, relocável, sem depender do Python do sistema).

Baixa o pacote, confere o SHA-256 fixado abaixo, extrai num staging e só
então troca a pasta final. O núcleo é stdlib pura: nada de pip nem
site-packages.

    py -3.14 -B codigo/ferramentas/preparar_runtime_python.py
    python3 codigo/ferramentas/preparar_runtime_python.py --plataforma macos-arm64
    py -3.14 -B codigo/ferramentas/preparar_runtime_python.py --pacote caminho/pacote

Sem `--plataforma`, vale a do SO atual. Para trocar de versão, atualize
VERSAO, PBS_TAG e os SHA-256 juntos (python.org: página da release;
python-build-standalone: campo `digest` dos assets da release).
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_utils import baixar_verificado, sha_arquivo  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
VERSAO = "3.14.10"
PBS_TAG = "20261026"
_PBS = ("https://github.com/astral-sh/python-build-standalone/releases/download/"
        f"{PBS_TAG}/cpython-{VERSAO}+{PBS_TAG}-{{alvo}}-install_only.tar.gz")
PLATAFORMAS = {
    "windows-x64": {
        "url": f"https://www.python.org/ftp/python/{VERSAO}/python-{VERSAO}-embed-amd64.zip",
        "sha256": "90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159",
        "exe": "python.exe",
    },
    "macos-x64": {
        "url": _PBS.format(alvo="x86_64-apple-darwin"),
        "sha256": "01cedae5d4a66ac570e13cb35fa570d0e79ba8e9affd4518a5d85b6c2b98ff10",
        "exe": "bin/python3",
    },
    "macos-arm64": {
        "url": _PBS.format(alvo="aarch64-apple-darwin"),
        "sha256": "30a18bcb9ab75e485b4bf4e5d783dde165571e7e42c56dff47a2d2c5345183a4",
        "exe": "bin/python3",
    },
}
# compat: o preparador nasceu só para Windows
SHA256 = PLATAFORMAS["windows-x64"]["sha256"]
URL = PLATAFORMAS["windows-x64"]["url"]
CACHE = REPO / "codigo/ferramentas/.cache"
MARCADOR = "TUCOTECA-RUNTIME.json"


def plataforma_atual() -> str:
    if sys.platform == "darwin":
        return "macos-arm64" if platform.machine().lower() in ("arm64", "aarch64") else "macos-x64"
    return "windows-x64"


def destino_padrao(plataforma: str) -> Path:
    return REPO / "programa" / plataforma / "python"


DESTINO = destino_padrao("windows-x64")


def _inseguro(nome: str) -> bool:
    partes = PurePosixPath(nome.replace("\\", "/")).parts
    return nome.startswith(("/", "\\")) or ".." in partes or ":" in nome


def _extrair_zip(pacote: Path, staging: Path) -> None:
    with zipfile.ZipFile(pacote) as z:
        for info in z.infolist():
            if _inseguro(info.filename):
                raise ValueError(f"caminho inseguro no pacote: {info.filename!r}")
        z.extractall(staging)


def _extrair_tar(pacote: Path, staging: Path) -> None:
    """install_only: tudo sob `python/`; links simbólicos ficam (bin/python3 → python3.14)."""
    with tarfile.open(pacote, "r:gz") as t:
        membros = t.getmembers()
        for m in membros:
            if _inseguro(m.name):
                raise ValueError(f"caminho inseguro no pacote: {m.name!r}")
            if PurePosixPath(m.name).parts[:1] != ("python",):
                raise ValueError(f"pacote fora do formato install_only: {m.name!r}")
        tmp = staging / ".tar"
        # filtro 'data' (3.12+): recusa links para fora, dispositivos e setuid
        t.extractall(tmp, filter="data")
    for item in (tmp / "python").iterdir():
        item.rename(staging / item.name)
    shutil.rmtree(tmp)


def instalar(pacote: Path, destino: Path | None = None, sha256: str | None = None,
             plataforma: str = "windows-x64") -> dict:
    """Extrai o pacote conferido em `destino` (troca atômica por renomeação)."""
    info = PLATAFORMAS[plataforma]
    sha256 = sha256 or info["sha256"]
    pacote = Path(pacote)
    destino = Path(destino) if destino is not None else destino_padrao(plataforma)
    obtido = sha_arquivo(pacote)
    if obtido != sha256:
        raise ValueError(f"SHA-256 divergente: esperado {sha256}, obtido {obtido}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".python-staging-", dir=destino.parent))
    try:
        if plataforma.startswith("windows"):
            _extrair_zip(pacote, staging)
        else:
            _extrair_tar(pacote, staging)
        exe = staging / info["exe"]
        if not (exe.is_file() or exe.is_symlink()):
            raise ValueError(f"pacote sem {info['exe']}: não é o runtime de {plataforma}")
        (staging / MARCADOR).write_text(json.dumps(
            {"versao": VERSAO, "plataforma": plataforma, "origem": info["url"],
             "sha256_zip": sha256}, indent=2) + "\n", encoding="utf-8")
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
    return {"ok": True, "versao": VERSAO, "plataforma": plataforma, "destino": str(destino)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plataforma", choices=sorted(PLATAFORMAS), default=plataforma_atual())
    ap.add_argument("--pacote", "--zip", type=Path, dest="pacote",
                    help="pacote já baixado (pula o download)")
    ap.add_argument("--destino", type=Path)
    args = ap.parse_args(argv)
    info = PLATAFORMAS[args.plataforma]
    nome = info["url"].rsplit("/", 1)[-1].replace("%2B", "+")
    try:
        pacote = args.pacote or baixar_verificado(info["url"], nome, CACHE,
                                                  sha256=info["sha256"], minimo=5_000_000)
        r = instalar(pacote, args.destino, plataforma=args.plataforma)
    except (OSError, ValueError, zipfile.BadZipFile, tarfile.TarError) as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        return 1
    print(f"[ok] Python {r['versao']} ({r['plataforma']}) embutido em {r['destino']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
