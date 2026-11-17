"""2.0 — 9 integrações open source + YouTube: sem rede/processos reais."""
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import bib_core as core
from bib_nucleo import apps_externos as EI
from bib_nucleo import apps_externos as EQ
from bib_nucleo import apps_externos as RV
from bib_nucleo import online, spotify
from bib_nucleo import videos_youtube as YT
from executar import afirmar


def _arq(tmp, nome="a.bin", conteudo=b"dados-"):
    p = Path(tmp) / nome
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(conteudo)
    return str(p)


# -- editores de imagem (Krita/GIMP/PhotoDemon) -----------------------------

def teste_editores_localizar_env_e_invalido():
    tmp = tempfile.mkdtemp()
    exe = _arq(tmp, "krita-fake.exe" if os.name == "nt" else "krita", b"MZ" + b"0" * 64)
    Path(exe).chmod(0o755)
    try:
        os.environ["BIBLIOTECA_KRITA"] = exe
        afirmar(EI.localizar_editor("krita") == exe)
        os.environ["BIBLIOTECA_KRITA"] = str(Path(tmp) / "ausente.exe")
        afirmar(EI.localizar_editor("krita") == "")
        try:
            EI.localizar_editor("photoshop")
        except ValueError:
            pass
        else:
            raise AssertionError("aceitou editor inválido")
    finally:
        os.environ.pop("BIBLIOTECA_KRITA", None)


def teste_editores_abrir_validacoes():
    r = EI.abrir_no_editor("photoshop", "x.png")
    afirmar(not r["ok"] and "inválido" in r["erro"], r)
    with patch.object(EI, "localizar_editor", return_value=""):
        r = EI.abrir_no_editor("gimp", "x.png")
        afirmar(not r["ok"] and "gimp.org" in r["erro"], r)
    with patch.object(EI, "localizar_editor", return_value="C:/fake/gimp.exe"):
        r = EI.abrir_no_editor("gimp", str(Path(tempfile.mkdtemp()) / "n.png"))
        afirmar(not r["ok"] and "não encontrado" in r["erro"], r)


def teste_editores_abrir_popen_mockado():
    tmp = tempfile.mkdtemp()
    img = _arq(tmp, "capa.png", b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    chamadas = []
    orig = EI.subprocess.Popen

    class FakePopen:
        def __init__(self, cmd, **_kw):
            chamadas.append(cmd)

    try:
        EI.subprocess.Popen = FakePopen
        with patch.object(EI, "localizar_editor", return_value="C:/fake/krita.exe"):
            r = EI.abrir_no_editor("krita", img)
        afirmar(r["ok"] and chamadas and chamadas[0][1] == img, (r, chamadas))
    finally:
        EI.subprocess.Popen = orig


def teste_editores_status_aberto():
    st = EI.status_editores()
    afirmar(set(st) == set(EI.PROVEDORES_IMAGEM), st)
    for nome, info in st.items():
        afirmar(info["site"].startswith("https://") and "open source" in info["licenca"].lower(), info)


# -- equalizadores (Audacity/APO/Peace + EQ ffmpeg) --------------------------

def teste_eq_presets_e_preset_invalido():
    afirmar({"flat", "bass", "treble", "vocal", "night"} <= set(EQ.PRESETS_EQ))
    r = EQ.aplicar_eq("qualquer.mp3", "super-bass")
    afirmar(not r["ok"] and "preset" in r["erro"], r)


def teste_eq_sem_ffmpeg_orienta():
    tmp = tempfile.mkdtemp()
    mp3 = _arq(tmp, "faixa.mp3", b"ID3" + b"0" * 200)
    import bib_nucleo.baixar as BX
    with patch.object(BX, "localizar_ffmpeg", return_value=""):
        r = EQ.aplicar_eq(mp3, "bass")
    afirmar(not r["ok"] and "ffmpeg" in r["erro"].lower(), r)


def teste_eq_aplicar_run_mockado():
    tmp = tempfile.mkdtemp()
    mp3 = _arq(tmp, "musica.mp3", b"ID3" + b"0" * 500)
    import bib_nucleo.baixar as BX

    def fake_run(cmd, **_kw):
        Path(cmd[-1]).write_bytes(b"audio-eq" * 100)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    with patch.object(BX, "localizar_ffmpeg", return_value="C:/fake/ffmpeg.exe"), \
            patch.object(EQ.subprocess, "run", side_effect=fake_run):
        r = EQ.aplicar_eq(mp3, "bass")
    afirmar(r["ok"] and Path(r["path"]).is_file() and "bass" in r["path"], r)
    afirmar(Path(r["path"]).suffix.lower() == ".mp3")


def teste_equalizadores_status_estrutura():
    st = EQ.status_equalizadores()
    afirmar(set(st) == set(EQ.PROVEDORES_EQUALIZADOR), st)
    afirmar("audacityteam" in st["audacity"]["site"])


# -- reprodutores de vídeo (VLC/MPV/MPC-HC) ----------------------------------

def teste_video_base_dirs_e_exts():
    afirmar(".mp4" in core.VIDEO_EXTS and ".mkv" in core.VIDEO_EXTS)
    core.garantir_dirs()
    afirmar(core.VIDEOS_DIR.is_dir() and core.VIDEOS_DIR.parent == core.DADOS_DIR)
    afirmar("videos" in core.scans.SKIP_DIRS)


def teste_reprodutores_validacoes():
    afirmar(RV.resolver_video(str(Path(tempfile.mkdtemp()) / "n.mp4")) == "")
    r = RV.reproduzir_video("sem-arquivo.mp4", "vlc")
    afirmar(not r["ok"] and "não encontrado" in r["erro"], r)
    r = RV.reproduzir_video("x.mp4", "winamp")
    afirmar(not r["ok"] and "inválido" in r["erro"], r)


def teste_reprodutores_popen_mockado():
    tmp = tempfile.mkdtemp()
    vid = _arq(tmp, "filme.mp4", b"\x00\x00\x00 ftyp" + b"0" * 200)
    chamadas = []

    class FakePopen:
        def __init__(self, cmd, **_kw):
            chamadas.append(cmd)

    orig = RV.subprocess.Popen
    try:
        RV.subprocess.Popen = FakePopen
        with patch.object(RV, "localizar_reprodutor", side_effect=lambda n: "" if n != "mpv" else "C:/fake/mpv.exe"):
            r = RV.reproduzir_video(vid, "auto")
        afirmar(r["ok"] and r["reprodutor"] == "mpv" and chamadas[0][1] == vid, (r, chamadas))
    finally:
        RV.subprocess.Popen = orig


# -- videoteca local ----------------------------------------------------------

def teste_videos_import_dedup_e_crud():
    tmp = tempfile.mkdtemp()
    src = Path(tmp) / "src"
    src.mkdir()
    (src / "filme-a.mp4").write_bytes(b"video-igual" * 100)
    (src / "filme-b.mp4").write_bytes(b"video-igual" * 100)
    (src / "outro.mkv").write_bytes(b"video-outro" * 100)
    db = Path(tmp) / "v.db"
    con = core.get_db(db)
    try:
        r = core.importar_videos(con, str(src))
        afirmar(r["novos"] == 2 and r["ignorados"] == 1, r)
        lista = core.listar_videos(con)
        afirmar(len(lista) == 2, lista)
        afirmar(core.listar_videos(con, "outro")[0]["titulo"] == "outro")
        try:
            core.criar_video(con, {"titulo": ""})
        except ValueError:
            pass
        else:
            raise AssertionError("criou vídeo sem título")
        core.excluir_video(con, lista[0]["id"])
        afirmar(len(core.listar_videos(con)) == 1)
        try:
            core.excluir_video(con, 999999)
        except LookupError:
            pass
        else:
            raise AssertionError("excluiu vídeo inexistente")
    finally:
        con.close()


# -- YouTube: pesquisar/navegar/baixar ---------------------------------------

def teste_youtube_identificar():
    afirmar(YT.identificar_youtube("dQw4w9WgXcQ") == "dQw4w9WgXcQ")
    afirmar(YT.identificar_youtube("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ")
    afirmar(YT.identificar_youtube("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ")
    afirmar(YT.identificar_youtube("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ")
    afirmar(YT.identificar_youtube("https://example.com/watch?v=dQw4w9WgXcQ") is None)
    afirmar(YT.identificar_youtube("curto") is None)


def teste_youtube_buscar_cache_sem_ytdlp():
    online.gravar_json(online.cache_path("videos-youtube", "rick"), {"itens": [{"video_id": "dQw4w9WgXcQ", "titulo": "R"}], "erros": [], "cache": False})
    with patch.object(YT, "_ytdlp", return_value=""):
        r = YT.buscar_youtube("rick")
        afirmar(r["cache"] and r["itens"][0]["video_id"] == "dQw4w9WgXcQ", r)
    try:
        with patch.object(YT, "_ytdlp", return_value=""):
            YT.buscar_youtube("termo-sem-cache-xyz")
    except ValueError as e:
        afirmar("yt-dlp" in str(e), e)
    else:
        raise AssertionError("buscou sem yt-dlp nem cache")
    try:
        YT.buscar_youtube("x")
    except ValueError:
        pass
    else:
        raise AssertionError("buscou termo curto")


def teste_youtube_buscar_run_mockado():
    saida = "dQw4w9WgXcQ\tNever Gonna\tRick\t212\nabc123_-XYZ\tOutro\tCanal\tNA\n"

    def fake_run(cmd, **_kw):
        afirmar(cmd[1].startswith("ytsearch"), cmd)
        return subprocess.CompletedProcess(cmd, 0, saida, "")

    with patch.object(YT, "_ytdlp", return_value="fake-ytdlp"), \
            patch.object(YT.subprocess, "run", side_effect=fake_run):
        r = YT.buscar_youtube("rick astley nunca", limite=5, atualizar=True)
    afirmar(len(r["itens"]) == 2 and r["itens"][0]["canal"] == "Rick", r)
    afirmar(r["itens"][0]["url"].endswith("dQw4w9WgXcQ"))
    with patch.object(YT, "_ytdlp", return_value=""):
        r2 = YT.buscar_youtube("rick astley nunca")
    afirmar(r2["cache"] and len(r2["itens"]) == 2, r2)


def teste_youtube_baixar_sem_ytdlp_e_id_invalido():
    tmp = tempfile.mkdtemp()
    con = core.get_db(Path(tmp) / "y.db")
    try:
        with patch.object(YT, "_ytdlp", return_value=""):
            r = YT.baixar_video_youtube(con, "dQw4w9WgXcQ")
        afirmar(not r["ok"] and "yt-dlp" in r["erro"], r)
        r = YT.baixar_video_youtube(con, "link-invalido")
        afirmar(not r["ok"] and "inválido" in r["erro"], r)
    finally:
        con.close()


def teste_youtube_baixar_run_mockado():
    tmp = tempfile.mkdtemp()
    con = core.get_db(Path(tmp) / "y2.db")
    vid = "dQw4w9WgXcQ"

    class FakeProc:
        def __init__(self, cmd):
            self.cmd = cmd
            out = Path(cmd[cmd.index("-o") + 1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"mp4-fake" * 200)
            self.stdout = iter(["[download]  45.0% de 10MiB\n"])
        def wait(self, timeout=None):
            return 0

    try:
        with patch.object(YT, "_ytdlp", return_value="fake-ytdlp"), \
                patch.object(YT, "info_video_youtube", return_value={"video_id": vid, "titulo": "Clipe", "canal": "Rick", "duracao_s": 212, "thumb": "https://img", "origem": "youtube"}), \
                patch.object(YT.subprocess, "Popen", side_effect=lambda cmd, **_kw: FakeProc(cmd)):
            r = YT.baixar_video_youtube(con, vid)
        afirmar(r["ok"] and r["video_id"] == vid and Path(r["path"]).is_file(), r)
        lista = core.listar_videos(con)
        afirmar(len(lista) == 1 and lista[0]["origem"] == "youtube", lista)
    finally:
        con.close()


# -- Spotify: regressão do print ----------------------------------------------

def teste_spotify_codigo_url_inteira():
    url = "http://127.0.0.1:43827/callback?code=ABC123xyz&state=abc"
    afirmar(spotify.extrair_codigo_retorno(url) == "ABC123xyz")
    afirmar(spotify.extrair_codigo_retorno("  puro123  ") == "puro123")
    afirmar(spotify.extrair_codigo_retorno("") == "")
    online.configurar_provedores({"spotify_client_id": "a" * 32})
    cli = spotify.ClienteSpotify()
    try:
        cli._verifier = "verificador-fake"
        with patch.object(online, "requisitar_json", return_value={"access_token": "a", "refresh_token": "r", "expires_in": 10}):
            cli.trocar_codigo(url)
            afirmar(cli.estado()["conectado"])
    finally:
        cli.fechar()
        cli.token_path.unlink(missing_ok=True)
        cli.app_token_path.unlink(missing_ok=True)


def teste_spotify_paginacao_cache_por_contexto():
    cli = spotify.ClienteSpotify()
    cli._pagina_publica = True
    cli._contexto_modo = "busca"
    chave = repr(("busca", "", "https://api.spotify.com/v1/search?offset=10"))
    online.gravar_json(online.cache_path("spotify", chave), {"itens": [], "next": "", "modo": "busca", "cache": False})
    with patch.object(spotify.ClienteSpotify, "catalogo", side_effect=ValueError("offline")):
        r = cli.consultar("", "", "https://api.spotify.com/v1/search?offset=10")
    afirmar(r["cache"] and "preservado" in r["aviso"], r)
    cli.fechar()


def teste_servico_videos_vazio():
    import tempfile as _t

    from servicos_ui import ServicoBiblioteca
    db = Path(_t.mkdtemp()) / "s.db"
    svc = ServicoBiblioteca(db)
    afirmar(svc.listar_videos() == [])
