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
            afirmar(chave in mapa, (tipo, chave))
        afirmar("dpad" in mapa and "analog_esq" in mapa and "analog_dir" in mapa, tipo)


def teste_gerar_perfil_xbox360_exato():
    from bib_nucleo import controles as C
    g = C.GUIDS["xbox360"]
    p = C.gerar_perfil("xbox360")
    afirmar(p["profiles\\1\\button_b"] == f"button:0,engine:sdl,guid:{g},port:0", p)
    afirmar(p["profiles\\1\\button_a"] == f"button:1,engine:sdl,guid:{g},port:0", p)
    afirmar(p["profiles\\1\\button_zl"] == f"axis:2,direction:+,engine:sdl,guid:{g},port:0,threshold:0.5", p)
    afirmar(p["profiles\\1\\button_zr"] == f"axis:2,direction:-,engine:sdl,guid:{g},port:0,threshold:0.5", p)
    afirmar(p["profiles\\1\\button_up"] == f"direction:up,engine:sdl,guid:{g},hat:0,port:0", p)
    circ = p["profiles\\1\\circle_pad"]
    afirmar("engine:analog_from_button" in circ and "deadzone:0.15" in circ, circ)
    afirmar("axis$0$1direction$-" in circ, circ)  # escape aninhado
    afirmar("axis$3$1direction$+" in p["profiles\\1\\c_stick"], p)
    try:
        C.gerar_perfil("watara")
        afirmar(False, "devia levantar")
    except ValueError:
        pass
    try:
        C.bind_botao(g, 0, ("fliper", 1))
        afirmar(False, "devia levantar")
    except ValueError:
        pass


def teste_gerar_perfil_tipos_divergentes():
    from bib_nucleo import controles as C
    ps = C.gerar_perfil("ps4")
    afirmar(ps["profiles\\1\\button_b"].startswith("button:1,"), ps)
    afirmar(ps["profiles\\1\\button_zl"].startswith("axis:3,direction:+"), ps)
    sp = C.gerar_perfil("switchpro")
    afirmar(sp["profiles\\1\\button_zl"] == f"button:6,engine:sdl,guid:{C.GUIDS['switchpro']},port:0", sp)
    afirmar(sp["profiles\\1\\button_start"].startswith("button:9,"), sp)
    xo = C.gerar_perfil("xboxone")
    afirmar(xo["profiles\\1\\button_zr"].startswith("axis:5,direction:+"), xo)


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
    r = C.aplicar_preset_controle("x360-teste")
    afirmar(r.get("ok"), r)
    texto = cfg.read_text(encoding="utf-8")
    afirmar("engine:sdl" in texto and "resolution_factor = 1" in texto,
            texto[:400])
    afirmar("[Controls]" in texto)
    r = C.aplicar_preset_controle("fantasma")
    afirmar(not r.get("ok"), r)
    r = C.fotografar_perfil("")
    afirmar(not r.get("ok"), r)


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
    afirmar("A" in C.resumir_estado({"botoes": {0, 15}, "lt": 0, "rt": 0,
                                     "lx": 0, "ly": 0, "rx": 0, "ry": 0}))


def teste_listar_controles_nao_quebra():
    from bib_nucleo import controles as C
    lst = C.listar_controles()
    afirmar(isinstance(lst, list), lst)
    for c in lst:
        afirmar({"nome", "familia"} <= set(c), c)
