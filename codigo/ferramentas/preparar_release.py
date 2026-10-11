#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepara uma release privada: pacote de fontes, bundles, notas e checksums.

Reune os artefatos ja validados em ``dist/`` numa pasta de release, confere
integridade por SHA-256, verifica que nenhum dado pessoal entrou e escreve as
notas. Nao publica nada: criar a release no GitHub e um passo posterior e
explicito.

    py -3.14 codigo/ferramentas/preparar_release.py --revisao <SHA> --saida dist/release/v1.0.0

O pacote de fontes e gerado aqui, congelado na revisao informada. Os bundles
Windows vem de ``dist/windows/`` com seus relatorios de verificacao; este
script apenas confere que os hashes batem com os ``SHA256SUMS-*.txt``.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DIST = REPO / "dist"
FONTES_DIR = DIST / "fontes"
WINDOWS_DIR = DIST / "windows"
VARIANTES = ("essencial", "completo")
PROIBIDAS = {"dados", "saves", "roms", "jogos", "programa", "dist", ".provas",
             ".build", ".cache", "historico", "backups", ".git", ".venv"}
PESSOAIS = re.compile(
    r"(?i)\.(db|db-journal|sqlite3?|lnk|zip|7z|rar|exe|dll|pyd|cia|3ds|nds|sav|dsv|"
    r"mp3|mp4|wav|ogg|flac|mkv|webm|png|jpg|jpeg)$")


def sha_arquivo(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def _proibido(rel: str) -> bool:
    partes = {x.lower() for x in Path(rel).parts}
    return bool(partes & PROIBIDAS) or bool(PESSOAIS.search(rel))


def conferir_pacote_fontes(pacote: Path, repo: Path = REPO) -> dict:
    """Reabre o ZIP de fontes: manifesto, hashes e nada de dado pessoal."""
    with zipfile.ZipFile(pacote) as z:
        nomes = z.namelist()
        if z.testzip():
            raise ValueError(f"{pacote.name}: ZIP corrompido")
        manifesto = json.loads(z.read("MANIFESTO-FONTES.json"))
        if set(nomes) != set(manifesto["arquivos"]) | {"MANIFESTO-FONTES.json"}:
            raise ValueError(f"{pacote.name}: conteúdo difere do manifesto")
        for rel, info in manifesto["arquivos"].items():
            if _proibido(rel):
                raise ValueError(f"{pacote.name}: caminho proibido no pacote: {rel}")
            if hashlib.sha256(z.read(rel)).hexdigest() != info["sha256"]:
                raise ValueError(f"{pacote.name}: hash divergente de {rel}")
            if (repo / rel).is_file() and z.read(rel) != (repo / rel).read_bytes():
                raise ValueError(f"{pacote.name}: {rel} difere da árvore de trabalho")
    return {"arquivos": len(manifesto["arquivos"]), "sha256": sha_arquivo(pacote)}


def _sums(variante: str) -> dict:
    """Lê SHA256SUMS-<variante>.txt publicado pelo builder."""
    arq = WINDOWS_DIR / f"SHA256SUMS-{variante}.txt"
    if not arq.is_file():
        raise ValueError(f"faltou {arq.name}; gere os bundles antes de preparar a release")
    somas = {}
    for linha in arq.read_text(encoding="utf-8").splitlines():
        sha, _, nome = linha.partition("  ")
        if sha:
            somas[nome.strip()] = sha
    return somas


def conferir_bundles(saida: Path, variantes=VARIANTES) -> list[dict]:
    """Copia os bundles e seus relatórios, conferindo hash e conteúdo."""
    ativos = []
    for variante in variantes:
        somas = _sums(variante)
        verificacao = WINDOWS_DIR / f"superhub-verificacao-{variante}.json"
        rel = json.loads(verificacao.read_text(encoding="utf-8"))
        entradas = []
        for item in rel["arquivos"]:
            nome, sha = item["nome"], item["sha256"]
            if somas.get(nome) != sha:
                raise ValueError(f"{nome}: SHA256SUMS-{variante}.txt não bate com a verificação")
            origem = WINDOWS_DIR / nome
            if not origem.is_file():
                raise ValueError(f"bundle ausente em dist/windows/: {nome}")
            if sha_arquivo(origem) != sha:
                raise ValueError(f"{nome}: arquivo em dist/windows/ não corresponde ao hash")
            shutil.copy2(origem, saida / nome)
            entradas.append({"nome": nome, "bytes": item["bytes"], "sha256": sha,
                             "provas_extraido": bool(item.get("provas_extraido"))})
        for extra in (verificacao.name, f"SHA256SUMS-{variante}.txt"):
            shutil.copy2(WINDOWS_DIR / extra, saida / extra)
        fontes = rel.get("fontes", {})
        ativos.append({"variante": variante, "arquivos": entradas,
                       "bytes_runtime": rel["bytes_runtime"], "extras": rel["extras"],
                       "fontes": {"arquivos": fontes.get("arquivos"),
                                  "sha256_arvore_app": fontes.get("sha256_arvore_app")},
                       "provas": sorted(rel["provas"]), "revisao": rel.get("revisao_git", "")})
    return ativos


NOTAS = """# TucoTeca {versao} — release privada

Release **privada** para uso pessoal de Tuco e Isa. O repositório é privado e
esta release não é pública. Nada aqui substitui a coleção pessoal: o pacote
começa com `dados/` vazio.

- **Revisão dos fontes:** `{revisao}`
- **Gerada em:** {data}
- **Plataforma:** Windows x64 (Python 3.14, Qt 6.10.2)

## O que vem dentro

| Arquivo | O que é |
|---|---|
| `tucoteca-fontes-{revisao_curta}.zip` | fontes, testes, documentação e empacotadores, com manifesto SHA-256 |
| `tucoteca-superhub-windows-x64-essencial-*.zip` | runtime completo sem Chromium (YouTube abre no navegador) |
| `tucoteca-superhub-windows-x64-completo-*.zip` | runtime com QtWebEngine e QtMultimedia (YouTube embutido) |
| `superhub-verificacao-*.json` | provas de cada variante na árvore montada e no ZIP extraído |
| `SHA256SUMS*.txt` | hashes para conferir a integridade |
| `NOTAS-RELEASE.md` | este arquivo |

## Como usar

1. Confira os hashes: `Get-FileHash -Algorithm SHA256 <arquivo>` e compare com
   `SHA256SUMS.txt`; ou `certutil -hashfile <arquivo> SHA256`.
2. Extraia o bundle escolhido **inteiro** em uma pasta própria (pendrive vale).
3. Abra `TucoTeca.bat`. `BibliotecaHub.bat` segue funcionando como alias.
4. A coleção nasce vazia em `dados/`. Para trazer a sua, use o pacote de
   coleção do Hub (exportar/importar), preservando `dados/` em atualizações.
5. `Debug-Console.bat` abre com terminal para diagnosticar; `Criar-Atalho.bat`
   cria o atalho da Área de Trabalho.

Os dois bundles incluem Python, Tk, Pillow, PySide6, 7-Zip, FFmpeg, yt-dlp,
QuickJS-NG, qBittorrent, Azahar e DeSmuME — nada precisa ser instalado no
Windows. O mapa completo de componentes e licenças está em
`manifesto-runtime.json` dentro de cada pacote.

## O que **não** vem

- Coleção, banco, capas, músicas, saves, perfis, ROMs e executáveis de jogos.
- Capas comerciais e qualquer arte protegida.
- Contas, telemetria ou serviços online obrigatórios: rede só sob ação sua
  (`BIBLIOTECA_REDE=0` desliga as ações remotas).

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
    texto = NOTAS.format(versao=versao, revisao=revisao, revisao_curta=revisao[:7], data=data)
    linhas = ["\n## Variantes desta release\n"]
    for item in variantes:
        linhas.append(
            f"### {item['variante']}\n\n"
            f"- runtime descompactado: {item['bytes_runtime'] / 1048576:.0f} MB\n"
            f"- arquivos: {', '.join(a['nome'] for a in item['arquivos'])}\n"
            f"- provas: {', '.join(item['provas'])}\n"
            f"- árvore `app/` conferida por SHA-256: "
            f"{item['fontes']['arquivos']} arquivos "
            f"(`{item['fontes']['sha256_arvore_app'][:12]}…`)\n"
            f"- revisão registrada no manifesto: `{item['revisao'] or 'não informada'}`\n")
    destino = saida / "NOTAS-RELEASE.md"
    destino.write_text(texto + "\n".join(linhas), encoding="utf-8")
    return destino


def preparar(revisao: str, saida: Path, variantes=VARIANTES) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", revisao):
        raise ValueError("--revisao deve ser o SHA Git completo (40 caracteres hexadecimais).")
    versao = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    saida.mkdir(parents=True, exist_ok=True)
    FONTES_DIR.mkdir(parents=True, exist_ok=True)
    pacote = FONTES_DIR / f"tucoteca-fontes-{revisao[:7]}.zip"
    sys.path.insert(0, str(REPO / "codigo"))
    from empacotar_fontes import empacotar_fontes
    empacotar_fontes(pacote, revisao=revisao)
    conferencia = conferir_pacote_fontes(pacote)
    shutil.copy2(pacote, saida / pacote.name)
    ativos = [{"nome": pacote.name, "sha256": conferencia["sha256"],
               "bytes": pacote.stat().st_size, "arquivos": conferencia["arquivos"]}]
    ativos += conferir_bundles(saida, variantes)
    dados_variantes = []
    for variante in variantes:
        rel = json.loads((saida / f"superhub-verificacao-{variante}.json").read_text(encoding="utf-8"))
        dados_variantes.append({"variante": variante, "bytes_runtime": rel["bytes_runtime"],
                                "arquivos": rel["arquivos"], "provas": sorted(rel["provas"]),
                                "fontes": rel.get("fontes", {}), "revisao": rel.get("revisao_git", "")})
    (saida / "SHA256SUMS.txt").write_text(
        "".join(f'{a["sha256"]}  {a["nome"]}\n' for a in sorted(ativos, key=lambda a: a["nome"])),
        encoding="utf-8")
    notas = escrever_notas(saida, versao, revisao, dados_variantes)
    registro = {"versao": versao, "revisao": revisao,
                "gerado_em": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "saida": str(saida), "arquivos": ativos, "notas": str(notas)}
    (saida / "release.json").write_text(json.dumps(registro, ensure_ascii=False, indent=2),
                                        encoding="utf-8")
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
    if not variantes or set(variantes) - set(VARIANTES):
        print("ERRO: variantes válidas: " + ", ".join(VARIANTES), file=sys.stderr)
        return 1
    try:
        r = preparar(args.revisao, args.saida, variantes)
    except (OSError, ValueError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    print(f"[ok] release preparada em {r['saida']}: {len(r['arquivos'])} arquivos")
    for a in r["arquivos"]:
        print(f"     {a['nome']} — {a['bytes'] / 1048576:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
