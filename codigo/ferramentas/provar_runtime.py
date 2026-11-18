"""Provas nativas opcionais, fora da suíte hermética (nunca tocam a instalação pessoal).

    py -3.14 -B codigo/ferramentas/provar_runtime.py qbit [--configurar-offline]
        qBittorrent isolado: API, torrent local, pausa/retomada.
    py -3.14 -B codigo/ferramentas/provar_runtime.py rede --saida PASTA [...]
        provedores oficiais (LRCLIB, LibRetro, SponsorBlock e, se pedido,
        yt-dlp/FFmpeg, catálogos e um vídeo público curto). Não baixa jogos nem
        exige credenciais; falha externa é relatada, não vira sucesso.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ---------------------------------------------------------------- qBittorrent

def _benc(valor):
    if isinstance(valor, int):
        return b"i" + str(valor).encode() + b"e"
    if isinstance(valor, bytes):
        return str(len(valor)).encode() + b":" + valor
    if isinstance(valor, dict):
        return b"d" + b"".join(_benc(k) + _benc(valor[k]) for k in sorted(valor)) + b"e"
    raise ValueError("tipo de fixture inválido")


def esperar(trabalho, pronto, timeout=25):
    limite = time.monotonic() + timeout
    ultimo = None
    while time.monotonic() < limite:
        try:
            ultimo = trabalho()
            if pronto(ultimo):
                return ultimo
        except Exception as e:
            ultimo = str(e)
        time.sleep(0.2)
    raise RuntimeError("qBittorrent não respondeu como esperado: " + str(ultimo))


def provar_qbit():
    from bib_nucleo import qbit as Q
    from bib_nucleo import qbit as nucleo_qbit
    inicio = nucleo_qbit.qbit_iniciar()
    if not inicio["ok"]:
        raise RuntimeError(inicio["erro"])
    handle = None
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.OpenProcess.restype = wintypes.HANDLE
        k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = k.OpenProcess(0x100001, False, inicio["pid"])
    try:
        ver = esperar(lambda: Q.qbit_request("app/version"), lambda s: s.startswith("v"))
        raw = b"offline-proof" * 1024
        nome = b"offline-proof.bin"
        info = {b"name": nome, b"length": len(raw), b"piece length": 16384,
                b"pieces": hashlib.sha1(raw).digest()}
        h = hashlib.sha1(_benc(info)).hexdigest()
        dest = Path(inicio["destino"])
        (dest / nome.decode()).write_bytes(raw)
        arq = dest.parent / "offline-proof.torrent"
        arq.write_bytes(_benc({b"info": info}))
        adicionar = nucleo_qbit.qbit_iniciar(str(arq))
        if not adicionar["ok"]:
            raise RuntimeError(adicionar["erro"])
        r = esperar(nucleo_qbit.qbit_listar, lambda r: any(t["hash"] == h and t["completo"] for t in r["torrents"]))
        t = next(t for t in r["torrents"] if t["hash"] == h)
        assert t["pct"] == 100 and Path(t["save_path"]) == dest / nome.decode(), t
        assert nucleo_qbit.qbit_controlar(h, "pausar")["ok"]
        esperar(nucleo_qbit.qbit_listar, lambda r: any(t["hash"] == h and t["estado"] == "stoppedUP" for t in r["torrents"]))
        assert nucleo_qbit.qbit_controlar(h, "retomar")["ok"]
        esperar(nucleo_qbit.qbit_listar, lambda r: any(t["hash"] == h and t["estado"] != "stoppedUP" for t in r["torrents"]))
        return {"versao": ver, "pct": t["pct"], "pausa_retomada": True, "destino": "perfil temporário"}
    finally:
        try:
            Q.qbit_request("app/shutdown", {})
        except Exception:
            pass
        if handle:
            if k.WaitForSingleObject(handle, 8000) == 0x102:
                k.TerminateProcess(handle, 1)  # exclusivamente o processo desta prova
                k.WaitForSingleObject(handle, 5000)
            k.CloseHandle(handle)
        else:
            time.sleep(2)


# ---------------------------------------------------------------- rede

def provar_rede(args):
    saida = Path(args.saida).resolve()
    saida.mkdir(parents=True, exist_ok=True)
    for chave in list(os.environ):
        if chave.startswith("BIBLIOTECA_"):
            os.environ.pop(chave)
    with tempfile.TemporaryDirectory(prefix="rede-prova-", dir=saida) as tmp:
        os.environ["BIBLIOTECA_HOME"] = tmp
        from bib_nucleo import baixar
        from bib_nucleo.banco import get_db, listar_musicas, listar_videos
        from bib_nucleo.base import DEFAULT_DB
        from bib_nucleo.rede import capas_libretro, fontes, letras, sponsorblock, videos_youtube
        resultados = {}
        def testar(nome, trabalho):
            try:
                r = trabalho()
                resultado = {"status": "OK", "resultado": r}
            except Exception as e:
                resultado = {"status": "falha externa", "erro": str(e)}
            resultados[nome] = resultado
            print(nome + ": " + json.dumps(resultado, ensure_ascii=False), flush=True)
        destino = saida / "ferramentas"
        if args.instalar_audio:
            def instalar(trabalho):
                r = trabalho(destino=destino)
                if not r.get("ok"):
                    raise ValueError(r.get("erro", "instalação não concluída"))
                exe = r["path"]
                cmd = [exe, "--version" if Path(exe).name == "yt-dlp.exe" else "-version"]
                run = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=45)
                if run.returncode:
                    raise ValueError("Ferramenta instalada não executou: " + run.stderr[-1000:])
                return {"bytes": r["bytes"], "sha_verificado": True, "versao": run.stdout.splitlines()[0]}
            with ThreadPoolExecutor(max_workers=2) as pool:
                fs = [pool.submit(testar, n, lambda f=f: instalar(f)) for n, f in (
                    ("yt-dlp-instalar", baixar.instalar_ytdlp), ("ffmpeg-instalar", baixar.instalar_ffmpeg))]
                for f in fs:
                    f.result()
        for chave, nome in (("BIBLIOTECA_YTDLP", "yt-dlp.exe"), ("BIBLIOTECA_FFMPEG", "ffmpeg.exe")):
            if (destino / nome).is_file():
                os.environ[chave] = str(destino / nome)
        def letra():
            r = letras.buscar_letras("Rick Astley", "Never Gonna Give You Up", "Whenever You Need Somebody", 213)
            if not r.get("ok"):
                raise ValueError(r["erro"])
            return {"sincronizadas": r["sincronizadas"], "linhas": len(r["linhas"])}
        def capa():
            r = capas_libretro.buscar_capa_libretro("NDS", "New Super Mario Bros. (USA)")
            return {"bytes": len(r["raw"]), "ext": r["ext"], "nome": "No-Intro exato"}
        if not args.somente_youtube:
            testar("lrclib", letra)
            testar("libretro", capa)
            testar("sponsorblock", lambda: {"segmentos": len(sponsorblock.buscar_segmentos(args.video_teste))})
        if args.catalogos:
            for nome, f in (("steamrip", fontes.buscar_steamrip), ("fitgirl", fontes.buscar_fitgirl)):
                def consultar(f=f):
                    r = f("Hollow Knight")
                    if r.get("erros") and not r.get("itens"):
                        raise ValueError("; ".join(str(e) for e in r["erros"]))
                    return {"itens": len(r.get("itens") or []), "baixou_jogos": False}
                testar(nome, consultar)
        if args.youtube:
            con = get_db(DEFAULT_DB)
            try:
                def baixar(f, listar):
                    r = f(con, args.video_teste)
                    if not r.get("ok"):
                        raise ValueError(r.get("erro", "download não concluído"))
                    return {"bytes": Path(r["path"]).stat().st_size, "itens_colecao": len(listar(con)), "sha": r["sha"]}
                testar("youtube-mp3", lambda: baixar(videos_youtube.baixar_audio_youtube, listar_musicas))
                testar("youtube-mp4", lambda: baixar(videos_youtube.baixar_video_youtube, listar_videos))
            finally:
                con.close()
    report = "youtube-runtime.json" if args.somente_youtube else "rede-runtime.json"
    (saida / report).write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="prova", required=True)
    pq = sub.add_parser("qbit", help="qBittorrent isolado")
    pq.add_argument("--configurar-offline", action="store_true")
    pr = sub.add_parser("rede", help="provedores oficiais (opt-in)")
    pr.add_argument("--saida", required=True)
    pr.add_argument("--instalar-audio", action="store_true")
    pr.add_argument("--youtube", action="store_true")
    pr.add_argument("--catalogos", action="store_true")
    pr.add_argument("--somente-youtube", action="store_true")
    pr.add_argument("--video-teste", default="jNQXAC9IVRw",
                    help="ID de vídeo público curto; default: Me at the zoo (19 s)")
    args = p.parse_args()
    if args.prova == "rede":
        provar_rede(args)
        return
    if args.configurar_offline:
        from bib_nucleo import qbit as Q
        # Só o perfil explicitamente passado pelo builder, nunca o perfil do PC.
        cfg = Q.qbit_preparar_perfil()
        texto = cfg.read_text(encoding="utf-8")
        texto = texto.replace("[BitTorrent]\n", "[BitTorrent]\nSession\\DHTEnabled=false\nSession\\LSDEnabled=false\nSession\\PeXEnabled=false\n")
        cfg.write_text(texto, encoding="utf-8")
    print(json.dumps(provar_qbit()))


if __name__ == "__main__":
    main()
