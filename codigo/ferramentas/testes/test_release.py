"""Preparador de release do instalador Electron, runtime Python e ícone.

Tudo hermético: repositório e build falsos em pasta temporária, sem Git,
sem rede e sem electron-builder.
"""
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

from executar import afirmar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gerar_icone as ICONE
import preparar_release as REL
import preparar_runtime_python as RUNTIME

SHA = "a" * 40


def _repo_falso(versao="1.2.0", pyproject="1.2.0", changelog=True) -> Path:
    repo = Path(tempfile.mkdtemp(prefix="suite-release-")) / "repo"
    arquivos = {
        "VERSION": versao + "\n",
        "pyproject.toml": f'[project]\nname = "tucoteca"\nversion = "{pyproject}"\n',
        "CHANGELOG.md": (f"# Changelog\n\n## [{versao}] - 2026-11-11\n\n### Adicionado\n\n- Instalador.\n\n"
                         "## [1.0.0] - 2026-01-01\n\n- antigo\n") if changelog else "# Changelog\n",
        "README.md": "TucoTeca", "LICENSE": "MIT",
        # está na lista explícita E sai na varredura de docs/ (regressão de duplicata)
        "docs/CONTRIBUTING.md": "# Colaboração",
        "codigo/bib_core.py": "# núcleo",
    }
    for nome, conteudo in arquivos.items():
        caminho = repo / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(conteudo, encoding="utf-8")
    return repo


def _dist_falso(repo: Path, versao="1.2.0", runtime=True, extra: str | None = None) -> Path:
    dist = repo / "codigo/frontends/electron/dist"
    recursos = dist / "win-unpacked/resources/tucoteca"
    for nome in ("codigo/frontends/ponte.py", "codigo/frontends/ponte_paridade.py",
                 "codigo/bib_core.py",
                 "codigo/ferramentas/abrir_hub.py", "LICENSE"):
        (recursos / nome).parent.mkdir(parents=True, exist_ok=True)
        (recursos / nome).write_text("#", encoding="utf-8")
    (recursos / "VERSION").write_text(versao + "\n", encoding="utf-8")
    if runtime:
        py = recursos / "programa/windows-x64/python"
        py.mkdir(parents=True)
        (py / "python.exe").write_bytes(b"MZ")
        (py / "TUCOTECA-RUNTIME.json").write_text('{"versao": "3.14.7"}', encoding="utf-8")
    if extra:
        (recursos / extra).parent.mkdir(parents=True, exist_ok=True)
        (recursos / extra).write_bytes(b"x")
    (dist / f"TucoTeca-Setup-{versao}-x64.exe").write_bytes(b"MZ instalador")
    return dist


def _erro(func, *args, **kwargs) -> str:
    try:
        func(*args, **kwargs)
    except ValueError as erro:
        return str(erro)
    raise AssertionError("esperava ValueError")


def teste_release_gera_anexos_coerentes():
    repo = _repo_falso()
    dist = _dist_falso(repo)
    saida = repo / "dist/release/v1.2.0"
    r = REL.preparar(SHA, saida, repo=repo, dist=dist, conferir_git=False)
    afirmar(r["ok"] and r["versao"] == "1.2.0", r)
    esperados = {"TucoTeca-Setup-1.2.0-x64.exe", "tucoteca-1.2.0-fontes.zip",
                 "NOTAS-RELEASE.md", "release.json", "SHA256SUMS.txt"}
    afirmar(set(r["anexos"]) == esperados, r["anexos"])
    # checksums cobrem todos os outros anexos e batem
    somas = dict(reversed(linha.split("  ", 1)) for linha in
                 (saida / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines())
    afirmar(set(somas) == esperados - {"SHA256SUMS.txt"}, somas)
    for nome, sha in somas.items():
        afirmar(hashlib.sha256((saida / nome).read_bytes()).hexdigest() == sha, nome)
    release = json.loads((saida / "release.json").read_text(encoding="utf-8"))
    afirmar(release["revisao"] == SHA and release["python_embutido"] is True, release)
    afirmar(release["python_versao"] == "3.14.7", release)
    notas = (saida / "NOTAS-RELEASE.md").read_text(encoding="utf-8")
    afirmar("Instalador." in notas and "antigo" not in notas, notas)
    afirmar("SmartScreen" in notas and "Atenção" not in notas, notas)
    with zipfile.ZipFile(saida / "tucoteca-1.2.0-fontes.zip") as z:
        afirmar(json.loads(z.read("MANIFESTO-FONTES.json"))["revisao_git"] == SHA)
        nomes = z.namelist()
        afirmar(len(nomes) == len(set(nomes)), "entradas duplicadas no ZIP de fontes")
        afirmar("docs/CONTRIBUTING.md" in nomes, nomes)
    # sem staging esquecido ao lado da saída
    afirmar([p.name for p in saida.parent.iterdir()] == ["v1.2.0"], list(saida.parent.iterdir()))


def teste_release_recusa_versoes_divergentes():
    repo = _repo_falso(pyproject="1.0.2")
    _dist_falso(repo)
    afirmar("pyproject.toml" in _erro(REL.ler_versao, repo))
    repo = _repo_falso(changelog=False)
    afirmar("CHANGELOG" in _erro(REL.ler_versao, repo))
    repo = _repo_falso()
    pacote = repo / "codigo/frontends/electron/package.json"
    pacote.parent.mkdir(parents=True)
    pacote.write_text('{"name": "tucoteca-electron", "version": "0.1.0"}', encoding="utf-8")
    afirmar("package.json" in _erro(REL.ler_versao, repo))
    pacote.write_text('{"name": "tucoteca-electron", "version": "1.2.0"}', encoding="utf-8")
    afirmar(REL.ler_versao(repo) == "1.2.0")
    repo = _repo_falso()
    dist = _dist_falso(repo, versao="1.1.0")
    msg = _erro(REL.preparar, SHA, repo / "saida", repo=repo, dist=dist, conferir_git=False)
    afirmar("TucoTeca-Setup-1.2.0-x64.exe" in msg and "1.1.0" in msg, msg)


def teste_release_recusa_estado_pessoal_e_runtime_ausente():
    for extra in ("dados/biblioteca.db", ".biblioteca.lock", "codigo/saves/x.sav"):
        repo = _repo_falso()
        dist = _dist_falso(repo, extra=extra)
        msg = _erro(REL.preparar, SHA, repo / "saida", repo=repo, dist=dist, conferir_git=False)
        afirmar("estado pessoal" in msg, (extra, msg))
        afirmar(not (repo / "saida").exists())
    repo = _repo_falso()
    dist = _dist_falso(repo, runtime=False)
    afirmar("Python embutido" in _erro(REL.preparar, SHA, repo / "s", repo=repo, dist=dist,
                                       conferir_git=False))
    r = REL.preparar(SHA, repo / "s", repo=repo, dist=dist, conferir_git=False, exigir_runtime=False)
    afirmar("Atenção" in (Path(r["saida"]) / "NOTAS-RELEASE.md").read_text(encoding="utf-8"))


def teste_release_nao_sobrescreve_e_exige_sha_completo():
    repo = _repo_falso()
    dist = _dist_falso(repo)
    saida = repo / "existe"
    saida.mkdir()
    afirmar("já existe" in _erro(REL.preparar, SHA, saida, repo=repo, dist=dist, conferir_git=False))
    afirmar("SHA" in _erro(REL.verificar_revisao, "abc123", repo))


def _zip_embed(conteudo: dict[str, bytes]) -> Path:
    caminho = Path(tempfile.mkdtemp(prefix="suite-embed-")) / "embed.zip"
    with zipfile.ZipFile(caminho, "w") as z:
        for nome, dados in conteudo.items():
            z.writestr(nome, dados)
    return caminho


def teste_runtime_python_confere_hash_e_troca_pasta():
    zip_ok = _zip_embed({"python.exe": b"MZ", "python314.zip": b"PK"})
    sha = hashlib.sha256(zip_ok.read_bytes()).hexdigest()
    destino = zip_ok.parent / "programa/windows-x64/python"
    destino.mkdir(parents=True)
    (destino / "velho.txt").write_text("antigo")
    r = RUNTIME.instalar(zip_ok, destino, sha256=sha)
    afirmar(r["ok"] and (destino / "python.exe").is_file(), r)
    afirmar(not (destino / "velho.txt").exists(), "pasta antiga não foi trocada")
    afirmar(json.loads((destino / RUNTIME.MARCADOR).read_text(encoding="utf-8"))["sha256_zip"] == sha)
    afirmar(sorted(p.name for p in destino.parent.iterdir()) == ["python"], "sobrou staging")
    # hash errado: nada muda
    afirmar("divergente" in _erro(RUNTIME.instalar, zip_ok, destino, sha256="0" * 64))
    afirmar((destino / "python.exe").is_file())
    # zip que não é o embeddable ou com caminho inseguro
    sem_exe = _zip_embed({"leia.txt": b"x"})
    afirmar("python.exe" in _erro(RUNTIME.instalar, sem_exe, sem_exe.parent / "py",
                                  sha256=hashlib.sha256(sem_exe.read_bytes()).hexdigest()))
    inseguro = _zip_embed({"../fora.txt": b"x", "python.exe": b"MZ"})
    afirmar("inseguro" in _erro(RUNTIME.instalar, inseguro, inseguro.parent / "py",
                                sha256=hashlib.sha256(inseguro.read_bytes()).hexdigest()))
    afirmar(not (inseguro.parent / "fora.txt").exists())


def teste_versoes_do_repositorio_coerentes():
    """O próprio checkout precisa passar no gate de versão do preparador."""
    versao = REL.ler_versao(REL.REPO)
    afirmar(versao == (REL.REPO / "VERSION").read_text(encoding="utf-8").strip(), versao)


def teste_icone_ico_valido_e_reproduzivel():
    destino = Path(tempfile.mkdtemp(prefix="suite-icone-"))
    [ico] = ICONE.gerar(destino)
    dados = ico.read_bytes()
    afirmar(dados[:4] == b"\0\0\1\0", "cabeçalho ICO")
    afirmar(int.from_bytes(dados[4:6], "little") == len(ICONE.TAMANHOS))
    afirmar(b"\x89PNG" in dados)
    afirmar(ICONE.gerar(destino)[0].read_bytes() == dados, "ícone não é reproduzível")
    versionado = REL.REPO / "codigo/frontends/electron/resources/icon.ico"
    afirmar(versionado.read_bytes() == dados, "icon.ico versionado difere do gerador")


def teste_fontes_incluem_electron_sem_artefatos():
    repo = _repo_falso()
    app = repo / "codigo/frontends/electron"
    for nome in ("package.json", "electron-builder.config.cjs", "resources/icon.ico",
                 "src/main/index.ts", "src/renderer/src/app.tsx", "src/renderer/index.html",
                 "src/renderer/src/estilo.css", "node_modules/electron/index.js",
                 "out/main/index.js", "dist/TucoTeca-Setup-1.2.0-x64.exe"):
        (app / nome).parent.mkdir(parents=True, exist_ok=True)
        (app / nome).write_text("x", encoding="utf-8")
    nomes = {p.relative_to(repo).as_posix() for p in REL.listar_fontes(repo)}
    base = "codigo/frontends/electron/"
    for nome in ("package.json", "electron-builder.config.cjs", "resources/icon.ico",
                 "src/main/index.ts", "src/renderer/src/app.tsx", "src/renderer/index.html",
                 "src/renderer/src/estilo.css"):
        afirmar(base + nome in nomes, (nome, sorted(nomes)))
    afirmar(not any(n.startswith((base + "node_modules", base + "out/", base + "dist/"))
                    for n in nomes), sorted(nomes))
