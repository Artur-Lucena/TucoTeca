#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepara os anexos de uma release: instaladores, fontes, notas e checksums.

Fluxo (detalhado em docs/RELEASES.md):

    # no Mac (o CI faz isto e publica as .dmg + conferencia-mac.json como artefato)
    python3 codigo/ferramentas/preparar_runtime_python.py --plataforma macos-arm64
    python3 codigo/ferramentas/preparar_runtime_python.py --plataforma macos-x64
    npm --prefix codigo/frontends/electron run dist:mac
    python3 codigo/ferramentas/preparar_release.py --revisao <SHA> --conferir-mac

    # no Windows
    py -3.14 -B codigo/ferramentas/preparar_runtime_python.py
    npm --prefix codigo/frontends/electron run dist
    py -3.14 -B codigo/ferramentas/preparar_release.py --revisao <SHA> --saida dist/release/v<versao> \
        [--mac <pasta com as .dmg e conferencia-mac.json>]

Exige checkout limpo no SHA informado, versões coerentes (codigo/VERSION,
pyproject.toml e seção em docs/CHANGELOG.md), os instaladores da mesma versão
e as árvores dos apps sem dados pessoais. As .dmg só entram com a conferência
feita no Mac na mesma revisão (SHA-256 conferido aqui). Não publica nada:
criar a release no GitHub é um passo posterior e explícito. Recusa
sobrescrever entregas.
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
    """codigo/VERSION manda; pyproject, package.json e CHANGELOG precisam concordar."""
    versao = (repo / "codigo/VERSION").read_text(encoding="utf-8").strip()
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
    texto = (repo / "docs/CHANGELOG.md").read_text(encoding="utf-8")
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


# pasta do núcleo dentro de cada app que o electron-builder gera
RECURSOS = {
    "windows-x64": "win-unpacked/resources/tucoteca",
    "macos-x64": "mac/TucoTeca.app/Contents/Resources/tucoteca",
    "macos-arm64": "mac-arm64/TucoTeca.app/Contents/Resources/tucoteca",
}
PYTHON_EMBUTIDO = {"windows-x64": "python.exe", "macos-x64": "bin/python3", "macos-arm64": "bin/python3"}
CONFERENCIA_MAC = "conferencia-mac.json"
NOTAS_ARQUIVO = "NOTAS-RELEASE.md"  # corpo da release; não é anexo

# o que o app instalado precisa para abrir a ponte (conferido no app empacotado)
ESSENCIAIS_APP = ("codigo/frontends/ponte.py", "codigo/frontends/ponte_paridade.py",
                  "codigo/frontends/ponte_params.py", "codigo/frontends/ponte_dominios.py",
                  "codigo/frontends/ponte_fontes.py",
                  "codigo/bib_nucleo/__init__.py", "codigo/ferramentas/abrir_hub.py", "codigo/VERSION", "LICENSE")


def conferir_app(dist: Path, exigir_runtime: bool = True, plataforma: str = "windows-x64") -> dict:
    """Confere a árvore do app (win-unpacked ou TucoTeca.app) que gerou o instalador."""
    recursos = dist / RECURSOS[plataforma]
    if not recursos.is_dir():
        raise ValueError(f"{recursos} ausente: o instalador não veio do build atual")
    for obrigatorio in ESSENCIAIS_APP:
        if not (recursos / obrigatorio).is_file():
            raise ValueError(f"app empacotado sem {obrigatorio}")
    proibidos = sorted(p.relative_to(recursos).as_posix() for p in recursos.rglob("*")
                       if p.is_file() and PROIBIDOS.search(p.relative_to(recursos).as_posix()))
    if proibidos:
        raise ValueError("estado pessoal no app empacotado: " + ", ".join(proibidos[:10]))
    pasta_python = recursos / "programa" / plataforma / "python"
    python = pasta_python / PYTHON_EMBUTIDO[plataforma]
    if exigir_runtime and not python.is_file():
        raise ValueError(f"app empacotado ({plataforma}) sem Python embutido "
                         "(use --sem-runtime para aceitar)")
    versao_runtime = None
    marcador = pasta_python / "TUCOTECA-RUNTIME.json"
    if marcador.is_file():
        versao_runtime = json.loads(marcador.read_text(encoding="utf-8")).get("versao")
    return {"python_embutido": python.is_file(), "python_versao": versao_runtime,
            "versao_app": (recursos / "codigo/VERSION").read_text(encoding="utf-8").strip()}


NOTAS = """## Instalar

**Windows 10/11** — baixe `{instalador}` e abra. Ele instala para o seu
usuário e já abre o TucoTeca. Se o Windows avisar que protegeu o computador:
*Mais informações → Executar assim mesmo*.
{secao_mac}
A coleção fica em *Documentos/TucoTeca* e continua lá ao atualizar ou
desinstalar. Para atualizar, é só instalar a versão nova por cima.
{aviso_runtime}
## Novidades

{novidades}

---
Revisão `{revisao}` · {data} · conferir downloads: `SHA256SUMS.txt`
"""

NOTAS_MAC = """
**macOS 13 ou mais novo** — baixe {lista}, abra e arraste o TucoTeca para
*Aplicativos*. Na primeira vez, clique com o botão direito no app → *Abrir*
(no macOS 15 ou mais novo: tente abrir, depois *Ajustes do Sistema →
Privacidade e Segurança → Abrir Mesmo Assim*). O macOS pergunta uma vez
porque o app não é notarizado pela Apple.
"""

ROTULO_ARCH = {"macos-arm64": "Apple Silicon: M1, M2…", "macos-x64": "Intel"}


def escrever_notas(destino: Path, versao: str, revisao: str, instalador: str,
                   novidades: str, app: dict, dmgs: dict | None = None) -> Path:
    """Texto da página da release (vai no corpo, não como anexo)."""
    aviso = "" if app["python_embutido"] else (
        "\n**Atenção:** este build não embute Python; é preciso ter o Python 3.14 "
        "instalado (`py -3.14`).\n")
    secao_mac = ""
    if dmgs:
        opcoes = [f"`{nome}` ({ROTULO_ARCH.get(info['plataforma'], info['plataforma'])})"
                  for nome, info in sorted(dmgs.items())]
        secao_mac = NOTAS_MAC.format(lista=" ou ".join(opcoes))
    texto = NOTAS.format(versao=versao, revisao=revisao, instalador=instalador,
                         data=datetime.date.today().isoformat(), aviso_runtime=aviso,
                         secao_mac=secao_mac, novidades=novidades or "Veja docs/CHANGELOG.md.")
    caminho = destino / NOTAS_ARQUIVO
    caminho.write_text(texto, encoding="utf-8")
    return caminho


def _ativo(p: Path) -> dict:
    return {"bytes": p.stat().st_size, "sha256": sha_arquivo(p)}


def dmg_mac(versao: str, arch: str) -> str:
    return f"TucoTeca-{versao}-mac-{arch}.dmg"


def conferir_mac(revisao: str, *, repo: Path = REPO, dist: Path = DIST_ELECTRON,
                 exigir_runtime: bool = True) -> dict:
    """No Mac, depois do `dist:mac`: confere cada .app e grava conferencia-mac.json."""
    if not re.fullmatch(r"[0-9a-f]{40}", revisao):
        raise ValueError("--revisao deve ser o SHA Git completo (40 caracteres hexadecimais).")
    versao = ler_versao(repo)
    dmgs = {}
    for arch in ("arm64", "x64"):
        dmg = dist / dmg_mac(versao, arch)
        if not dmg.is_file():
            continue
        plataforma = f"macos-{arch}"
        app = conferir_app(dist, exigir_runtime, plataforma)
        if app["versao_app"] != versao:
            raise ValueError(f"{dmg.name}: app empacotado é {app['versao_app']}, VERSION é {versao}")
        dmgs[dmg.name] = {"plataforma": plataforma, **_ativo(dmg),
                          "python_embutido": app["python_embutido"], "python_versao": app["python_versao"]}
    if not dmgs:
        raise ValueError(f"nenhuma {dmg_mac(versao, '<arch>')} em {dist}; rode `npm run dist:mac`")
    conferencia = {"versao": versao, "revisao": revisao, "dmgs": dmgs}
    (dist / CONFERENCIA_MAC).write_text(json.dumps(conferencia, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
    return conferencia


def ler_conferencia_mac(pasta: Path, versao: str, revisao: str, exigir_runtime: bool = True) -> dict:
    """As .dmg trazidas do Mac: mesma versão e revisão, e SHA-256 igual ao conferido lá."""
    arquivo = Path(pasta) / CONFERENCIA_MAC
    try:
        conferencia = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError) as erro:
        raise ValueError(f"{arquivo} ilegível ou ausente: {erro}") from erro
    if conferencia.get("versao") != versao or conferencia.get("revisao") != revisao:
        raise ValueError(f"conferência do Mac é de {conferencia.get('versao')} @ "
                         f"{str(conferencia.get('revisao'))[:7]}, a release é {versao} @ {revisao[:7]}")
    dmgs = conferencia.get("dmgs") or {}
    if not dmgs:
        raise ValueError("conferência do Mac sem .dmg")
    for nome, info in dmgs.items():
        dmg = Path(pasta) / nome
        if not dmg.is_file():
            raise ValueError(f"{nome} ausente em {pasta}")
        if sha_arquivo(dmg) != info.get("sha256"):
            raise ValueError(f"{nome} não é a .dmg conferida no Mac (SHA-256 diferente)")
        if exigir_runtime and not info.get("python_embutido"):
            raise ValueError(f"{nome} sem Python embutido (use --sem-runtime para aceitar)")
    return dmgs


def preparar(revisao: str, saida: Path, *, repo: Path = REPO, dist: Path = DIST_ELECTRON,
             exigir_runtime: bool = True, conferir_git: bool = True, mac: Path | None = None) -> dict:
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
    dmgs = ler_conferencia_mac(Path(mac), versao, revisao, exigir_runtime) if mac else {}

    saida.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{saida.name}-", dir=saida.parent))
    try:
        shutil.copy2(instalador, staging / instalador.name)
        for nome in dmgs:
            shutil.copy2(Path(mac) / nome, staging / nome)  # type: ignore[arg-type]
        empacotar_fontes(staging / f"tucoteca-{versao}-fontes.zip", repo=repo, revisao=revisao)
        escrever_notas(staging, versao, revisao, instalador.name,
                       secao_changelog(repo, versao), app, dmgs)
        anexos = {p.name: _ativo(p) for p in sorted(staging.iterdir()) if p.name != NOTAS_ARQUIVO}
        instaladores = {instalador.name: {"plataforma": "windows-x64",
                                          "python_embutido": app["python_embutido"],
                                          "python_versao": app["python_versao"]}}
        instaladores.update({nome: {k: info[k] for k in ("plataforma", "python_embutido", "python_versao")}
                             for nome, info in dmgs.items()})
        release = {"esquema": 3, "projeto": "TucoTeca", "versao": versao, "revisao": revisao,
                   "gerado_em": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "instaladores": instaladores,
                   "python_embutido": app["python_embutido"],
                   "python_versao": app["python_versao"], "anexos": anexos}
        (staging / "release.json").write_text(
            json.dumps(release, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        linhas = [f"{sha_arquivo(p)}  {p.name}" for p in sorted(staging.iterdir())
                  if p.name != NOTAS_ARQUIVO]
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
    ap.add_argument("--saida", type=Path, help="pasta nova, ex.: dist/release/v1.2.0")
    ap.add_argument("--dist", type=Path, default=DIST_ELECTRON, help="saída do electron-builder")
    ap.add_argument("--mac", type=Path, help="pasta com as .dmg e o conferencia-mac.json do Mac")
    ap.add_argument("--conferir-mac", action="store_true",
                    help="no Mac: confere os .app e grava conferencia-mac.json em --dist")
    ap.add_argument("--sem-runtime", action="store_true",
                    help="aceita app sem Python embutido (fica avisado nas notas)")
    args = ap.parse_args(argv)
    try:
        if args.conferir_mac:
            c = conferir_mac(args.revisao, dist=args.dist, exigir_runtime=not args.sem_runtime)
            for nome, info in c["dmgs"].items():
                print(f"[ok] {nome} ({info['plataforma']}, Python {info['python_versao']})")
            return 0
        if args.saida is None:
            raise ValueError("--saida é obrigatório (ou use --conferir-mac)")
        r = preparar(args.revisao, args.saida, dist=args.dist, exigir_runtime=not args.sem_runtime,
                     mac=args.mac)
    except (OSError, ValueError) as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        return 1
    print(f"[ok] release {r['versao']} em {r['saida']}")
    for nome in r["anexos"]:
        print(f"     {nome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
