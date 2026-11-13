#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepara os anexos de uma release: instalador, fontes, notas e checksums.

Fluxo (detalhado em docs/RELEASES.md):

    py -3.14 -B codigo/ferramentas/preparar_runtime_python.py
    npm --prefix codigo/frontends/electron run dist
    py -3.14 -B codigo/ferramentas/preparar_release.py --revisao <SHA> --saida dist/release/v<versao>

Exige checkout limpo no SHA informado, versões coerentes (VERSION,
pyproject.toml e seção no CHANGELOG), o instalador da mesma versão e a
árvore `win-unpacked` sem dados pessoais. Não publica nada: criar a release
no GitHub é um passo posterior e explícito. Recusa sobrescrever entregas.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_utils import sha_arquivo  # noqa: E402
from empacotar_fontes import empacotar_fontes, listar_fontes  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DIST_ELECTRON = REPO / "codigo/frontends/electron/dist"
# Dentro de resources/tucoteca do app instalado só entra código, docs e o
# runtime Python; qualquer coisa com cara de coleção/estado pessoal reprova.
PROIBIDOS = re.compile(
    r"(?i)(^|/)(dados|saves|roms|backups|\.provas|historico)(/|$)"
    r"|\.(db|db-journal|sqlite3?|lnk|sav|dsv|cia|3ds|nds|lock)$")


def ler_versao(repo: Path = REPO) -> str:
    """VERSION manda; pyproject e CHANGELOG precisam concordar."""
    versao = (repo / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", versao):
        raise ValueError(f"VERSION inválido: {versao!r}")
    # regex em vez de tomllib: o projeto ainda suporta Python 3.10
    m = re.search(r'^\[project\][^\[]*?^version\s*=\s*"([^"]+)"',
                  (repo / "pyproject.toml").read_text(encoding="utf-8"), re.M | re.S)
    declarada = m.group(1) if m else None
    if declarada != versao:
        raise ValueError(f"pyproject.toml declara {declarada!r}, VERSION diz {versao!r}")
    pacote = repo / "codigo/frontends/electron/package.json"
    if pacote.is_file():
        npm = json.loads(pacote.read_text(encoding="utf-8")).get("version")
        if npm != versao:
            raise ValueError(f"package.json do Electron declara {npm!r}, VERSION diz {versao!r}")
    if not secao_changelog(repo, versao):
        raise ValueError(f"CHANGELOG.md sem seção [{versao}]")
    return versao


def secao_changelog(repo: Path, versao: str) -> str:
    texto = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(rf"^## \[{re.escape(versao)}\][^\n]*\n(.*?)(?=^## \[|\Z)", texto, re.M | re.S)
    return m.group(1).strip() if m else ""


def verificar_revisao(revisao: str, repo: Path = REPO) -> None:
    """Exige HEAD limpo na revisão informada e fontes todos rastreados."""
    if not re.fullmatch(r"[0-9a-f]{40}", revisao):
        raise ValueError("--revisao deve ser o SHA Git completo (40 caracteres hexadecimais).")

    def git(*args: str) -> str:
        r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True,
                           encoding="utf-8", timeout=30)
        if r.returncode:
            raise ValueError(f"git {args[0]} falhou: {r.stderr.strip()}")
        return r.stdout

    if git("status", "--porcelain", "--untracked-files=all").strip():
        raise ValueError("a árvore de trabalho não está limpa; congele os fontes antes")
    head = git("rev-parse", "HEAD").strip()
    if head != revisao:
        raise ValueError(f"HEAD ({head[:7]}) não é a revisão informada ({revisao[:7]})")
    rastreados = set(git("ls-files", "-z").split("\0"))
    extras = {p.relative_to(repo).as_posix() for p in listar_fontes(repo)} - rastreados
    if extras:
        raise ValueError("fontes não rastreados pelo Git: " + ", ".join(sorted(extras)))


def localizar_instalador(dist: Path, versao: str) -> Path:
    instalador = dist / f"TucoTeca-Setup-{versao}-x64.exe"
    if not instalador.is_file():
        outros = sorted(p.name for p in dist.glob("TucoTeca-Setup-*.exe")) if dist.is_dir() else []
        raise ValueError(f"instalador {instalador.name} ausente em {dist}"
                         + (f" (há: {', '.join(outros)})" if outros else
                            "; rode `npm --prefix codigo/frontends/electron run dist`"))
    return instalador


def conferir_app(dist: Path, exigir_runtime: bool = True) -> dict:
    """Confere a árvore win-unpacked que gerou o instalador."""
    recursos = dist / "win-unpacked" / "resources" / "tucoteca"
    if not recursos.is_dir():
        raise ValueError(f"{recursos} ausente: o instalador não veio do build atual")
    for obrigatorio in ("codigo/frontends/ponte.py", "codigo/frontends/ponte_paridade.py",
                        "codigo/bib_core.py",
                        "codigo/ferramentas/abrir_hub.py", "VERSION", "LICENSE"):
        if not (recursos / obrigatorio).is_file():
            raise ValueError(f"app empacotado sem {obrigatorio}")
    proibidos = sorted(p.relative_to(recursos).as_posix() for p in recursos.rglob("*")
                       if p.is_file() and PROIBIDOS.search(p.relative_to(recursos).as_posix()))
    if proibidos:
        raise ValueError("estado pessoal no app empacotado: " + ", ".join(proibidos[:10]))
    python = recursos / "programa/windows-x64/python/python.exe"
    if exigir_runtime and not python.is_file():
        raise ValueError("app empacotado sem Python embutido (use --sem-runtime para aceitar)")
    versao_runtime = None
    marcador = python.parent / "TUCOTECA-RUNTIME.json"
    if marcador.is_file():
        versao_runtime = json.loads(marcador.read_text(encoding="utf-8")).get("versao")
    return {"python_embutido": python.is_file(), "python_versao": versao_runtime,
            "versao_app": (recursos / "VERSION").read_text(encoding="utf-8").strip()}


NOTAS = """# TucoTeca {versao}

Revisão `{revisao}` · {data}

## Instalação (Windows 10/11, 64 bits)

1. Baixe `{instalador}`.
2. Execute-o e escolha a pasta (instala só para o seu usuário, sem admin).
3. Abra o TucoTeca pelo atalho do Menu Iniciar ou da Área de Trabalho.

A coleção fica em `Documentos\\TucoTeca` (ou em `BIBLIOTECA_HOME`, se
definido) e **não** é apagada ao atualizar ou desinstalar.

O instalador não é assinado: na primeira execução o Windows SmartScreen pode
avisar ("O Windows protegeu o computador" → "Mais informações" →
"Executar assim mesmo"). Confira o SHA-256 em `SHA256SUMS.txt` antes.
{aviso_runtime}
## Novidades

{novidades}
"""


def escrever_notas(destino: Path, versao: str, revisao: str, instalador: str,
                   novidades: str, app: dict) -> Path:
    aviso = "" if app["python_embutido"] else (
        "\n**Atenção:** este build não embute Python; é preciso ter o Python 3.14 "
        "instalado (`py -3.14`).\n")
    texto = NOTAS.format(versao=versao, revisao=revisao, instalador=instalador,
                         data=datetime.date.today().isoformat(), aviso_runtime=aviso,
                         novidades=novidades or "Veja CHANGELOG.md.")
    caminho = destino / "NOTAS-RELEASE.md"
    caminho.write_text(texto, encoding="utf-8")
    return caminho


def _ativo(p: Path) -> dict:
    return {"bytes": p.stat().st_size, "sha256": sha_arquivo(p)}


def preparar(revisao: str, saida: Path, *, repo: Path = REPO, dist: Path = DIST_ELECTRON,
             exigir_runtime: bool = True, conferir_git: bool = True) -> dict:
    saida = Path(saida).resolve()
    if saida.exists():
        raise ValueError(f"{saida} já existe; entregas antigas não são sobrescritas")
    if conferir_git:
        verificar_revisao(revisao, repo)
    versao = ler_versao(repo)
    instalador = localizar_instalador(dist, versao)
    app = conferir_app(dist, exigir_runtime)
    if app["versao_app"] != versao:
        raise ValueError(f"app empacotado é {app['versao_app']}, VERSION é {versao}; refaça o dist")

    saida.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{saida.name}-", dir=saida.parent))
    try:
        shutil.copy2(instalador, staging / instalador.name)
        empacotar_fontes(staging / f"tucoteca-{versao}-fontes.zip", repo=repo, revisao=revisao)
        escrever_notas(staging, versao, revisao, instalador.name,
                       secao_changelog(repo, versao), app)
        anexos = {p.name: _ativo(p) for p in sorted(staging.iterdir())}
        release = {"esquema": 2, "projeto": "TucoTeca", "versao": versao, "revisao": revisao,
                   "gerado_em": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "plataforma": "windows-x64", "instalador": instalador.name,
                   "python_embutido": app["python_embutido"],
                   "python_versao": app["python_versao"], "anexos": anexos}
        (staging / "release.json").write_text(
            json.dumps(release, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        linhas = [f"{sha_arquivo(p)}  {p.name}" for p in sorted(staging.iterdir())]
        (staging / "SHA256SUMS.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
        staging.rename(saida)
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    return {"ok": True, "saida": str(saida), "versao": versao,
            "anexos": sorted(p.name for p in saida.iterdir())}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--revisao", required=True, help="SHA completo do commit congelado")
    ap.add_argument("--saida", type=Path, required=True, help="pasta nova, ex.: dist/release/v1.2.0")
    ap.add_argument("--dist", type=Path, default=DIST_ELECTRON, help="saída do electron-builder")
    ap.add_argument("--sem-runtime", action="store_true",
                    help="aceita app sem Python embutido (fica avisado nas notas)")
    args = ap.parse_args(argv)
    try:
        r = preparar(args.revisao, args.saida, dist=args.dist, exigir_runtime=not args.sem_runtime)
    except (OSError, ValueError) as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        return 1
    print(f"[ok] release {r['versao']} em {r['saida']}")
    for nome in r["anexos"]:
        print(f"     {nome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
