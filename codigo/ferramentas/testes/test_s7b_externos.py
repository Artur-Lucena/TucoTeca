"""S7 (fluxos externos): letras LRCLIB, capa LibRetro, desejo -> fontes -> coleção.

Tudo hermético: rede simulada e banco em arquivo temporário.
"""
from __future__ import annotations

import io
import json
import os
import struct
import tempfile
import urllib.error
import zlib
from pathlib import Path
from unittest.mock import patch

from executar import afirmar


class _Resp:
    def __init__(self, dados: bytes):
        self._d = dados

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n=-1):
        return self._d


def _png_bytes(w: int = 16, h: int = 16) -> bytes:
    raw = b"".join(b"\x00" + b"\x40\x80\xc0" * w for _ in range(h))

    def bloco(tipo: bytes, dados: bytes) -> bytes:
        return (struct.pack(">I", len(dados)) + tipo + dados
                + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + bloco(b"IDAT", zlib.compress(raw)) + bloco(b"IEND", b""))


def _banco():
    from bib_nucleo import banco as B
    tmp = Path(tempfile.mkdtemp(prefix="suite-s7b-"))
    return B, B.get_db(tmp / "biblioteca.db"), tmp


# ---------------------------------------------------------------- letras LRCLIB

def teste_letras_parse_lrc_ordena_e_ignora_lixo():
    from bib_nucleo.rede import letras
    texto = "[00:21.50] segunda\n[00:05.00] primeira\nlixo sem tempo\n[01:02] terceira"
    linhas = letras.linhas_lrc(texto)
    afirmar([item["texto"] for item in linhas] == ["primeira", "segunda", "terceira"], linhas)
    afirmar(linhas[0]["t"] == 5.0 and linhas[2]["t"] == 62.0, linhas)


def teste_letras_busca_usa_user_agent_cache_e_nao_repete():
    from bib_nucleo.rede import letras
    corpo = json.dumps({"syncedLyrics": "[00:01.00] oi\n[00:03.00] tchau",
                        "plainLyrics": "oi\ntchau"}).encode("utf-8")
    with patch.dict(os.environ):
        os.environ.pop("BIBLIOTECA_REDE", None)
        with patch("urllib.request.urlopen", return_value=_Resp(corpo)) as abrir:
            r1 = letras.buscar_letras("Hollow Knight", "Dream", "OST", 180)
            r2 = letras.buscar_letras("Hollow Knight", "Dream", "OST", 180)
    afirmar(r1["ok"] and r1["sincronizadas"] and len(r1["linhas"]) == 2, r1)
    afirmar(r1["cache"] is False and r2["cache"] is True, (r1, r2))
    afirmar(abrir.call_count == 1, "o segundo pedido deve vir do cache")
    req = abrir.call_args[0][0]
    afirmar("artist_name=Hollow+Knight" in req.full_url and "duration=180" in req.full_url, req.full_url)
    afirmar(req.get_header("User-agent", "").startswith("TucoTeca/"), "User-Agent deve identificar o app")


def teste_letras_nao_cadastrada_e_rede_desligada():
    from bib_nucleo.rede import letras
    nf = urllib.error.HTTPError("https://lrclib.net", 404, "nf", {}, io.BytesIO(b""))
    with patch.dict(os.environ):
        os.environ.pop("BIBLIOTECA_REDE", None)
        with patch("urllib.request.urlopen", side_effect=nf):
            r = letras.buscar_letras("Artista Sem Letra", "Faixa Rara")
        afirmar(r["ok"] is False and "não tem letra" in r["erro"], r)
        os.environ["BIBLIOTECA_REDE"] = "0"
        try:
            letras.buscar_letras("A", "B")
            afirmar(False, "com a rede desligada, deve levantar")
        except ValueError as e:
            afirmar("BIBLIOTECA_REDE" in str(e), e)


# ---------------------------------------------------------------- capa LibRetro

def teste_libretro_nome_e_url_do_boxart():
    from bib_nucleo.rede import capas_libretro as C
    afirmar(C.nome_arquivo('Zelda: A Link/Between & "Worlds"') == "Zelda_ A Link_Between _ _Worlds_",
            C.nome_arquivo('Zelda: A Link/Between & "Worlds"'))
    url = C.url_boxart("3DS", "Super Mario 3D Land")
    afirmar(url == "https://thumbnails.libretro.com/Nintendo%20-%20Nintendo%203DS/"
                   "Named_Boxarts/Super%20Mario%203D%20Land.png", url)
    try:
        C.url_boxart("PC", "Qualquer")
        afirmar(False, "PC não tem catálogo LibRetro")
    except ValueError as e:
        afirmar("3DS e NDS" in str(e), e)


def teste_libretro_busca_devolve_imagem_validada():
    from bib_nucleo import online
    from bib_nucleo.rede import capas_libretro as C
    png = _png_bytes()
    with patch.dict(os.environ):
        os.environ.pop("BIBLIOTECA_REDE", None)
        with patch.object(online, "baixar_imagem", return_value=(png, ".png", "/cache/x.img")) as bi:
            r = C.buscar_capa_libretro("NDS", "Pokemon Black")
    afirmar(r["raw"] == png and r["ext"] == ".png", r)
    afirmar("Nintendo%20-%20Nintendo%20DS" in bi.call_args[0][0], bi.call_args)


def teste_capa_libretro_salva_na_colecao():
    from bib_nucleo.rede import capas_libretro as C
    from servicos_ui import ServicoBiblioteca
    B, con, tmp = _banco()
    try:
        gid = B.criar_jogo(con, {"titulo": "Super Mario 3D Land"})["id"]
        con.commit()
    finally:
        con.close()
    svc = ServicoBiblioteca(tmp / "biblioteca.db")
    png = _png_bytes()
    with patch.object(ServicoBiblioteca, "jogo", return_value={"id": gid, "titulo": "Super Mario 3D Land",
                                                              "plataforma": "3DS"}), \
         patch.object(C, "buscar_capa_libretro", return_value={"raw": png, "ext": ".png", "url": "x"}):
        svc.buscar_capa_libretro(gid)
    con = B.get_db(tmp / "biblioteca.db")
    try:
        jogo = B.listar_jogos(con, q="Super Mario")[0]
        afirmar(jogo["capa"], "a capa precisa ficar associada ao jogo")
    finally:
        con.close()


# ---------------------------------------------------------------- desejo -> fontes -> coleção

def teste_desejo_busca_fontes_isola_erro_de_uma_fonte():
    from bib_nucleo.rede import fontes
    from servicos_ui import ServicoBiblioteca
    svc = ServicoBiblioteca(Path(tempfile.mkdtemp(prefix="suite-fontes-")) / "b.db")

    def steam(termo, timeout=20):
        return {"itens": [{"titulo": "Hollow Knight (SteamRip)", "url": "https://steamrip.com/hk/"}],
                "erros": []}

    def fitgirl(termo, timeout=20):
        raise OSError("site fora do ar")
    with patch.object(fontes, "buscar_steamrip", side_effect=steam), \
         patch.object(fontes, "buscar_fitgirl", side_effect=fitgirl):
        r = svc.buscar_fontes_desejo("Hollow Knight")
    afirmar(len(r["steamrip"]) == 1 and r["steamrip"][0]["url"].startswith("https://"), r)
    afirmar(r["fitgirl"] == [] and any("fitgirl" in e for e in r["erros"]), r)


def teste_desejo_baixar_importa_e_tira_da_lista():
    from bib_nucleo.rede import fontes, repacks
    from servicos_ui import ServicoBiblioteca
    B, con, tmp = _banco()
    try:
        B.adicionar_desejo(con, "367520", "Hollow Knight")
        did = B.listar_desejos(con)[0]["id"]
        con.commit()
        afirmar(len(B.listar_desejos(con)) == 1)
    finally:
        con.close()
    arquivo = tmp / "hollow-knight.rar"
    arquivo.write_bytes(b"Rar!\x1a\x07\x00")
    svc = ServicoBiblioteca(tmp / "biblioteca.db")
    with patch.object(fontes, "baixar_steamrip", return_value={"ok": True, "path": str(arquivo)}), \
         patch.object(repacks, "importar_repack", return_value={"ok": True, "titulo": "Hollow Knight"}):
        r = svc.baixar_fonte_steamrip("https://steamrip.com/hk/", did)
    afirmar(r.get("ok") is True, r)
    con = B.get_db(tmp / "biblioteca.db")
    try:
        afirmar(B.listar_desejos(con) == [], "o desejo obtido deve sair da lista ativa")
        afirmar(B.listar_desejos(con, incluir_obtidos=True)[0]["obtido_em"], "histórico perdido")
        B.sincronizar_desejos(con, [{"appid": "367520", "titulo": "Hollow Knight"}])
        afirmar(not B.listar_desejos(con), "sincronização ressuscitou desejo obtido")
    finally:
        con.close()


def teste_desejo_importacao_falha_preserva_arquivo_e_desejo():
    from bib_nucleo.rede import fontes, repacks
    from servicos_ui import ServicoBiblioteca
    B, con, tmp = _banco()
    B.adicionar_desejo(con, "2", "Jogo")
    did = B.listar_desejos(con)[0]["id"]
    con.close()
    arq = tmp / "jogo.zip"
    arq.write_bytes(b"arquivo preservado")
    svc = ServicoBiblioteca(tmp / "biblioteca.db")
    with patch.object(fontes, "baixar_steamrip", return_value={"ok": True, "path": str(arq)}), \
         patch.object(repacks, "importar_repack", return_value={"ok": False, "erro": "sem executável"}):
        r = svc.baixar_fonte_steamrip("https://steamrip.com/x/", did)
    afirmar(not r["ok"] and arq.is_file())
    con = B.get_db(tmp / "biblioteca.db")
    try:
        afirmar(len(B.listar_desejos(con)) == 1)
    finally:
        con.close()


def teste_letras_malformadas_nao_entram_no_cache():
    from bib_nucleo.rede import letras
    with patch("urllib.request.urlopen", return_value=_Resp(b"[]")):
        r = letras.buscar_letras("A", "Formato errado")
    afirmar(not r["ok"] and "inválida" in r["erro"], r)
    linhas = letras.linhas_lrc("[00:01.125][00:03.250] refrão\n[00:99] lixo")
    afirmar([item["t"] for item in linhas] == [1.125, 3.25], linhas)


def teste_desejo_download_falho_nao_mexe_na_lista():
    from bib_nucleo.rede import fontes
    from servicos_ui import ServicoBiblioteca
    B, con, tmp = _banco()
    try:
        B.adicionar_desejo(con, "1", "Jogo")
        did = B.listar_desejos(con)[0]["id"]
        con.commit()
    finally:
        con.close()
    svc = ServicoBiblioteca(tmp / "biblioteca.db")
    with patch.object(fontes, "baixar_steamrip", return_value={"ok": False, "erro": "host caiu"}):
        r = svc.baixar_fonte_steamrip("https://steamrip.com/x/", did)
    afirmar(r["ok"] is False and r["erro"] == "host caiu", r)
    con = B.get_db(tmp / "biblioteca.db")
    try:
        afirmar(len(B.listar_desejos(con)) == 1, "download falho não pode apagar o desejo")
    finally:
        con.close()
