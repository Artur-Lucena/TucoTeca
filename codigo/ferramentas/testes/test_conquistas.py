"""Conquistas do Hub calculadas de saves nativos, nunca de conta Steam."""
import json
import sqlite3
import struct
import tempfile
from pathlib import Path
from unittest.mock import patch

from bib_nucleo import conquistas as C, online
from executar import afirmar


def _jogo(appid="3934270"):
    raiz = Path(tempfile.mkdtemp())
    return {"uuid": "a" * 32, "titulo": "Jogo", "shop": "steam", "object_id": appid,
            "executable_path": str(raiz / "Jogo.exe"), "save_path": str(raiz / "save.json")}


def teste_conquistas_save_nativo_retroativo_offline_e_persistente():
    jogo = _jogo()
    save = Path(jogo["save_path"])
    save.write_text(json.dumps({"achievement_progress": {"primeira": {"complete": True}, "segunda": {"complete": False}}}))
    publico = {"achievementpercentages": {"achievements": [{"name": "primeira", "percent": "30"}, {"name": "segunda", "percent": "10"}]}}
    with patch.object(online, "requisitar_json", return_value=publico) as req:
        r = C.sincronizar_catalogo(jogo)
        afirmar(r["desbloqueadas"] == 1 and r["avaliaveis"] == 2, r)
        afirmar("GetGlobalAchievementPercentagesForApp" in req.call_args.args[0])
        afirmar("steamid" not in req.call_args.args[0])
    before = save.read_bytes()
    save.write_text(json.dumps({"achievement_progress": {"primeira": {"complete": False}, "segunda": {"complete": True}}}))
    with patch.object(online, "requisitar_json", side_effect=AssertionError("leitura local usou rede")):
        r = C.avaliar_save(jogo)
        afirmar(r["desbloqueadas"] == 2, "desbloqueio não persistiu ou novo progresso foi ignorado")
        save.unlink()
        r = C.avaliar_save(jogo)
        afirmar(r["desbloqueadas"] == 2 and r["avaliaveis"] == 0, r)
    afirmar((C.pasta_conquistas(jogo) / "estado.json").is_file())
    afirmar(before, "fixture vazia")


def _vetor(strings):
    return struct.pack("<Q", len(strings)) + b"".join(struct.pack("<Q", len(s.encode())) + s.encode() for s in strings)


def teste_conquistas_mewgenics_sqlite_nativo_tres_requisitos():
    jogo = _jogo("686060")
    save = Path(jogo["save_path"]).with_suffix(".sav")
    jogo["save_path"] = str(save)
    con = sqlite3.connect(save)
    con.execute("CREATE TABLE properties (key TEXT PRIMARY KEY,data)")
    con.execute("CREATE TABLE files (key TEXT PRIMARY KEY,data BLOB)")
    con.execute("INSERT INTO properties VALUES ('mapflag_SewersUnlocked',1)")
    con.execute("INSERT INTO files VALUES ('unlocks',?)", (struct.pack("<I", 3) + _vetor(["Colorless", "Medic"]),))
    casa = b"House1"
    con.execute("INSERT INTO files VALUES ('house_unlocks',?)", (struct.pack("<I", 1) + struct.pack("<Q", len(casa)) + casa + _vetor(["Default", "SmallHouse_Attic"]),))
    con.commit()
    con.close()
    original = save.read_bytes()
    ids = ("class_unlock_medic", "map_unlock_sewers", "house_upgrade_attic", "sem_regra")
    publico = {"achievementpercentages": {"achievements": [{"name": i} for i in ids]}}
    with patch.object(online, "requisitar_json", return_value=publico):
        r = C.sincronizar_catalogo(jogo)
    afirmar(r["desbloqueadas"] == 3 and r["avaliaveis"] == 3 and r["total"] == 4, r)
    afirmar(save.read_bytes() == original, "leitor escreveu no save nativo")


def teste_conquistas_regras_de_contador_sem_inferir_de_texto():
    jogo = _jogo("123")
    Path(jogo["save_path"]).write_text('{"bosses": 2, "flag": true}')
    publico = {"achievementpercentages": {"achievements": [{"name": "mate_10_bosses"}]}}
    with patch.object(online, "requisitar_json", return_value=publico):
        r = C.sincronizar_catalogo(jogo)
    afirmar(r["avaliaveis"] == 0 and r["desbloqueadas"] == 0, r)
    C.salvar_regras(jogo, '{"mate_10_bosses":{"path":["bosses"],"op":"gte","value":10}}')
    afirmar(C.avaliar_save(jogo)["desbloqueadas"] == 0)
    Path(jogo["save_path"]).write_text('{"bosses": 10}')
    afirmar(C.avaliar_save(jogo)["desbloqueadas"] == 1)
    try:
        C.salvar_regras(jogo, '{"x":{"path":["bosses"],"op":"eval","value":"qualquer_codigo()"}}')
    except ValueError:
        pass
    else:
        raise AssertionError("aceitou execução arbitrária como regra")


_HTML_COMUNIDADE = """
<div class="achieveRow ">
  <div class="achieveImgHolder"><img src="https://shared.example/a.jpg" /></div>
  <div class="achieveTxtHolder"><div class="achievePercent">62.6%</div>
    <div class="achieveTxt"><h3>Primeira Caçada</h3><h5>Cace 1 javali</h5></div></div>
</div>
<div class="achieveRow ">
  <div class="achieveImgHolder"><img src="https://shared.example/b.jpg" /></div>
  <div class="achieveTxtHolder"><div class="achievePercent">10.0%</div>
    <div class="achieveTxt"><h3>Empate A</h3><h5>Faça A</h5></div></div>
</div>
<div class="achieveRow ">
  <div class="achieveImgHolder"><img src="https://shared.example/c.jpg" /></div>
  <div class="achieveTxtHolder"><div class="achievePercent">10.0%</div>
    <div class="achieveTxt"><h3>Empate B</h3><h5>Faça B</h5></div></div>
</div>
<div class="achieveRow ">
  <div class="achieveTxtHolder"><div class="achievePercent">5.0%</div>
    <div class="achieveTxt"><h3>Sem Imagem</h3><h5></h5></div></div>
</div>
"""


def teste_conquistas_comunidade_parse_e_vinculo_sem_chave():
    parse = C._ParseComunidade()
    parse.feed(_HTML_COMUNIDADE)
    afirmar(len(parse.itens) == 4, parse.itens)
    afirmar(parse.itens[0]["titulo"] == "Primeira Caçada"
            and parse.itens[0]["requisito"] == "Cace 1 javali"
            and parse.itens[0]["icon"] == "https://shared.example/a.jpg"
            and parse.itens[0]["percent"] == "62.6%", parse.itens[0])
    afirmar(parse.itens[3]["icon"] == "" and parse.itens[3]["requisito"] == "")
    internos = {"id_unico": "62.6", "id_a": "10.0", "id_b": "10.0", "id_orfao": "99.9"}
    # Percentuais, mesmo únicos nesta amostra, não identificam a conquista.
    sem_local = C.unir_comunidade(internos, parse.itens, {})
    afirmar(all(i.get("metadados_pendentes") and i["titulo"] == i["id"] for i in sem_local), sem_local)
    itens = C.unir_comunidade(internos, parse.itens, {"id_unico": {"titulo": "Primeira Caçada"}})
    exato = next(i for i in itens if i["id"] == "id_unico")
    afirmar(exato["titulo"] == "Primeira Caçada" and exato["icon"] == "https://shared.example/a.jpg"
            and exato["origem"] == "steam-comunidade", exato)
    pendentes = [i for i in itens if i.get("metadados_pendentes")]
    afirmar({"id_a", "id_b", "id_orfao"} == {i["id"] for i in pendentes}, pendentes)
    orfao = next(i for i in itens if i["id"] == "id_orfao")
    afirmar(orfao["titulo"] == "id_orfao" and orfao["icon"] == "", orfao)
    usados = [i for i in itens if i["id"] in ("id_a", "id_b")]
    afirmar(len(usados) == 2 and all(i["origem"] == "steam-comunidade" for i in usados), usados)
    afirmar(len(itens) == 4, "referências públicas não devem inventar IDs oficiais")


def teste_conquistas_sync_sem_chave_usa_comunidade_e_icons():
    jogo = _jogo()
    save = Path(jogo["save_path"])
    save.write_text(json.dumps({"achievement_progress": {"id_unico": {"complete": True}}}))
    percents = {"achievementpercentages": {"achievements": [{"name": "id_unico", "percent": "62.6"}]}}
    with patch.object(online, "baixar_texto", return_value=_HTML_COMUNIDADE) as html, \
            patch.object(online, "requisitar_json", return_value=percents) as api, \
            patch.object(C, "definicoes_locais", return_value={"id_unico": {"titulo": "Primeira Caçada"}}):
        r = C.sincronizar_catalogo(jogo)
        afirmar(html.call_args.args[0].startswith("https://steamcommunity.com/stats/"), html.call_args)
        afirmar("GetGlobalAchievementPercentagesForApp" in api.call_args.args[0])
        for chamada in (html.call_args, api.call_args):
            afirmar("steamid" not in chamada.args[0] and "key=" not in chamada.args[0])
    item = next(i for i in r["itens"] if i["id"] == "id_unico")
    afirmar(item["titulo"] == "Primeira Caçada" and item["requisito"] == "Cace 1 javali", item)
    afirmar(r["desbloqueadas"] == 1 and r["avaliaveis"] == 1, r)
    afirmar(C._objeto(C.pasta_conquistas(jogo) / "catalogo.json")["fonte"] == "steam-comunidade")
    referencias = C._objeto(C.pasta_conquistas(jogo) / "catalogo.json")["referencias_publicas"]
    afirmar(len(referencias) == 4 and any(i["titulo"] == "Empate A" for i in referencias), referencias)
    with patch.object(online, "requisitar_json", side_effect=AssertionError("releitura usou rede")), \
            patch.object(online, "baixar_texto", side_effect=AssertionError("releitura usou rede")):
        afirmar(C.avaliar_save(jogo)["desbloqueadas"] == 1)


def teste_conquistas_comunidade_falha_cai_pra_nomes_sem_chave():
    jogo = _jogo()
    save = Path(jogo["save_path"])
    save.write_text(json.dumps({"achievement_progress": {"so_nome": {"complete": False}}}))
    percents = {"achievementpercentages": {"achievements": [{"name": "so_nome", "percent": "1.0"}]}}
    with patch.object(online, "baixar_texto", side_effect=ValueError("Comunidade fora")), \
            patch.object(online, "requisitar_json", return_value=percents):
        r = C.sincronizar_catalogo(jogo)
    afirmar(r["total"] == 1 and r["itens"][0]["titulo"] == "so_nome", r)
    afirmar(any("Comunidade fora" in a for a in r["avisos"]), r)


def teste_conquistas_comunidade_entidades_vazias_e_volume():
    p = C._ParseComunidade()
    p.feed('<div class="achieveRow "><div class="achieveTxtHolder">'
           '<div class="achievePercent">62,6%</div>'
           '<div class="achieveTxt"><h3>A &amp; B</h3></div></div></div>'
           '<div class="achieveRow "><div class="achieveTxtHolder"></div></div>')
    afirmar(len(p.itens) == 2, p.itens)
    afirmar(p.itens[0]["titulo"] == "A & B" and p.itens[0]["percent"] == "62,6%", p.itens[0])
    afirmar(p.itens[1]["titulo"] == "", p.itens[1])
    itens = C.unir_comunidade({"x": "62,6"}, p.itens, {})
    afirmar(itens[0]["titulo"] == "x" and itens[0]["metadados_pendentes"], itens)
    itens = C.unir_comunidade({"x": "62,6"}, p.itens, {"x": {"titulo": "A & B"}})
    afirmar(itens[0]["titulo"] == "A & B" and not itens[0]["metadados_pendentes"], itens)
    grande = [{"name": f"a{i}", "percent": f"{i % 100}.0"} for i in range(6000)]
    com = [{"titulo": f"T{i}", "requisito": "", "icon": "", "percent": f"{i % 100}.0"} for i in range(6000)]
    itens = C.unir_comunidade({a["name"]: a["percent"] for a in grande}, com, {})
    afirmar(len(itens) == C.MAX_ITENS and all(i["metadados_pendentes"] for i in itens), len(itens))
    afirmar(all(set(i) >= {"id", "titulo", "requisito", "icon", "origem"} for i in itens), len(itens))
    try:
        C.catalogo_comunidade("0")
    except ValueError:
        pass
    else:
        raise AssertionError("aceitou appid zero")


def teste_conquistas_falha_sincronizacao_preserva_catalogo_e_progresso():
    jogo = _jogo()
    Path(jogo["save_path"]).write_text('{"achievement_progress":{"a":{"complete":true}}}')
    with patch.object(online, "requisitar_json", return_value={"achievementpercentages": {"achievements": [{"name": "a"}]}}):
        C.sincronizar_catalogo(jogo)
    catalogo = (C.pasta_conquistas(jogo) / "catalogo.json").read_bytes()
    with patch.object(online, "requisitar_json", side_effect=ValueError("offline")):
        try:
            C.sincronizar_catalogo(jogo)
        except ValueError:
            pass
    afirmar((C.pasta_conquistas(jogo) / "catalogo.json").read_bytes() == catalogo)
    afirmar(C.avaliar_save(jogo)["desbloqueadas"] == 1)
