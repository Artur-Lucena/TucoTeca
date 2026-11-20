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
        "codigo/VERSION": versao + "\n",
        "pyproject.toml": f'[project]\nname = "tucoteca"\nversion = "{pyproject}"\n',
        "docs/CHANGELOG.md": (f"# Changelog\n\n## [{versao}] - 2026-11-11\n\n### Adicionado\n\n- Instalador.\n\n"
                         "## [1.0.0] - 2026-01-01\n\n- antigo\n") if changelog else "# Changelog\n",
        "README.md": "TucoTeca", "LICENSE": "MIT",
        # está na lista explícita E sai na varredura de docs/ (regressão de duplicata)
        "docs/CONTRIBUTING.md": "# Colaboração",
        "codigo/bib_nucleo/__init__.py": "# núcleo",
    }
    for nome, conteudo in arquivos.items():
        caminho = repo / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(conteudo, encoding="utf-8")
    return repo


def _dist_falso(repo: Path, versao="1.2.0", runtime=True, extra: str | None = None) -> Path:
    dist = repo / "codigo/frontends/electron/dist"
    recursos = dist / "win-unpacked/resources/tucoteca"
    for nome in REL.ESSENCIAIS_APP:
        if nome == "codigo/VERSION":
            continue
        (recursos / nome).parent.mkdir(parents=True, exist_ok=True)
        (recursos / nome).write_text("#", encoding="utf-8")
    (recursos / "codigo/VERSION").write_text(versao + "\n", encoding="utf-8")
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


def _mac_falso(repo: Path, versao="1.2.0", archs=("arm64", "x64")) -> Path:
    """dist do Mac: .app por arquitetura (como o electron-builder) e as .dmg."""
    dist = Path(tempfile.mkdtemp(prefix="suite-dist-mac-"))
    for arch in archs:
        plataforma = f"macos-{arch}"
        recursos = dist / REL.RECURSOS[plataforma]
        for nome in REL.ESSENCIAIS_APP:
            (recursos / nome).parent.mkdir(parents=True, exist_ok=True)
            (recursos / nome).write_text(versao + "\n" if nome == "codigo/VERSION" else "#", encoding="utf-8")
        py = recursos / "programa" / plataforma / "python"
        (py / "bin").mkdir(parents=True)
        (py / "bin/python3").write_bytes(b"\xcf\xfa\xed\xfe")
        (py / "TUCOTECA-RUNTIME.json").write_text('{"versao": "3.14.10"}', encoding="utf-8")
        (dist / REL.dmg_mac(versao, arch)).write_bytes(b"dmg " + arch.encode())
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
    afirmar(set(somas) == esperados - {"SHA256SUMS.txt", "NOTAS-RELEASE.md"}, somas)
    for nome, sha in somas.items():
        afirmar(hashlib.sha256((saida / nome).read_bytes()).hexdigest() == sha, nome)
    release = json.loads((saida / "release.json").read_text(encoding="utf-8"))
    afirmar(release["revisao"] == SHA and release["python_embutido"] is True, release)
    afirmar(release["python_versao"] == "3.14.7", release)
    notas = (saida / "NOTAS-RELEASE.md").read_text(encoding="utf-8")
    afirmar("Instalador." in notas and "antigo" not in notas, notas)
    afirmar("Executar assim mesmo" in notas and "Atenção" not in notas, notas)
    afirmar("NOTAS-RELEASE.md" not in json.loads((saida / "release.json").read_text(encoding="utf-8"))["anexos"])
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


def teste_release_com_dmgs_conferidas_no_mac():
    repo = _repo_falso()
    dist = _dist_falso(repo)
    mac = _mac_falso(repo)
    c = REL.conferir_mac(SHA, repo=repo, dist=mac)
    afirmar(set(c["dmgs"]) == {"TucoTeca-1.2.0-mac-arm64.dmg", "TucoTeca-1.2.0-mac-x64.dmg"}, c)
    afirmar(c["dmgs"]["TucoTeca-1.2.0-mac-x64.dmg"]["python_versao"] == "3.14.10", c)
    saida = repo / "dist/release/v1.2.0"
    r = REL.preparar(SHA, saida, repo=repo, dist=dist, conferir_git=False, mac=mac)
    afirmar({"TucoTeca-1.2.0-mac-arm64.dmg", "TucoTeca-1.2.0-mac-x64.dmg"} <= set(r["anexos"]), r)
    release = json.loads((saida / "release.json").read_text(encoding="utf-8"))
    afirmar(release["instaladores"]["TucoTeca-1.2.0-mac-arm64.dmg"]["plataforma"] == "macos-arm64", release)
    afirmar("TucoTeca-1.2.0-mac-x64.dmg" in (saida / "SHA256SUMS.txt").read_text(encoding="utf-8"))
    notas = (saida / "NOTAS-RELEASE.md").read_text(encoding="utf-8")
    afirmar("Apple Silicon" in notas and "Abrir Mesmo Assim" in notas and "Executar assim mesmo" in notas, notas)
    # .dmg trocada depois da conferência, ou conferência de outra revisão: recusa
    (mac / "TucoTeca-1.2.0-mac-x64.dmg").write_bytes(b"outra")
    afirmar("SHA-256" in _erro(REL.preparar, SHA, repo / "s1", repo=repo, dist=dist, conferir_git=False, mac=mac))
    mac2 = _mac_falso(repo)
    REL.conferir_mac("b" * 40, repo=repo, dist=mac2)
    afirmar("conferência do Mac" in _erro(REL.preparar, SHA, repo / "s3", repo=repo, dist=dist,
                                         conferir_git=False, mac=mac2))
    # Mac sem Python embutido no .app
    mac3 = _mac_falso(repo, archs=("arm64",))
    (mac3 / REL.RECURSOS["macos-arm64"] / "programa/macos-arm64/python/bin/python3").unlink()
    afirmar("Python embutido" in _erro(REL.conferir_mac, SHA, repo=repo, dist=mac3))


def _linux_falso(versao="1.2.0") -> Path:
    """dist do Linux: linux-unpacked (como o electron-builder) e o AppImage."""
    dist = Path(tempfile.mkdtemp(prefix="suite-dist-linux-"))
    recursos = dist / REL.RECURSOS["linux-x64"]
    for nome in REL.ESSENCIAIS_APP:
        (recursos / nome).parent.mkdir(parents=True, exist_ok=True)
        (recursos / nome).write_text(versao + "\n" if nome == "codigo/VERSION" else "#", encoding="utf-8")
    py = recursos / "programa/linux-x64/python"
    (py / "bin").mkdir(parents=True)
    (py / "bin/python3").write_bytes(b"\x7fELF")
    (py / "TUCOTECA-RUNTIME.json").write_text('{"versao": "3.14.10"}', encoding="utf-8")
    (dist / REL.appimage_linux(versao)).write_bytes(b"\x7fELF AppImage")
    return dist


def teste_release_com_appimage_conferido_no_linux():
    repo = _repo_falso()
    dist = _dist_falso(repo)
    linux = _linux_falso()
    c = REL.conferir_linux(SHA, repo=repo, dist=linux)
    nome = "TucoTeca-1.2.0-linux-x64.AppImage"
    afirmar(list(c["appimages"]) == [nome] and c["appimages"][nome]["python_versao"] == "3.14.10", c)
    mac = _mac_falso(repo)
    REL.conferir_mac(SHA, repo=repo, dist=mac)
    saida = repo / "dist/release/v1.2.0"
    r = REL.preparar(SHA, saida, repo=repo, dist=dist, conferir_git=False, mac=mac, linux=linux)
    afirmar(nome in r["anexos"], r)
    release = json.loads((saida / "release.json").read_text(encoding="utf-8"))
    plataformas = {i["plataforma"] for i in release["instaladores"].values()}
    afirmar(plataformas == {"windows-x64", "macos-arm64", "macos-x64", "linux-x64"}, release)
    notas = (saida / "NOTAS-RELEASE.md").read_text(encoding="utf-8")
    afirmar(f"chmod +x {nome}" in notas and "--no-sandbox" in notas, notas)
    (linux / nome).write_bytes(b"trocado")
    afirmar("SHA-256" in _erro(REL.preparar, SHA, repo / "s1", repo=repo, dist=dist, conferir_git=False, linux=linux))
    afirmar("ausente" in _erro(REL.conferir_linux, SHA, repo=repo, dist=_linux_falso(versao="1.1.0")))
    afirmar("SHA Git completo" in _erro(REL.conferir_linux, "abc", repo=repo, dist=linux))


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


def teste_runtime_python_mac_extrai_install_only():
    import io
    import tarfile
    if not hasattr(tarfile, "data_filter"):
        print("(Python sem o filtro seguro do tarfile: skip; o preparador recusa)")
        return
    tmp = Path(tempfile.mkdtemp(prefix="suite-runtime-mac-"))
    pacote = tmp / "cpython-mac.tar.gz"
    with tarfile.open(pacote, "w:gz") as tar:
        for nome, dados in (("python/bin/python3", b"#!bin"), ("python/lib/python3.14/os.py", b"# os")):
            info = tarfile.TarInfo(nome)
            info.size = len(dados)
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(dados))
    sha = hashlib.sha256(pacote.read_bytes()).hexdigest()
    destino = tmp / "programa/macos-arm64/python"
    r = RUNTIME.instalar(pacote, destino, sha256=sha, plataforma="macos-arm64")
    afirmar(r["ok"] and (destino / "bin" / "python3").is_file(), r)
    afirmar((destino / "lib/python3.14/os.py").is_file(), "lib não veio para a raiz do runtime")
    marca = json.loads((destino / RUNTIME.MARCADOR).read_text(encoding="utf-8"))
    afirmar(marca["plataforma"] == "macos-arm64" and marca["sha256_zip"] == sha, marca)
    # pacote fora do formato install_only (sem a pasta python/) é recusado
    torto = tmp / "torto.tar.gz"
    with tarfile.open(torto, "w:gz") as tar:
        info = tarfile.TarInfo("bin/python3")
        info.size = 1
        tar.addfile(info, io.BytesIO(b"x"))
    afirmar("install_only" in _erro(RUNTIME.instalar, torto, tmp / "py", plataforma="macos-x64",
                                    sha256=hashlib.sha256(torto.read_bytes()).hexdigest()))
    afirmar(RUNTIME.PLATAFORMAS["macos-x64"]["url"].endswith("x86_64-apple-darwin-install_only.tar.gz"))
    afirmar(RUNTIME.PLATAFORMAS["linux-x64"]["url"].endswith("x86_64-unknown-linux-gnu-install_only.tar.gz"))
    afirmar(all(len(p["sha256"]) == 64 for p in RUNTIME.PLATAFORMAS.values()))
    # o mesmo pacote serve de runtime do Linux (mesmo formato install_only)
    r = RUNTIME.instalar(pacote, tmp / "programa/linux-x64/python", sha256=sha, plataforma="linux-x64")
    afirmar(r["plataforma"] == "linux-x64" and (tmp / "programa/linux-x64/python/bin/python3").is_file(), r)


def teste_versoes_do_repositorio_coerentes():
    """O próprio checkout precisa passar no gate de versão do preparador."""
    versao = REL.ler_versao(REL.REPO)
    afirmar(versao == (REL.REPO / "codigo/VERSION").read_text(encoding="utf-8").strip(), versao)


def teste_icone_ico_valido_e_reproduzivel():
    """Formatos ICO/ICNS e os ícones versionados com os pixels do gerador.

    Só tamanhos pequenos são renderizados aqui: o desenho é o mesmo em todos e
    o de 256/1024 px em Python puro levaria dezenas de segundos.
    """
    pequenos = {lado: ICONE.png(lado) for lado in (16, 32)}
    ico = ICONE.ico(pequenos)
    afirmar(ico[:4] == b"\0\0\1\0" and int.from_bytes(ico[4:6], "little") == 2, "cabeçalho ICO")
    afirmar(ICONE.ico({lado: ICONE.png(lado) for lado in (16, 32)}) == ico, "ícone não é reproduzível")
    icns = ICONE.icns({lado: pequenos[16] for _, lado in ICONE.ICNS_TIPOS})
    afirmar(icns[:4] == b"icns" and int.from_bytes(icns[4:8], "big") == len(icns), "cabeçalho ICNS")
    recursos = REL.REPO / "codigo/frontends/electron/resources"
    cru = (recursos / "icon.icns").read_bytes()
    tipos, pos = [], 8
    while pos < len(cru):
        tipos.append(cru[pos:pos + 4].decode("ascii"))
        afirmar(cru[pos + 8:pos + 16] == b"\x89PNG\r\n\x1a\n", "entrada ICNS sem PNG")
        pos += int.from_bytes(cru[pos + 4:pos + 8], "big")
    afirmar(pos == len(cru) and tipos == [t for t, _ in ICONE.ICNS_TIPOS], tipos)
    # versionados: mesmos pixels do gerador (os bytes do PNG dependem do zlib do SO)
    pngs_ico = _pngs_ico((recursos / "icon.ico").read_bytes())
    afirmar(sorted(pngs_ico) == sorted(ICONE.TAMANHOS), sorted(pngs_ico))
    for lado in (16, 48):
        afirmar(pngs_ico[lado] == ICONE.renderizar(lado), f"icon.ico {lado}px difere do gerador")
    afirmar(_pngs_icns(cru)["ic11"] == ICONE.renderizar(32, 4, ICONE._pixel_mac), "icon.icns 32px difere do gerador")


def _pixels_png(png: bytes) -> bytes:
    """Linhas cruas (filtro + RGBA) de um PNG de um bloco IDAT, como o gerador escreve."""
    import zlib
    pos, idat = 8, b""
    while pos < len(png):
        n = int.from_bytes(png[pos:pos + 4], "big")
        if png[pos + 4:pos + 8] == b"IDAT":
            idat += png[pos + 8:pos + 8 + n]
        pos += 12 + n
    return zlib.decompress(idat)


def _pngs_ico(dados: bytes) -> dict:
    n = int.from_bytes(dados[4:6], "little")
    saida = {}
    for i in range(n):
        ent = dados[6 + 16 * i:22 + 16 * i]
        lado = ent[0] or 256
        tam, desl = int.from_bytes(ent[8:12], "little"), int.from_bytes(ent[12:16], "little")
        saida[lado] = _pixels_png(dados[desl:desl + tam])
    return saida


def _pngs_icns(dados: bytes) -> dict:
    saida, pos = {}, 8
    while pos < len(dados):
        n = int.from_bytes(dados[pos + 4:pos + 8], "big")
        saida[dados[pos:pos + 4].decode("ascii")] = _pixels_png(dados[pos + 8:pos + n])
        pos += n
    return saida


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


def teste_user_agent_segue_version():
    from bib_nucleo import versao
    esperado = (REL.REPO / "codigo/VERSION").read_text(encoding="utf-8").strip()
    afirmar(versao.versao_app() == esperado, versao.versao_app())
    afirmar(versao.user_agent().startswith(f"TucoTeca/{esperado} (+https://github.com/"), versao.user_agent())
    afirmar(versao.user_agent("x").endswith("; x)"), versao.user_agent("x"))
