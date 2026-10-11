"""Preparacao de release: revisao conferivel, pacote sem dados pessoais, notas."""
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

from executar import afirmar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import empacotar_fontes as FONTES
import montar_superhub as MS
import preparar_release as REL

SHA = "a" * 40


def _repo_minimo(tmp: Path) -> Path:
    repo = tmp / "repo"
    (repo / "codigo/bib_nucleo").mkdir(parents=True)
    (repo / "codigo/bib_nucleo/__init__.py").write_text("# nucleo", encoding="utf-8")
    (repo / "codigo/bib_nucleo/arquivos.py").write_text(
        "from contextlib import contextmanager\n"
        "from pathlib import Path\n\n"
        "@contextmanager\n"
        "def destino_temporario(destino):\n"
        "    tmp = Path(str(destino) + '.tmp')\n"
        "    yield tmp\n"
        "    tmp.replace(destino)\n", encoding="utf-8")
    (repo / "codigo/bib_core.py").write_text("# fachada", encoding="utf-8")
    (repo / "codigo/frontends/qml/secoes").mkdir(parents=True)
    (repo / "codigo/frontends/qml/secoes/Inicio.qml").write_text("import QtQuick; Item {}",
                                                                encoding="utf-8")
    (repo / "docs").mkdir()
    (repo / "docs/ARQUITETURA.md").write_text("# arquitetura", encoding="utf-8")
    (repo / "codigo/ferramentas").mkdir(parents=True)
    (repo / "codigo/ferramentas/builders.py").write_text("# builder", encoding="utf-8")
    (repo / "README.md").write_text("Projeto", encoding="utf-8")
    (repo / "LICENSE").write_text("MIT", encoding="utf-8")
    (repo / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    for nome in ("codigo/__pycache__/x.pyc", ".provas/cobertura/c.json", ".venv/pyvenv.cfg",
                 ".pytest_cache/v/cache/lastfailed", ".ruff_cache/0", "dist/antigo.zip",
                 "dados/biblioteca.db", "codigo/historico/antigo.py", "TucoTeca.lnk"):
        p = repo / nome
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# descartavel", encoding="utf-8")
    (repo / ".github/workflows/testes.yml").parent.mkdir(parents=True, exist_ok=True)
    (repo / ".github/workflows/testes.yml").write_text("name: Testes\n", encoding="utf-8")
    (repo / ".github/ISSUE_TEMPLATE/bug.md").parent.mkdir(parents=True, exist_ok=True)
    (repo / ".github/ISSUE_TEMPLATE/bug.md").write_text("template\n", encoding="utf-8")
    return repo


def teste_pacote_fontes_recusa_revisao_invalida():
    tmp = Path(tempfile.mkdtemp(prefix="release-rev-"))
    repo = _repo_minimo(tmp)
    for ruim in ("", "abc", "a" * 39, "g" * 40, "A" * 40):
        try:
            FONTES.empacotar_fontes(tmp / "x.zip", repo=repo, revisao=ruim)
        except ValueError:
            continue
        afirmar(False, f"aceitou revisão inválida: {ruim!r}")
    # Vazia é permitida (árvore de trabalho), desde que não seja string inventada.
    ok = FONTES.empacotar_fontes(tmp / "ok.zip", repo=repo)
    afirmar(ok["ok"], ok)


def teste_pacote_fontes_registra_versao_e_revisao():
    tmp = Path(tempfile.mkdtemp(prefix="release-man-"))
    repo = _repo_minimo(tmp)
    saida = tmp / "fontes.zip"
    FONTES.empacotar_fontes(saida, repo=repo, revisao=SHA)
    with zipfile.ZipFile(saida) as z:
        manifesto = json.loads(z.read("MANIFESTO-FONTES.json"))
        nomes = z.namelist()
    afirmar(manifesto["revisao_git"] == SHA, manifesto.get("revisao_git"))
    afirmar(manifesto["versao"] == "9.9.9", manifesto.get("versao"))
    afirmar("VERSION" in nomes and "LICENSE" in nomes, nomes)
    afirmar("codigo/ferramentas/builders.py" in nomes, nomes)
    afirmar(".github/ISSUE_TEMPLATE/bug.md" in nomes, "template de issue ficou fora")
    for nome in nomes:
        partes = {x.lower() for x in Path(nome).parts}
        afirmar(not partes & {"dados", "dist", ".provas", ".venv", ".pytest_cache",
                              ".ruff_cache", "historico"}, nome)
        afirmar(not nome.endswith(".lnk") and not nome.endswith(".zip"), nome)


def teste_versoes_release_registra_revisao_sem_herdar_lixo():
    tmp = Path(tempfile.mkdtemp(prefix="release-vers-"))
    repo = _repo_minimo(tmp)
    versoes = {"python": "3.14.0", "qt": "6.10.2", "extras": "essencial",
               "revisao_git": "b" * 40}
    r = MS._versoes_release(tmp, versoes, SHA, repo=repo)
    afirmar(r["tucoteca"] == "9.9.9", r)
    afirmar(r["revisao_git"] == SHA, r)
    afirmar((tmp / "VERSION").read_text(encoding="utf-8").strip() == "9.9.9")
    texto = (tmp / "VERSAO.txt").read_text(encoding="utf-8")
    afirmar(SHA in texto and "Windows x64, essencial" in texto, texto)
    # Sem --revisao, a revisão anterior não pode continuar no pacote.
    versoes = dict(r, revisao_git="c" * 40)
    r2 = MS._versoes_release(tmp, versoes, "", repo=repo)
    afirmar("revisao_git" not in r2, r2)
    afirmar("não identificada" in (tmp / "VERSAO.txt").read_text(encoding="utf-8"))
    for ruim in ("abc", "a" * 41, "z" * 40):
        try:
            MS._versoes_release(tmp, dict(versoes), ruim, repo=repo)
        except ValueError:
            continue
        afirmar(False, f"aceitou revisão inválida: {ruim!r}")


def teste_conferencia_recusa_pacote_com_dado_pessoal():
    tmp = Path(tempfile.mkdtemp(prefix="release-conf-"))
    pacote = tmp / "ruim.zip"
    dados = b"sqlite pessoal"
    manifesto = {"esquema": 1, "projeto": "TucoTeca",
                 "arquivos": {"dados/biblioteca.db": {"bytes": len(dados),
                                                      "sha256": hashlib.sha256(dados).hexdigest()}}}
    with zipfile.ZipFile(pacote, "w") as z:
        z.writestr("dados/biblioteca.db", dados)
        z.writestr("MANIFESTO-FONTES.json", json.dumps(manifesto))
    try:
        REL.conferir_pacote_fontes(pacote, repo=tmp)
    except ValueError as e:
        afirmar("dados/biblioteca.db" in str(e), e)
    else:
        afirmar(False, "aceitou banco pessoal no pacote de fontes")


def teste_conferencia_detecta_hash_divergente():
    tmp = Path(tempfile.mkdtemp(prefix="release-hash-"))
    pacote = tmp / "fraco.zip"
    manifesto = {"esquema": 1, "projeto": "TucoTeca",
                 "arquivos": {"README.md": {"bytes": 3, "sha256": "0" * 64}}}
    with zipfile.ZipFile(pacote, "w") as z:
        z.writestr("README.md", "abc")
        z.writestr("MANIFESTO-FONTES.json", json.dumps(manifesto))
    try:
        REL.conferir_pacote_fontes(pacote, repo=tmp)
    except ValueError as e:
        afirmar("hash divergente" in str(e), e)
    else:
        afirmar(False, "aceitou hash divergente")


def teste_notas_release_registram_variantes_e_limites():
    tmp = Path(tempfile.mkdtemp(prefix="release-notas-"))
    dados = [{"variante": "essencial", "bytes_runtime": 500 * 1048576,
              "arquivos": [{"nome": "bundle.zip", "bytes": 1, "sha256": SHA}],
              "provas": ["ffmpeg", "ui"], "fontes": {"arquivos": 179, "sha256_arvore_app": SHA},
              "revisao": SHA}]
    notas = REL.escrever_notas(tmp, "1.0.0", SHA, dados)
    texto = notas.read_text(encoding="utf-8")
    afirmar(SHA in texto and SHA[:7] in texto, texto[:200])
    afirmar("## Variantes desta release" in texto and "### essencial" in texto, texto)
    afirmar(SHA in texto and "ffmpeg" in texto, texto)
    afirmar("gamepad" in texto and "SmartScreen" in texto, "limites conhecidos sumiram")
    afirmar("BIBLIOTECA_REDE=0" in texto, "modo avião não documentado nas notas")
