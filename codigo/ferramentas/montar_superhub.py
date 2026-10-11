#!/usr/bin/env python3
"""Runtime Windows independente: ferramentas locais, perfis vazios, ZIP/7z."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

import montar_portatil as MP

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

LEIAME = """TUCOTECA SUPERHUB — Windows x64, portátil

Extraia toda a pasta e abra BibliotecaHub.bat. Não precisa instalar Python,
emuladores ou ferramentas no Windows. Tudo usa os caminhos desta pasta.

app/          fontes Python locais, editáveis
python/       Python + Tk + suporte de imagem
ferramentas/  7-Zip, FFmpeg, yt-dlp, QuickJS-NG e qBittorrent
emuladores/   Azahar e DeSmuME com perfis novos
dados/        sua coleção e perfis; criada/usada localmente
manifesto-runtime.json  componentes, versões, tamanhos e SHA-256

Downloads > Iniciar cliente abre o qBittorrent do Hub em um perfil independente.
Magnets abertos no catálogo são encaminhados a ele, sem associação do Windows.
Velocidade, ETA, pausar e retomar usam sua API local em 127.0.0.1.

O programa, ferramentas, imagens locais e emulação funcionam sem rede.
Obter conteúdo, buscar catálogos/capas e atualizar componentes usa a internet.

Saves, ROMs, mods e sua coleção viajam pelo pacote de coleção do próprio Hub.
Este runtime começa com dados/perfis novos. Para atualizar, preserve dados/.
Licenças e URLs dos fontes ficam junto de cada componente e no manifesto.
"""


def sha_arquivo(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def baixar_verificado(url: str, nome: str, sha: str = "") -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / nome
    if p.is_file() and (not sha or sha_arquivo(p) == sha):
        return p
    tmp = p.with_suffix(p.suffix + ".part")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TucoTeca-build"})
        with urllib.request.urlopen(req, timeout=90) as r, tmp.open("wb") as f:
            shutil.copyfileobj(r, f, 1024 * 256)
        if sha and sha_arquivo(tmp) != sha:
            raise ValueError("SHA-256 divergente: " + nome)
        tmp.replace(p)
    finally:
        if tmp.exists():
            tmp.unlink()
    return p


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
    componentes = {}
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
            if p.is_file() and not any(l in p.name for l in ("pt_BR", "_en", "_pt.")):
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


def incluir_qt(raiz: Path):
    """Qt Quick completo, plugins e licenças das wheels fixadas no requirements."""
    from importlib.metadata import distribution
    for nome in ("PySide6-Essentials", "shiboken6"):
        dist = distribution(nome)
        if dist.version != "6.10.2":
            raise ValueError("Instale requirements-ui.txt antes de montar o runtime Qt.")
        for arquivo in dist.files or []:
            if ".." in arquivo.parts or "__pycache__" in arquivo.parts or arquivo.suffix == ".pyc":
                continue
            origem = Path(dist.locate_file(arquivo))
            if origem.is_file():
                destino = raiz / "python/Lib" / str(arquivo)
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(origem, destino)
    return "6.10.2"


def criar_manifesto(raiz: Path, componentes: dict, versoes: dict) -> dict:
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
    (raiz / "manifesto-runtime.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifesto


def validar_runtime(raiz: Path) -> dict:
    """Executa exclusivamente binários do pacote em uma casa vazia e sem PATH externo."""
    py = raiz / "python/python.exe"
    env = {k: v for k, v in os.environ.items() if not k.startswith("BIBLIOTECA_")}
    env["PATH"] = str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32")
    env["PYTHONIOENCODING"] = "utf-8"
    serie = json.loads((raiz / "manifesto-runtime.json").read_text(encoding="utf-8"))["versoes"]["serie_tk"]
    env["TCL_LIBRARY"] = str(raiz / "python/tcl" / ("tcl" + serie))
    env["TK_LIBRARY"] = str(raiz / "python/tcl" / ("tk" + serie))
    resultados = {}
    with tempfile.TemporaryDirectory(prefix="superhub-prova-", dir=CACHE) as tmp:
        env["BIBLIOTECA_HOME"] = str(raiz)  # testa descoberta da própria árvore
        script = ("import bib_core as c; from pathlib import Path; "
                  "assert c.runtime_portatil(); "
                  "assert all(c.localizar_ferramenta(n) for n in ('7z','ffmpeg','ytdlp','quickjs','qbittorrent')); "
                  "assert str(c.default_emu_3ds()).startswith(str(c.HOME_DIR)); "
                  "assert str(c.default_emu_nds()).startswith(str(c.HOME_DIR)); "
                  "from PIL import Image, ImageTk; import tkinter as tk; "
                  "im=Image.new('RGB',(16,16),'red'); im.save('prova.jpg'); "
                  "im2=Image.open('prova.jpg'); assert im2.size==(16,16); "
                  "r=tk.Tk(); foto=ImageTk.PhotoImage(im2, master=r); r.destroy(); "
                  "print('runtime local OK; JPEG e PhotoImage OK')")
        comandos = {"python-tk-pillow": [str(py), "-c", script],
                    "ffmpeg": [str(raiz / "ferramentas/ffmpeg/ffmpeg.exe"), "-version"],
                    "7zip": [str(raiz / "ferramentas/7zip/7z.exe"), "i"],
                    "ytdlp": [str(py), str(raiz / "ferramentas/yt-dlp/yt-dlp.pyz"), "--version"],
                    "quickjs": [str(raiz / "ferramentas/quickjs/qjs.exe"), "-e", "console.log(1+1)"]}
        for nome, comando in comandos.items():
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
        r = subprocess.run([str(ff), "-v", "error", "-y", "-i", str(wav), "-codec:a", "libmp3lame", str(mp3)],
                           env=env, capture_output=True, timeout=30)
        if r.returncode or not mp3.is_file():
            raise ValueError("conversão MP3 não funcionou no FFmpeg empacotado")
        resultados["audio-mp3"] = {"bytes": mp3.stat().st_size, "ok": True}
        env["BIBLIOTECA_QBIT_PROFILE"] = str(Path(tmp) / "perfis")
        env["BIBLIOTECA_JOGOS_DIR"] = str(Path(tmp) / "downloads")
        r = subprocess.run([str(py), str(REPO / "codigo/ferramentas/provar_qbit_runtime.py"),
                            "--configurar-offline"], env=env, cwd=tmp,
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        if r.returncode:
            raise ValueError("qBittorrent integrado falhou: " + r.stderr[-2000:])
        resultados["qbittorrent"] = json.loads(r.stdout.strip())
        # Selftest não deixa banco de prova no runtime a distribuir.
        env["BIBLIOTECA_HOME"] = tmp
        env["BIBLIOTECA_AZAHAR_DIR"] = str(raiz / "emuladores/Azahar")
        env["BIBLIOTECA_DESMUME_DIR"] = str(raiz / "emuladores/DeSmuME")
        r = subprocess.run([str(py), str(raiz / "app/desktop.py"), "--selftest"], env=env,
                           cwd=tmp, capture_output=True, text=True, encoding="utf-8", timeout=60)
        if r.returncode or "[ok] selftest" not in r.stdout:
            raise ValueError("UI do runtime falhou: " + r.stderr[-1000:])
        resultados["ui"] = {"saida": r.stdout.strip()}
    return resultados


def empacotar(raiz: Path, formato="todos") -> list[Path]:
    DIST.mkdir(parents=True, exist_ok=True)
    hoje = datetime.date.today().strftime("%Y%m%d")
    saidas = []
    if formato in ("zip", "todos"):
        p = DIST / f"tucoteca-superhub-windows-x64-{hoje}.zip"
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for f in sorted(raiz.rglob("*")):
                z.write(f, f.relative_to(raiz))
        with zipfile.ZipFile(p) as z:
            if z.testzip():
                raise ValueError("ZIP gerado está corrompido")
        saidas.append(p)
    if formato in ("7z", "todos"):
        p = DIST / f"tucoteca-superhub-windows-x64-{hoje}.7z"
        if p.exists():
            p.unlink()
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


def montar(formato="todos", reutilizar=False):
    anterior = MP.BUILD
    MP.BUILD = BUILD
    try:
        if reutilizar:
            raiz = BUILD
            manifesto = json.loads((raiz / "manifesto-runtime.json").read_text(encoding="utf-8"))
            MP.copiar_app(raiz / "app")
            componentes, v = manifesto["componentes"], manifesto["versoes"]
        else:
            raiz, v = MP.montar_base(sem_azahar=True)
            componentes = incluir_componentes(raiz)
            incluir_pillow(raiz)
        v["qt"] = incluir_qt(raiz)
        (raiz / "README-PORTATIL.txt").write_text(LEIAME, encoding="utf-8")
        shutil.copy2(REPO / "LICENSE", raiz / "LICENSE-TucoTeca.txt")
        MP.podar_dieta(raiz)
        m = criar_manifesto(raiz, componentes, v)
        provas = validar_runtime(raiz)
        componentes["qbittorrent"]["versao"] = provas["qbittorrent"]["versao"].lstrip("v")
        m = criar_manifesto(raiz, componentes, v)
        rel = {"bytes_runtime": m["bytes_runtime"], "provas": provas,
               "componentes": componentes}
        (DIST / "superhub-verificacao.json").parent.mkdir(parents=True, exist_ok=True)
        (DIST / "superhub-verificacao.json").write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")
        saidas = empacotar(raiz, formato)
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
                comprovacao = validar_runtime(extraido)
                rel["arquivos"].append({"nome": arquivo.name, "bytes": arquivo.stat().st_size,
                                         "sha256": sha_arquivo(arquivo), "provas_extraido": comprovacao})
                print(f"[ok] runtime extraído de {arquivo.name}: componentes e API local verificados")
        (DIST / "superhub-verificacao.json").write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")
        return saidas
    finally:
        MP.BUILD = anterior


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--formato", choices=("zip", "7z", "todos"), default="todos")
    ap.add_argument("--reutilizar", action="store_true", help="atualiza fontes no runtime já montado")
    args = ap.parse_args()
    montar(args.formato, args.reutilizar)


if __name__ == "__main__":
    main()
