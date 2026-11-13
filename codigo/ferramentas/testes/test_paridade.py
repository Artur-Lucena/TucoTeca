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
