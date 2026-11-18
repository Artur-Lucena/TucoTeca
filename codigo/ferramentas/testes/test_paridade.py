"""Paridade Electron × antigo Qt: métodos de `ponte_paridade` com serviço real.

Cenários em sandbox (HOME da suíte), com ROM 3DS e `user/` do Azahar
simulados por patch — nada de emulador, jogo ou rede reais.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from bib_nucleo import emuladores as EMU
from executar import afirmar
from ponte import Ponte
from servicos_ui import ServicoBiblioteca

TID = "0004000000055D00"


def _chamar(ponte, metodo, params=None, ident=1):
    linha = json.dumps({"id": ident, "metodo": metodo, "params": params or {}}, ensure_ascii=False)
    return json.loads(ponte.executar_linha(linha))


def _ok(ponte, metodo, params=None):
    r = _chamar(ponte, metodo, params)
    afirmar(r["ok"] is True, (metodo, r))
    return r["resultado"]


def _erro(ponte, metodo, params=None):
    r = _chamar(ponte, metodo, params)
    afirmar(r["ok"] is False, (metodo, r))
    return r["erro"]


def _cena_3ds():
    """Serviço real + jogo 3DS + mod de origem + user/ do Azahar simulado."""
    tmp = Path(tempfile.mkdtemp(prefix="paridade-emu-"))
    user = tmp / "azahar-user"
    for pasta in ("cheats", "load/textures", "config"):
        (user / pasta).mkdir(parents=True, exist_ok=True)
    origem = tmp / "Mod Teste"
    (origem / "romfs").mkdir(parents=True)
    (origem / "romfs" / "a.bin").write_bytes(b"x")
    servico = ServicoBiblioteca(tmp / "b.db")
    gid = servico.salvar_jogo(0, {"titulo": "Jogo 3DS",
                                  "launch_options": str(tmp / "jogo.3ds")})["id"]
    patches = (patch.object(EMU, "title_id_da_rom", return_value=TID),
               patch.object(EMU, "azahar_user_dir", return_value=str(user)))
    return tmp, servico, gid, origem, patches


def teste_emulacao_sem_rom_3ds_explica_e_nao_muda_nada():
    tmp = Path(tempfile.mkdtemp(prefix="paridade-pc-"))
    servico = ServicoBiblioteca(tmp / "b.db")
    gid = servico.salvar_jogo(0, {"titulo": "Jogo PC", "executable_path": "C:/x/jogo.exe"})["id"]
    ponte = Ponte(servico)
    estado = _ok(ponte, "emulacao.jogo", {"id": gid})
    afirmar(estado["tid"] == "" and "3DS" in estado["erro"], estado)
    afirmar(estado["mods"] == [] and estado["cheats"] == [], estado)
    afirmar("3DS" in _erro(ponte, "emulacao.mod", {"id": gid, "acao": "desligar_todos"}))


def teste_emulacao_mods_importar_alternar_desligar_remover():
    _tmp, servico, gid, origem, (p1, p2) = _cena_3ds()
    ponte = Ponte(servico)
    with p1, p2:
        estado = _ok(ponte, "emulacao.mod", {"id": gid, "acao": "importar", "arquivo": str(origem)})
        afirmar([m["nome"] for m in estado["mods"]] == ["Mod Teste"], estado)
        afirmar(estado["tid"] == TID and estado["mods_off"] is False, estado)
        ligado = _ok(ponte, "emulacao.mod", {"id": gid, "acao": "alternar", "nome": "Mod Teste"})
        afirmar(ligado["mods"][0]["ativo"] is True, ligado)
        afirmar(servico.jogo(gid).get("azahar_mods"), "ativo não persistiu no jogo")
        off = _ok(ponte, "emulacao.mod", {"id": gid, "acao": "desligar_todos"})
        afirmar(off["mods_off"] is True and off["mods"][0]["ativo"] is True, off)
        afirmar("não encontrado" in _erro(ponte, "emulacao.mod",
                                          {"id": gid, "acao": "alternar", "nome": "Fantasma"}))
        biblio = EMU.mods_titulo_dir(TID) / "Mod Teste"
        afirmar(biblio.is_dir())
        removido = _ok(ponte, "emulacao.mod", {"id": gid, "acao": "remover", "nome": "Mod Teste"})
        afirmar(removido["mods"] == [] and not biblio.exists(), removido)


def teste_emulacao_cheats_e_validacao_de_parametros():
    _tmp, servico, gid, _origem, (p1, p2) = _cena_3ds()
    ponte = Ponte(servico)
    with p1, p2:
        estado = _ok(ponte, "emulacao.cheat", {"id": gid, "acao": "adicionar",
                                               "nome": "Vida infinita", "codigo": "00112233 44556677"})
        nomes = [c.get("nome") for c in estado["cheats"]]
        afirmar("Vida infinita" in nomes, estado["cheats"])
        antes = next(c for c in estado["cheats"] if c.get("nome") == "Vida infinita")
        depois = _ok(ponte, "emulacao.cheat", {"id": gid, "acao": "alternar", "nome": "Vida infinita"})
        novo = next(c for c in depois["cheats"] if c.get("nome") == "Vida infinita")
        afirmar(novo.get("ativo") != antes.get("ativo"), (antes, novo))
        vazio = _ok(ponte, "emulacao.cheat", {"id": gid, "acao": "remover", "nome": "Vida infinita"})
        afirmar(all(c.get("nome") != "Vida infinita" for c in vazio["cheats"]), vazio)
        # parâmetros inválidos viram erro claro, sem tocar no disco
        afirmar("codigo" in _erro(ponte, "emulacao.cheat", {"id": gid, "acao": "adicionar", "nome": "X"}))
        afirmar("acao" in _erro(ponte, "emulacao.cheat", {"id": gid, "acao": "apagar_tudo", "nome": "X"}))
        afirmar("id" in _erro(ponte, "emulacao.cheat", {"id": "1", "acao": "alternar", "nome": "X"}))
        afirmar("arquivo" in _erro(ponte, "emulacao.textura", {"id": gid, "acao": "instalar"}))


def teste_jogo_aberto_bloqueia_mudancas_mas_nao_leitura():
    _tmp, servico, gid, origem, (p1, p2) = _cena_3ds()
    ponte = Ponte(servico)
    falso = {"id": 99, "escopo": "jogo", "estado": "rodando"}
    with p1, p2, patch.object(ponte.trabalhos, "listar", return_value=[falso]):
        afirmar(_ok(ponte, "emulacao.jogo", {"id": gid})["tid"] == TID)
        for metodo, params in (
                ("emulacao.mod", {"id": gid, "acao": "importar", "arquivo": str(origem)}),
                ("emulacao.cheat", {"id": gid, "acao": "adicionar", "nome": "A", "codigo": "1 2"}),
                ("emulacao.textura", {"id": gid, "acao": "alternar"}),
                ("emulacao.preset", {"acao": "aplicar", "nome": "x"}),
                ("emulacao.atualizar", {"chave": "azahar", "info": {"tag": "v1"}})):
            afirmar("Feche o jogo" in _erro(ponte, metodo, params), metodo)
        afirmar(EMU.listar_mods(TID) == [], "mod importado com jogo aberto")
    # sessão terminada: a mesma chamada passa
    with p1, p2, patch.object(ponte.trabalhos, "listar",
                              return_value=[{**falso, "estado": "ok"}]):
        _ok(ponte, "emulacao.mod", {"id": gid, "acao": "importar", "arquivo": str(origem)})


def _esperar_fim(ponte, ident, limite=5.0):
    import time
    fim = time.monotonic() + limite
    while time.monotonic() < fim:
        item = next(t for t in ponte.trabalhos.listar() if t["id"] == ident)
        if item["estado"] not in ("rodando", "cancelando"):
            return item
        time.sleep(0.02)
    raise AssertionError(f"trabalho {ident} não terminou")


def teste_atualizar_emulador_vira_trabalho_e_exige_consulta():
    tmp = Path(tempfile.mkdtemp(prefix="paridade-emu-up-"))
    servico = ServicoBiblioteca(tmp / "b.db")
    ponte = Ponte(servico)
    afirmar("Consulte" in _erro(ponte, "emulacao.atualizar", {"chave": "azahar", "info": {}}))
    chamadas = []
    with patch.object(servico, "emu_atualizar",
                      side_effect=lambda c, i: chamadas.append((c, i)) or {"ok": True}):
        r = _ok(ponte, "emulacao.atualizar", {"chave": "azahar", "info": {"tag": "2125.0"}})
        item = _esperar_fim(ponte, r["trabalho"]["id"])
    afirmar(item["estado"] == "ok" and item["escopo"] == "emulador", item)
    afirmar("2125.0" in item["detalhe"]["aviso"], item)
    afirmar(chamadas == [("azahar", {"tag": "2125.0"})], chamadas)
    with patch.object(servico, "emu_atualizar", side_effect=ValueError("sem espaço")):
        r = _ok(ponte, "emulacao.atualizar", {"chave": "azahar", "info": {"tag": "2125.0"}})
        item = _esperar_fim(ponte, r["trabalho"]["id"])
    afirmar(item["estado"] == "erro" and "sem espaço" in item["erro"], item)


def _prov_falso(chamadas, tag_remota="v2"):
    def release_info():
        chamadas.append("release_info")
        return {"tag": tag_remota, "size": 40 * 1048576, "url": "https://exemplo.invalid/emu.zip"}
    return {"chave": "azahar", "nome": "Azahar Falso", "origens": (), "sistemas": (),
            "rom_exts": (), "release_info": release_info, "versao_local": lambda: "v1",
            "instalar": lambda info, progresso=None: {"ok": True, "tag": tag_remota}}


def teste_emuladores_status_sem_rede_e_consulta_explicita():
    from bib_nucleo import emuladores
    tmp = Path(tempfile.mkdtemp(prefix="paridade-emus-"))
    ponte = Ponte(ServicoBiblioteca(tmp / "b.db"))
    chamadas = []
    falsos = {"azahar": _prov_falso(chamadas), "desmume": _prov_falso(chamadas)}
    with patch.object(emuladores, "provedores", lambda: falsos):
        status = _ok(ponte, "emulacao.status")
        afirmar(len(status["itens"]) == 2 and "release_info" not in chamadas, (status, chamadas))
        consulta = _ok(ponte, "emulacao.consultar", {"chave": "azahar"})
    afirmar(consulta["tag"] == "v2" and consulta["atualizado"] is False, consulta)
    afirmar(consulta["tamanho_mb"] == 40 and consulta["info"]["tag"] == "v2", consulta)


def teste_controles_listar_fotografar_aplicar_gerar_estado():
    from bib_nucleo import controles
    tmp = Path(tempfile.mkdtemp(prefix="paridade-pads-"))
    ponte = Ponte(ServicoBiblioteca(tmp / "b.db"))
    salvos = ["Padrão"]
    with patch.object(controles, "listar_controles", lambda: [{"nome": "Xbox", "familia": "xbox360"}]), \
            patch.object(controles, "listar_presets_controle", lambda: list(salvos)), \
            patch.object(controles, "fotografar_perfil",
                         lambda n: salvos.append(n) or {"ok": True, "preset": n}), \
            patch.object(controles, "aplicar_preset_controle", lambda n: {"ok": True, "chaves": 12}), \
            patch.object(controles, "detectar_sdl", lambda: []), \
            patch.object(controles, "nomes_sdl", lambda: {}), \
            patch.object(controles, "salvar_mapa_gerado",
                         lambda tipo, **kw: salvos.append(kw["nome"]) or {"ok": True}), \
            patch.object(controles, "ler_estado_xinput", lambda slot: {"slot": slot}), \
            patch.object(controles, "resumir_estado", lambda est: f"A slot={est['slot']}"):
        lista = _ok(ponte, "controles.listar")
        afirmar(lista["pads"][0]["nome"] == "Xbox" and lista["presets"] == ["Padrão"], lista)
        afirmar(any(t["tipo"] == "xbox360" for t in lista["tipos"]), lista)
        foto = _ok(ponte, "controles.fotografar", {"nome": "Meu Pad"})
        afirmar("Meu Pad" in foto["presets"], foto)
        afirmar(_ok(ponte, "controles.aplicar", {"nome": "Meu Pad"})["ok"] is True)
        gerado = _ok(ponte, "controles.gerar", {"tipo": "xbox360"})
        afirmar("xbox360-hub" in gerado["presets"], gerado)
        afirmar(_ok(ponte, "controles.estado")["resumo"] == "A slot=0")
        afirmar("tipo" in _erro(ponte, "controles.gerar", {"tipo": "patinete"}).lower())
        afirmar("nome" in _erro(ponte, "controles.fotografar", {"nome": "  "}))
        with patch.object(ponte.trabalhos, "listar",
                          return_value=[{"id": 1, "escopo": "jogo", "estado": "rodando"}]):
            afirmar("Feche o jogo" in _erro(ponte, "controles.aplicar", {"nome": "Meu Pad"}))


def teste_equalizacao_vira_trabalho_e_valida_preset():
    from bib_nucleo import baixar
    tmp = Path(tempfile.mkdtemp(prefix="paridade-eq-"))
    servico = ServicoBiblioteca(tmp / "b.db")
    ponte = Ponte(servico)
    with patch.object(baixar, "ffmpeg_pronto", lambda: False):
        lista = _ok(ponte, "musicas.eq_presets")
    afirmar("bass" in lista["presets"] and lista["ffmpeg"] is False, lista)
    afirmar("preset" in _erro(ponte, "musicas.eq", {"caminho": "C:/m/a.mp3", "preset": "turbo"}))
    with patch.object(servico, "aplicar_eq_musica",
                      lambda c, p: {"ok": True, "path": c + f".{p}.mp3"}):
        r = _ok(ponte, "musicas.eq", {"caminho": "C:/m/faixa.mp3", "preset": "bass"})
        item = _esperar_fim(ponte, r["trabalho"]["id"])
    afirmar(item["estado"] == "ok" and "faixa.mp3" in item["rotulo"], item)
    afirmar(item["detalhe"]["path"].endswith(".bass.mp3"), item)


def teste_volume_do_pc_le_define_e_indisponivel_nao_quebra():
    from bib_nucleo import volume
    tmp = Path(tempfile.mkdtemp(prefix="paridade-vol-"))
    ponte = Ponte(ServicoBiblioteca(tmp / "b.db"))
    estado = {"nivel": 40, "mudo": False}

    def definir(nivel, mudo=None):
        estado["nivel"] = nivel
        return {"ok": True, **estado}

    def mudo():
        estado["mudo"] = not estado["mudo"]
        return {"ok": True, **estado}

    with patch.object(volume, "ler_volume_pc", lambda: {"ok": True, **estado}), \
            patch.object(volume, "definir_volume_pc", definir), \
            patch.object(volume, "alternar_mudo_pc", mudo):
        afirmar(_ok(ponte, "sistema.volume")["nivel"] == 40)
        afirmar(_ok(ponte, "sistema.volume_definir", {"nivel": 75})["nivel"] == 75)
        afirmar(_ok(ponte, "sistema.volume_mudo")["mudo"] is True)
        afirmar("nivel" in _erro(ponte, "sistema.volume_definir", {"nivel": "alto"}))
    with patch.object(volume, "ler_volume_pc", lambda: {"ok": False, "erro": "sem Core Audio"}), \
            patch.object(volume, "definir_volume_pc", lambda n, mudo=None: {"ok": False, "erro": "sem Core Audio"}):
        afirmar(_ok(ponte, "sistema.volume")["ok"] is False)
        afirmar("Core Audio" in _erro(ponte, "sistema.volume_definir", {"nivel": 10}))


def teste_desejos_importar_json_e_buscar_fontes_pela_ponte():
    from bib_nucleo.rede import fontes
    tmp = Path(tempfile.mkdtemp(prefix="paridade-desejos-"))
    servico = ServicoBiblioteca(tmp / "b.db")
    ponte = Ponte(servico)
    arquivo = tmp / "wishlist.json"
    arquivo.write_text(json.dumps([{"appid": "10", "titulo": "Alpha"},
                                   {"appid": "20", "titulo": "Beta"}]), encoding="utf-8")
    r = _ok(ponte, "desejos.importar_wishlist", {"caminho": str(arquivo)})
    afirmar("2 novos" in r["avisos"][0], r)
    titulos = sorted(d["titulo"] for d in servico.snapshot()["desejos"])
    afirmar(titulos == ["Alpha", "Beta"], titulos)
    vazio = tmp / "vazio.json"
    vazio.write_text("[]", encoding="utf-8")
    _erro(ponte, "desejos.importar_wishlist", {"caminho": str(vazio)})

    with patch.object(fontes, "buscar_steamrip",
                      lambda t: {"itens": [{"titulo": f"{t} Repack", "url": "https://steamrip.com/x"}]}), \
            patch.object(fontes, "buscar_fitgirl", side_effect=OSError("tempo esgotado")):
        achados = _ok(ponte, "desejos.buscar_fontes", {"titulo": "Alpha"})
    afirmar(achados["steamrip"] == [{"titulo": "Alpha Repack", "url": "https://steamrip.com/x"}], achados)
    afirmar(achados["fitgirl"] == [] and "tempo esgotado" in achados["erros"][0], achados)
    afirmar("titulo" in _erro(ponte, "desejos.buscar_fontes", {"titulo": " "}))


def teste_manutencao_plano_so_le_e_sanear_religar_respeitam_trava():
    tmp = Path(tempfile.mkdtemp(prefix="paridade-manut-"))
    servico = ServicoBiblioteca(tmp / "b.db")
    ponte = Ponte(servico)
    pasta = tmp / "Jogo"
    pasta.mkdir()
    (pasta / "setup.exe").write_bytes(b"MZ" + b"0" * 64)
    antes = sorted(p.name for p in pasta.iterdir())
    plano = _ok(ponte, "manutencao.plano", {"caminho": str(pasta)})
    afirmar(isinstance(plano, dict) and "pasta" in plano, plano)
    afirmar(sorted(p.name for p in pasta.iterdir()) == antes, "plano alterou a pasta")
    afirmar(_ok(ponte, "manutencao.plano", {"caminho": str(tmp / "nao-existe")})["ok"] is False)

    gid = servico.salvar_jogo(0, {"titulo": "Jogo", "executable_path": str(pasta / "velho.exe")})["id"]
    novo = pasta / "jogo.exe"
    novo.write_bytes(b"MZ")
    diag = _ok(ponte, "jogo.religar", {"id": gid, "campo": "executable_path", "caminho": str(novo)})
    afirmar(diag["jogo"]["executable_path"] == str(novo), diag)
    afirmar("campo" in _erro(ponte, "jogo.religar", {"id": gid, "campo": "titulo", "caminho": "x"}))
    with patch.object(ponte.trabalhos, "listar",
                      return_value=[{"id": 1, "escopo": "jogo", "estado": "rodando"}]):
        for metodo, params in (("manutencao.sanear", {"caminho": str(pasta)}),
                               ("jogo.religar", {"id": gid, "campo": "executable_path",
                                                 "caminho": str(novo)}),
                               ("jogo.jogar_elevado", {"id": gid})):
            afirmar("Feche o jogo" in _erro(ponte, metodo, params), metodo)


def teste_jogar_elevado_pede_uac_simulado():
    from bib_nucleo import emuladores as emuladores
    tmp = Path(tempfile.mkdtemp(prefix="paridade-uac-"))
    servico = ServicoBiblioteca(tmp / "b.db")
    ponte = Ponte(servico)
    gid = servico.salvar_jogo(0, {"titulo": "Jogo", "executable_path": "C:/x/jogo.exe"})["id"]
    pedidos = []
    with patch.object(emuladores, "preparar_lancamento", lambda jogo: {"aviso": ""}), \
            patch.object(emuladores, "executar_jogo_dict",
                         lambda jogo, elevar=False: pedidos.append(elevar) or {"ok": True, "modo": "runas-uac"}), \
            patch.object(emuladores, "iniciar_sessao_manual", lambda gid, titulo: None):
        r = _ok(ponte, "jogo.jogar_elevado", {"id": gid})
    afirmar(r["ok"] is True and r["modo"] == "runas-uac" and pedidos == [True], (r, pedidos))


def teste_ferramentas_listar_sem_exe_e_prever_importar_selecionados():
    tmp = Path(tempfile.mkdtemp(prefix="paridade-drop-"))
    servico = ServicoBiblioteca(tmp / "b.db")
    ponte = Ponte(servico)
    lista = _ok(ponte, "ferramentas.listar")
    afirmar(set(lista) == {"imagens", "equalizadores", "videos"}, lista)
    afirmar(all("exe" not in f and "instalado" in f for grupo in lista.values() for f in grupo), lista)

    pasta = tmp / "Jogos"
    with patch.object(servico, "prever_pasta",
                      lambda c: {"ok": True, "itens": [{"titulo": "Celeste", "executable_path": "C:/j/c.exe"}],
                                 "raizes": [c], "info": {}, "erro": ""}):
        pasta.mkdir()
        previa = _ok(ponte, "jogos.prever", {"caminho": str(pasta)})
    afirmar(previa["ok"] and previa["itens"][0]["titulo"] == "Celeste", previa)
    with patch.object(servico, "analisar_arquivo",
                      lambda c: {"ok": True, "tipo": "rom", "item": {"titulo": "Zelda"}, "aviso": "sem capa"}):
        arquivo = _ok(ponte, "jogos.prever", {"caminho": str(tmp / "zelda.3ds")})
    afirmar(arquivo["itens"] == [{"titulo": "Zelda"}] and arquivo["avisos"] == ["sem capa"], arquivo)
    with patch.object(servico, "analisar_arquivo",
                      lambda c: {"ok": True, "tipo": "desconhecido", "item": None, "detalhe": "não é jogo"}):
        nada = _ok(ponte, "jogos.prever", {"caminho": str(tmp / "leia.txt")})
    afirmar(nada["ok"] is False and "não é jogo" in nada["erro"], nada)

    r = _ok(ponte, "jogos.importar_selecionados",
            {"itens": [{"titulo": "Celeste", "executable_path": "C:/j/c.exe"}]})
    afirmar(r, r)
    afirmar([j["titulo"] for j in servico.snapshot()["jogos"]] == ["Celeste"], servico.snapshot()["jogos"])
    afirmar("Nada selecionado" in _erro(ponte, "jogos.importar_selecionados", {"itens": []}))
    afirmar("itens" in _erro(ponte, "jogos.importar_selecionados", {"itens": ["x"]}))


def teste_torrents_listar_marca_fora_do_destino():
    tmp = Path(tempfile.mkdtemp(prefix="paridade-torr-"))
    servico = ServicoBiblioteca(tmp / "b.db")
    ponte = Ponte(servico)
    leitura = {"torrents": [{"hash": "a", "nome": "A", "pct": 100, "completo": True, "save_path": "D:/Downloads/A"},
                            {"hash": "b", "nome": "B", "pct": 100, "completo": True, "save_path": "D:/Jogos/B"},
                            {"hash": "c", "nome": "C", "pct": 10, "save_path": ""}], "erros": []}
    with patch.object(servico, "listar_torrents", lambda: leitura), \
            patch.object(servico, "fora_do_destino", lambda c: "Downloads" in c):
        itens = _ok(ponte, "torrents.listar")["itens"]
    afirmar([i["fora_destino"] for i in itens] == [True, False, False], itens)


def teste_backup_manual_e_sessoes_abertas_pela_ponte():
    from bib_nucleo import emuladores as emuladores
    tmp = Path(tempfile.mkdtemp(prefix="paridade-sessoes-"))
    servico = ServicoBiblioteca(tmp / "b.db")
    ponte = Ponte(servico)
    gid = servico.salvar_jogo(0, {"titulo": "Jogo UAC", "executable_path": "C:/x/j.exe"})["id"]
    antes = len(servico.backups())
    r = _ok(ponte, "colecao.backup")
    afirmar(r["ok"] and r["db"].startswith("biblioteca-") and len(servico.backups()) == antes + 1, r)

    marcador = emuladores.iniciar_sessao_manual(gid, "Jogo UAC")
    afirmar(marcador["ok"], marcador)
    abertas = _ok(ponte, "sessoes.listar")
    afirmar([s["titulo"] for s in abertas] == ["Jogo UAC"] and abertas[0]["gid"] == gid, abertas)
    afirmar("horas" in _erro(ponte, "sessoes.encerrar", {"arquivo": abertas[0]["arquivo"], "horas": "2"}))
    _ok(ponte, "sessoes.encerrar", {"arquivo": abertas[0]["arquivo"], "horas": 1.5})
    afirmar(_ok(ponte, "sessoes.listar") == [], "sessão continuou aberta")
    afirmar(abs(float(servico.jogo(gid).get("horas") or 0) - 1.5) < 1e-6, servico.jogo(gid))
    # marcador forjado fora da pasta de sessões não fecha nada
    _erro(ponte, "sessoes.encerrar", {"arquivo": str(tmp / "sessao-1-x.json"), "horas": 1})


def teste_erros_recentes_e_saves_com_trava():
    tmp = Path(tempfile.mkdtemp(prefix="paridade-erros-"))
    servico = ServicoBiblioteca(tmp / "b.db")
    ponte = Ponte(servico)
    afirmar(isinstance(_ok(ponte, "sistema.erros", {"linhas": 10})["texto"], str))
    afirmar("linhas" in _erro(ponte, "sistema.erros", {"linhas": 0}))
    gid = servico.salvar_jogo(0, {"titulo": "Jogo", "executable_path": "C:/x/j.exe"})["id"]
    with patch.object(servico, "backup_pos_sessao", lambda g: {"ok": True, "saves": {"arquivos": 0}}), \
            patch.object(servico, "restaurar_saves", lambda g, c: {"ok": True, "restaurado": c}):
        afirmar(_ok(ponte, "saves.snapshot", {"id": gid})["ok"] is True)
        afirmar(_ok(ponte, "saves.restaurar", {"id": gid, "caminho": "x.zip"})["restaurado"] == "x.zip")
        with patch.object(ponte.trabalhos, "listar",
                          return_value=[{"id": 1, "escopo": "jogo", "estado": "rodando"}]):
            afirmar("Feche o jogo" in _erro(ponte, "saves.restaurar", {"id": gid, "caminho": "x.zip"}))
            afirmar("Feche o jogo" in _erro(ponte, "saves.snapshot", {"id": gid}))


def teste_colecao_exportar_importar_falha_vira_erro_e_zip_funciona():
    tmp = Path(tempfile.mkdtemp(prefix="paridade-colecao-"))
    servico = ServicoBiblioteca(tmp / "b.db")
    ponte = Ponte(servico)
    servico.salvar_jogo(0, {"titulo": "Celeste", "executable_path": "C:/j/c.exe"})
    exportado = _ok(ponte, "colecao.exportar", {"pasta": str(tmp)})
    zips = sorted(tmp.glob("tucoteca-*.zip"))
    afirmar(len(zips) == 1, (exportado, list(tmp.iterdir())))
    # pasta no lugar do .zip (o que a tela fazia antes) é erro claro, não "importada"
    afirmar("pacote" in _erro(ponte, "colecao.importar", {"caminho": str(tmp)}).lower())
    outro = ServicoBiblioteca(tmp / "outro.db")
    r = _ok(Ponte(outro), "colecao.importar", {"caminho": str(zips[0])})
    afirmar(r.get("ok") is not False, r)
    afirmar([j["titulo"] for j in outro.snapshot()["jogos"]] == ["Celeste"], outro.snapshot()["jogos"])


def teste_aparencia_salva_tema_densidade_e_escala():
    tmp = Path(tempfile.mkdtemp(prefix="paridade-aparencia-"))
    ponte = Ponte(ServicoBiblioteca(tmp / "b.db"))
    r = _ok(ponte, "aparencia.salvar", {"tema": "claro", "densidade": "bigpicture", "escala_texto": 1.2})
    afirmar(r["tema"] == "claro" and r["densidade"] == "bigpicture" and r["escala_texto"] == 1.2, r)
    afirmar(_ok(ponte, "aparencia.ler")["escala_texto"] == 1.2)
    afirmar(_ok(ponte, "aparencia.salvar", {"escala_texto": 9})["escala_texto"] == 1.5)
    afirmar("escala_texto" in _erro(ponte, "aparencia.salvar", {"escala_texto": "grande"}))


def teste_ponte_params_mensagens_e_valores():
    from ponte_params import inteiro, lista, objeto, opcao, texto

    def falha(f, *a, **k):
        try:
            f(*a, **k)
        except ValueError as e:
            return str(e)
        raise AssertionError("esperava ValueError")

    afirmar(texto({"c": "  x  "}, "c") == "x")
    afirmar(falha(texto, {"c": "  "}, "c") == "c deve ser um texto")
    afirmar(falha(texto, {}, "c") == "c deve ser um texto")
    afirmar(texto({}, "c", obrigatorio=False, padrao="p") == "p")
    afirmar("passa de 3" in falha(texto, {"c": "abcd"}, "c", maximo=3))
    afirmar(inteiro({"id": 3}, "id") == 3)
    afirmar(falha(inteiro, {"id": True}, "id") == "id deve ser um inteiro")
    afirmar(falha(inteiro, {"id": 0}, "id", positivo=True) == "id deve ser um inteiro positivo")
    afirmar(falha(opcao, {"a": "z"}, "a", ("x", "y")) == "a deve ser um de: x, y")
    afirmar(falha(objeto, {"o": []}, "o") == "o deve ser um objeto")
    afirmar(falha(lista, {"l": {}}, "l") == "l deve ser uma lista")
