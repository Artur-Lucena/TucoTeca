"""DeSmuME: spec, NDS e2e, fundir NDS, instalar fake, preparar sem aviso cripto."""
import tempfile
import zipfile
from pathlib import Path

import bib_core as core
from bib_nucleo import emuladores as EMU
from executar import afirmar


def _rom_nds(d, nome="Jogo Teste.nds", titulo="JOGO TESTE", code=b"ATCE",
             nome_en="Test Game EN"):
    head = bytearray(0x200)
    head[:12] = titulo.encode("ascii")[:12].ljust(12, b"\x00")
    head[0x0C:0x10] = code
    head[0x68:0x6C] = (0x4000).to_bytes(4, "little")
    banner = bytearray(0x1000)
    banner[0x222:0x224] = (0x001F).to_bytes(2, "little")
    enc = nome_en.encode("utf-16-le")[:0x100].ljust(0x100, b"\x00")
    banner[0x340:0x440] = enc
    p = d / nome
    p.write_bytes(bytes(head).ljust(0x4000, b"\x00") + bytes(banner))
    return p


def teste_spec_desmume():
    provs = core.provedores()
    afirmar(set(provs) == {"azahar", "desmume"}, set(provs))
    dm = provs["desmume"]
    afirmar(dm["origem"] == "rom-nds" and dm["origens"] == ("rom-nds",), dm)
    afirmar(dm["rom_exts"] == {".nds", ".dsi"}, dm)
    afirmar(dm["saves_subs"] == () and dm["pacote_subs"] == (), dm)
    for k in ("exe", "user_dir", "flags", "aplicar_preset", "ler_metadados",
              "icone", "release_info", "versao_local", "instalar"):
        afirmar(callable(dm[k]), k)


def teste_analisar_nds():
    tmp = Path(tempfile.mkdtemp(prefix="suite-dm-"))
    rom = _rom_nds(tmp)
    ana = core.analisar_arquivo(str(rom))
    afirmar(ana["tipo"] == "rom" and ana["provedor"] == "desmume", ana)
    afirmar(ana["item"]["origem"] == "rom-nds", ana["item"])
    afirmar(ana["item"]["titulo"] == "Test Game EN", ana["item"])
    afirmar(ana["item"]["game_code"] == "ATCE", ana["item"])


def teste_scan_nds():
    tmp = Path(tempfile.mkdtemp(prefix="suite-ds-"))
    _rom_nds(tmp, "a.nds", nome_en="Alfa")
    _rom_nds(tmp, "b.nds", nome_en="Beta", code=b"BJPJ")
    achados, info = core.scan_roms([str(tmp)], emu_exe="EMU", retornar_info=True,
                                   prov_chave="desmume")
    afirmar(len(achados) == 2, achados)
    afirmar(all(a["origem"] == "rom-nds" and a["executable_path"] == "EMU" for a in achados))
    afirmar({a["titulo"] for a in achados} == {"Alfa", "Beta"}, achados)


def teste_fundir_nds_separa_variantes():
    a = {"titulo": "Z", "executable_path": "e", "origem": "rom-nds",
         "rom_path": "/r/a.nds", "shop": "", "object_id": "", "horas": 0.0}
    b = dict(a, rom_path="/r/b.nds")
    r = core.fundir_duplicados([a, b])
    afirmar(len(r) == 2, r)
    c = dict(a, rom_path="/r/a.nds")
    r = core.fundir_duplicados([a, c])
    afirmar(len(r) == 1, r)


def teste_preparar_nds_sem_aviso_cripto():
    tmp = Path(tempfile.mkdtemp(prefix="suite-dp-"))
    rom = _rom_nds(tmp)
    r = core.preparar_lancamento({"origem": "rom-nds", "launch_options": str(rom),
                                  "azahar_preset": "inexistente"})
    afirmar(r["preset_aplicado"] is None and r["aviso"] is not None
            and "aes_keys" not in (r["aviso"] or ""), r)


def teste_instalar_desmume_fake():
    import os
    if os.name != "nt":
        print("(só Windows: skip)")
        return
    tmp = Path(tempfile.mkdtemp(prefix="suite-di-"))
    src = tmp / "rel"
    src.mkdir()
    (src / "DeSmuME_9.9.9_x64.exe").write_bytes(b"MZ" + b"0" * 12_000_000)
    zp = tmp / "d.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(src / "DeSmuME_9.9.9_x64.exe", "DeSmuME_9.9.9_x64.exe")
    dest = tmp / "emu"
    orig = EMU.desmume_dir
    EMU.desmume_dir = lambda: dest
    try:
        res = EMU.desmume_instalar({"url": zp.as_uri(), "tag": "t9"})
        afirmar(res.get("ok"), res)
        afirmar((dest / "desmume.exe").is_file(), res)
        afirmar(not (dest / "DeSmuME_9.9.9_x64.exe").exists(), "não renomeou")
        afirmar((dest / "desmume-versao.txt").read_text(encoding="utf-8") == "t9")
    finally:
        EMU.desmume_dir = orig


def teste_preview_pasta_inclui_nds():
    tmp = Path(tempfile.mkdtemp(prefix="suite-dq-"))
    _rom_nds(tmp, "z.nds", nome_en="Zeta NDS")
    _roots, itens, info = core.preview_pasta([str(tmp)])
    achou = [i for i in itens if i.get("origem") == "rom-nds"]
    afirmar(len(achou) == 1 and achou[0]["titulo"] == "Zeta NDS", achados_str(itens))
    afirmar("emu_nds" in info, info)


def teste_score_rom_nds_igual_3ds():
    tmp = Path(tempfile.mkdtemp(prefix="suite-dw-"))
    rom = _rom_nds(tmp, "s.nds", nome_en="Score")
    a = core.pontuar({"titulo": "S", "executable_path": "e", "shop": "",
                      "object_id": "", "horas": 0.0, "origem": "rom-nds",
                      "rom_path": str(rom), "tem_metadados": True})
    b = core.pontuar({"titulo": "S", "executable_path": "e", "shop": "",
                      "object_id": "", "horas": 0.0, "origem": "rom-3ds",
                      "rom_path": str(rom), "tem_metadados": True})
    afirmar(a["score"] == b["score"] == 0.6, (a["score"], b["score"]))
    afirmar("ROM existe neste SO" in a["motivos"], a["motivos"])


def teste_tui_mostra_nds():
    import app_tui as tui

    class FakeScr:
        def getmaxyx(self):
            return (24, 80)

        def addnstr(self, *a):
            pass

        def erase(self):
            pass

        def refresh(self):
            pass

        def getch(self):
            return ord("q")

    class FakeCurses:
        COLOR_CYAN = COLOR_BLACK = COLOR_GREEN = COLOR_RED = 1

        def curs_set(self, *a):
            pass

        def has_colors(self):
            return False

    tui.curses = FakeCurses()
    tmp = Path(tempfile.mkdtemp(prefix="suite-dt-"))
    t = tui.Tui(FakeScr(), tmp / "u.db")
    t.desenhar()  # não pode levantar (status NDS incluso)


def achados_str(itens):
    return [(i.get("titulo"), i.get("origem")) for i in itens]
