"""Parser NDS: header + banner sintéticos (sem ROM real)."""
import tempfile
from pathlib import Path

from bib_nucleo import scans
from executar import afirmar


def _rom_nds(titulo="TESTGAME", code=b"ATCE", nome_en="Test Game EN"):
    head = bytearray(0x200)
    head[:12] = titulo.encode("ascii")[:12].ljust(12, b"\x00")
    head[0x0C:0x10] = code
    head[0x68:0x6C] = (0x4000).to_bytes(4, "little")
    banner = bytearray(0x1000)
    banner[0:2] = (0x0003).to_bytes(2, "little")
    for i in range(512):  # xadrez 4bpp: cor 1 e 2 alternadas
        banner[0x20 + i] = 0x21 if (i // 4) % 2 == 0 else 0x12
    banner[0x220:0x222] = (0).to_bytes(2, "little")       # 0: preto
    banner[0x222:0x224] = (0x001F).to_bytes(2, "little")  # 1: vermelho
    banner[0x224:0x226] = (0x03E0).to_bytes(2, "little")  # 2: verde
    enc = nome_en.encode("utf-16-le")[:0x100].ljust(0x100, b"\x00")
    banner[0x240 + 0x100:0x240 + 0x200] = enc
    p = Path(tempfile.mkdtemp(prefix="suite-nds-")) / "jogo.nds"
    p.write_bytes(bytes(head).ljust(0x4000, b"\x00") + bytes(banner))
    return p


def teste_metadados_nds():
    p = _rom_nds()
    m = scans.ler_metadados_nds(str(p))
    afirmar(m.get("titulo") == "Test Game EN", m)
    afirmar(m.get("game_code") == "ATCE", m)
    afirmar(m.get("regiao") == "América do Norte", m)
    afirmar(m.get("tem_metadados") is True, m)


def teste_metadados_nds_sem_banner():
    p = Path(tempfile.mkdtemp(prefix="suite-nds2-")) / "x.nds"
    head = bytearray(0x200)
    head[:12] = b"PLAIN".ljust(12, b"\x00")
    head[0x0C:0x10] = b"BJPJ"
    p.write_bytes(bytes(head))
    m = scans.ler_metadados_nds(str(p))
    afirmar(m.get("titulo") == "PLAIN" and m.get("game_code") == "BJPJ", m)
    afirmar(m.get("regiao") == "Japão", m)
    afirmar("tem_metadados" not in m, m)


def teste_icone_nds_png_valido():
    p = _rom_nds()
    png = scans.icone_nds_para_png(str(p))
    afirmar(png and png[:8] == b"\x89PNG\r\n\x1a\n", (png or b"")[:8])
    import struct
    larg, alt = struct.unpack(">II", png[16:24])
    afirmar((larg, alt) == (96, 96), (larg, alt))


def teste_icone_nds_cores():
    import struct
    import zlib
    p = _rom_nds()
    png = scans.icone_nds_para_png(str(p), alvo_px=32)
    assert png
    pos = 8
    idat = b""
    while pos < len(png):
        (tam,) = struct.unpack(">I", png[pos:pos + 4])
        tipo = png[pos + 4:pos + 8]
        if tipo == b"IDAT":
            idat += png[pos + 8:pos + 8 + tam]
        pos += 12 + tam
    raw = zlib.decompress(idat)
    px = raw[1:4]  # primeiro pixel da 1ª linha (filtro 0)
    afirmar(tuple(px) == (255, 0, 0), tuple(px))  # cor 1 = vermelho


def teste_rom_invalida():
    afirmar(scans.ler_metadados_nds("/nao/existe.nds") == {})
    afirmar(scans.icone_nds_para_png("/nao/existe.nds") is None)

def teste_titulo_multilinha_limpo():
    tmp = Path(tempfile.mkdtemp(prefix="suite-ndsm-"))
    head = bytearray(0x200)
    head[:12] = b"MULTI"
    head[0x0C:0x10] = b"AMCE"
    head[0x68:0x6C] = (0x4000).to_bytes(4, "little")
    banner = bytearray(0x1000)
    nome = "Pokémon\nBlack Version\nNintendo".encode("utf-16-le")
    banner[0x340:0x340 + len(nome)] = nome
    p = tmp / "m.nds"
    p.write_bytes(bytes(head).ljust(0x4000, b"\x00") + bytes(banner))
    m = scans.ler_metadados_nds(str(p))
    afirmar(m.get("titulo") == "Pokémon Black Version", m)


def teste_tags_nds_limpas():
    from bib_nucleo.scans import _titulo_de_rom
    afirmar(_titulo_de_rom(Path("Pokemon - Black Version (USA, Europe) (NDSi Enhanced).nds"))
            == "Pokemon Black Version")
    afirmar(_titulo_de_rom(Path("Pokemon - Pearl Version (USA) (Rev 5).nds"))
            == "Pokemon Pearl Version")


def teste_roots_nds_reais():
    roots = scans.default_roms_nds_roots()
    afirmar(any("Roms NDs" in r for r in roots), roots)


def teste_capa_falha_vira_aviso():
    from bib_nucleo import banco
    tmp = Path(tempfile.mkdtemp(prefix="suite-nc-"))
    (tmp / "vazia.nds").write_bytes(b"0")
    con = banco.get_db(tmp / "t.db")
    try:
        res = scans.importar_lista(con, [{"titulo": "Sem Icone", "executable_path": "",
                                         "status": "backlog", "origem": "rom-nds",
                                         "rom_path": str(tmp / "vazia.nds")}])
        afirmar(res["novos"] == 1, res)
        afirmar(any("Sem Icone" in a for a in res["avisos"]), res)
        afirmar("Sem Icone" in scans.resumo_importacao(res), res)
    finally:
        con.close()
