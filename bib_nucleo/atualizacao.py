"""Atualização transacional do runtime; user/ nunca faz parte da troca.

A cópia anterior e um diário persistente permitem recuperar uma interrupção.
Rollback só é anunciado após comparação de todos os arquivos por SHA-256.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

VERSAO = "versao-azahar.txt"
DIARIO = "transacao.json"


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def _arquivos(raiz: Path) -> dict[str, Path]:
    out = {}
    if not raiz.exists():
        return out
    for pasta, dirs, nomes in os.walk(raiz):
        if Path(pasta) == raiz:
            dirs[:] = [d for d in dirs if d.casefold() != "user"]
        for nome in [*dirs, *nomes]:
            if (Path(pasta) / nome).is_symlink():
                raise ValueError("Runtime com links simbólicos: atualização cancelada")
        for nome in nomes:
            p = Path(pasta) / nome
            out[p.relative_to(raiz).as_posix()] = p
    return out


def _manifesto(raiz: Path) -> dict[str, str]:
    return {n: _sha(p) for n, p in _arquivos(raiz).items()}


def _json_atomico(p: Path, dados):
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def _copiar(orig: Path, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".hub-tmp")
    try:
        shutil.copy2(orig, tmp)
        tmp.replace(dest)
    finally:
        if tmp.exists():
            tmp.unlink()


def recuperar(dest: Path) -> dict:
    """Recupera apenas transações pendentes. Preserva backup se houver erro."""
    anterior = dest.with_name(dest.name + ".anterior")
    diario = anterior / DIARIO
    if not diario.is_file():
        return {"ok": True, "recuperado": False}
    try:
        estado = json.loads(diario.read_text(encoding="utf-8"))
        if estado["estado"] != "pendente":
            return {"ok": True, "recuperado": False}
        esperados = estado["arquivos"]
        orig = anterior / "runtime"
        if _manifesto(orig) != esperados:
            raise OSError("backup anterior incompleto; restauração automática interrompida")
        dest.mkdir(parents=True, exist_ok=True)
        for nome, arq in _arquivos(dest).items():
            if nome not in esperados:
                arq.unlink()
        for nome, arq in _arquivos(orig).items():
            _copiar(arq, dest / nome)
        if _manifesto(dest) != esperados:
            raise OSError("arquivos restaurados não correspondem ao backup")
        estado["estado"] = "restaurado"
        _json_atomico(diario, estado)
        return {"ok": True, "recuperado": True, "anterior": str(anterior)}
    except (OSError, ValueError, KeyError) as e:
        return {"ok": False, "recuperado": False, "anterior": str(anterior),
                "erro": f"Recuperação incompleta: {e}. Backup preservado em {anterior}"}


def _aplicar(stage: Path, dest: Path, tag: str) -> dict:
    anterior = dest.with_name(dest.name + ".anterior")
    recuperacao = recuperar(dest)
    if not recuperacao["ok"]:
        return recuperacao
    dest.parent.mkdir(parents=True, exist_ok=True)
    # O backup fica completo antes da primeira alteração no runtime.
    with tempfile.TemporaryDirectory(prefix=".azahar-backup-", dir=dest.parent) as tmp:
        backup = Path(tmp)
        runtime = backup / "runtime"
        runtime.mkdir()
        antigos = _manifesto(dest)
        for nome, arq in _arquivos(dest).items():
            _copiar(arq, runtime / nome)
        if _manifesto(runtime) != antigos:
            raise OSError("backup não conferiu; instalação atual preservada")
        estado = {"estado": "pendente", "tag": tag, "arquivos": antigos}
        _json_atomico(backup / DIARIO, estado)
        if anterior.exists():
            shutil.rmtree(anterior)
        backup.rename(anterior)
    try:
        dest.mkdir(parents=True, exist_ok=True)
        novos = _manifesto(stage)
        # Avisos/licenças locais e marcador portátil sobrevivem ao update.
        preservados = {n: h for n, h in antigos.items()
                       if Path(n).name in ("COPYING.txt", "FONTE.txt", "portable.txt")
                       and n not in novos}
        for nome, arq in _arquivos(dest).items():
            if nome not in novos and nome not in preservados:
                arq.unlink()
        for nome, arq in _arquivos(stage).items():
            _copiar(arq, dest / nome)
        if _manifesto(dest) != {**novos, **preservados}:
            raise OSError("verificação final do runtime falhou")
        estado["estado"] = "concluido"
        _json_atomico(anterior / DIARIO, estado)
        return {"ok": True, "anterior": str(anterior) if antigos else None}
    except Exception as e:
        r = recuperar(dest)
        detalhe = "versão anterior restaurada e verificada" if r["ok"] else r["erro"]
        return {"ok": False, "restaurado": r["ok"], "anterior": str(anterior),
                "erro": f"Atualização falhou: {e}; {detalhe}"}


def instalar(info: dict, dest: Path, progresso=None, plataforma=None,
               exe_nomes=("azahar.exe",), deps=("Qt6Core.dll", "Qt6Gui.dll",
               "plugins/platforms/qwindows.dll"), renomear_exe=None,
               versao_nome=VERSAO) -> dict:
    plataforma = plataforma or os.name
    url, tag = info.get("url"), str(info.get("tag") or "").strip()
    if not url or not tag:
        return {"ok": False, "erro": "release inválido (sem URL/tag)"}
    rec = recuperar(dest)
    if not rec["ok"]:
        return rec
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".azahar-stage-", dir=dest.parent) as tmp:
            tmp = Path(tmp)
            pacote = tmp / "download"
            h = hashlib.sha256()
            feito = 0
            with urllib.request.urlopen(url, timeout=60) as r, pacote.open("wb") as f:
                total = int(r.headers.get("Content-Length") or info.get("size") or 0)
                for bloco in iter(lambda: r.read(256 * 1024), b""):
                    f.write(bloco); h.update(bloco); feito += len(bloco)
                    if progresso:
                        progresso(feito, total)
            if info.get("size") and feito != info["size"]:
                raise ValueError("tamanho divergente no download")
            if info.get("sha256") and h.hexdigest() != info["sha256"].lower():
                raise ValueError("sha256 divergente (arquivo descartado)")
            stage = tmp / "nova"
            stage.mkdir()
            if plataforma == "nt":
                with zipfile.ZipFile(pacote) as z:
                    for i in z.infolist():
                        partes = PurePosixPath(i.filename.replace("\\", "/")).parts
                        if (not partes or ".." in partes or i.filename.startswith(("/", "\\"))
                                or any(":" in p or p.casefold() == "user" for p in partes)):
                            raise ValueError("pacote contém caminho inválido ou dados de usuário")
                    z.extractall(stage)
                import fnmatch
                candidatas = [stage, *(p for p in stage.iterdir() if p.is_dir())]
                achado = None
                for cand in candidatas:
                    for pat in exe_nomes:
                        alvos = sorted(cand.glob(pat)) if any(c in pat for c in "*?[") else ([cand / pat] if (cand / pat).is_file() else [])
                        if alvos:
                            achado = (cand, alvos[0])
                            break
                    if achado:
                        break
                if achado is None:
                    raise ValueError(f"executável não encontrado no pacote ({'/'.join(exe_nomes)})")
                raiz, exe_baixado = achado
                stage = raiz
                nome_exe, assinatura = exe_baixado.name, b"MZ"
                for dep in deps:
                    if not (stage / dep).is_file() or not (stage / dep).stat().st_size:
                        raise ValueError(f"dependência ausente: {dep}")
                if renomear_exe and exe_baixado.name != renomear_exe:
                    exe_baixado.rename(stage / renomear_exe)
                    nome_exe = renomear_exe
            else:
                nome_exe, assinatura = "azahar.AppImage", b"\x7fELF"
                shutil.copy2(pacote, stage / nome_exe)
                (stage / nome_exe).chmod(0o755)
            exe = stage / nome_exe
            with exe.open("rb") as f:
                if f.read(len(assinatura)) != assinatura or exe.stat().st_size < 10_000_000:
                    raise ValueError("executável inválido no pacote")
            (stage / versao_nome).write_text(tag, encoding="utf-8")
            r = _aplicar(stage, dest, tag)
            if r["ok"]:
                r.update(tag=tag, exe=str(dest / nome_exe), exe_existe=True)
            return r
    except Exception as e:
        return {"ok": False, "erro": f"Atualização cancelada: {type(e).__name__}: {e}"}
