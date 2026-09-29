"""Controles: GUIDs, mapas padrão, merge de perfil, captura, detecção."""
import os
import tempfile
from pathlib import Path

from executar import afirmar


def teste_guids_e_mapas_completos():
    from bib_nucleo import controles as C
    for tipo, guid in C.GUIDS.items():
        afirmar(len(guid) == 32 and all(c in "0123456789abcdef" for c in guid), (tipo, guid))
        afirmar(tipo in C.MAPAS and tipo in C.NOMES_TIPO, tipo)
        mapa = C.MAPAS[tipo]
        for chave in C.BOTOES_3DS:
            afirmar(chave in mapa and mapa[chave][0] in ("btn", "eixo"), (tipo, chave))
    afirmar(set(C.DPAD) == {"button_up", "button_down", "button_left", "button_right"})
    afirmar(len(C.STICK_ESQ) == 4 and len(C.STICK_DIR) == 4)


def teste_gerar_perfil_xbox360_exato():
    from bib_nucleo import controles as C
    g = C.GUIDS["xbox360"]
    p = C.gerar_perfil("xbox360")
    afirmar(p["profiles\\1\\button_b"] ==
            f"api:controller,button:0,engine:sdl,guid:{g},maptype:guid+port,name:A,port:0", p)
    afirmar(p["profiles\\1\\button_a"] ==
            f"api:controller,button:1,engine:sdl,guid:{g},maptype:guid+port,name:B,port:0", p)
    afirmar(p["profiles\\1\\button_zl"] ==
            f"api:controller,axis:2,direction:+,engine:sdl,guid:{g},maptype:guid+port,name:Left Trigger,port:0,threshold:0.500000", p)
    afirmar(p["profiles\\1\\button_up"] ==
            f"api:controller,button:11,engine:sdl,guid:{g},maptype:guid+port,name:D-Pad Up,port:0", p)
    circ = p["profiles\\1\\circle_pad"]
    afirmar(circ ==
            f"api:controller,axis_x:0,axis_y:1,deadzone:0.100000,engine:sdl,guid:{g},maptype:guid+port,name_x:Left Stick X,name_y:Left Stick Y,port:0", circ)
    afirmar("axis_x:2,axis_y:3" in p["profiles\\1\\c_stick"], p)
    try:
        C.gerar_perfil("watara")
        afirmar(False, "devia levantar")
    except ValueError:
        pass


def teste_gerar_perfil_tipos_divergentes():
    from bib_nucleo import controles as C
    ps = C.gerar_perfil("ps4")
    afirmar(",button:1," in ps["profiles\\1\\button_b"], ps)
    afirmar(ps["profiles\\1\\button_zl"].startswith("api:controller,axis:3,direction:+"), ps)
    sp = C.gerar_perfil("switchpro")
    afirmar(sp["profiles\\1\\button_zl"] == f"api:controller,button:6,engine:sdl,guid:{C.GUIDS['switchpro']},maptype:guid+port,name:ZL,port:0", sp)
    afirmar(",button:9," in sp["profiles\\1\\button_start"], sp)
    xo = C.gerar_perfil("xboxone")
    afirmar(xo["profiles\\1\\button_zr"].startswith("api:controller,axis:5,direction:+"), xo)


def teste_fotografar_aplicar_roundtrip():
    from bib_nucleo import controles as C
    tmp = Path(tempfile.mkdtemp(prefix="suite-ctl-"))
    emu = Path(os.environ.get("BIBLIOTECA_AZAHAR_DIR"))
    (emu / "user" / "config").mkdir(parents=True, exist_ok=True)
    (emu / "azahar.exe").write_bytes(b"MZ")
    cfg = emu / "user" / "config" / "qt-config.ini"
    cfg.write_text("[Controls]\nprofiles\\1\\button_a=code:65,engine:keyboard\n[Renderer]\nresolution_factor=1\n",
                   encoding="utf-8")
    r = C.fotografar_perfil("Meu Pad!")
    afirmar(r.get("ok") and r["preset"] == "meu-pad", r)
    afirmar("meu-pad" in C.listar_presets_controle())
    r = C.salvar_mapa_gerado("xbox360", nome="x360-teste")
    afirmar(r.get("ok") and r["chaves"] >= 17, r)
    # envenena: profile travado no 0 (bug real achado no Azahar 2126)
    with open(cfg, "a", encoding="utf-8") as fh:
        fh.write("profile\\default=true\nprofile=1\n")
    r = C.aplicar_preset_controle("x360-teste")
    afirmar(r.get("ok") and r.get("chaves", 0) >= 17, r)
    texto = cfg.read_text(encoding="utf-8")
    afirmar("api:controller,button:1" in texto and "resolution_factor" in texto,
            texto[:400])
    afirmar("[Controls]" in texto)
    afirmar('profiles\\1\\button_a\\default=false' in texto, texto[:600])
    afirmar('profiles\\1\\button_a="api:controller,button:1' in texto)
    afirmar(texto.count("profiles\\1\\button_a=") == 1, "chave duplicada!")
    afirmar("profile\\default" not in texto, "veneno profile\\default ficou!")
    afirmar("\nprofile=1\n" in texto or texto.startswith("profile=1\n")
            or "\nprofile=1" in texto)
    sec = texto.index("[Controls]")
    prox = texto.index("[Renderer]")
    afirmar(sec < texto.index('profiles\\1\\button_a="api:') < prox,
            "bind fora da seção Controls!")
    afirmar('profiles\\1\\name="x360-teste"' in texto, "nome Default mantido!")
    afirmar('profiles\\1\\name\\default=false' in texto)
    r = C.aplicar_preset_controle("fantasma")
    afirmar(not r.get("ok"), r)
    r = C.fotografar_perfil("")
    afirmar(not r.get("ok"), r)


def teste_fotografar_pula_identidade():
    import configparser
    from bib_nucleo import controles as C
    tmp = Path(tempfile.mkdtemp(prefix="suite-ctl-"))
    emu = Path(os.environ.get("BIBLIOTECA_AZAHAR_DIR"))
    (emu / "user" / "config").mkdir(parents=True, exist_ok=True)
    (emu / "azahar.exe").write_bytes(b"MZ")
    (emu / "user" / "config" / "qt-config.ini").write_text(
        "[Controls]\nprofiles\\1\\name=Pad\n"
        "profiles\\1\\input_maptype=2\n"
        "profiles\\1\\button_a\\default=false\n"
        "profiles\\1\\button_a=\"api:controller,button:1,engine:sdl\"\n",
        encoding="utf-8")
    r = C.fotografar_perfil("sem-id")
    afirmar(r.get("ok"), r)
    ini = configparser.ConfigParser()
    ini.optionxform = str
    ini.read(r["arquivo"], encoding="utf-8")
    chaves = [k for k, _ in ini.items("Controls")]
    afirmar(chaves == ["profiles\\1\\button_a"], chaves)


def teste_perfil_ativo_e_detectar_sdl():
    from bib_nucleo import controles as C
    tmp = Path(tempfile.mkdtemp(prefix="suite-ctl-"))
    emu = Path(os.environ.get("BIBLIOTECA_AZAHAR_DIR"))
    (emu / "user" / "config").mkdir(parents=True, exist_ok=True)
    (emu / "azahar.exe").write_bytes(b"MZ")
    cfg = emu / "user" / "config" / "qt-config.ini"
    g = C.GUIDS["xbox360"]
    cfg.write_text("[Controls]\nprofile=1\n"
                   "profiles\\1\\button_a=code:65,engine:keyboard\n"
                   f"profiles\\2\\button_a=api:controller,button:1,engine:sdl,guid:{g},maptype:guid+port,name:B,port:0\n",
                   encoding="utf-8")
    afirmar(C.perfil_ativo() == 1)
    det = C.detectar_sdl()
    afirmar(len(det) == 1 and det[0]["guid"] == g
            and det[0]["nome"] == "B" and det[0]["perfil"] == "profiles", det)
    r = C.fotografar_perfil("amostra")
    afirmar(r.get("ok"), r)
    import configparser
    ini = configparser.ConfigParser()
    ini.optionxform = str
    ini.read(r["arquivo"], encoding="utf-8")
    afirmar(ini.has_option("Controls", "profiles\\1\\button_a"), ini.sections())
    r = C.salvar_mapa_gerado("xbox360", nome="x360b")
    afirmar(r.get("ok"), r)
    r = C.aplicar_preset_controle("x360b")
    afirmar(r.get("ok"), r)
    texto = cfg.read_text(encoding="utf-8")
    afirmar("profiles\\2\\button_b" in texto and "api:controller,button:0" in texto,
            texto[:500])
    afirmar("profiles\\1\\button_a=code:65,engine:keyboard" in texto)


def teste_aplicar_garante_size():
    from bib_nucleo import controles as C
    tmp = Path(tempfile.mkdtemp(prefix="suite-ctl-"))
    emu = Path(os.environ.get("BIBLIOTECA_AZAHAR_DIR"))
    (emu / "user" / "config").mkdir(parents=True, exist_ok=True)
    (emu / "azahar.exe").write_bytes(b"MZ")
    cfg = emu / "user" / "config" / "qt-config.ini"
    cfg.write_text("[Controls]\nprofile=1\nprofiles\\size=1\n"
                   "profiles\\2\\button_a=code:65,engine:keyboard\n",
                   encoding="utf-8")
    r = C.salvar_mapa_gerado("xbox360", nome="x360-size")
    afirmar(r.get("ok"), r)
    r = C.aplicar_preset_controle("x360-size")
    afirmar(r.get("ok"), r)
    texto = cfg.read_text(encoding="utf-8")
    afirmar("profiles\\size=2" in texto, texto[:300])
    afirmar('profiles\\2\\button_a="api:controller,button:1' in texto)
    afirmar("profiles\\2\\button_a=code:65" not in texto.replace(
        'profiles\\2\\button_a="api', ""))


def teste_fotografar_pula_flags():
    import configparser
    from bib_nucleo import controles as C
    tmp = Path(tempfile.mkdtemp(prefix="suite-ctl-"))
    emu = Path(os.environ.get("BIBLIOTECA_AZAHAR_DIR"))
    (emu / "user" / "config").mkdir(parents=True, exist_ok=True)
    (emu / "azahar.exe").write_bytes(b"MZ")
    cfg = emu / "user" / "config" / "qt-config.ini"
    cfg.write_text("[Controls]\nprofile=0\n"
                   "profiles\\1\\button_a\\default=false\n"
                   "profiles\\1\\button_a=\"api:controller,button:1,engine:sdl\"\n",
                   encoding="utf-8")
    r = C.fotografar_perfil("limpa")
    afirmar(r.get("ok"), r)
    ini = configparser.ConfigParser()
    ini.optionxform = str
    ini.read(r["arquivo"], encoding="utf-8")
    chaves = [k for k, _ in ini.items("Controls")]
    afirmar(chaves == ["profiles\\1\\button_a"], chaves)


def teste_aplicar_em_slot_explicito():
    from bib_nucleo import controles as C
    tmp = Path(tempfile.mkdtemp(prefix="suite-ctl-"))
    emu = Path(os.environ.get("BIBLIOTECA_AZAHAR_DIR"))
    (emu / "user" / "config").mkdir(parents=True, exist_ok=True)
    (emu / "azahar.exe").write_bytes(b"MZ")
    cfg = emu / "user" / "config" / "qt-config.ini"
    cfg.write_text("[Controls]\nprofile=0\nprofiles\\size=1\n"
                   "profiles\\1\\button_a=code:65,engine:keyboard\n",
                   encoding="utf-8")
    r = C.salvar_mapa_gerado("xbox360", nome="x360-slot")
    afirmar(r.get("ok"), r)
    r = C.aplicar_preset_controle("x360-slot", perfil=1)
    afirmar(r.get("ok"), r)
    texto = cfg.read_text(encoding="utf-8")
    afirmar("\nprofile=1\n" in texto or "profile=1" in texto.splitlines(), texto[:300])
    afirmar("profiles\\size=2" in texto)
    afirmar('profiles\\2\\button_a="api:controller,button:1' in texto)
    afirmar("profiles\\1\\button_a=code:65,engine:keyboard" in texto)
    r = C.aplicar_preset_controle("x360-slot", perfil=-1)
    afirmar(not r.get("ok"), r)


def teste_higienizar_remove_crud():
    from bib_nucleo import controles as C
    tmp = Path(tempfile.mkdtemp(prefix="suite-ctl-"))
    emu = Path(os.environ.get("BIBLIOTECA_AZAHAR_DIR"))
    (emu / "user" / "config").mkdir(parents=True, exist_ok=True)
    (emu / "azahar.exe").write_bytes(b"MZ")
    cfg = emu / "user" / "config" / "qt-config.ini"
    cfg.write_text("[Controls]\nprofile=1\nprofiles\\size=2\n"
                   "profiles\\1\\button_a\\default\\default=false\n"
                   "profiles\\1\\button_a\\default=false\n"
                   "profiles\\1\\button_a=\"x\"\n"
                   "profiles\\1\\button_a=\"y\"\n"
                   "[Renderer]\nresolution_factor=1\n",
                   encoding="utf-8")
    r = C.higienizar_controles()
    afirmar(r.get("ok") and r["removidas"] == 2, r)
    texto = cfg.read_text(encoding="utf-8")
    afirmar("\\default\\default" not in texto, texto)
    afirmar(texto.count("profiles\\1\\button_a=") == 1)
    afirmar("resolution_factor=1" in texto)
    r = C.higienizar_controles()
    afirmar(r.get("ok") and r["removidas"] == 0, r)


def teste_nomes_sdl_da_amostra():
    from bib_nucleo import controles as C
    tmp = Path(tempfile.mkdtemp(prefix="suite-ctl-"))
    emu = Path(os.environ.get("BIBLIOTECA_AZAHAR_DIR"))
    (emu / "user" / "config").mkdir(parents=True, exist_ok=True)
    (emu / "azahar.exe").write_bytes(b"MZ")
    g = C.GUIDS["xbox360"]
    (emu / "user" / "config" / "qt-config.ini").write_text(
        "[Controls]\n"
        f"profiles\\1\\button_a=\"api:controller,button:1,engine:sdl,guid:{g},maptype:guid+port,name:B,port:0\"\n"
        f"profiles\\1\\button_zl=\"api:controller,axis:2,direction:+,engine:sdl,guid:{g},maptype:guid+port,name:LT,port:0,threshold:0.500000\"\n"
        f"profiles\\1\\circle_pad=\"api:controller,axis_x:0,axis_y:1,deadzone:0.100000,engine:sdl,guid:{g},maptype:guid+port,name_x:LX,name_y:LY,port:0\"\n",
        encoding="utf-8")
    tab = C.nomes_sdl()
    afirmar(tab == {("btn", 1): "B", ("eixo", 2, "+"): "LT",
                    ("stick", "x"): "LX", ("stick", "y"): "LY"}, tab)


def teste_gerar_perfil_com_rotulos_reais():
    from bib_nucleo import controles as C
    g = "0300b9695e0400008e02000000007200"
    rot = {("btn", 0): "A / X", ("btn", 1): "B / C",
           ("rstick", "x"): "RX", ("rstick", "y"): "RY"}
    p = C.gerar_perfil("xbox360", guid=g, rotulos=rot)
    afirmar(",name:A / X,port:0" in p["profiles\\1\\button_b"], p)
    afirmar("name_x:Left Stick X" in p["profiles\\1\\circle_pad"], p)
    afirmar("name_x:RX" in p["profiles\\1\\c_stick"], p)
    afirmar(f"guid:{g}" in p["profiles\\1\\button_a"], p)


def teste_capturar_simulado():
    from bib_nucleo import controles as C
    seq = iter([{"botoes": set(), "eixos": {}}, {"botoes": set(), "eixos": {}},
                {"botoes": {3}, "eixos": {}}])
    r = C.capturar(lambda: next(seq), timeout=5)
    afirmar(r == {"ok": True, "tipo": "botao", "indice": 3}, r)
    seq = iter([{"botoes": set(), "eixos": {"lx": 20000}}])
    r = C.capturar(lambda: next(seq), timeout=5)
    afirmar(r["tipo"] == "eixo" and r["indice"] == 0 and r["direcao"] == "+", r)
    r = C.capturar(lambda: {"botoes": set(), "eixos": {}}, timeout=0.2)
    afirmar(not r.get("ok") and "esgotado" in r["erro"], r)
    r = C.capturar(lambda: 1 / 0, timeout=5)
    afirmar(not r.get("ok"), r)
    afirmar(C.resumir_estado(None) == "—")
    afirmar("A" in C.resumir_estado({"botoes": {12, 3}, "lt": 0, "rt": 0,
                                     "lx": 0, "ly": 0, "rx": 0, "ry": 0}))
    afirmar("→" in C.resumir_estado({"botoes": {3}, "lt": 0, "rt": 0,
                                     "lx": 0, "ly": 0, "rx": 0, "ry": 0}))
    afirmar(C.xinput_para_sdl(12) == 0 and C.xinput_para_sdl(0) == 11
            and C.xinput_para_sdl(11) is None)


def teste_listar_controles_nao_quebra():
    from bib_nucleo import controles as C
    lst = C.listar_controles()
    afirmar(isinstance(lst, list), lst)
    for c in lst:
        afirmar({"nome", "familia"} <= set(c), c)
