#!/usr/bin/env python3
"""Runtime Windows independente: ferramentas locais, perfis vazios, ZIP/7z."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import montar_portatil as MP
from build_utils import baixar_verificado, sha_arquivo

REPO = MP.REPO
CACHE = MP.CACHE / "superhub"
BUILD = MP.BUILD.parent / "superhub"
DIST = MP.DIST / "windows"

ASSETS = {
    "ytdlp": ("https://github.com/yt-dlp/yt-dlp/releases/download/2026.08.19/yt-dlp",
              "yt-dlp.pyz", "1fa6733c37ea6fb51c99ad8fe785e7b7e5f3246c9b980230329d4fb72ed8d4d6", "2026.08.19"),
    "quickjs": ("https://github.com/quickjs-ng/quickjs/releases/download/v0.17.0/qjs-windows-x86_64.exe",
                "qjs.exe", "2aeabf0092c3262d6b2609824418f7dd7ed1f1df939f73b2b15645230cac0d77", "0.17.0"),
}

LICENCAS_QT = {
    "LGPL-3.0-only": "da7eabb7bafdf7d3ae5e9f223aa5bdc1eece45ac569dc21b3b037520b4464768",
    "GPL-3.0-only": "8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903",
    "GPL-2.0-only": "8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643",
}

LEIAME = """TUCOTECA SUPERHUB — Windows x64, portátil

Extraia toda a pasta e abra TucoTeca.bat (BibliotecaHub.bat é alias legado). Não precisa instalar Python,
emuladores ou ferramentas no Windows. Tudo usa os caminhos desta pasta.

app/          fontes Python locais, editáveis
python/       Python + suporte de imagem
ferramentas/  7-Zip, FFmpeg, yt-dlp, QuickJS-NG e qBittorrent
emuladores/   Azahar e DeSmuME com perfis novos
dados/        sua coleção e perfis; criada/usada localmente
manifesto-runtime.json  componentes, versões, tamanhos e SHA-256

Variantes: a "completa" inclui QtWebEngine (YouTube dentro do Hub) e player
interno QtMultimedia. A "essencial" não inclui Chromium e abre o YouTube no
navegador do sistema. Gamepad não está implementado. Tamanhos no relatório.

Downloads > Iniciar cliente abre o qBittorrent do Hub em um perfil independente.
Magnets abertos no catálogo são encaminhados a ele, sem associação do Windows.
Velocidade, ETA, pausar e retomar usam sua API local em 127.0.0.1.

O programa, ferramentas, imagens locais e emulação funcionam sem rede.
Obter conteúdo, buscar catálogos/capas e atualizar componentes usa a internet.
BIBLIOTECA_REDE=0 bloqueia ações remotas do Hub; não é firewall de ferramentas externas.

O pacote de coleção inclui metadados, capas, músicas, presets e saves de
emuladores selecionados. Ele não inclui os executáveis dos jogos nem as ROMs.
Este runtime começa com dados/perfis novos. Para atualizar, preserve dados/.
Licenças e URLs dos fontes ficam junto de cada componente e no manifesto.
"""


def copiar_runtime(origem: Path, destino: Path, excluir=()) -> dict:
    """Somente árvore de runtime: não inclui estado, debug ou arquivos de outro SO."""
    podados = bytes_copiados = 0
    destino.mkdir(parents=True, exist_ok=True)
    for pasta, dirs, nomes in os.walk(origem, followlinks=False):
        mantidos = []
        for d in dirs:
            p = Path(pasta, d)
            if d in excluir or p.is_symlink() or getattr(p.lstat(), "st_file_attributes", 0) & 0x400:
                continue
            mantidos.append(d)
        dirs[:] = mantidos
        for nome in nomes:
            p = Path(pasta, nome)
            if p.is_symlink():
                continue
            if (p.suffix.lower() in (".pdb", ".bak", ".log", ".appimage", ".pyc", ".ini")
                    or nome.lower().startswith("uninst") or nome == "azahar-room.exe"):
                podados += p.stat().st_size
                continue
            alvo = destino / p.relative_to(origem)
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, alvo)
            bytes_copiados += p.stat().st_size
    return {"copiados": bytes_copiados, "podados": podados}


def _nota(destino, projeto, versao, fonte, licenca):
    (destino / "FONTE.txt").write_text(
        f"{projeto}\nVersão: {versao}\nFonte/redistribuição: {fonte}\nLicença: {licenca}\n"
        "Executável original, agregado como processo independente.\n", encoding="utf-8")


def _registrar(componentes, nome, raiz, exe, versao, fonte, licenca, modo="nativo"):
    componentes[nome] = {"executavel": exe.relative_to(raiz).as_posix(), "versao": versao,
                         "fonte": fonte, "licenca": licenca, "modo": modo, "plataforma": "win32"}


def _dll_7z(exe: Path) -> Path:
    candidatos = [exe.parent / "7z.dll"]
    if os.name == "nt":
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, r"Software\7-Zip") as k:
                    candidatos.append(Path(winreg.QueryValueEx(k, "Path")[0]) / "7z.dll")
            except OSError:
                pass
    candidatos.append(Path(tempfile.gettempdir()) / "opencode/7z-full/7z.dll")
    for p in candidatos:
        if p.is_file():
            return p
    raise ValueError("7z.dll não encontrada junto do 7-Zip instalado")


def incluir_componentes(raiz: Path) -> dict:
    sys.path.insert(0, str(REPO / "codigo"))
    from bib_nucleo import baixar, emuladores, repacks
    from bib_nucleo.ferramentas import localizar_ferramenta
    componentes: dict[str, dict] = {}
    gpl = MP.garantir_gpl()
    az = emuladores.default_emu_3ds()
    dm = emuladores.default_emu_nds()
    for nome, exe, projeto, fonte in (("Azahar", az, "azahar.exe", MP.AZAHAR_URL),
                                      ("DeSmuME", dm, "desmume.exe", MP.DESMUME_URL)):
        if not exe or not Path(exe).is_file():
            raise ValueError(nome + " precisa estar disponível para montar o runtime completo")
        dest = raiz / "emuladores" / nome
        copiar_runtime(Path(exe).parent, dest, excluir=("user", "Battery", "States", "__pycache__"))
        if nome == "Azahar":
            (dest / "user").mkdir(exist_ok=True)
        shutil.copy2(gpl, dest / "COPYING.txt")
        ver = emuladores.azahar_versao_local() if nome == "Azahar" else emuladores.desmume_versao_local()
        _nota(dest, nome, ver, fonte, "GPL-2.0-or-later")
        _registrar(componentes, nome.lower(), raiz, dest / projeto, ver, fonte, "GPL-2.0-or-later")

    fer = raiz / "ferramentas"
    qb = localizar_ferramenta("qbittorrent")
    if not qb:
        raise ValueError("qBittorrent não encontrado para montar o runtime")
    dest = fer / "qbittorrent"
    copiar_runtime(Path(qb).parent, dest)
    # Translations da UI Qt apenas em português/inglês; resto está no próprio exe.
    trans = dest / "translations"
    if trans.is_dir():
        for p in trans.iterdir():
            if p.is_file() and not any(sufixo in p.name for sufixo in ("pt_BR", "_en", "_pt.")):
                p.unlink()
    shutil.copy2(gpl, dest / "COPYING.txt")
    _nota(dest, "qBittorrent", "5.2.4", "https://github.com/qbittorrent/qBittorrent", "GPL-2.0-or-later")
    _registrar(componentes, "qbittorrent", raiz, dest / "qbittorrent.exe", "5.2.4",
               "https://github.com/qbittorrent/qBittorrent", "GPL-2.0-or-later")

    exe7 = repacks.ferramenta_7z()
    if exe7 is None:
        raise ValueError("7-Zip não encontrado")
    dll7 = _dll_7z(exe7)
    dest = fer / "7zip"
    dest.mkdir(parents=True)
    shutil.copy2(exe7, dest / "7z.exe")
    shutil.copy2(dll7, dest / "7z.dll")
    for nome in ("License.txt", "readme.txt"):
        origem = dll7.parent / nome
        if origem.is_file():
            shutil.copy2(origem, dest / nome)
    if not (dest / "License.txt").exists():
        lic = baixar_verificado("https://raw.githubusercontent.com/ip7z/7zip/main/DOC/License.txt", "7zip-License.txt")
        shutil.copy2(lic, dest / "License.txt")
    _nota(dest, "7-Zip", "26.03", "https://www.7-zip.org", "LGPL + restrição unRAR; ver License.txt")
    _registrar(componentes, "7z", raiz, dest / "7z.exe", "26.03", "https://www.7-zip.org", "LGPL/unRAR")

    ff = baixar.localizar_ffmpeg()
    if not ff:
        raise ValueError("FFmpeg não encontrado")
    dest = fer / "ffmpeg"
    dest.mkdir(parents=True)
    shutil.copy2(ff, dest / "ffmpeg.exe")
    lic = baixar_verificado("https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/COPYING.GPLv3", "FFmpeg-COPYING.GPLv3")
    shutil.copy2(lic, dest / "COPYING.GPLv3")
    _nota(dest, "FFmpeg", "instalação local", "https://www.gyan.dev/ffmpeg/builds/", "GPL-3.0; ver configuração do binário")
    _registrar(componentes, "ffmpeg", raiz, dest / "ffmpeg.exe", "instalação local",
               "https://www.gyan.dev/ffmpeg/builds/", "GPL-3.0")

    for nome, sub, exe, fonte, licenca, arquivo_licenca in (
        ("ytdlp", "yt-dlp", "yt-dlp.pyz", "https://github.com/yt-dlp/yt-dlp", "Unlicense",
         "https://raw.githubusercontent.com/yt-dlp/yt-dlp/2026.08.19/LICENSE"),
        ("quickjs", "quickjs", "qjs.exe", "https://github.com/quickjs-ng/quickjs", "MIT",
         "https://raw.githubusercontent.com/quickjs-ng/quickjs/v0.17.0/LICENSE")):
        url, cache_nome, sha, ver = ASSETS[nome]
        origem = baixar_verificado(url, cache_nome, sha)
        dest = fer / sub
        dest.mkdir(parents=True)
        shutil.copy2(origem, dest / exe)
        shutil.copy2(baixar_verificado(arquivo_licenca, nome + "-LICENSE"), dest / "LICENSE")
        _nota(dest, nome, ver, fonte, licenca)
        _registrar(componentes, nome, raiz, dest / exe, ver, fonte, licenca,
                   "python" if nome == "ytdlp" else "nativo")

    return componentes


def incluir_pillow(raiz: Path):
    import PIL
    origem = Path(PIL.__file__).parent
    dest = raiz / "python/Lib/PIL"
    shutil.copytree(origem, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for p in dest.glob("*.pyd"):
        if p.name.startswith(("_avif", "_imagingft", "_imagingcms")):
            p.unlink()  # não usados por PNG/JPG/WebP/GIF nem pelo redimensionamento
    licencas = Path(sys.base_prefix) / "Lib/site-packages"
    for info in licencas.glob("pillow-*.dist-info"):
        if (info / "licenses").is_dir():
            shutil.copytree(info / "licenses", raiz / "python/LICENSES-Pillow", dirs_exist_ok=True)


def incluir_qt(raiz: Path, extras="essencial"):
    """Qt Quick completo, plugins e licenças das wheels fixadas no requirements."""
    from importlib.metadata import distribution
    nomes = ("PySide6-Essentials", "shiboken6") + (("PySide6-Addons",) if extras == "completo" else ())
    for nome in nomes:
        dist = distribution(nome)
        if dist.version != "6.10.2":
            raise ValueError("Instale codigo/ferramentas/requirements-ui.txt antes de montar o runtime Qt.")
        for arquivo in dist.files or []:
            if ".." in arquivo.parts or "__pycache__" in arquivo.parts or arquivo.suffix == ".pyc":
                continue
            origem = Path(str(dist.locate_file(arquivo)))
            if origem.is_file():
                destino = raiz / "python/Lib" / str(arquivo)
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(origem, destino)
    # Chromium só precisa das duas línguas usadas neste hub pessoal.
    for locales in (raiz / "python/Lib/PySide6").rglob("qtwebengine_locales"):
        for p in locales.glob("*.pak"):
            if p.stem not in ("en-US", "pt-BR"):
                p.unlink()
    incluir_licencas_qt(raiz)
    return "6.10.2"


def incluir_licencas_qt(raiz: Path):
    """As wheels só trazem o aviso comercial; inclui também os textos livres."""
    destino = raiz / "python/LICENSES-Qt"
    destino.mkdir(parents=True, exist_ok=True)
    for nome, sha in LICENCAS_QT.items():
        url = f"https://raw.githubusercontent.com/qt/qtbase/v6.10.2/LICENSES/{nome}.txt"
        origem = baixar_verificado(url, f"qt-6.10.2-{nome}.txt", sha)
        shutil.copy2(origem, destino / (nome + ".txt"))
    (destino / "FONTES.txt").write_text(
        "Qt / PySide6 / shiboken6 6.10.2, wheels originais, bibliotecas dinâmicas.\n"
        "Textos LGPL/GPL fornecidos em paralelo ao aviso comercial original.\n"
        "Qt: https://code.qt.io/cgit/qt/qtbase.git/?h=v6.10.2\n"
        "PySide6/shiboken6: https://code.qt.io/cgit/pyside/pyside-setup.git/?h=v6.10.2\n"
        "QtWebEngine (variante completa): https://code.qt.io/cgit/qt/qtwebengine.git/?h=v6.10.2\n"
        "Licenças/avisos dos módulos: https://doc.qt.io/qt-6/licensing.html\n"
        "Chromium: chrome://credits no WebEngine; avisos adicionais nos fontes.\n"
        "Pode substituir DLLs/bindings em python/Lib/PySide6 e python/Lib/shiboken6\n"
        "por versões compatíveis; não há proteção que impeça relink/modificação.\n",
        encoding="utf-8")


def validar_fontes_runtime(raiz: Path, repo: Path = REPO) -> dict:
    """Confere conteúdo e conjunto dos fontes copiados, inclusive ao reutilizar."""
    esperados = {destino: repo / origem for origem, destino in MP.arquivos_app(repo)}
    for origem, destino in (("codigo/bib_nucleo", "bib_nucleo"),
                            ("codigo/frontends/qml", "qml")):
        base = repo / origem
        for p in base.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix not in (".pyc", ".pyo"):
                esperados[(Path(destino) / p.relative_to(base)).as_posix()] = p
    app = raiz / "app"
    atuais = {p.relative_to(app).as_posix() for p in app.rglob("*") if p.is_file()
              and "__pycache__" not in p.parts and p.suffix not in (".pyc", ".pyo")}
    if atuais != set(esperados):
        raise ValueError("Fontes ausentes/obsoletos no runtime: " +
                         ", ".join(sorted(atuais ^ set(esperados))))
    hashes = {}
    for rel, origem in sorted(esperados.items()):
        sha = sha_arquivo(origem)
        if sha_arquivo(app / rel) != sha:
            raise ValueError("Fonte do runtime diverge da revisão: " + rel)
        hashes[rel] = sha
    resultado = {"arquivos": len(hashes), "sha256_arvore_app": hashlib.sha256(
        json.dumps(hashes, sort_keys=True).encode()).hexdigest()}
    congelado = repo / "MANIFESTO-FONTES.json"
    if congelado.is_file():
        resultado["sha256_manifesto_fontes"] = sha_arquivo(congelado)
    return resultado


def criar_manifesto(raiz: Path, componentes: dict, versoes: dict, fontes=None) -> dict:
    arquivos = {}
    for p in sorted(raiz.rglob("*")):
        if not p.is_file() or p.name == "manifesto-runtime.json":
            continue
        rel = p.relative_to(raiz).as_posix()
        if rel.startswith("dados/") or "/user/" in rel:
            continue
        arquivos[rel] = {"bytes": p.stat().st_size, "sha256": sha_arquivo(p)}
    manifesto = {"esquema": 1, "projeto": "TucoTeca SuperHub", "plataforma": "win32",
                 "arquitetura": "x64", "versoes": versoes, "componentes": componentes,
                 "arquivos": arquivos, "bytes_runtime": sum(d["bytes"] for d in arquivos.values())}
    if fontes is not None:
        manifesto["fontes"] = fontes
    (raiz / "manifesto-runtime.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifesto


def validar_runtime(raiz: Path, extras="essencial") -> dict:
    """Executa exclusivamente binários do pacote em uma casa vazia e sem PATH externo."""
    py = raiz / "python/python.exe"
    env = {k: v for k, v in os.environ.items() if not k.startswith("BIBLIOTECA_")}
    env["PATH"] = str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extras == "completo":
        env["TUCOTECA_EXTRAS"] = "completo"
    resultados = {}
    manifesto = json.loads((raiz / "manifesto-runtime.json").read_text(encoding="utf-8"))
    if manifesto["versoes"].get("extras") != extras:
        raise ValueError("Variante do manifesto não corresponde à prova solicitada.")
    if "fontes" in manifesto and validar_fontes_runtime(raiz) != manifesto["fontes"]:
        raise ValueError("Revisão dos fontes não corresponde ao manifesto do runtime.")
    for rel, info in manifesto["arquivos"].items():
        p = raiz / rel
        if raiz.resolve() not in p.resolve().parents or not p.is_file() or sha_arquivo(p) != info["sha256"]:
            raise ValueError("Arquivo divergente no manifesto: " + rel)
    # Quarentena curta para os perfis de terceiros: alguns componentes Win32
    # não resolvem Known Folders quando USERPROFILE/TEMP apontam a uma árvore
    # artificial profundamente aninhada. A prova de áudio continua criando
    # deliberadamente um WAV com caminho longo, não pula o transporte MCI.
    quarentena = Path(tempfile.gettempdir()) / "opencode"
    quarentena.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="superhub-prova-", dir=quarentena) as tmp:
        for chave, sub in (("APPDATA", "appdata"), ("LOCALAPPDATA", "localappdata"),
                           ("HOME", "home"), ("USERPROFILE", "home"), ("TEMP", "temp"), ("TMP", "temp")):
            pasta = Path(tmp) / sub
            pasta.mkdir(exist_ok=True)
            env[chave] = str(pasta)
        env["BIBLIOTECA_HOME"] = str(raiz)  # testa descoberta da própria árvore
        script = ("import bib_core as c; from pathlib import Path; "
                  "assert c.runtime_portatil(); "
                  "assert all(c.localizar_ferramenta(n) for n in ('7z','ffmpeg','ytdlp','quickjs','qbittorrent')); "
                  "assert str(c.default_emu_3ds()).startswith(str(c.HOME_DIR)); "
                  "assert str(c.default_emu_nds()).startswith(str(c.HOME_DIR)); "
                  "from importlib.util import find_spec; "
                  f"assert (find_spec('PySide6.QtWebEngineQuick') is not None)=={extras == 'completo'}; "
                  f"assert (find_spec('PySide6.QtMultimedia') is not None)=={extras == 'completo'}; "
                  "from PIL import Image; "
                  "im=Image.new('RGB',(16,16),'red'); im.save('prova.jpg'); "
                  "im2=Image.open('prova.jpg'); assert im2.size==(16,16); "
                  "print('runtime local OK; JPEG OK')")
        comandos = {"python-pillow": [str(py), "-c", script],
                    "ffmpeg": [str(raiz / "ferramentas/ffmpeg/ffmpeg.exe"), "-version"],
                    "7zip": [str(raiz / "ferramentas/7zip/7z.exe"), "i"],
                    "ytdlp": [str(py), str(raiz / "ferramentas/yt-dlp/yt-dlp.pyz"), "--version"],
                    "quickjs": [str(raiz / "ferramentas/quickjs/qjs.exe"), "-e", "console.log(1+1)"]}
        if extras == "completo":
            comandos["webengine"] = [str(py), "-c",
                                     "import PySide6.QtWebEngineQuick as q; print('webengine ok', q.__name__)"]
        for nome, comando in comandos.items():
            if comando[0] == str(py):
                comando.insert(1, "-B")
            inicio = time.monotonic()
            r = subprocess.run(comando, env=env, cwd=tmp, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=40)
            if r.returncode:
                raise ValueError(f"{nome} falhou no pacote: {r.stderr[-1500:]}")
            if nome == "7zip" and str(raiz / "ferramentas/7zip/7z.dll") not in r.stdout:
                raise ValueError("7-Zip carregou DLL externa")
            resultados[nome] = {"segundos": round(time.monotonic() - inicio, 3), "saida": r.stdout[:300]}
        import wave
        wav = Path(tmp) / "audio.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(22050)
            w.writeframes(b"\0" * 44100)
        mp3 = Path(tmp) / "audio.mp3"
        ff = raiz / "ferramentas/ffmpeg/ffmpeg.exe"
        rf = subprocess.run([str(ff), "-v", "error", "-y", "-i", str(wav), "-codec:a", "libmp3lame", str(mp3)],
                            env=env, capture_output=True, timeout=30)
        if rf.returncode or not mp3.is_file():
            raise ValueError("conversão MP3 não funcionou no FFmpeg empacotado")
        resultados["audio-mp3"] = {"bytes": mp3.stat().st_size, "ok": True}
        env["BIBLIOTECA_QBIT_PROFILE"] = str(Path(tmp) / "perfis")
        env["BIBLIOTECA_JOGOS_DIR"] = str(Path(tmp) / "downloads")
        r = subprocess.run([str(py), "-B", str(raiz / "app/provar_qbit_runtime.py"),
                            "--configurar-offline"], env=env, cwd=tmp,
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        if r.returncode:
            raise ValueError("qBittorrent integrado falhou: " + r.stderr[-2000:])
        resultados["qbittorrent"] = json.loads(r.stdout.strip())
        # Selftest não deixa banco de prova no runtime a distribuir.
        env["BIBLIOTECA_HOME"] = tmp
        env["BIBLIOTECA_AZAHAR_DIR"] = str(raiz / "emuladores/Azahar")
        env["BIBLIOTECA_DESMUME_DIR"] = str(raiz / "emuladores/DeSmuME")
        r = subprocess.run([str(py), "-B", str(raiz / "app/desktop.py"), "--selftest"], env=env,
                           cwd=tmp, capture_output=True, text=True, encoding="utf-8", timeout=60)
        if r.returncode or "[ok] selftest" not in r.stdout:
            raise ValueError("UI do runtime falhou: " + r.stderr[-1000:])
        resultados["ui"] = {"saida": r.stdout.strip()}
        # Não basta importar a DLL: renderiza QML e reproduz mídia real gerada
        # localmente. Chromium usa HTML local com interceptor bloqueando a rede.
        prova_qt = Path(tmp) / "qt"
        r = subprocess.run([str(py), "-B", str(raiz / "app/provar_qt_runtime.py"), "--extras", extras,
                            "--saida", str(prova_qt), "--ffmpeg", str(ff)], env=env, cwd=tmp,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=150)
        if r.returncode:
            raise ValueError("Qt nativo falhou no runtime: " + (r.stdout + r.stderr)[-4000:])
        resultados["qt-nativo"] = json.loads((prova_qt / "qt-runtime.json").read_text(encoding="utf-8"))
        r = subprocess.run([str(py), "-B", str(raiz / "app/provar_integracoes_locais.py"), "--saida", str(Path(tmp) / "locais")],
                           env=env, cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if r.returncode:
            raise ValueError("Integrações locais falharam no runtime: " + (r.stdout + r.stderr)[-2000:])
        resultados["integracoes-locais"] = json.loads(r.stdout.strip())
    pessoais = list((raiz / "dados").rglob("*")) if (raiz / "dados").exists() else []
    pessoais += list((raiz / "emuladores").rglob("*.dsv"))
    pessoais += list((raiz / "emuladores").rglob("*.sav"))
    if any(p.is_file() for p in pessoais):
        raise ValueError("Prova deixou estado/perfis no runtime; não empacote estes arquivos.")
    return resultados


def empacotar(raiz: Path, formato="todos", extras="essencial") -> list[Path]:
    DIST.mkdir(parents=True, exist_ok=True)
    versao = (raiz / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", versao):
        raise ValueError("VERSION inválida para nomear o pacote")
    tag = "completo" if extras == "completo" else "essencial"
    saidas = []
    if formato in ("zip", "todos"):
        p = DIST / f"tucoteca-{versao}-windows-x64-{tag}.zip"
        if p.exists():
            raise ValueError(f"pacote já existe; preserve-o antes de gerar outro: {p}")
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for f in sorted(raiz.rglob("*")):
                z.write(f, f.relative_to(raiz))
        with zipfile.ZipFile(p) as z:
            if z.testzip():
                raise ValueError("ZIP gerado está corrompido")
        saidas.append(p)
    if formato in ("7z", "todos"):
        p = DIST / f"tucoteca-{versao}-windows-x64-{tag}.7z"
        if p.exists():
            raise ValueError(f"pacote já existe; preserve-o antes de gerar outro: {p}")
        exe = raiz / "ferramentas/7zip/7z.exe"
        r = subprocess.run([str(exe), "a", str(p), ".\\*", "-t7z", "-mx=9",
                            "-m0=lzma2:d=64m", "-ms=on", "-mmt=2", "-bsp0"],
                           cwd=raiz, capture_output=True, timeout=900)
        if r.returncode:
            raise ValueError("7z não compactou: " + r.stderr.decode("utf-8", "replace"))
        r = subprocess.run([str(exe), "t", str(p), "-bsp0"], capture_output=True, timeout=120)
        if r.returncode:
            raise ValueError("7z gerado falhou na verificação")
        saidas.append(p)
    for p in saidas:
        print(f"[ok] {p.name}: {p.stat().st_size / 1048576:.2f} MB")
    return saidas


def _versoes_release(raiz: Path, versoes: dict, revisao: str, repo: Path | None = None) -> dict:
    """Grava versão/revisão no pacote sem herdar dado de runtime reutilizado."""
    repo = REPO if repo is None else Path(repo)
    if revisao and not re.fullmatch(r"[0-9a-f]{40}", revisao):
        raise ValueError("A revisão deve ser o SHA Git completo (40 caracteres hexadecimais).")
    versoes["tucoteca"] = (repo / "VERSION").read_text(encoding="utf-8").strip()
    versoes.pop("revisao_git", None)  # nunca herdar a revisão de um runtime reutilizado
    if revisao:
        versoes["revisao_git"] = revisao
    (raiz / "VERSION").write_text(versoes["tucoteca"] + "\n", encoding="utf-8")
    (raiz / "VERSAO.txt").write_text(
        f"TucoTeca {versoes['tucoteca']} — Windows x64, {versoes.get('extras', 'essencial')}\n"
        f"Revisão Git: {revisao or 'árvore de trabalho não identificada'}\n"
        f"Python: {versoes.get('python', '?')}\nQt: {versoes.get('qt', '?')}\n"
        "Componentes, licenças e hashes: manifesto-runtime.json\n", encoding="utf-8")
    return versoes


def montar(formato="todos", reutilizar=False, extras="essencial", revisao=""):
    anterior = MP.BUILD
    MP.BUILD = BUILD / extras
    if extras not in ("completo", "essencial"):
        raise SystemExit(f"--extras deve ser completo|essencial (veio {extras!r})")
    if revisao and not re.fullmatch(r"[0-9a-f]{40}", revisao):
        raise ValueError("A revisão deve ser o SHA Git completo (40 caracteres hexadecimais).")
    try:
        if reutilizar:
            raiz = MP.BUILD
            manifesto = json.loads((raiz / "manifesto-runtime.json").read_text(encoding="utf-8"))
            if manifesto["versoes"].get("extras") != extras:
                raise ValueError("Não reutilize um runtime de outra variante.")
            MP.copiar_app(raiz / "app")
            componentes, v = manifesto["componentes"], manifesto["versoes"]
        else:
            raiz, v = MP.montar_base(sem_azahar=True)
            componentes = incluir_componentes(raiz)
            incluir_pillow(raiz)
        v["qt"] = incluir_qt(raiz, extras)
        v["extras"] = "completo" if extras == "completo" else "essencial"
        _versoes_release(raiz, v, revisao)
        (raiz / "README-PORTATIL.txt").write_text(LEIAME, encoding="utf-8")
        shutil.copy2(REPO / "LICENSE", raiz / "LICENSE-TucoTeca.txt")
        MP.podar_dieta(raiz)
        fontes = validar_fontes_runtime(raiz)
        m = criar_manifesto(raiz, componentes, v, fontes)
        provas = validar_runtime(raiz, extras=extras)
        componentes["qbittorrent"]["versao"] = provas["qbittorrent"]["versao"].lstrip("v")
        ffmpeg = re.search(r"ffmpeg version (\S+)", provas["ffmpeg"]["saida"])
        if not ffmpeg:
            raise ValueError("FFmpeg não informou sua versão")
        componentes["ffmpeg"]["versao"] = ffmpeg[1]
        _nota(raiz / "ferramentas/ffmpeg", "FFmpeg", ffmpeg[1],
              componentes["ffmpeg"]["fonte"], componentes["ffmpeg"]["licenca"])
        m = criar_manifesto(raiz, componentes, v, fontes)
        rel = {"bytes_runtime": m["bytes_runtime"], "provas": provas,
               "componentes": componentes, "extras": extras, "fontes": fontes,
               "tucoteca": v.get("tucoteca", ""), "revisao_git": v.get("revisao_git", ""),
               "python": v.get("python", ""), "qt": v.get("qt", "")}
        verificacao = DIST / f"superhub-verificacao-{extras}.json"
        verificacao.parent.mkdir(parents=True, exist_ok=True)
        verificacao.write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")
        saidas = empacotar(raiz, formato, extras)
        # Prova da distribuição, não só da árvore usada para gerar o arquivo.
        rel["arquivos"] = []
        for arquivo in saidas:
            with tempfile.TemporaryDirectory(prefix="extraido-", dir=CACHE) as tmp:
                extraido = Path(tmp)
                if arquivo.suffix == ".zip":
                    with zipfile.ZipFile(arquivo) as z:
                        z.extractall(extraido)
                else:
                    r = subprocess.run([str(raiz / "ferramentas/7zip/7z.exe"), "x", str(arquivo),
                                        "-o" + str(extraido), "-y", "-bsp0"], capture_output=True, timeout=120)
                    if r.returncode:
                        raise ValueError("não extraiu o 7z gerado")
                comprovacao = validar_runtime(extraido, extras=extras)
                rel["arquivos"].append({"nome": arquivo.name, "bytes": arquivo.stat().st_size,
                                         "sha256": sha_arquivo(arquivo), "provas_extraido": comprovacao})
                print(f"[ok] runtime extraído de {arquivo.name}: componentes e API local verificados")
        verificacao.write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")
        (DIST / f"SHA256SUMS-{extras}.txt").write_text("".join(
            f'{a["sha256"]}  {a["nome"]}\n' for a in rel["arquivos"]), encoding="utf-8")
        return saidas
    finally:
        MP.BUILD = anterior


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--formato", choices=("zip", "7z", "todos"), default="todos")
    ap.add_argument("--reutilizar", action="store_true", help="atualiza fontes no runtime já montado")
    ap.add_argument("--extras", choices=("completo", "essencial"), default="essencial",
                     help="completo = QtWebEngine/Multimedia (sem gamepad); "
                          "essencial = leve, abre YouTube no navegador do sistema")
    ap.add_argument("--revisao", default="", help="SHA completo do checkout limpo/congelado para a release")
    args = ap.parse_args()
    montar(args.formato, args.reutilizar, args.extras, revisao=args.revisao)


if __name__ == "__main__":
    main()
