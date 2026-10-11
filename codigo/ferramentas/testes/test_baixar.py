"""Fila CSV → mp3: parser Exportify, dedup da fila, estados v14 (sem rede)."""
import tempfile
from pathlib import Path

import bib_core as core
from executar import afirmar

CAB = ("Track URI,ISRC,Track Name,Album Name,Artist Name(s),Release Date,"
       "Duration (ms),Popularity\n")


def _csv(tmp, linhas, nome="pl.csv"):
    p = Path(tmp) / nome
    p.write_text(CAB + "".join(linhas), encoding="utf-8")
    return p


def teste_baixar_parser_e_primeiro_artista():
    from bib_nucleo import baixar as BX
    afirmar(BX.primeiro_artista("Chico Buarque;MPB4") == "Chico Buarque")
    afirmar(BX.primeiro_artista("Solo") == "Solo")
    afirmar(BX.primeiro_artista("") == "")
    tmp = Path(tempfile.mkdtemp(prefix="suite-bx-"))
    p = _csv(tmp, [
        'spotify:track:1,x,"Cotidiano","Construção","Chico Buarque",1971,1,1\n',
        'spotify:track:2,x,"Apesar De Você","Chico Buarque","Chico Buarque;MPB4",1978,1,1\n',
        'spotify:track:3,x,"","Sem Titulo","Anon",2000,1,1\n',
        'spotify:track:4,x,"A, Vida","Album X","Y",2001,1,1\n',
    ])
    r = BX.ler_csv_exportify(p)
    afirmar(r["erros"] == [], r)
    afirmar(r["ignorados"] == 1, r)
    afirmar(len(r["itens"]) == 3, r)
    afirmar(r["itens"][1]["artista"] == "Chico Buarque", r)
    afirmar(r["itens"][2]["titulo"] == "A, Vida", r)
    ruim = tmp / "nada.csv"
    ruim.write_text("a,b\n1,2\n", encoding="utf-8")
    r = BX.ler_csv_exportify(ruim)
    afirmar(r["itens"] == [] and r["erros"], r)
    r = BX.ler_csv_exportify(tmp / "sumiu.csv")
    afirmar(r["itens"] == [] and r["erros"], r)


def teste_baixar_fila_dedup_e_estados():
    from bib_nucleo import baixar as BX
    tmp = Path(tempfile.mkdtemp(prefix="suite-bx-"))
    con = core.get_db(tmp / "b.db")
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(downloads)").fetchall()}
        afirmar({"titulo", "uri", "estado", "video_id"} <= cols, sorted(cols))
        p = _csv(tmp, [
            'spotify:track:1,x,"Cotidiano","Construção","Chico Buarque",1971,1,1\n',
            'spotify:track:1,x,"Cotidiano","Construção","Chico Buarque",1971,1,1\n',
            'spotify:track:9,x,"COTIDIANO","Outro","CHICO BUARQUE",1971,1,1\n',
        ])
        r = BX.ler_csv_exportify(p)
        q = core.enfileirar_downloads(con, r["itens"])
        afirmar(q == {"novos": 1, "ignorados": 2, "erros": []}, (r, q))
        q = core.enfileirar_downloads(con, [{"titulo": "", "artista": "X"}])
        afirmar(q["novos"] == 0 and q["ignorados"] == 1, q)
        # faixa que o Hub já tem não entra na fila
        core.criar_musica(con, {"titulo": "Cotidiano", "artista": "Chico Buarque",
                                "musica_sha": "s" * 64})
        q = core.enfileirar_downloads(
            con, [{"titulo": "Cotidiano", "artista": "Chico Buarque",
                   "uri": "spotify:track:7"}])
        afirmar(q["novos"] == 0 and q["ignorados"] == 1, q)
        pand = core.listar_downloads(con, estado="pendente")
        afirmar(len(pand) == 1, pand)
        did = pand[0]["id"]
        d = core.marcar_download(con, did, "baixando", video_id="abc123")
        afirmar(d["estado"] == "baixando" and d["video_id"] == "abc123", d)
        d = core.marcar_download(con, did, "pronta", musica_sha="s" * 63 + "0")
        afirmar(d["estado"] == "pronta", d)
        afirmar(core.listar_downloads(con, estado="pronta")[0]["id"] == did)
        try:
            core.marcar_download(con, did, "voando")
            afirmar(False, "devia levantar")
        except ValueError:
            pass
        try:
            core.listar_downloads(con, estado="voando")
            afirmar(False, "devia levantar")
        except ValueError:
            pass
        try:
            core.marcar_download(con, 9999, "falha")
            afirmar(False, "devia levantar")
        except LookupError:
            pass
        afirmar(core.limpar_downloads(con) == 1)
        afirmar(core.listar_downloads(con) == [])
        try:
            core.limpar_downloads(con, estados=("pendente", "voando"))
            afirmar(False, "devia levantar")
        except ValueError:
            pass
    finally:
        con.close()


def teste_baixar_v14_idempotente():
    tmp = Path(tempfile.mkdtemp(prefix="suite-bx-"))
    con = core.get_db(tmp / "b.db")
    con.close()
    con = core.get_db(tmp / "b.db")  # reabre: migração não duplica nem perde
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(downloads)").fetchall()}
        afirmar("video_id" in cols, sorted(cols))
        afirmar(core.listar_downloads(con) == [])
    finally:
        con.close()


def teste_baixar_localizar_e_consulta():
    import os
    from bib_nucleo import baixar as BX
    afirmar(BX.consulta_busca("Chico", "Cotidiano") == "ytsearch1:Chico - Cotidiano")
    afirmar(BX.consulta_busca("", "Solo") == "ytsearch1:Solo")
    afirmar(BX.consulta_busca("", "") == "")
    afirmar("BIBLIOTECA_YTDLP" in BX.erro_sem_ytdlp())
    tmp = Path(tempfile.mkdtemp(prefix="suite-bx-"))
    falso = tmp / ("yt-dlp.exe" if os.name == "nt" else "yt-dlp")
    falso.write_bytes(b"fake")
    falso.chmod(0o755)
    velho = os.environ.get("BIBLIOTECA_YTDLP")
    os.environ["BIBLIOTECA_YTDLP"] = str(falso)
    try:
        afirmar(BX.localizar_ytdlp() == str(falso))
    finally:
        if velho is None:
            os.environ.pop("BIBLIOTECA_YTDLP", None)
        else:
            os.environ["BIBLIOTECA_YTDLP"] = velho


def teste_baixar_casar_video_mock():
    from bib_nucleo import baixar as BX

    class R:
        def __init__(self, rc=0, out="", err=""):
            self.returncode = rc
            self.stdout = out
            self.stderr = err

    velho = BX.subprocess.run
    try:
        BX.subprocess.run = lambda *a, **k: R(0, "abc123\tTitulo X\n")
        c = BX.casar_video("yt", "Chico", "Cotidiano")
        afirmar(c == {"video_id": "abc123", "video_titulo": "Titulo X"}, c)
        BX.subprocess.run = lambda *a, **k: R(1, "", "ERROR: nada")
        try:
            BX.casar_video("yt", "Chico", "Cotidiano")
            afirmar(False, "devia levantar")
        except ValueError:
            pass
        BX.subprocess.run = lambda *a, **k: R(0, "sem-tab-aqui\n")
        try:
            BX.casar_video("yt", "Chico", "Cotidiano")
            afirmar(False, "devia levantar")
        except ValueError:
            pass

        def _boom(*a, **k):
            raise OSError("sem exec")
        BX.subprocess.run = _boom
        try:
            BX.casar_video("yt", "Chico", "Cotidiano")
            afirmar(False, "devia levantar")
        except ValueError:
            pass
        try:
            BX.casar_video("yt", "", "")
            afirmar(False, "devia levantar")
        except ValueError:
            pass
    finally:
        BX.subprocess.run = velho


def teste_baixar_faixa_mock():
    from bib_nucleo import baixar as BX

    class R:
        def __init__(self, rc=0, out="", err=""):
            self.returncode = rc
            self.stdout = out
            self.stderr = err

    class P:
        def __init__(self, rc=0):
            self.stdout = ["[download]  45.0% of 3MiB\n",
                           "[download] 100.0% done\n"]
            self._rc = rc
        def wait(self, timeout=None):
            return self._rc

    tmp = Path(tempfile.mkdtemp(prefix="suite-bx-"))
    stage = tmp / "stage"
    stage.mkdir()
    con = core.get_db(tmp / "b.db")
    velho_run, velho_pop = BX.subprocess.run, BX.subprocess.Popen
    try:
        core.enfileirar_downloads(con, [{"titulo": "Cotidiano",
                                         "artista": "Chico",
                                         "uri": "spotify:track:1"}])
        core.enfileirar_downloads(con, [{"titulo": "Ruim",
                                         "artista": "X",
                                         "uri": "spotify:track:2"}])
        did = core.listar_downloads(con)[0]["id"]
        did2 = core.listar_downloads(con)[1]["id"]
        (stage / "abc123.m4a").write_bytes(b"audio" * 100)
        vistos = []
        BX.subprocess.run = lambda *a, **k: R(0, "abc123\tTitulo X\n")
        BX.subprocess.Popen = lambda *a, **k: P(0)
        r = BX.baixar_faixa(con, did, ytdlp="yt-fake", destino=stage,
                            progresso=lambda i, p: vistos.append(p))
        afirmar(r.get("ok") and r.get("video_id") == "abc123", r)
        afirmar(vistos and vistos[-1] == 100.0, vistos)
        d = core.listar_downloads(con, estado="baixado")
        afirmar(len(d) == 1 and d[0]["musica_path"].endswith("abc123.m4a"), d)
        # rc != 0 vira falha com video_id guardado
        BX.subprocess.Popen = lambda *a, **k: P(1)
        r = BX.baixar_faixa(con, did2, ytdlp="yt-fake", destino=stage)
        afirmar(not r.get("ok"), r)
        d = core.listar_downloads(con, estado="falha")
        afirmar(len(d) == 1 and d[0]["video_id"] == "abc123", d)
        # estado final não baixa de novo; id inexistente não levanta
        r = BX.baixar_faixa(con, did, ytdlp="yt-fake", destino=stage)
        afirmar(not r.get("ok"), r)
        r = BX.baixar_faixa(con, 9999, ytdlp="yt-fake", destino=stage)
        afirmar(not r.get("ok"), r)
    finally:
        BX.subprocess.run = velho_run
        BX.subprocess.Popen = velho_pop
        con.close()


def _zip_ff(exe_bytes):
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("ffmpeg-9.0/bin/ffmpeg.exe", exe_bytes)
    return buf.getvalue()


def _urlopen_binario(dados_ou_erro):
    import urllib.request
    chamadas = []

    class Resp:
        def __init__(self, dados):
            self._dados = dados
            self.headers = {}
        def read(self, n=-1):
            if not self._dados:
                return b""
            out, self._dados = self._dados[:n], self._dados[n:]
            return out
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def falso(req, timeout=None):
        chamadas.append(getattr(req, "full_url", ""))
        if isinstance(dados_ou_erro, Exception):
            raise dados_ou_erro
        return Resp(bytes(dados_ou_erro))
    velho = urllib.request.urlopen
    urllib.request.urlopen = falso
    return velho, chamadas


def teste_baixar_converter_ffmpeg_mock():
    import os
    from bib_nucleo import baixar as BX
    tmp = Path(tempfile.mkdtemp(prefix="suite-bx-"))
    stage = tmp / "stage"
    stage.mkdir()
    con = core.get_db(tmp / "b.db")
    velho_run, velho_loc = BX.subprocess.run, BX.localizar_ffmpeg
    try:
        (stage / "vid1.m4a").write_bytes(b"audio" * 500)
        core.enfileirar_downloads(con, [{"titulo": "Bee", "artista": "Aaa",
                                         "uri": "u1"}])
        did = core.listar_downloads(con)[0]["id"]
        core.marcar_download(con, did, "baixado", video_id="vid1",
                             musica_path=str(stage / "vid1.m4a"))

        def _ff(*a, **k):
            dest = Path(a[0][-1])
            dest.write_bytes(b"MP3convertido" * 100)
            class R:
                returncode = 0
                stderr = ""
            return R()
        BX.subprocess.run = _ff
        r = BX.converter_faixa(con, did, ffmpeg="ff-fake", capa_auto=False)
        afirmar(r.get("ok") and r["path"].endswith(".mp3")
                and "aviso" not in r, r)
        afirmar(not (stage / "vid1.m4a").exists(), "staging devia sumir")
        d = core.listar_downloads(con, estado="pronta")
        afirmar(len(d) == 1 and d[0]["musica_sha"], d)
        lst = core.listar_musicas(con, q="bee")
        afirmar(len(lst) == 1 and lst[0]["artista"] == "Aaa", lst)
        # ffmpeg quebrado vira falha (staging preservado p/ retry)
        (stage / "vid2.m4a").write_bytes(b"audio" * 500)
        core.enfileirar_downloads(con, [{"titulo": "Cee", "artista": "Dee",
                                         "uri": "u2"}])
        did2 = core.listar_downloads(con, estado="pendente")[0]["id"]
        core.marcar_download(con, did2, "baixado", video_id="vid2",
                             musica_path=str(stage / "vid2.m4a"))

        def _ff_ruim(*a, **k):
            class R:
                returncode = 1
                stderr = "ERROR: codec"
            return R()
        BX.subprocess.run = _ff_ruim
        r = BX.converter_faixa(con, did2, ffmpeg="ff-fake", capa_auto=False)
        afirmar(not r.get("ok") and "codec" in r.get("erro", ""), r)
        afirmar((stage / "vid2.m4a").is_file(), "staging devia ficar")
        afirmar(core.listar_downloads(con, estado="falha")[0]["id"] == did2)
        # estado errado e id inexistente não levantam
        afirmar(not BX.converter_faixa(con, did, ffmpeg="ff")["ok"])
        afirmar(not BX.converter_faixa(con, 9999, ffmpeg="ff")["ok"])
        # localizar_ffmpeg respeita o env
        ff = tmp / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        ff.write_bytes(b"fake")
        ff.chmod(0o755)
        velho_env = os.environ.get("BIBLIOTECA_FFMPEG")
        os.environ["BIBLIOTECA_FFMPEG"] = str(ff)
        try:
            afirmar(BX.localizar_ffmpeg() == str(ff))
            afirmar("BIBLIOTECA_FFMPEG" in BX.erro_sem_ffmpeg())
        finally:
            if velho_env is None:
                os.environ.pop("BIBLIOTECA_FFMPEG", None)
            else:
                os.environ["BIBLIOTECA_FFMPEG"] = velho_env
    finally:
        BX.subprocess.run = velho_run
        BX.localizar_ffmpeg = velho_loc
        con.close()


def teste_baixar_converter_sem_ffmpeg():
    from bib_nucleo import baixar as BX
    tmp = Path(tempfile.mkdtemp(prefix="suite-bx-"))
    stage = tmp / "stage"
    stage.mkdir()
    con = core.get_db(tmp / "b.db")
    velho_loc = BX.localizar_ffmpeg
    BX.localizar_ffmpeg = lambda: ""
    try:
        (stage / "n1.m4a").write_bytes(b"audio" * 500)
        (stage / "n2.webm").write_bytes(b"video" * 500)
        core.enfileirar_downloads(con, [{"titulo": "Nat", "artista": "A",
                                         "uri": "u1"}])
        core.enfileirar_downloads(con, [{"titulo": "Web", "artista": "B",
                                         "uri": "u2"}])
        ids = [d["id"] for d in core.listar_downloads(con)]
        core.marcar_download(con, ids[0], "baixado", video_id="n1",
                             musica_path=str(stage / "n1.m4a"))
        core.marcar_download(con, ids[1], "baixado", video_id="n2",
                             musica_path=str(stage / "n2.webm"))
        r = BX.importar_fila_pronta(con, capa_auto=False)
        afirmar(r["novas"] == 1 and r["ignoradas"] == 1, r)
        afirmar(r["avisos"] and "ffmpeg" in r["avisos"][0].lower(), r)
        d = core.listar_downloads(con, estado="pronta")
        afirmar(len(d) == 1 and d[0]["musica_path"].endswith(".m4a"), d)
        f = core.listar_downloads(con, estado="falha")
        afirmar(len(f) == 1 and "ffmpeg" in f[0]["erro"].lower(), f)
        afirmar(core.listar_downloads(con, estado="baixado") == [])
    finally:
        BX.localizar_ffmpeg = velho_loc
        con.close()


def teste_baixar_instalar_ffmpeg_mock():
    import urllib.request
    from bib_nucleo import baixar as BX
    tmp = Path(tempfile.mkdtemp(prefix="suite-bx-"))
    velho_min = BX.FFMPEG_ZIP_MIN
    BX.FFMPEG_ZIP_MIN = 10
    velho, chamadas = _urlopen_binario(_zip_ff(b"MZ" + b"0" * 3000))
    try:
        r = BX.instalar_ffmpeg(destino=tmp / "fer")
        afirmar(r.get("ok") and (tmp / "fer" / "ffmpeg.exe").is_file(), r)
        afirmar(chamadas and "gyan.dev" in chamadas[0], chamadas)
    finally:
        urllib.request.urlopen = velho
        BX.FFMPEG_ZIP_MIN = velho_min
    velho, _ch = _urlopen_binario(_zip_ff(b"sem-mz-aqui"))
    BX.FFMPEG_ZIP_MIN = 10
    try:
        r = BX.instalar_ffmpeg(destino=tmp / "fer2")
        afirmar(not r.get("ok") and "MZ" in r.get("erro", ""), r)
    finally:
        urllib.request.urlopen = velho
        BX.FFMPEG_ZIP_MIN = velho_min
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("nada/util.txt", b"x")
    velho, _ch = _urlopen_binario(buf.getvalue())
    BX.FFMPEG_ZIP_MIN = 10
    try:
        r = BX.instalar_ffmpeg(destino=tmp / "fer3")
        afirmar(not r.get("ok") and "ausente" in r.get("erro", ""), r)
    finally:
        urllib.request.urlopen = velho
        BX.FFMPEG_ZIP_MIN = velho_min


def teste_baixar_instalar_ytdlp_mock():
    import urllib.request
    from bib_nucleo import baixar as BX
    tmp = Path(tempfile.mkdtemp(prefix="suite-bx-"))
    velho_min = BX.YTDLP_EXE_MIN
    BX.YTDLP_EXE_MIN = 10
    velho, chamadas = _urlopen_binario(b"MZ" + b"1" * 3000)
    try:
        r = BX.instalar_ytdlp(destino=tmp / "fer")
        afirmar(r.get("ok") and (tmp / "fer" / "yt-dlp.exe").is_file(), r)
        afirmar(chamadas and "yt-dlp" in chamadas[0], chamadas)
    finally:
        urllib.request.urlopen = velho
        BX.YTDLP_EXE_MIN = velho_min
    velho, _ch = _urlopen_binario(OSError("rede"))
    BX.YTDLP_EXE_MIN = 10
    try:
        r = BX.instalar_ytdlp(destino=tmp / "fer2")
        afirmar(not r.get("ok") and "download" in r.get("erro", ""), r)
    finally:
        urllib.request.urlopen = velho
        BX.YTDLP_EXE_MIN = velho_min


def teste_baixar_pronto_e_ferramentas():
    import os
    from bib_nucleo import baixar as BX
    from bib_nucleo import base
    tmp = Path(tempfile.mkdtemp(prefix="suite-bx-"))
    (tmp / "peq.exe").write_bytes(b"MZ")
    afirmar(BX.ffmpeg_pronto() == "" or isinstance(BX.ffmpeg_pronto(), str))
    velho_env = os.environ.get("BIBLIOTECA_FFMPEG")
    os.environ["BIBLIOTECA_FFMPEG"] = str(tmp / "peq.exe")
    try:
        afirmar(BX.localizar_ffmpeg() == (str(tmp / "peq.exe") if os.name == "nt" else ""))
        afirmar(BX.ffmpeg_pronto() == "", "pequeno demais devia reprovar")
    finally:
        if velho_env is None:
            os.environ.pop("BIBLIOTECA_FFMPEG", None)
        else:
            os.environ["BIBLIOTECA_FFMPEG"] = velho_env
    if os.name == "nt":
        fer = Path(str(base.WIN_ROOT).rstrip("\\/")) / "Games" / "ferramentas"
        fer.mkdir(parents=True, exist_ok=True)
        (fer / "yt-dlp.exe").write_bytes(b"MZ" + b"0" * 2_000_000)
        velho_yt = os.environ.get("BIBLIOTECA_YTDLP")
        os.environ.pop("BIBLIOTECA_YTDLP", None)
        try:
            afirmar(BX.localizar_ytdlp() == str(fer / "yt-dlp.exe"))
            afirmar(BX.ytdlp_pronto() == str(fer / "yt-dlp.exe"))
        finally:
            if velho_yt is not None:
                os.environ["BIBLIOTECA_YTDLP"] = velho_yt
    else:
        afirmar(BX.dir_ferramentas() is None)


def teste_download_state_preserva_staging_apos_falha():
    tmp = Path(tempfile.mkdtemp(prefix="suite-bx-"))
    con = core.get_db(tmp / "b.db")
    try:
        core.enfileirar_downloads(con, [{"titulo": "T", "uri": "u"}])
        did = core.listar_downloads(con)[0]["id"]
        core.marcar_download(con, did, "baixado", video_id="id", musica_path="stage/audio.m4a")
        r = core.marcar_download(con, did, "falha", erro="codec indisponível")
        afirmar(r["musica_path"] == "stage/audio.m4a" and r["video_id"] == "id", r)
    finally:
        con.close()
