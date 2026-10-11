"""Cópia/hardlinks seguros: opt-in, não apaga a origem nem toca em destinos existentes."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


def eh_link(p):
    return p.is_symlink() or bool(getattr(p.lstat(), "st_file_attributes", 0) & 0x400)


def copiar_ou_ligar(origem, destino, hardlinks=False):
    origem, destino = Path(origem).absolute(), Path(destino).absolute()
    if not origem.is_dir() or origem == Path(origem.anchor) or eh_link(origem):
        raise ValueError("Escolha uma pasta real de jogo.")
    origem = origem.resolve()
    if destino.exists() or destino.is_symlink():
        raise ValueError("O destino já existe; nada foi alterado.")
    if origem == destino.resolve() or origem in destino.resolve().parents:
        raise ValueError("O destino não pode ficar dentro da origem.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    ligados = copiados = 0
    with tempfile.TemporaryDirectory(dir=destino.parent, prefix=".organizar-") as tmp:
        stage = Path(tmp) / "jogo"
        stage.mkdir()
        for pasta, dirs, arquivos in os.walk(origem, followlinks=False):
            if any(eh_link(Path(pasta, n)) for n in (*dirs, *arquivos)):
                raise ValueError("A origem contém links/junctions; escolha uma pasta sem redirecionamentos.")
            base = stage / Path(pasta).relative_to(origem)
            base.mkdir(parents=True, exist_ok=True)
            for nome in arquivos:
                src, dst = Path(pasta, nome), base / nome
                if hardlinks:
                    try:
                        os.link(src, dst)
                        ligados += 1
                        continue
                    except OSError:
                        pass  # outro volume/FS: cópia, nunca junction silenciosa
                shutil.copy2(src, dst)
                copiados += 1
        if destino.exists():
            raise ValueError("O destino foi criado durante a operação; origem preservada.")
        stage.rename(destino)
    return {"ok": True, "path": str(destino), "hardlinks": ligados, "copiados": copiados,
            "aviso": "Hardlinks compartilham alterações: não são backup." if ligados else "Origem preservada."}
