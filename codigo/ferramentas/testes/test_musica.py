"""Músicas: tags ID3, varredura, import com dedup, CRUD v12, pacote v4."""
import json
import os
import struct
import tempfile
import zipfile
from pathlib import Path

import bib_core as core
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
    con = core.get_db(tmp / "m.db")
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(musicas)").fetchall()}
        afirmar({"titulo", "musica_sha", "musica_path"} <= cols, sorted(cols))
        r = MUS.importar_musicas(con, src)
        afirmar(r == {"novos": 2, "ignorados": 0, "erros": []}, r)
        r = MUS.importar_musicas(con, src)
        afirmar(r["novos"] == 0 and r["ignorados"] == 2, r)
        lst = core.listar_musicas(con)
        afirmar(len(lst) == 2, lst)
        afirmar(core.listar_musicas(con, q="cee")[0]["titulo"] == "Dee")
        mid = core.listar_musicas(con, q="bee")[0]["id"]
        alvo = Path(core.listar_musicas(con, q="bee")[0]["musica_path"])
        afirmar(alvo.is_file(), alvo)
        core.excluir_musica(con, mid)
        afirmar(not alvo.exists() and len(core.listar_musicas(con)) == 1)
        try:
            core.criar_musica(con, {"titulo": "", "musica_sha": "x"})
            afirmar(False, "devia levantar")
        except ValueError:
            pass
        try:
            core.excluir_musica(con, 9999)
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
    con = core.get_db(leg)
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(musicas)").fetchall()}
        afirmar("musica_sha" in cols, sorted(cols))
        njogos = con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()["n"]
        afirmar(njogos == 0, njogos)
    finally:
        con.close()


def teste_musica_helpers_texto_e_sugestao():
    from bib_nucleo import musicas as MUS
    afirmar(MUS.texto_musica({"titulo": "Bee", "artista": "Aaa"}) == "Aaa — Bee")
    afirmar(MUS.texto_musica({"titulo": "Solo", "artista": ""}) == "Solo")
    afirmar(MUS.texto_musica({}) == "")
    afirmar(MUS.harmoni_dir() is None)  # sandbox sem music/ (onboarding)
    s = MUS.sugestao_harmoni_dir()
    afirmar(isinstance(s, str), s)
    if os.name == "nt":
        afirmar(s.endswith("music"), s)
    else:
        afirmar(s == "", s)


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
    con = core.get_db(tmp / "m.db")
    try:
        MUS.importar_musicas(con, src)
    finally:
        con.close()
    dest = tmp / "p.zip"
    r = PAC.exportar_pacote(dest, db_path=tmp / "m.db", incluir_saves=False)
    afirmar(r.get("ok"), r)
    nomes = [i.filename for i in zipfile.ZipFile(dest).infolist()]
    afirmar(any(n.startswith("musicas/") for n in nomes), nomes)
    con2 = core.get_db(tmp / "m2.db")
    con2.close()
    r = PAC.importar_pacote(dest, db_path=tmp / "m2.db")
    afirmar(r.get("ok") and r.get("musicas", 0) == 1, r)
    con2 = core.get_db(tmp / "m2.db")
    try:
        lst = core.listar_musicas(con2)
        afirmar(len(lst) == 1 and lst[0]["titulo"] == "Bee", lst)
        afirmar(Path(lst[0]["musica_path"]).is_file(), lst)
    finally:
        con2.close()
