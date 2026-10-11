"""Smoke opt-in dos provedores oficiais; nunca altera a instalação pessoal.

--instalar-audio publica yt-dlp/FFmpeg somente na pasta de provas escolhida.
--youtube baixa somente um vídeo público curto para verificar o fluxo real.
Não baixa jogos e não exige credenciais. Erros externos são relatados, não
transformados em um resultado de integração bem-sucedida.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rede", action="store_true", required=True)
    p.add_argument("--saida", required=True)
    p.add_argument("--instalar-audio", action="store_true")
    p.add_argument("--youtube", action="store_true")
    p.add_argument("--catalogos", action="store_true")
    p.add_argument("--somente-youtube", action="store_true")
    p.add_argument("--video-teste", default="jNQXAC9IVRw", help="ID de vídeo público curto; default: Me at the zoo (19 s)")
    args = p.parse_args()
    saida = Path(args.saida).resolve()
    saida.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(__file__).parent.parent))
    for chave in list(os.environ):
        if chave.startswith("BIBLIOTECA_"):
            os.environ.pop(chave)
    with tempfile.TemporaryDirectory(prefix="rede-prova-", dir=saida) as tmp:
        os.environ["BIBLIOTECA_HOME"] = tmp
        from bib_nucleo import baixar
        from bib_nucleo.rede import capas_libretro, fontes, letras, sponsorblock, videos_youtube
        from bib_nucleo.banco import get_db, listar_musicas, listar_videos
        from bib_nucleo.base import DEFAULT_DB
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


if __name__ == "__main__":
    main()
