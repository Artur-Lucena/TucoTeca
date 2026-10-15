#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepara uma release privada: pacote de fontes, bundles, notas e checksums.

Reúne os artefatos já validados em dist/windows numa pasta nova, confere
integridade e revisão dos fontes e escreve as notas. Não publica nada:
criar a release no GitHub é um passo posterior e explícito.

    py -3.14 codigo/ferramentas/preparar_release.py --revisao <SHA> --saida dist/release/v1.0.1

Exige um checkout limpo no SHA informado, bundles da mesma versão/revisão
e provas na árvore e no ZIP extraído. Recusa sobrescrever entregas antigas.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from build_utils import sha_arquivo
from empacotar_fontes import empacotar_fontes, listar_fontes

REPO = Path(__file__).resolve().parents[2]
WINDOWS_DIR = REPO / "dist/windows"
VARIANTES = ("essencial", "completo")
PROIBIDAS = {"dados", "saves", "roms", "jogos", "programa", "dist", ".provas",
             ".build", ".cache", "historico", "backups", ".git", ".venv",
             ".pytest_cache", ".ruff_cache", "__pycache__"}
PESSOAIS = re.compile(
    r"(?i)\.(db|db-journal|sqlite3?|lnk|zip|7z|rar|exe|dll|pyd|cia|3ds|nds|sav|dsv|"
    r"mp3|mp4|wav|ogg|flac|mkv|webm|png|jpg|jpeg)$")


def _caminho_seguro(rel: str) -> None:
    partes = rel.rstrip("/").split("/")
    if (not rel or "\\" in rel or ":" in rel or any(ord(c) < 32 for c in rel)
            or any(p in ("", ".", "..") for p in partes)):
        raise ValueError(f"caminho inseguro no pacote: {rel!r}")


def _proibido(rel: str) -> bool:
    partes = {x.lower() for x in PurePosixPath(rel).parts}
    return bool(partes & PROIBIDAS) or bool(PESSOAIS.search(rel))


def _entradas_zip(z: zipfile.ZipFile) -> set[str]:
    nomes = set()
    arquivos = set()
    for info in z.infolist():
        _caminho_seguro(info.orig_filename)
        normalizado = info.filename.rstrip("/").casefold()
        if normalizado in nomes or stat.S_ISLNK(info.external_attr >> 16):
            raise ValueError(f"entrada duplicada ou link no ZIP: {info.filename}")
        nomes.add(normalizado)
        if not info.is_dir():
            arquivos.add(info.filename)
    return arquivos


def _conferir_hashes(z: zipfile.ZipFile, arquivos: dict) -> None:
    for rel, info in arquivos.items():
        _caminho_seguro(rel)
        if z.getinfo(rel).file_size != info["bytes"]:
            raise ValueError(f"tamanho divergente de {rel}")
        h = hashlib.sha256()
        with z.open(rel) as f:
            for bloco in iter(lambda: f.read(1024 * 1024), b""):
                h.update(bloco)
        if h.hexdigest() != info["sha256"]:
            raise ValueError(f"hash divergente de {rel}")


def conferir_pacote_fontes(pacote: Path, repo: Path = REPO,
                           revisao: str | None = None, versao: str | None = None) -> dict:
    """Reabre o ZIP de fontes: manifesto, hashes e nada de dado pessoal."""
    with zipfile.ZipFile(pacote) as z:
        nomes = _entradas_zip(z)
        manifesto = json.loads(z.read("MANIFESTO-FONTES.json"))
        if set(nomes) != set(manifesto["arquivos"]) | {"MANIFESTO-FONTES.json"}:
            raise ValueError(f"{pacote.name}: conteúdo difere do manifesto")
        if revisao is not None and manifesto.get("revisao_git") != revisao:
            raise ValueError("pacote de fontes de outra revisão")
        if versao is not None and manifesto.get("versao") != versao:
            raise ValueError("pacote de fontes de outra versão")
        for rel, info in manifesto["arquivos"].items():
            if _proibido(rel):
                raise ValueError(f"{pacote.name}: caminho proibido no pacote: {rel}")
        _conferir_hashes(z, manifesto["arquivos"])
        for rel in manifesto["arquivos"]:
            if not (repo / rel).is_file() or z.read(rel) != (repo / rel).read_bytes():
                raise ValueError(f"{pacote.name}: {rel} difere da árvore de trabalho")
    return {"arquivos": len(manifesto["arquivos"]), "sha256": sha_arquivo(pacote)}


def _sums(variante: str, windows_dir: Path | None = None) -> dict:
    """Lê SHA256SUMS-<variante>.txt publicado pelo builder."""
    base = WINDOWS_DIR if windows_dir is None else Path(windows_dir)
    arq = base / f"SHA256SUMS-{variante}.txt"
    if not arq.is_file():
        raise ValueError(f"faltou {arq.name}; gere os bundles antes de preparar a release")
    somas = {}
    for linha in arq.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        m = re.fullmatch(r"([0-9a-f]{64})  ([^/\\:]+)", linha)
        if not m or m[2] in somas:
            raise ValueError(f"{arq.name}: checksum inválido ou repetido")
        _caminho_seguro(m[2])
        somas[m[2]] = m[1]
    return somas


def _fontes_app(repo: Path) -> dict[str, Path]:
    from montar_portatil import arquivos_app
    esperados = {"app/" + destino: repo / origem for origem, destino in arquivos_app(repo)}
    for origem, destino in (("codigo/bib_nucleo", "bib_nucleo"),
                            ("codigo/frontends/qml", "qml")):
        base = repo / origem
        for p in base.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix not in (".pyc", ".pyo"):
                esperados[f"app/{destino}/{p.relative_to(base).as_posix()}"] = p
    return esperados


def conferir_zip_runtime(pacote: Path, relatorio: dict, revisao: str,
                         versao: str, repo: Path = REPO) -> dict:
    """Confere o ZIP sem executar nem extrair binários: conteúdo, fontes e privacidade."""
    with zipfile.ZipFile(pacote) as z:
        nomes = _entradas_zip(z)
        m = json.loads(z.read("manifesto-runtime.json"))
        v = m["versoes"]
        if (v.get("revisao_git"), v.get("tucoteca"), v.get("extras")) != (
                revisao, versao, relatorio["extras"]):
            raise ValueError(f"{pacote.name}: revisão/versão/variante do manifesto diverge")
        if nomes != set(m["arquivos"]) | {"manifesto-runtime.json"}:
            raise ValueError(f"{pacote.name}: conteúdo difere do manifesto de runtime")
        for nome in nomes:
            partes = {p.lower() for p in PurePosixPath(nome).parts}
            if partes & {"dados", "user", "saves", "roms", "battery", "states", "perfis",
                         ".git", ".provas", "__pycache__"} or re.search(
                    r"(?i)(aes_keys\.txt$|\.(db|sqlite3?|sav|dsv|cia|3ds|nds|lnk)$)", nome):
                raise ValueError(f"{pacote.name}: dado pessoal no runtime: {nome}")
        _conferir_hashes(z, m["arquivos"])
        if z.read("VERSION").decode("utf-8").strip() != versao:
            raise ValueError(f"{pacote.name}: VERSION diverge")
        if revisao not in z.read("VERSAO.txt").decode("utf-8"):
            raise ValueError(f"{pacote.name}: VERSAO.txt não registra a revisão")
        if m.get("componentes") != relatorio.get("componentes"):
            raise ValueError(f"{pacote.name}: componentes divergem do relatório")
        for componente in m["componentes"].values():
            if componente["executavel"] not in nomes or not componente.get("fonte") or not componente.get("licenca"):
                raise ValueError(f"{pacote.name}: componente sem executável, fonte ou licença")
        licencas = {"LICENSE-TucoTeca.txt", "python/LICENSE.txt", "python/LICENSES-Pillow/LICENSE"}
        licencas.update(f"python/LICENSES-Qt/{n}.txt" for n in (
            "LGPL-3.0-only", "GPL-3.0-only", "GPL-2.0-only"))
        if not licencas <= nomes:
            raise ValueError(f"{pacote.name}: textos de licença ausentes")
        esperados = _fontes_app(repo)
        if {n for n in nomes if n.startswith("app/")} != set(esperados):
            raise ValueError(f"{pacote.name}: conjunto de fontes app/ diverge")
        hashes = {}
        for nome, origem in sorted(esperados.items()):
            if z.read(nome) != origem.read_bytes():
                raise ValueError(f"{pacote.name}: fonte diverge da revisão: {nome}")
            hashes[nome.removeprefix("app/")] = m["arquivos"][nome]["sha256"]
        fontes = {"arquivos": len(hashes), "sha256_arvore_app": hashlib.sha256(
            json.dumps(hashes, sort_keys=True).encode()).hexdigest()}
        if fontes != m.get("fontes") or fontes != relatorio.get("fontes"):
            raise ValueError(f"{pacote.name}: hash da árvore app/ diverge")
        addons = {"python/Lib/PySide6/QtWebEngineQuick.pyd", "python/Lib/PySide6/QtMultimedia.pyd"}
        if (relatorio["extras"] == "completo" and not addons <= nomes) or (
                relatorio["extras"] == "essencial" and addons & nomes):
            raise ValueError(f"{pacote.name}: Addons não correspondem à variante")
    return fontes


def conferir_bundles(revisao: str, versao: str, variantes=VARIANTES,
                     windows_dir: Path | None = None, repo: Path = REPO) -> list[dict]:
    """Valida todos os bundles antes de copiar qualquer arquivo para a entrega."""
    windows_dir = WINDOWS_DIR if windows_dir is None else Path(windows_dir)
    ativos = []
    for variante in variantes:
        somas = _sums(variante, windows_dir)
        verificacao = windows_dir / f"superhub-verificacao-{variante}.json"
        rel = json.loads(verificacao.read_text(encoding="utf-8"))
        if rel.get("revisao_git") != revisao:
            raise ValueError(f"bundle {variante} foi gerado de {rel.get('revisao_git') or 'revisão desconhecida'},"
                             f" não de {revisao}; gere os bundles de novo com --revisao")
        if rel.get("tucoteca") != versao or rel.get("extras") != variante:
            raise ValueError(f"bundle {variante}: versão/variante diverge")
        if not isinstance(rel.get("provas"), dict) or not rel["provas"] or not rel.get("arquivos"):
            raise ValueError(f"bundle {variante}: relatório incompleto, sem provas ou arquivos")
        if set(somas) != {a["nome"] for a in rel["arquivos"]}:
            raise ValueError(f"bundle {variante}: lista de checksums diverge")
        entradas = []
        for item in rel["arquivos"]:
            nome, sha = item["nome"], item["sha256"]
            _caminho_seguro(nome)
            if "/" in nome or not nome.endswith(".zip") or nome != f"tucoteca-{versao}-windows-x64-{variante}.zip":
                raise ValueError(f"nome inesperado de bundle: {nome}")
            provas = item.get("provas_extraido")
            if not isinstance(provas, dict) or set(provas) != set(rel["provas"]):
                raise ValueError(f"{nome}: faltam provas do ZIP extraído")
            if somas.get(nome) != sha:
                raise ValueError(f"{nome}: SHA256SUMS-{variante}.txt não bate com a verificação")
            origem = windows_dir / nome
            if not origem.is_file():
                raise ValueError(f"bundle ausente em {windows_dir}: {nome}")
            if origem.stat().st_size != item["bytes"] or sha_arquivo(origem) != sha:
                raise ValueError(f"{nome}: arquivo em dist/windows/ não corresponde ao hash")
            conferir_zip_runtime(origem, rel, revisao, versao, repo)
            entradas.append({"nome": nome, "bytes": item["bytes"], "sha256": sha,
                             "provas_extraido": True})
        fontes = rel.get("fontes", {})
        ativos.append({"variante": variante, "arquivos": entradas,
                       "bytes_runtime": rel["bytes_runtime"], "extras": rel["extras"],
                       "fontes": {"arquivos": fontes.get("arquivos"),
                                  "sha256_arvore_app": fontes.get("sha256_arvore_app")},
                       "provas": sorted(rel["provas"]), "revisao": rel["revisao_git"],
                       "python": rel["python"], "qt": rel["qt"],
                       "componentes": rel["componentes"], "relatorio": verificacao.name})
    return ativos


NOTAS = """# TucoTeca {versao}

Primeira release privada publicada: um hub local para jogos, músicas e vídeos,
sem conta própria ou telemetria. A tag anterior `v1.0.0` foi preservada como
registro da preparação; não teve release. Esta versão corrige o empacotamento
e reúne os fontes, os dois bundles Windows e as provas da mesma revisão.

- **Revisão dos fontes:** `{revisao}`
- **Gerada em:** {data}
- **Plataforma dos bundles:** Windows x64

## O que vem dentro

| Arquivo | O que é |
|---|---|
| `tucoteca-{versao}-fontes.zip` | fontes, testes, documentação e empacotadores, com manifesto SHA-256 |
| `tucoteca-{versao}-windows-x64-essencial.zip` | sem Chromium; YouTube abre no navegador do sistema |
| `tucoteca-{versao}-windows-x64-completo.zip` | QtWebEngine e QtMultimedia; YouTube embutido e vídeo interno |
| `superhub-verificacao-*.json` | provas de cada variante na árvore montada e no ZIP extraído |
| `SHA256SUMS.txt` | hashes de todos os outros anexos, inclusive relatórios e notas |
| `LICENCAS.md` | licenças, versões e links para os fontes dos componentes |
| `release.json` | proveniência e inventário dos anexos |
| `NOTAS-RELEASE.md` | este arquivo |

## Como usar

1. Confira os hashes: `Get-FileHash -Algorithm SHA256 <arquivo>` e compare com
   `SHA256SUMS.txt`; ou `certutil -hashfile <arquivo> SHA256`.
2. Extraia o bundle escolhido **inteiro** em uma pasta própria (pendrive vale).
3. Abra `TucoTeca.bat`. `BibliotecaHub.bat` segue funcionando como alias.
4. A coleção nasce vazia em `dados/`. Para trazer a sua, use exportar/importar
   pacote de coleção no Hub. Jogos e ROMs não fazem parte desse pacote.
5. `Debug-Console.bat` abre com terminal para diagnosticar; `Criar-Atalho.bat`
   cria o atalho da Área de Trabalho.

Os dois bundles incluem Python, Tk, Pillow, PySide6, 7-Zip, FFmpeg, yt-dlp,
QuickJS-NG, qBittorrent, Azahar e DeSmuME. Não é preciso instalar Python
separadamente. Os textos das licenças e os links para os fontes de
terceiros ficam dentro do runtime; o código-fonte desses componentes não está
no ZIP de fontes da TucoTeca.

## Atualizar sem perder a coleção

Feche o Hub e faça uma cópia de segurança da pasta antiga. Extraia a nova
versão em outra pasta; não descompacte por cima de `dados/`. Importe um pacote
de coleção ou copie seu `dados/` para a nova pasta. Preserve separadamente
saves, perfis de emuladores e arquivos externos. Confira a biblioteca antes
de abandonar a versão antiga. Nenhum instalador altera sua coleção sozinho.

## O que **não** vem

- Coleção, banco, capas, músicas, saves, perfis, ROMs e executáveis de jogos.
- Capas comerciais e qualquer arte protegida.
- Contas próprias, telemetria ou serviços online obrigatórios.
  `BIBLIOTECA_REDE=0` bloqueia ações remotas do Hub; não é firewall de
  qBittorrent, navegador ou outros programas externos.

## Limites conhecidos desta versão

- Navegação por gamepad ainda não implementada em nenhuma variante.
- Sem assinatura de código: o Windows pode mostrar o aviso do SmartScreen.
- Build macOS apenas mantido nos fontes; não há bundle macOS validado.
- `es.exe` (Everything) é opcional e por conta do usuário; sem ele a busca usa
  a varredura normal.

## Verificar os testes

Os gates rodam a cada push em `.github/workflows/testes.yml` (stdlib, Qt,
Windows/Linux, Python 3.10 e 3.14, além da varredura de segredos). Localmente:

```powershell
py -3.14 codigo/ferramentas/testes/executar.py
py -3.14 -m pytest --cobertura
```

Cada caso roda em sandbox própria, sem rede e sem tocar a coleção real.
"""


def escrever_notas(saida: Path, versao: str, revisao: str, variantes: list[dict]) -> Path:
    data = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    texto = NOTAS.format(versao=versao, revisao=revisao, data=data)
    linhas = ["\n## Variantes desta release\n"]
    for item in variantes:
        linhas.append(
            f"### {item['variante']}\n\n"
            f"- runtime descompactado: {item['bytes_runtime'] / 1048576:.0f} MiB\n"
            f"- arquivos: {', '.join(a['nome'] for a in item['arquivos'])}\n"
            f"- Python {item.get('python', '?')}; Qt {item.get('qt', '?')}\n"
            f"- provas: {', '.join(item['provas'])}\n"
            f"- árvore `app/` conferida por SHA-256: "
            f"{item['fontes']['arquivos']} arquivos "
            f"(`{item['fontes']['sha256_arvore_app'][:12]}…`)\n"
            f"- revisão registrada no manifesto: `{item['revisao'] or 'não informada'}`\n")
    destino = saida / "NOTAS-RELEASE.md"
    destino.write_text(texto + "\n".join(linhas), encoding="utf-8")
    return destino


def verificar_revisao(revisao: str, repo: Path = REPO) -> None:
    """Exige HEAD limpo na revisão informada antes de montar a release."""
    if not re.fullmatch(r"[0-9a-f]{40}", revisao):
        raise ValueError("--revisao deve ser o SHA Git completo (40 caracteres hexadecimais).")
    sujo = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                          cwd=repo, capture_output=True, text=True, encoding="utf-8", timeout=30)
    if sujo.returncode:
        raise ValueError("não foi possível inspecionar o Git desta pasta")
    if sujo.stdout.strip():
        raise ValueError("a árvore de trabalho não está limpa; congele os fontes antes")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True,
                          text=True, encoding="utf-8", timeout=30)
    if head.returncode or head.stdout.strip() != revisao:
        raise ValueError(f"HEAD ({head.stdout.strip()[:7]}) não é a revisão informada ({revisao[:7]})")
    rastreados = subprocess.run(["git", "ls-files", "-z"], cwd=repo, capture_output=True,
                               text=True, encoding="utf-8", timeout=30)
    if rastreados.returncode:
        raise ValueError("não foi possível conferir os fontes rastreados pelo Git")
    extras = {p.relative_to(repo).as_posix() for p in listar_fontes(repo)} - set(rastreados.stdout.split("\0"))
    if extras:
        raise ValueError("fontes não rastreados pelo Git: " + ", ".join(sorted(extras)))


def _ativo(p: Path) -> dict:
    return {"nome": p.name, "bytes": p.stat().st_size, "sha256": sha_arquivo(p)}


def escrever_licencas(saida: Path, variantes: list[dict]) -> None:
    linhas = ["# Licenças dos componentes\n",
              "O código da TucoTeca é MIT (`LICENSE-TucoTeca.txt` no runtime).\n",
              "Os componentes abaixo mantêm suas licenças. Os textos acompanham o\n"
              "runtime; os links apontam aos projetos/fontes originais. O ZIP de\n"
              "fontes da TucoTeca não inclui o código-fonte desses terceiros.\n",
              "| Componente | Versão | Licença / fontes |\n|---|---|---|",
              f"| Python | {variantes[0]['python']} | [PSF](https://www.python.org/downloads/source/); `python/LICENSE.txt` |",
              "| Tcl/Tk | ver manifesto | [BSD](https://www.tcl-lang.org/software/tcltk/); `python/tcl/LICENSE-*.txt` |",
              "| Pillow | ver instalação empacotada | [HPND](https://github.com/python-pillow/Pillow); `python/LICENSES-Pillow/` |",
              f"| Qt / PySide6 / shiboken6 | {variantes[0]['qt']} | [LGPL/GPL e termos dos módulos](https://doc.qt.io/qt-6/licensing.html); `python/LICENSES-Qt/` |"]
    componentes = {}
    for variante in variantes:
        componentes.update(variante["componentes"])
    for nome, c in sorted(componentes.items()):
        linhas.append(f"| {nome} | {c['versao']} | [{c['licenca']}]({c['fonte']}); textos junto do componente |")
    linhas.append("\nQtWebEngine/Chromium só aparece na variante completa. Seus avisos\n"
                  "adicionais podem ser consultados em `chrome://credits` no WebEngine\n"
                  "e nos [fontes da Qt](https://code.qt.io/cgit/qt/qtwebengine.git/).\n"
                  "As bibliotecas Qt ficam separadas em `python/Lib/PySide6/`, sem\n"
                  "impedir substituição por versões compatíveis. O uso e a eventual\n"
                  "redistribuição devem respeitar as obrigações de cada licença.\n")
    (saida / "LICENCAS.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def preparar(revisao: str, saida: Path, variantes=VARIANTES,
             repo: Path = REPO, windows_dir: Path | None = None) -> dict:
    repo, saida = Path(repo), Path(saida)
    variantes = tuple(variantes)
    if not variantes or len(set(variantes)) != len(variantes) or set(variantes) - set(VARIANTES):
        raise ValueError("variantes válidas, sem repetição: " + ", ".join(VARIANTES))
    if saida.exists() or saida.is_symlink():
        raise ValueError("destino já existe; preserve a entrega anterior e escolha outra pasta")
    verificar_revisao(revisao, repo)
    versao = (repo / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", versao):
        raise ValueError("VERSION deve conter uma versão SemVer numérica")
    windows_dir = repo / "dist/windows" if windows_dir is None else Path(windows_dir)
    dados_variantes = conferir_bundles(revisao, versao, variantes, windows_dir, repo)
    saida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".tucoteca-release-", dir=saida.parent) as tmp:
        stage = Path(tmp) / "entrega"
        stage.mkdir()
        pacote = stage / f"tucoteca-{versao}-fontes.zip"
        empacotar_fontes(pacote, repo=repo, revisao=revisao)
        conferir_pacote_fontes(pacote, repo, revisao, versao)
        for variante in dados_variantes:
            for item in variante["arquivos"]:
                destino = stage / item["nome"]
                shutil.copy2(windows_dir / item["nome"], destino)
                if sha_arquivo(destino) != item["sha256"]:
                    raise ValueError("bundle mudou durante a cópia: " + destino.name)
            shutil.copy2(windows_dir / variante["relatorio"], stage / variante["relatorio"])
        escrever_notas(stage, versao, revisao, dados_variantes)
        escrever_licencas(stage, dados_variantes)
        ativos = [_ativo(p) for p in sorted(stage.iterdir())]
        registro = {"esquema": 1, "projeto": "TucoTeca", "versao": versao,
                    "tag": "v" + versao, "revisao": revisao, "plataforma": "windows-x64",
                    "gerado_em": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "arquivos": ativos, "variantes": dados_variantes,
                    "notas": "NOTAS-RELEASE.md"}
        (stage / "release.json").write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8")
        (stage / "SHA256SUMS.txt").write_text("".join(
            f"{sha_arquivo(p)}  {p.name}\n" for p in sorted(stage.iterdir())), encoding="utf-8")
        verificar_revisao(revisao, repo)
        stage.rename(saida)
    return registro


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--revisao", required=True, help="SHA completo do checkout congelado")
    ap.add_argument("--saida", type=Path, required=True, help="pasta de destino da release")
    ap.add_argument("--variantes", default=",".join(VARIANTES),
                    help="variantes a incluir (padrão: essencial,completo)")
    args = ap.parse_args(argv)
    variantes = tuple(v.strip() for v in args.variantes.split(",") if v.strip())
    if not variantes or len(set(variantes)) != len(variantes) or set(variantes) - set(VARIANTES):
        print("ERRO: variantes válidas: " + ", ".join(VARIANTES), file=sys.stderr)
        return 1
    try:
        r = preparar(args.revisao, args.saida, variantes)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.SubprocessError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    print(f"[ok] release preparada em {args.saida}: {len(r['arquivos']) + 2} arquivos")
    for a in r["arquivos"]:
        print(f"     {a['nome']} — {a['bytes'] / 1048576:.1f} MiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
