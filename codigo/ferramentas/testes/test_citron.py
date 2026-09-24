"""Citron (Switch): spec, NSP/XCI e2e, fundir Switch, instalar fake, preset v11."""
import os
import tempfile
import zipfile
from pathlib import Path

import bib_core as core
from bib_nucleo import emuladores as EMU
from executar import afirmar


def _rom_switch(d, nome="Zelda Teste.nsp"):
    p = Path(d) / nome
    p.write_bytes(b"PFS0" + b"\x00" * 64)
    return p


def teste_spec_citron():
    provs = core.provedores()
    afirmar(set(provs) == {"azahar", "desmume", "citron"}, set(provs))
    ct = provs["citron"]
    afirmar(ct["origem"] == "rom-switch" and ct["origens"] == ("rom-switch",), ct)
    afirmar(ct["rom_exts"] == core.ROM_EXTS_SWITCH, ct["rom_exts"])
    afirmar(ct["saves_subs"] == ("nand/user/save", "sdmc"), ct)
    afirmar(ct["pacote_subs"] == ("nand/user/save", "sdmc"), ct)
    for k in ("exe", "user_dir", "flags", "aplicar_preset", "ler_metadados",
              "icone", "release_info", "versao_local", "instalar"):
        afirmar(callable(ct[k]), k)
    afirmar(core.provedor_por_extensao(".nsp")["chave"] == "citron")
    afirmar(core.provedor_por_extensao(".xci")["chave"] == "citron")
    afirmar(core.provedor_por_origem("rom-switch")["chave"] == "citron")


def teste_analisar_nsp():
    tmp = Path(tempfile.mkdtemp(prefix="suite-sw-"))
    rom = _rom_switch(tmp)
    ana = core.analisar_arquivo(str(rom))
    afirmar(ana["tipo"] == "rom" and ana["provedor"] == "citron", ana)
    afirmar(ana["item"]["origem"] == "rom-switch", ana["item"])
    afirmar(ana["item"]["titulo"] == "Zelda Teste", ana["item"])


def teste_scan_switch():
    tmp = Path(tempfile.mkdtemp(prefix="suite-ss-"))
    _rom_switch(tmp, "a.nsp")
    _rom_switch(tmp, "b.xci")
    (tmp / "c.nds").write_bytes(b"0" * 16)
    achados, info = core.scan_roms([str(tmp)], emu_exe="EMU", retornar_info=True,
                                   prov_chave="citron")
    afirmar(len(achados) == 2, achados)
    afirmar(all(a["origem"] == "rom-switch" and a["executable_path"] == "EMU" for a in achados))
    afirmar({a["titulo"] for a in achados} == {"a", "b"}, achados)


def teste_fundir_switch_separa_variantes():
    a = {"titulo": "Z", "executable_path": "e", "origem": "rom-switch",
         "rom_path": "/r/a.nsp", "shop": "", "object_id": "", "horas": 0.0}
    b = dict(a, rom_path="/r/b.nsp")
    r = core.fundir_duplicados([a, b])
    afirmar(len(r) == 2, r)
    c = dict(a, rom_path="/r/a.nsp")
    r = core.fundir_duplicados([a, c])
    afirmar(len(r) == 1, r)


def teste_preparar_switch_avisa_chaves():
    tmp = Path(tempfile.mkdtemp(prefix="suite-sp-"))
    rom = _rom_switch(tmp)
    r = core.preparar_lancamento({"origem": "rom-switch", "launch_options": str(rom),
                                  "citron_preset": "inexistente"})
    afirmar(r["preset_aplicado"] is None, r)
    afirmar(r["aviso"] is not None and "prod.keys" in r["aviso"], r)


def teste_preparar_switch_preset_ok():
    tmp = Path(tempfile.mkdtemp(prefix="suite-sq-"))
    rom = _rom_switch(tmp)
    ud = tmp / "user"
    (ud / "config").mkdir(parents=True)
    (ud / "config" / "qt-config.ini").write_text("[General]\n", encoding="utf-8")
    (ud / "keys").mkdir()
    (ud / "keys" / "prod.keys").write_text("x", encoding="utf-8")
    fw = ud / "nand" / "system" / "Contents" / "registered"
    fw.mkdir(parents=True)
    pre = tmp / "presets" / "citron"
    pre.mkdir(parents=True)
    (pre / "perf.ini").write_text("[General]\n", encoding="utf-8")
    orig_exe = EMU.default_emu_switch
    orig_ud = EMU.citron_user_dir
    orig_pre = EMU.presets_prov_dir
    EMU.default_emu_switch = lambda: str(tmp / "citron.exe")
    EMU.citron_user_dir = lambda exe="": str(ud)
    EMU.presets_prov_dir = lambda chave="citron": pre if chave == "citron" else orig_pre(chave)
    try:
        r = core.preparar_lancamento({"origem": "rom-switch", "launch_options": str(rom),
                                      "citron_preset": "perf"})
        afirmar(r["preset_aplicado"] == "perf" and r["aviso"] is None, r)
    finally:
        EMU.default_emu_switch = orig_exe
        EMU.citron_user_dir = orig_ud
        EMU.presets_prov_dir = orig_pre


def teste_migracao_v11_citron_preset():
    tmp = Path(tempfile.mkdtemp(prefix="suite-sv-"))
    con = core.get_db(tmp / "v.db")
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(jogos)").fetchall()}
        afirmar("citron_preset" in cols, sorted(cols))
        g = core.criar_jogo(con, {"titulo": "SW", "executable_path": "",
                                  "status": "backlog", "citron_preset": "perf"})
        afirmar(g["citron_preset"] == "perf" if "citron_preset" in g else True, g)
        r = core.importar_lista(con, [{"titulo": "SW2", "executable_path": "",
                                       "launch_options": str(tmp / "g.nsp"),
                                       "origem": "rom-switch",
                                       "citron_preset": "q"}])
        afirmar(r["novos"] == 1, r)
        row = con.execute("SELECT citron_preset FROM jogos WHERE titulo='SW2'").fetchone()
        afirmar(row["citron_preset"] == "q", dict(row))
    finally:
        con.close()


def teste_preview_pasta_inclui_switch():
    tmp = Path(tempfile.mkdtemp(prefix="suite-sw2-"))
    _rom_switch(tmp, "Zeta Switch.nsp")
    _roots, itens, info = core.preview_pasta([str(tmp)])
    achou = [i for i in itens if i.get("origem") == "rom-switch"]
    afirmar(len(achou) == 1 and achou[0]["titulo"] == "Zeta Switch", achados_str(itens))
    afirmar("emu_switch" in info, info)


def teste_score_rom_switch():
    tmp = Path(tempfile.mkdtemp(prefix="suite-sw3-"))
    rom = _rom_switch(tmp, "s.nsp")
    a = core.pontuar({"titulo": "S", "executable_path": "e", "shop": "",
                      "object_id": "", "horas": 0.0, "origem": "rom-switch",
                      "rom_path": str(rom)})
    afirmar(a["score"] == 0.5, (a["score"], a["motivos"]))
    afirmar("ROM existe neste SO" in a["motivos"], a["motivos"])


def teste_instalar_citron_fake():
    if os.name != "nt":
        print("(só Windows: skip)")
        return
    tmp = Path(tempfile.mkdtemp(prefix="suite-si-"))
    src = tmp / "rel"
    src.mkdir()
    (src / "citron.exe").write_bytes(b"MZ" + b"0" * 12_000_000)
    zp = tmp / "c.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(src / "citron.exe", "citron.exe")
    dest = tmp / "emu"
    orig = EMU._citron_dir
    EMU._citron_dir = lambda: dest
    try:
        res = EMU.citron_instalar({"url": zp.as_uri(), "tag": "2026-04-27"})
        afirmar(res.get("ok"), res)
        afirmar((dest / "citron.exe").is_file(), res)
        afirmar((dest / "versao-citron.txt").read_text(encoding="utf-8") == "2026-04-27")
    finally:
        EMU._citron_dir = orig


def teste_release_info_sem_rede_da_erro():
    info = EMU.citron_release_info(timeout=1)
    afirmar("erro" in info, info)


def achados_str(itens):
    return [(i.get("titulo"), i.get("origem")) for i in itens]
