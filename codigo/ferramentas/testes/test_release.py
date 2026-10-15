"""Preparacao de release: revisao conferivel, pacote sem dados pessoais, notas."""
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from executar import afirmar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import empacotar_fontes as FONTES
import montar_superhub as MS
import preparar_release as REL
from montar_portatil import APP_ARQS, APP_PACOTES

SHA = "a" * 40


def _repo_minimo(tmp: Path) -> Path:
    repo = tmp / "repo"
    for origem, _ in APP_ARQS:
        p = repo / origem
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# fonte sintético\n", encoding="utf-8")
    for origem, _ in APP_PACOTES:
        p = repo / origem / "__init__.py"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# pacote sintético\n", encoding="utf-8")
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
    (repo / "codigo/ferramentas").mkdir(parents=True, exist_ok=True)
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


def _git_limpo(repo: Path, revisao=SHA):
    """Contrato Git simulado: nenhum processo externo é autorizado na suíte."""
    def run(cmd, **kwargs):
        afirmar(Path(kwargs["cwd"]) == repo, kwargs)
        if cmd[1] == "status":
            texto = ""
        elif cmd[1] == "rev-parse":
            texto = revisao + "\n"
        elif cmd[1] == "ls-files":
            texto = "\0".join(p.relative_to(repo).as_posix() for p in FONTES.listar_fontes(repo)) + "\0"
        else:
            raise AssertionError(cmd)
        return subprocess.CompletedProcess(cmd, 0, texto, "")
    return patch.object(REL.subprocess, "run", side_effect=run)


def _bundle(fonte: Path, repo: Path, variante="essencial", revisao=SHA, pessoal=None):
    """ZIP sintético completo para testar o preparo, não uma prova de runtime real."""
    fonte.mkdir(parents=True, exist_ok=True)
    versao = (repo / "VERSION").read_text(encoding="utf-8").strip()
    conteudo = {n: p.read_bytes() for n, p in REL._fontes_app(repo).items()}
    conteudo.update({"VERSION": (versao + "\n").encode(), "VERSAO.txt": revisao.encode(),
                     "LICENSE-TucoTeca.txt": b"MIT", "python/LICENSE.txt": b"PSF",
                     "python/LICENSES-Pillow/LICENSE": b"HPND",
                     "python/tcl/LICENSE-tcl9.0.txt": b"BSD", "python/tcl/LICENSE-tk9.0.txt": b"BSD",
                     "ferramentas/quickjs/qjs.exe": b"MZ-fake", "ferramentas/quickjs/LICENSE": b"MIT"})
    for lic in ("LGPL-3.0-only", "GPL-3.0-only", "GPL-2.0-only"):
        conteudo[f"python/LICENSES-Qt/{lic}.txt"] = b"licenca sintetica"
    if variante == "completo":
        for nome in ("QtMultimedia", "QtWebEngineQuick"):
            conteudo[f"python/Lib/PySide6/{nome}.pyd"] = b"MZ-fake"
    if pessoal:
        conteudo[pessoal] = b"estado pessoal sintetico"
    arquivos = {n: {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in conteudo.items()}
    hashes = {n.removeprefix("app/"): v["sha256"] for n, v in arquivos.items() if n.startswith("app/")}
    fontes = {"arquivos": len(hashes), "sha256_arvore_app": hashlib.sha256(
        json.dumps(hashes, sort_keys=True).encode()).hexdigest()}
    componentes = {"quickjs": {"executavel": "ferramentas/quickjs/qjs.exe", "versao": "0.17.0",
                               "licenca": "MIT", "fonte": "https://github.com/quickjs-ng/quickjs"}}
    manifesto = {"versoes": {"tucoteca": versao, "revisao_git": revisao, "extras": variante},
                 "arquivos": arquivos, "componentes": componentes, "fontes": fontes}
    pacote = fonte / f"tucoteca-{versao}-windows-x64-{variante}.zip"
    with zipfile.ZipFile(pacote, "w") as z:
        for n, b in conteudo.items():
            z.writestr(n, b)
        z.writestr("manifesto-runtime.json", json.dumps(manifesto))
    sha = REL.sha_arquivo(pacote)
    rel = {"bytes_runtime": sum(a["bytes"] for a in arquivos.values()),
           "provas": {"ui": {"saida": "sintético"}}, "extras": variante,
           "tucoteca": versao, "python": "3.14.7", "qt": "6.10.2",
           "fontes": fontes, "componentes": componentes, "revisao_git": revisao,
           "arquivos": [{"nome": pacote.name, "bytes": pacote.stat().st_size, "sha256": sha,
                         "provas_extraido": {"ui": {"saida": "sintético"}}}]}
    _gravar_relatorio(fonte, variante, rel)
    (fonte / f"SHA256SUMS-{variante}.txt").write_text(f"{sha}  {pacote.name}\n", encoding="utf-8")
    return rel


def _gravar_relatorio(fonte, variante, rel):
    (fonte / f"superhub-verificacao-{variante}.json").write_text(json.dumps(rel), encoding="utf-8")


def _recusa(acao, trecho):
    try:
        acao()
    except ValueError as e:
        afirmar(trecho in str(e), e)
    else:
        afirmar(False, "deveria recusar: " + trecho)


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


def teste_preparar_recusa_bundle_de_outra_revisao():
    """Bundle comprovando outra revisão não pode entrar na release."""
    tmp = Path(tempfile.mkdtemp(prefix="release-mix-"))
    repo = _repo_minimo(tmp)
    fonte = tmp / "windows"
    outra = "b" * 40
    _bundle(fonte, repo, revisao=outra)
    saida = tmp / "release"
    with _git_limpo(repo):
        _recusa(lambda: REL.preparar(SHA, saida, ("essencial",), repo=repo, windows_dir=fonte), outra)
    afirmar(not saida.exists(), "escreveu uma entrega de revisão misturada")


def teste_preparar_fluxo_completo_fontes_bundles_notas_e_checksums():
    tmp = Path(tempfile.mkdtemp(prefix="release-e2e-"))
    repo = _repo_minimo(tmp)
    fonte = tmp / "windows"
    for variante in REL.VARIANTES:
        _bundle(fonte, repo, variante)
    saida = tmp / "release"
    with _git_limpo(repo):
        registro = REL.preparar(SHA, saida, repo=repo, windows_dir=fonte)
    nomes = {p.name for p in saida.iterdir()}
    afirmar(len(nomes) == 9, nomes)
    somas = {n: s for s, n in (linha.split("  ", 1) for linha in (saida / "SHA256SUMS.txt").read_text().splitlines())}
    afirmar(set(somas) == nomes - {"SHA256SUMS.txt"}, somas)
    for nome, sha in somas.items():
        afirmar(REL.sha_arquivo(saida / nome) == sha, nome)
    afirmar({a["nome"] for a in registro["arquivos"]} == nomes - {"SHA256SUMS.txt", "release.json"})
    afirmar(registro["revisao"] == SHA and registro["tag"] == "v9.9.9", registro)
    afirmar(json.loads((saida / "release.json").read_text(encoding="utf-8")) == registro)
    afirmar(str(tmp) not in json.dumps(registro), "registro publicou caminho pessoal absoluto")
    REL.conferir_pacote_fontes(saida / "tucoteca-9.9.9-fontes.zip", repo, SHA, "9.9.9")
    afirmar("### completo" in (saida / "NOTAS-RELEASE.md").read_text(encoding="utf-8"))
    afirmar("LGPL" in (saida / "LICENCAS.md").read_text(encoding="utf-8"))


def teste_preparar_recusa_metadados_hash_e_provas_incompletas():
    tmp = Path(tempfile.mkdtemp(prefix="release-provas-"))
    repo = _repo_minimo(tmp)
    fonte = tmp / "windows"
    for campo, ruim, trecho in (("tucoteca", "1.0.0", "versão/variante"),
                                ("extras", "completo", "versão/variante"),
                                ("provas", {}, "relatório incompleto"),
                                ("arquivos", [], "relatório incompleto")):
        rel = _bundle(fonte, repo)
        rel[campo] = ruim
        _gravar_relatorio(fonte, "essencial", rel)
        _recusa(lambda: REL.conferir_bundles(SHA, "9.9.9", ("essencial",), fonte, repo), trecho)
    for campo, ruim, trecho in (("bytes", 0, "não corresponde ao hash"),
                                ("provas_extraido", {}, "faltam provas"),
                                ("sha256", "0" * 64, "não bate")):
        rel = _bundle(fonte, repo)
        rel["arquivos"][0][campo] = ruim
        _gravar_relatorio(fonte, "essencial", rel)
        _recusa(lambda: REL.conferir_bundles(SHA, "9.9.9", ("essencial",), fonte, repo), trecho)


def teste_preparar_recusa_dados_pessoais_mesmo_com_hash_valido():
    tmp = Path(tempfile.mkdtemp(prefix="release-priv-"))
    repo = _repo_minimo(tmp)
    fonte = tmp / "windows"
    for nome in ("dados/biblioteca.db", "emuladores/Azahar/user/config.ini",
                 "emuladores/DeSmuME/Battery/save.dsv", "emuladores/Azahar/aes_keys.txt"):
        _bundle(fonte, repo, pessoal=nome)
        _recusa(lambda: REL.conferir_bundles(SHA, "9.9.9", ("essencial",), fonte, repo), "dado pessoal")


def teste_preparar_confere_fontes_e_addons_dentro_do_zip():
    tmp = Path(tempfile.mkdtemp(prefix="release-app-"))
    repo = _repo_minimo(tmp)
    fonte = tmp / "windows"
    _bundle(fonte, repo)
    (repo / "codigo/bib_core.py").write_text("# mudança posterior", encoding="utf-8")
    _recusa(lambda: REL.conferir_bundles(SHA, "9.9.9", ("essencial",), fonte, repo), "fonte diverge")
    _bundle(fonte, repo, pessoal="python/Lib/PySide6/QtMultimedia.pyd")
    _recusa(lambda: REL.conferir_bundles(SHA, "9.9.9", ("essencial",), fonte, repo), "Addons")


def teste_release_recusa_caminhos_inseguros_e_entradas_duplicadas():
    tmp = Path(tempfile.mkdtemp(prefix="release-path-"))
    for nome in ("../fora.py", "/fora.py", "C:/fora.py", "codigo\\fora.py", "codigo/../fora.py"):
        pacote = tmp / "ruim.zip"
        with zipfile.ZipFile(pacote, "w") as z:
            info = zipfile.ZipInfo(nome)
            info.filename = nome  # preserva a barra invertida mesmo no Windows
            z.writestr(info, "x")
        _recusa(lambda: REL.conferir_pacote_fontes(pacote, tmp), "caminho inseguro")
    pacote = tmp / "duplo.zip"
    with zipfile.ZipFile(pacote, "w") as z:
        z.writestr("README.md", "x")
        z.writestr("readme.md", "y")
    _recusa(lambda: REL.conferir_pacote_fontes(pacote, tmp), "entrada duplicada")


def teste_release_recusa_git_sujo_head_divergente_e_fonte_ignorado():
    tmp = Path(tempfile.mkdtemp(prefix="release-git-"))
    repo = _repo_minimo(tmp)
    with _git_limpo(repo):
        REL.verificar_revisao(SHA, repo)
    with patch.object(REL.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, " M README.md", "")):
        _recusa(lambda: REL.verificar_revisao(SHA, repo), "não está limpa")
    with _git_limpo(repo, "b" * 40):
        _recusa(lambda: REL.verificar_revisao(SHA, repo), "não é a revisão")
    retornos = [subprocess.CompletedProcess([], 0, "", ""),
                subprocess.CompletedProcess([], 0, SHA, ""),
                subprocess.CompletedProcess([], 0, "README.md\0", "")]
    with patch.object(REL.subprocess, "run", side_effect=retornos):
        _recusa(lambda: REL.verificar_revisao(SHA, repo), "fontes não rastreados")


def teste_release_preserva_destino_existente_e_recusa_variantes_repetidas():
    tmp = Path(tempfile.mkdtemp(prefix="release-antiga-"))
    saida = tmp / "release"
    saida.mkdir()
    anterior = saida / "importante.txt"
    anterior.write_text("preservar", encoding="utf-8")
    _recusa(lambda: REL.preparar(SHA, saida), "destino já existe")
    afirmar(anterior.read_text() == "preservar")
    _recusa(lambda: REL.preparar(SHA, tmp / "nova", ("essencial", "essencial")), "sem repetição")


def teste_release_falha_em_staging_nao_deixa_entrega_parcial():
    tmp = Path(tempfile.mkdtemp(prefix="release-atomica-"))
    repo = _repo_minimo(tmp)
    fonte = tmp / "windows"
    _bundle(fonte, repo)
    saida = tmp / "saida/release"
    with _git_limpo(repo), patch.object(REL, "escrever_notas", side_effect=OSError("falha simulada")):
        try:
            REL.preparar(SHA, saida, ("essencial",), repo, fonte)
        except OSError:
            pass
        else:
            afirmar(False, "não reproduziu a falha")
    afirmar(not saida.exists() and not list(saida.parent.iterdir()), "deixou uma entrega parcial")


def teste_superhub_licencas_qt_fixadas_e_nome_versionado_sem_sobrescrever():
    tmp = Path(tempfile.mkdtemp(prefix="release-qt-license-"))
    chamadas = []
    def baixar(url, nome, sha):
        chamadas.append((url, sha))
        p = tmp / nome
        p.write_text("licença sintética", encoding="utf-8")
        return p
    raiz = tmp / "runtime"
    raiz.mkdir()
    with patch.object(MS, "baixar_verificado", side_effect=baixar):
        MS.incluir_licencas_qt(raiz)
    afirmar(len(chamadas) == 3 and all("v6.10.2/LICENSES/" in u and len(s) == 64 for u, s in chamadas))
    afirmar("PySide6" in (raiz / "python/LICENSES-Qt/FONTES.txt").read_text(encoding="utf-8"))
    (raiz / "VERSION").write_text("1.0.1\n", encoding="utf-8")
    with patch.object(MS, "DIST", tmp / "dist"):
        pacote = MS.empacotar(raiz, "zip")[0]
        afirmar(pacote.name == "tucoteca-1.0.1-windows-x64-essencial.zip", pacote.name)
        original = pacote.read_bytes()
        _recusa(lambda: MS.empacotar(raiz, "zip"), "pacote já existe")
        afirmar(pacote.read_bytes() == original, "sobrescreveu o pacote anterior")


def teste_release_alias_legado_preserva_argumentos_e_atalho_canonico():
    from montar_portatil import BAT_ATALHO
    alias = (REL.REPO / "BibliotecaHub.bat").read_text(encoding="utf-8")
    afirmar('call "%~dp0TucoTeca.bat" %*' in alias, alias)
    afirmar("exit /b %errorlevel%" in alias.lower(), alias)
    afirmar("TucoTeca.bat" in BAT_ATALHO and "BibliotecaHub.bat" not in BAT_ATALHO, BAT_ATALHO)
