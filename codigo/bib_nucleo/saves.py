"""Snapshots de saves escolhidos pelo usuário; não adivinha pastas nem move jogos."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from bib_nucleo.arquivos import destino_temporario, gravar_json, ler_json
from bib_nucleo.base import BACKUP_DIR, DADOS_DIR


def chave_jogo(jogo):
    return str(uuid.UUID(str(jogo["uuid"])))


def caminhos_saves(jogo):
    config = ler_json(DADOS_DIR / "saves-config.json", {})
    lista = config.get(chave_jogo(jogo), []) if isinstance(config, dict) else []
    return lista if isinstance(lista, list) and all(isinstance(p, str) for p in lista) else []


def configurar_saves(jogo, caminhos):
    if len(caminhos) > 20:
        raise ValueError("Escolha no máximo 20 arquivos ou pastas de saves.")
    validados = []
    for caminho in caminhos:
        p = Path(str(caminho).strip()).expanduser()
        if not p.exists() or _link(p):
            raise ValueError(f"Save ausente ou link: {p}")
        p = p.resolve()
        if p == Path(p.anchor) or p == BACKUP_DIR.resolve() or BACKUP_DIR.resolve() in p.parents:
            raise ValueError("Escolha somente o arquivo/pasta de saves, não uma raiz ou backup.")
        if p.is_dir() and p in BACKUP_DIR.resolve().parents:
            raise ValueError("A pasta de saves não pode conter os próprios backups.")
        if str(p) not in validados:
            validados.append(str(p))
    alvo = DADOS_DIR / "saves-config.json"
    config = ler_json(alvo, {})
    config = config if isinstance(config, dict) else {}
    config[chave_jogo(jogo)] = validados
    gravar_json(alvo, config, backup=True)
    return validados


def _link(p):
    return p.is_symlink() or bool(getattr(p.lstat(), "st_file_attributes", 0) & 0x400)


def _arquivos(base):
    if not base.exists():
        raise ValueError(f"Save não encontrado: {base}")
    if _link(base):
        raise ValueError(f"Link não permitido nos saves: {base}")
    if base.is_file():
        yield base, base.name
        return
    if not base.is_dir():
        raise ValueError(f"Save não encontrado: {base}")
    for pasta, dirs, nomes in os.walk(base, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not _link(Path(pasta, d)))
        for nome in sorted(nomes):
            arq = Path(pasta, nome)
            if not _link(arq) and arq.is_file():
                yield arq, arq.relative_to(base).as_posix()


def snapshot_saves(jogo, manter=10, limite_bytes=5 * 1024 ** 3, *, permitir_ausentes=False):
    caminhos = caminhos_saves(jogo)
    if not caminhos:
        return {"ok": True, "arquivos": 0, "aviso": "Nenhuma pasta de saves configurada para este jogo."}
    raiz = BACKUP_DIR / "saves" / chave_jogo(jogo)
    raiz.mkdir(parents=True, exist_ok=True)
    destino = raiz / f"saves-{datetime.now():%Y%m%d-%H%M%S-%f}.zip"
    manifesto, total = [], 0
    with destino_temporario(destino) as tmp:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for i, caminho in enumerate(caminhos):
                if permitir_ausentes and not Path(caminho).exists():
                    continue
                for arq, rel in _arquivos(Path(caminho)):
                    antes = arq.stat()
                    total += antes.st_size
                    if antes.st_size > 512 * 1024 ** 2 or total > limite_bytes or len(manifesto) >= 100_000:
                        raise ValueError("Snapshot excede o limite de tamanho/arquivos.")
                    nome = f"saves/{i}/{rel}"
                    sha = hashlib.sha256()
                    lidos = 0
                    with arq.open("rb") as src, z.open(nome, "w", force_zip64=True) as dst:
                        for bloco in iter(lambda: src.read(1024 * 1024), b""):
                            lidos += len(bloco)
                            if lidos > antes.st_size or total - antes.st_size + lidos > limite_bytes:
                                raise ValueError("Save cresceu durante o snapshot; tente novamente.")
                            sha.update(bloco)
                            dst.write(bloco)
                    depois = arq.stat()
                    if lidos != antes.st_size or (antes.st_size, antes.st_mtime_ns) != (depois.st_size, depois.st_mtime_ns):
                        raise ValueError(f"Save alterado durante o snapshot: {arq.name}; tente novamente.")
                    manifesto.append({"nome": nome, "bytes": antes.st_size, "sha256": sha.hexdigest()})
            z.writestr("snapshot.json", json.dumps({"esquema": 1, "jogo": chave_jogo(jogo),
                       "titulo": jogo["titulo"], "origens": caminhos,
                       "tipos": ["arquivo" if Path(p).is_file() else "pasta" for p in caminhos],
                       "arquivos": manifesto},
                       ensure_ascii=False, indent=2))
        with zipfile.ZipFile(tmp) as z:
            if z.testzip():
                raise ValueError("Snapshot corrompido; o anterior foi preservado.")
    for antigo in sorted(raiz.glob("saves-*.zip"), reverse=True)[max(1, int(manter)):]:
        try:
            antigo.unlink()
        except OSError:
            pass
    return {"ok": True, "destino": str(destino), "arquivos": len(manifesto), "bytes": total}


def listar_snapshots(jogo):
    raiz = BACKUP_DIR / "saves" / chave_jogo(jogo)
    return [{"nome": p.name, "path": str(p), "bytes": p.stat().st_size}
            for p in sorted(raiz.glob("saves-*.zip"), reverse=True) if p.is_file() and not _link(p)]


def restaurar_snapshot(jogo, arquivo, limite_bytes=5 * 1024 ** 3):
    """Valida identidade, caminhos e SHA antes de tocar em saves; guarda o atual."""
    from bib_nucleo.pacotes import _membro_pacote_ok, destino_seguro
    arquivo = Path(arquivo)
    permitidos = {s["path"] for s in listar_snapshots(jogo)}
    if str(arquivo) not in permitidos or _link(arquivo):
        raise ValueError("Escolha um snapshot local deste jogo.")
    caminhos = caminhos_saves(jogo)
    tarefas, total = [], 0
    with zipfile.ZipFile(arquivo) as z:
        if z.getinfo("snapshot.json").file_size > 8_000_000:
            raise ValueError("Manifesto grande demais.")
        meta = json.loads(z.read("snapshot.json"))
        if not isinstance(meta, dict) or meta.get("esquema") != 1 or meta.get("jogo") != chave_jogo(jogo):
            raise ValueError("O snapshot pertence a outro jogo/versão.")
        if meta.get("origens") != caminhos:
            raise ValueError("Os caminhos de saves mudaram; configure os mesmos caminhos do snapshot antes de restaurar.")
        tipos = meta.get("tipos")
        if tipos is not None and (not isinstance(tipos, list) or len(tipos) != len(caminhos)
                                  or any(t not in ("arquivo", "pasta") for t in tipos)):
            raise ValueError("Tipos de saves inválidos no snapshot.")
        arqs = meta.get("arquivos")
        if not isinstance(arqs, list) or len(arqs) > 100_000:
            raise ValueError("Manifesto inválido.")
        vistos = set()
        if len(z.namelist()) != len(set(z.namelist())):
            raise ValueError("Membros duplicados no snapshot.")
        for item in arqs:
            if (not isinstance(item, dict) or not isinstance(item.get("nome"), str)
                    or not isinstance(item.get("bytes"), int) or item["bytes"] < 0
                    or not isinstance(item.get("sha256"), str)):
                raise ValueError("Registro inválido no snapshot.")
            nome = item["nome"]
            partes = nome.split("/")
            if (len(partes) < 3 or partes[0] != "saves" or not partes[1].isdigit()
                    or _membro_pacote_ok("azahar-user/sdmc/" + "/".join(partes[2:])) != "save"
                    or nome.casefold() in vistos):
                raise ValueError("Caminho inválido no snapshot.")
            vistos.add(nome.casefold())
            i = int(partes[1])
            if i >= len(caminhos):
                raise ValueError("Configure novamente os mesmos arquivos/pastas de saves.")
            base, relativo = Path(caminhos[i]), Path(*partes[2:])
            eh_arquivo = tipos[i] == "arquivo" if tipos is not None else base.is_file()
            if base.exists() and base.is_file() != eh_arquivo:
                raise ValueError("O tipo de save configurado mudou; nada foi restaurado.")
            if eh_arquivo:
                if relativo != Path(base.name):
                    raise ValueError("O arquivo de save configurado não corresponde ao snapshot.")
                dest = destino_seguro(base.parent, base.name)
            else:
                dest = destino_seguro(base, relativo)
            zi = z.getinfo(nome)
            total += zi.file_size
            if zi.file_size > 512 * 1024 ** 2 or total > limite_bytes or zi.file_size != item["bytes"]:
                raise ValueError("Snapshot acima do limite ou com tamanho divergente.")
            with z.open(nome) as src:
                sha = hashlib.sha256()
                for bloco in iter(lambda: src.read(1024 * 1024), b""):
                    sha.update(bloco)
            if sha.hexdigest() != item["sha256"]:
                raise ValueError("SHA-256 divergente no snapshot; saves atuais preservados.")
            tarefas.append((nome, dest))
        # Não poda antes de concluir; o ZIP selecionado continua disponível.
        antes = snapshot_saves(jogo, manter=100_001, limite_bytes=limite_bytes, permitir_ausentes=True)
        for nome, dest in tarefas:
            with destino_temporario(dest) as tmp, z.open(nome) as src, tmp.open("wb") as dst:
                for bloco in iter(lambda: src.read(1024 * 1024), b""):
                    dst.write(bloco)
    return {"ok": True, "arquivos": len(tarefas), "backup_antes": antes.get("destino", "")}


# ---------------------------------------------------------------- galeria
# Galeria local por UUID do jogo; somente imagens, sem scripts ou links.

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
