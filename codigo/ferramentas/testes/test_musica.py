"""Músicas: tags ID3, varredura, import com dedup, CRUD v12, pacote v4."""
import json
import os
import struct
import tempfile
import zipfile
from pathlib import Path

from bib_nucleo import banco
from executar import afirmar


def _frame(fid: str, texto: str) -> bytes:
    corpo = b"\x03" + texto.encode("utf-8")
    return fid.encode("ascii") + struct.pack(">I", len(corpo)) + b"\x00\x00" + corpo


def _mp3(tmp, nome="A - B.mp3", titulo="Bee", artista="Aaa", album="Al"):
    dados = (_frame("TIT2", titulo) + _frame("TPE1", artista)
             + _frame("TALB", album) + b"\xff\xfb\x90\x00" * 64)
    n = len(dados)
    sync = bytes([(n >> 21) & 0x7F, (n >> 14) & 0x7F,
                  (n >> 7) & 0x7F, n & 0x7F])
    p = Path(tmp) / nome
    p.write_bytes(b"ID3\x03\x00\x00" + sync + dados)
    return p


def teste_musica_tags_e_varredura():
    from bib_nucleo import musicas as MUS
    tmp = Path(tempfile.mkdtemp(prefix="suite-mus-"))
    _mp3(tmp)
    (tmp / "ruim.mp3").write_bytes(b"lixo sem tag")
    (tmp / "nota.txt").write_bytes(b"ignorado")
    t = MUS.ler_tags(tmp / "A - B.mp3")
    afirmar(t == {"titulo": "Bee", "artista": "Aaa", "album": "Al"}, t)
    t = MUS.ler_tags(tmp / "ruim.mp3")
    afirmar(t["titulo"] == "ruim", t)
    t = MUS.ler_tags(tmp / "X - Y feat Z.mp3")
    afirmar(t["titulo"] == "Y feat Z" and t["artista"] == "X", t)
    itens = MUS.varrer_pasta(tmp)
    afirmar(len(itens) == 2, itens)
    afirmar(all(i["sha"] and i["slug"] for i in itens), itens)
    afirmar(MUS.varrer_pasta(tmp / "nao-existe") == [])


def teste_musica_import_dedup_crud():
    from bib_nucleo import musicas as MUS
    tmp = Path(tempfile.mkdtemp(prefix="suite-mus-"))
    src = tmp / "src"
    src.mkdir()
    _mp3(src, "A - B.mp3")
    _mp3(src, "C - D.mp3", titulo="Dee", artista="Cee", album="")
    con = banco.get_db(tmp / "m.db")
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(musicas)").fetchall()}
        afirmar({"titulo", "musica_sha", "musica_path", "musica_capa"} <= cols,
                sorted(cols))
        r = MUS.importar_musicas(con, src, capa_auto=False)
        afirmar(r == {"novos": 2, "ignorados": 0, "erros": [], "capas": 0}, r)
        r = MUS.importar_musicas(con, src, capa_auto=False)
        afirmar(r["novos"] == 0 and r["ignorados"] == 2, r)
        lst = banco.listar_musicas(con)
        afirmar(len(lst) == 2, lst)
        afirmar(banco.listar_musicas(con, q="cee")[0]["titulo"] == "Dee")
        mid = banco.listar_musicas(con, q="bee")[0]["id"]
        alvo = Path(banco.listar_musicas(con, q="bee")[0]["musica_path"])
        afirmar(alvo.is_file(), alvo)
        banco.excluir_musica(con, mid)
        afirmar(not alvo.exists() and len(banco.listar_musicas(con)) == 1)
        try:
            banco.criar_musica(con, {"titulo": "", "musica_sha": "x"})
            afirmar(False, "devia levantar")
        except ValueError:
            pass
        try:
            banco.excluir_musica(con, 9999)
            afirmar(False, "devia levantar")
        except LookupError:
            pass
    finally:
        con.close()


def teste_musica_tracks_json_e_migracao_v12():
    import sqlite3

    from bib_nucleo import musicas as MUS
    tmp = Path(tempfile.mkdtemp(prefix="suite-mus-"))
    src = tmp / "src"
    (src / "sub").mkdir(parents=True)
    _mp3(src / "sub", "E - F.mp3", titulo="Eff", artista="Ee", album="")
    (tmp / "data").mkdir()
    (tmp / "data" / "tracks.json").write_text(
        json.dumps([{"artist": "Ee", "track": "Eff", "album": "AlbX"}]),
        encoding="utf-8")
    # src está fora de tmp/data? tracks.json vizinho: music/data ou music/
    (src / "tracks.json").write_text(
        json.dumps([{"artist": "Ee", "track": "Eff", "album": "AlbX"}]),
        encoding="utf-8")
    itens = MUS.varrer_pasta(src)
    afirmar(len(itens) == 1 and itens[0]["album"] == "AlbX", itens)
    leg = tmp / "leg.db"
    con = sqlite3.connect(str(leg))
    con.execute("CREATE TABLE jogos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL,"
                " executable_path TEXT DEFAULT '', exe_win TEXT DEFAULT '', exe_linux TEXT DEFAULT '',"
                " exe_mac TEXT DEFAULT '', wine_prefix TEXT DEFAULT '', launch_options TEXT DEFAULT '',"
                " status TEXT DEFAULT 'backlog', nota INTEGER, favorito INTEGER DEFAULT 0,"
                " horas REAL DEFAULT 0, ultima_execucao TEXT, observacoes TEXT DEFAULT '',"
                " origem TEXT DEFAULT 'manual', shop TEXT DEFAULT '', object_id TEXT DEFAULT '',"
                " game_code TEXT DEFAULT '', regiao TEXT DEFAULT '', azahar_preset TEXT DEFAULT '',"
                " citron_preset TEXT DEFAULT '', uuid TEXT DEFAULT '', etiquetas TEXT DEFAULT '',"
                " save_path TEXT DEFAULT '', azahar_mods TEXT DEFAULT '',"
                " azahar_mods_off INTEGER DEFAULT 0, capa TEXT DEFAULT '', confianca REAL DEFAULT 0,"
                " criado_em TEXT, atualizado_em TEXT,"
                " UNIQUE(titulo, executable_path, launch_options))")
    con.commit()
    con.close()
    con = banco.get_db(leg)
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(musicas)").fetchall()}
        afirmar("musica_sha" in cols, sorted(cols))
        njogos = con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()["n"]
        afirmar(njogos == 0, njogos)
    finally:
        con.close()


def teste_musica_tracks_json_invalido():
    from bib_nucleo import musicas as MUS
    tmp = Path(tempfile.mkdtemp(prefix="suite-mus-"))
    src = tmp / "src"
    src.mkdir()
    _mp3(src, "A - B.mp3", titulo="Bee", artista="Aaa", album="")
    for ruim in ("42", '"só-string"', '{"tracks": "nao-lista"}',
                 '{"outra": 1}'):
        (src / "tracks.json").write_text(ruim, encoding="utf-8")
        itens = MUS.varrer_pasta(src)
        afirmar(len(itens) == 1 and itens[0]["album"] == "", (ruim, itens))


def teste_pacote_v4_musicas():
    from bib_nucleo import musicas as MUS
    from bib_nucleo import pacotes as PAC
    tmp = Path(tempfile.mkdtemp(prefix="suite-mus-"))
    src = tmp / "src"
    src.mkdir()
    _mp3(src, "A - B.mp3")
    con = banco.get_db(tmp / "m.db")
    try:
        MUS.importar_musicas(con, src, capa_auto=False)
    finally:
        con.close()
    dest = tmp / "p.zip"
    r = PAC.exportar_pacote(dest, db_path=tmp / "m.db", incluir_saves=False)
    afirmar(r.get("ok"), r)
    nomes = [i.filename for i in zipfile.ZipFile(dest).infolist()]
    afirmar(any(n.startswith("musicas/") for n in nomes), nomes)
    con2 = banco.get_db(tmp / "m2.db")
    con2.close()
    r = PAC.importar_pacote(dest, db_path=tmp / "m2.db")
    afirmar(r.get("ok") and r.get("musicas", 0) == 1, r)
    con2 = banco.get_db(tmp / "m2.db")
    try:
        lst = banco.listar_musicas(con2)
        afirmar(len(lst) == 1 and lst[0]["titulo"] == "Bee", lst)
        afirmar(Path(lst[0]["musica_path"]).is_file(), lst)
    finally:
        con2.close()


def teste_musica_capa_auto_env():

    from bib_nucleo import musicas as MUS
    afirmar(MUS.capa_musica_auto() is True)
    velho = os.environ.get("BIBLIOTECA_CAPA_MUSICA_AUTO")
    os.environ["BIBLIOTECA_CAPA_MUSICA_AUTO"] = "0"
    try:
        afirmar(MUS.capa_musica_auto() is False)
    finally:
        if velho is None:
            os.environ.pop("BIBLIOTECA_CAPA_MUSICA_AUTO", None)
        else:
            os.environ["BIBLIOTECA_CAPA_MUSICA_AUTO"] = velho


def _urlopen_mockado(respostas):
    import urllib.request
    chamadas = []

    class Resp:
        def __init__(self, dados):
            self._dados = dados
        def read(self, n=-1):
            return self._dados if n < 0 else self._dados[:n]
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def falso(req, timeout=None):
        chamadas.append(getattr(req, "full_url", ""))
        if not respostas:
            raise AssertionError("rede além do roteiro")
        item = respostas.pop(0)
        if isinstance(item, Exception):
            raise item
        return Resp(item)
    velho = urllib.request.urlopen
    urllib.request.urlopen = falso
    return velho, chamadas


def teste_musica_capa_busca_e_baixa_mock():
    import json
    import urllib.request

    from bib_nucleo import musicas as MUS
    tmp = Path(tempfile.mkdtemp(prefix="suite-mus-"))
    src = tmp / "src"
    src.mkdir()
    _mp3(src, "A - B.mp3")
    con = banco.get_db(tmp / "m.db")
    busca = json.dumps({"results": [
        {"artworkUrl100": "https://example.com/a/100x100bb.jpg"}]}).encode()
    velho, chamadas = _urlopen_mockado([busca, b"JPG" * 800, busca])
    try:
        MUS.importar_musicas(con, src, capa_auto=False)
        mid = banco.listar_musicas(con)[0]["id"]
        r = MUS.baixar_capa_album(con, mid)
        afirmar(r.get("ok") and r.get("capa", "").endswith(".jpg"), r)
        row = banco.listar_musicas(con)[0]
        afirmar(row["musica_capa"] == r["capa"], row)
        from bib_nucleo.base import CAPAS_DIR
        afirmar((CAPAS_DIR / r["capa"]).is_file(), r)
        n_antes = len(chamadas)
        r = MUS.baixar_capa_album(con, mid)  # 2ª vez: cache, sem rede
        afirmar(r.get("ok") and len(chamadas) == n_antes, (r, chamadas))
        f = MUS.baixar_capas_faltantes(con)
        afirmar(f == {"novas": 0, "pendentes": 0, "erros": []}, f)
        url = MUS.capa_album_url("Aaa", "Al", "Bee")
        afirmar(url == "https://example.com/a/600x600bb.jpg", url)
        r = MUS.baixar_capa_album(con, 9999)
        afirmar(not r.get("ok"), r)
    finally:
        urllib.request.urlopen = velho
        con.close()


def teste_musica_capa_rede_falha():
    import urllib.request

    from bib_nucleo import musicas as MUS
    tmp = Path(tempfile.mkdtemp(prefix="suite-mus-"))
    src = tmp / "src"
    src.mkdir()
    _mp3(src, "A - B.mp3")
    con = banco.get_db(tmp / "m.db")
    velho, _ch = _urlopen_mockado([urllib.request.URLError("offline"),
                                   urllib.request.URLError("offline")])
    try:
        MUS.importar_musicas(con, src, capa_auto=False)
        mid = banco.listar_musicas(con)[0]["id"]
        r = MUS.baixar_capa_album(con, mid)
        afirmar(not r.get("ok") and r.get("capa_pendente"), r)
        r = MUS.baixar_capas_faltantes(con)
        afirmar(r["novas"] == 0 and r["pendentes"] == 1, r)
    finally:
        urllib.request.urlopen = velho
        con.close()
    afirmar(MUS.capa_album_url("", "", "") == "")  # sem consulta, sem rede


def teste_musica_capa_v15_legado():
    import sqlite3
    tmp = Path(tempfile.mkdtemp(prefix="suite-mus-"))
    leg = tmp / "leg.db"
    con = sqlite3.connect(str(leg))
    con.execute("CREATE TABLE musicas (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                " titulo TEXT NOT NULL, artista TEXT DEFAULT '',"
                " album TEXT DEFAULT '', musica_path TEXT DEFAULT '',"
                " musica_sha TEXT DEFAULT '', origem TEXT DEFAULT 'harmoni',"
                " criado_em TEXT, atualizado_em TEXT, UNIQUE(musica_sha))")
    con.execute("INSERT INTO musicas (titulo, musica_sha) VALUES ('Velha', 's')")
    con.commit()
    con.close()
    con = banco.get_db(leg)
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(musicas)").fetchall()}
        afirmar("musica_capa" in cols, sorted(cols))
        lst = banco.listar_musicas(con)
        afirmar(len(lst) == 1 and lst[0]["titulo"] == "Velha", lst)
    finally:
        con.close()


def teste_musica_capa_salvar_e_pacote():
    from bib_nucleo import musicas as MUS
    from bib_nucleo import pacotes as PAC
    tmp = Path(tempfile.mkdtemp(prefix="suite-mus-"))
    src = tmp / "src"
    src.mkdir()
    _mp3(src, "A - B.mp3")
    con = banco.get_db(tmp / "m.db")
    try:
        MUS.importar_musicas(con, src, capa_auto=False)
        mid = banco.listar_musicas(con)[0]["id"]
        r = banco.salvar_capa_musica_bytes(con, mid, "arte.jpg", b"J" * 2048)
        afirmar(r.get("ok") and r["capa"].startswith(f"mus-{mid}-"), r)
        r = banco.salvar_capa_musica_bytes(con, 9999, "a.jpg", b"J" * 2048)
        afirmar(not r.get("ok"), r)
        r = banco.salvar_capa_musica_bytes(con, mid, "a.txt", b"J" * 2048)
        afirmar(not r.get("ok"), r)
    finally:
        con.close()
    dest = tmp / "p.zip"
    r = PAC.exportar_pacote(dest, db_path=tmp / "m.db", incluir_saves=False)
    afirmar(r.get("ok"), r)
    nomes = [i.filename for i in zipfile.ZipFile(dest).infolist()]
    afirmar(any(n.startswith("capas/mus-") for n in nomes), nomes)
    r = PAC.importar_pacote(dest, db_path=tmp / "m2.db")
    afirmar(r.get("ok") and r.get("musicas", 0) == 1, r)
    con2 = banco.get_db(tmp / "m2.db")
    try:
        lst = banco.listar_musicas(con2)
        afirmar(len(lst) == 1 and lst[0]["musica_capa"].startswith("mus-"), lst)
        from bib_nucleo.base import CAPAS_DIR
        afirmar((CAPAS_DIR / lst[0]["musica_capa"]).is_file(), lst)
    finally:
        con2.close()


def teste_pacote_audio_sha_e_capa_em_reimportacao():
    from bib_nucleo import musicas as MUS
    from bib_nucleo import pacotes as PAC
    tmp = Path(tempfile.mkdtemp(prefix="suite-mus-"))
    src = tmp / "src"
    src.mkdir()
    _mp3(src)
    db = tmp / "origem.db"
    con = banco.get_db(db)
    MUS.importar_musicas(con, src, capa_auto=False)
    m = banco.listar_musicas(con)[0]
    banco.salvar_capa_musica_bytes(con, m["id"], "arte.jpg", b"J" * 2048)
    con.close()
    pacote = tmp / "ok.zip"
    PAC.exportar_pacote(pacote, db_path=db, incluir_saves=False)
    destino = tmp / "destino.db"
    afirmar(PAC.importar_pacote(pacote, db_path=destino)["ok"])
    con = banco.get_db(destino)
    salvo = banco.listar_musicas(con)[0]
    con.execute("UPDATE musicas SET musica_capa='' WHERE id=?", (salvo["id"],))
    con.commit()
    con.close()
    res = PAC.importar_pacote(pacote, db_path=destino)
    con = banco.get_db(destino)
    afirmar(banco.listar_musicas(con)[0]["musica_capa"], res)
    con.close()
    # Pacote com áudio adulterado e hash antigo, numa casa sem arquivo existente.
    from unittest.mock import patch

    from bib_nucleo import base
    adulterado = tmp / "ruim.zip"
    with zipfile.ZipFile(pacote) as original, zipfile.ZipFile(adulterado, "w") as out:
        for info in original.infolist():
            out.writestr(info.filename, b"alterado" if info.filename.startswith("musicas/")
                         else original.read(info.filename))
    nova_pasta = tmp / "audio"
    with patch.object(base, "MUSICAS_DIR", nova_pasta):
        r = PAC.importar_pacote(adulterado, db_path=tmp / "ruim.db")
    afirmar(r["musicas"] == 0 and r["musicas_ignoradas"] == 1, r)
    afirmar(list(nova_pasta.iterdir()) == [], "áudio adulterado foi publicado")


def teste_resolver_audio_caminho_windows_em_casa_local():
    from unittest.mock import patch

    from bib_nucleo import base
    from bib_nucleo import musicas as MUS
    tmp = Path(tempfile.mkdtemp(prefix="suite-mus-"))
    alvo = tmp / "faixa.mp3"
    alvo.write_bytes(b"audio")
    with patch.object(base, "MUSICAS_DIR", tmp):
        afirmar(MUS.resolver_musica(r"Z:\outra-maquina\dados\musicas\faixa.mp3") == str(alvo))
    afirmar(MUS.resolver_musica("\x00") == "")
