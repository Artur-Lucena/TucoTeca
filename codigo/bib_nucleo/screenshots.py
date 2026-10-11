"""Galeria local por UUID do jogo; somente imagens, sem scripts ou links."""
from pathlib import Path

from bib_nucleo.base import DADOS_DIR
from bib_nucleo.saves import chave_jogo


def pasta_screenshots(jogo):
    pasta = DADOS_DIR / "screenshots" / chave_jogo(jogo)
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def listar_screenshots(jogo, limite=200):
    pasta = pasta_screenshots(jogo)
    arqs = []
    for p in pasta.iterdir():
        if (p.is_file() and not p.is_symlink() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
                and not getattr(p.lstat(), "st_file_attributes", 0) & 0x400):
            arqs.append(p)
    arqs.sort(key=lambda p: p.stat().st_mtime_ns, reverse=True)
    return [{"nome": p.name, "url": p.resolve().as_uri(), "path": str(p)} for p in arqs[:limite]]
