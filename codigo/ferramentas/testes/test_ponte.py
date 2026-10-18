"""Ponte NDJSON (F0): protocolo do desktop Electron, exercitado em processo.

O runner da suíte bloqueia processos externos; por isso a ponte é importada
direto (`import ponte`) e dirigida com entrada/saída de texto em memória.
"""
import io
import json
import tempfile
from pathlib import Path

import bib_core as core
from executar import afirmar
from ponte import Ponte, iniciar


class ServicoFalso:
    db_path = "db-falsa"

    def snapshot(self):
        return {"jogos": [], "musicas": [], "desejos": []}


def _chamar(ponte, pedido):
    linha = json.dumps(pedido, ensure_ascii=False)
    resposta = ponte.executar_linha(linha)
    afirmar(resposta is not None, linha)
    return json.loads(resposta)


def teste_ping_responde():
    ponte = Ponte(ServicoFalso())
    r = _chamar(ponte, {"id": 1, "metodo": "nucleo.ping"})
    afirmar(r["ok"] is True, r)
    afirmar(r["id"] == 1 and r["resultado"]["pong"] is True, r)
    afirmar(r["resultado"]["versao"], r)
    afirmar(r["resultado"]["home"], r)
    afirmar(r["resultado"]["db"] == "db-falsa", r)


def teste_metodo_desconhecido():
    ponte = Ponte(ServicoFalso())
    r = _chamar(ponte, {"id": 2, "metodo": "x.y"})
    afirmar(r["ok"] is False and r["id"] == 2, r)
    afirmar("desconhecido" in r["erro"], r)


def teste_linha_invalida_tem_id_null():
    ponte = Ponte(ServicoFalso())
    r = json.loads(ponte.executar_linha("{nao e json"))
    afirmar(r == {"id": None, "ok": False, "erro": "JSON inválido"}, r)


def teste_linha_em_branco_ignorada():
    ponte = Ponte(ServicoFalso())
    afirmar(ponte.executar_linha("") is None, "vazio")
    afirmar(ponte.executar_linha("   \n") is None, "só espaços")


def teste_excecao_vira_erro_e_ponte_sobrevive():
    def quebra(servico, params):
        raise RuntimeError("falha proposital")

    def soma(servico, params):
        return {"soma": int(params["a"]) + int(params["b"])}

    ponte = Ponte(ServicoFalso(), metodos={"t.quebra": quebra, "t.soma": soma})
    r = _chamar(ponte, {"id": 3, "metodo": "t.quebra"})
    afirmar(r["ok"] is False and "falha proposital" in r["erro"], r)
    r2 = _chamar(ponte, {"id": 4, "metodo": "t.soma", "params": {"a": 2, "b": 3}})
    afirmar(r2["ok"] is True and r2["resultado"]["soma"] == 5, r2)


def teste_params_invalido_e_erro_claro():
    ponte = Ponte(ServicoFalso())
    r = _chamar(ponte, {"id": 5, "metodo": "nucleo.snapshot", "params": "texto"})
    afirmar(r["ok"] is False and "params" in r["erro"], r)


def teste_servir_processa_varias_linhas():
    entrada = io.StringIO('{"id": 10, "metodo": "nucleo.ping"}\n\n{"id": 11, "metodo": "x.y"}\n')
    saida = io.StringIO()
    Ponte(ServicoFalso()).servir(entrada, saida)
    linhas = [json.loads(t) for t in saida.getvalue().splitlines()]
    afirmar([t["id"] for t in linhas] == [10, 11], saida.getvalue())
    afirmar(linhas[0]["ok"] is True and linhas[1]["ok"] is False, saida.getvalue())


def teste_snapshot_real_em_home_temporario():
    from servicos_ui import ServicoBiblioteca
    tmp = Path(tempfile.mkdtemp(prefix="suite-ponte-"))
    db = tmp / "hub.db"
    con = core.get_db(db)
    try:
        core.criar_jogo(con, {"titulo": "Jogo da Ponte", "executable_path": ""})
    finally:
        con.close()
    ponte = Ponte(ServicoBiblioteca(db))
    r = _chamar(ponte, {"id": 7, "metodo": "nucleo.snapshot", "params": {}})
    afirmar(r["ok"] is True, r)
    dados = r["resultado"]
    titulos = [j["titulo"] for j in dados["jogos"]]
    afirmar("Jogo da Ponte" in titulos, titulos)
    afirmar(isinstance(dados["jogos"][0].get("capa_url", ""), str), dados["jogos"][0])


def teste_modulos_listar_via_ponte():
    ponte = Ponte(ServicoFalso())
    r = _chamar(ponte, {"id": 8, "metodo": "modulos.listar"})
    afirmar(r["ok"] is True, r)
    chaves = [m["chave"] for m in r["resultado"]]
    afirmar(chaves == ["inicio", "jogos", "musicas", "desejos",
                       "downloads", "integracoes", "videos", "youtube"], chaves)


def teste_bloqueio_de_lock_na_partida():
    trava = core.adquirir_lock()
    afirmar(trava.get("ok") is True, trava)
    try:
        saida = io.StringIO()
        rc = iniciar([], entrada=io.StringIO(""), saida=saida)
        afirmar(rc == 2, rc)
        evento = json.loads(saida.getvalue().strip())
        afirmar(evento["evento"] == "bloqueio", evento)
        afirmar("aberta" in evento["dados"]["erro"], evento)
    finally:
        core.liberar_lock()


def teste_iniciar_serve_com_factory():
    saida = io.StringIO()
    rc = iniciar([], entrada=io.StringIO('{"id": 9, "metodo": "nucleo.ping"}\n'),
                 saida=saida, servico_factory=ServicoFalso)
    afirmar(rc == 0, rc)
    r = json.loads(saida.getvalue().strip())
    afirmar(r["id"] == 9 and r["ok"] is True, r)


def teste_buscar_despacha_para_o_servico():
    class ComBusca(ServicoFalso):
        def buscar(self, termo, limite=12):
            return [{"tipo": "jogo", "id": 1, "titulo": f"eco:{termo}",
                     "limite": limite}]

    ponte = Ponte(ComBusca())
    r = _chamar(ponte, {"id": 12, "metodo": "nucleo.buscar",
                        "params": {"termo": "zelda", "limite": 5}})
    afirmar(r["ok"] is True, r)
    afirmar(r["resultado"] == [{"tipo": "jogo", "id": 1, "titulo": "eco:zelda",
                                "limite": 5}], r)
    padrao = _chamar(ponte, {"id": 12, "metodo": "nucleo.buscar",
                             "params": {"termo": "zelda"}})
    afirmar(padrao["resultado"][0]["limite"] == 12, padrao)
    invalido = _chamar(ponte, {"id": 12, "metodo": "nucleo.buscar",
                               "params": {"termo": "zelda", "limite": 0}})
    afirmar(invalido["ok"] is False and "limite" in invalido["erro"], invalido)


def teste_buscar_real_acha_jogo_sem_acento():
    from servicos_ui import ServicoBiblioteca
    tmp = Path(tempfile.mkdtemp(prefix="suite-busca-"))
    db = tmp / "hub.db"
    con = core.get_db(db)
    try:
        core.criar_jogo(con, {"titulo": "Pokémon X", "executable_path": ""})
    finally:
        con.close()
    ponte = Ponte(ServicoBiblioteca(db))
    r = _chamar(ponte, {"id": 13, "metodo": "nucleo.buscar",
                        "params": {"termo": "pokemon"}})
    afirmar(r["ok"] is True, r)
    afirmar([i["titulo"] for i in r["resultado"]] == ["Pokémon X"], r)
    afirmar(r["resultado"][0]["tipo"] == "jogo", r)
    vazio = _chamar(ponte, {"id": 14, "metodo": "nucleo.buscar",
                            "params": {"termo": "  "}})
    afirmar(vazio["ok"] is True and vazio["resultado"] == [], vazio)


def teste_preferencias_ler_e_trocar():
    from servicos_ui import ServicoBiblioteca
    tmp = Path(tempfile.mkdtemp(prefix="suite-prefs-"))
    servico = ServicoBiblioteca(tmp / "hub.db")
    inicial = servico.preferencias()
    afirmar(list(inicial["perfis"]) == ["Tuco", "Isa"], inicial)
    afirmar(inicial["ativo"] in ("Tuco", "Isa"), inicial)
    afirmar(inicial["atalhos"]["paleta"] == "Ctrl+K", inicial["atalhos"])
    original = inicial["ativo"]
    outro = "Isa" if original == "Tuco" else "Tuco"
    afirmar(servico.trocar_perfil(outro)["ativo"] == outro, "troca")
    afirmar(servico.preferencias()["ativo"] == outro, "troca não persistiu")
    servico.trocar_perfil(original)  # devolve o sandbox ao estado anterior


def teste_preferencias_via_ponte_e_nome_invalido():
    class ComPrefs(ServicoFalso):
        ativo = "Tuco"

        def preferencias(self):
            return {"ativo": type(self).ativo, "perfis": ["Tuco", "Isa"], "atalhos": {}}

        def trocar_perfil(self, nome):
            if nome not in ("Tuco", "Isa"):
                raise ValueError("Perfil precisa ser Tuco ou Isa.")
            type(self).ativo = nome
            return self.preferencias()

    ponte = Ponte(ComPrefs())
    afirmar(_chamar(ponte, {"id": 15, "metodo": "preferencias.ler"})["resultado"]["ativo"]
            == "Tuco", "ler")
    r = _chamar(ponte, {"id": 16, "metodo": "preferencias.trocar_perfil",
                        "params": {"nome": "Isa"}})
    afirmar(r["ok"] is True and r["resultado"]["ativo"] == "Isa", r)
    erro = _chamar(ponte, {"id": 17, "metodo": "preferencias.trocar_perfil",
                           "params": {"nome": "Ninguem"}})
    afirmar(erro["ok"] is False and "Tuco ou Isa" in erro["erro"], erro)
    tipo_errado = _chamar(ponte, {"id": 18, "metodo": "preferencias.trocar_perfil",
                                  "params": {"nome": 7}})
    afirmar(tipo_errado["ok"] is False and "texto" in tipo_errado["erro"], tipo_errado)


def _semear_banco(db: Path) -> None:
    """Garante o schema antes das mutações dirigidas pela ponte (F2)."""
    con = core.get_db(db)
    con.close()


def teste_ponte_saude_e_jogo_ler():
    from servicos_ui import ServicoBiblioteca
    tmp = Path(tempfile.mkdtemp(prefix="suite-saude-"))
    db = tmp / "hub.db"
    _semear_banco(db)
    con = core.get_db(db)
    try:
        criado = core.criar_jogo(con, {"titulo": "Jogo Sondado", "executable_path": ""})
    finally:
        con.close()
    ponte = Ponte(ServicoBiblioteca(db))
    r = _chamar(ponte, {"id": 20, "metodo": "jogo.ler", "params": {"id": criado["id"]}})
    afirmar(r["ok"] is True and r["resultado"]["titulo"] == "Jogo Sondado", r)
    saude = _chamar(ponte, {"id": 21, "metodo": "nucleo.saude"})
    afirmar(saude["ok"] is True, saude)
    afirmar(saude["resultado"]["total"] == 1, saude)
    afirmar(criado["id"] in saude["resultado"]["ids_pendentes"], saude)
    faltante = _chamar(ponte, {"id": 22, "metodo": "jogo.ler", "params": {"id": 999}})
    afirmar(faltante["ok"] is False and "biblioteca" in faltante["erro"], faltante)
    invalido = _chamar(ponte, {"id": 23, "metodo": "jogo.ler", "params": {"id": "x"}})
    afirmar(invalido["ok"] is False and "inteiro" in invalido["erro"], invalido)


def teste_ponte_jogo_salvar_cria_e_atualiza():
    from servicos_ui import ServicoBiblioteca
    tmp = Path(tempfile.mkdtemp(prefix="suite-salvar-"))
    db = tmp / "hub.db"
    _semear_banco(db)
    ponte = Ponte(ServicoBiblioteca(db))
    criado = _chamar(ponte, {"id": 24, "metodo": "jogo.salvar",
                             "params": {"dados": {"titulo": "Criado pela Ponte", "nota": 7}}})
    afirmar(criado["ok"] is True, criado)
    ident = criado["resultado"]["id"]
    afirmar(criado["resultado"]["titulo"] == "Criado pela Ponte", criado)
    editado = _chamar(ponte, {"id": 25, "metodo": "jogo.salvar",
                              "params": {"id": ident,
                                         "dados": {"status": "jogando", "nota": ""}}})
    afirmar(editado["ok"] is True, editado)
    afirmar(editado["resultado"]["status"] == "jogando", editado)
    afirmar(editado["resultado"]["nota"] is None, editado)
    afirmar(editado["resultado"]["titulo"] == "Criado pela Ponte", editado)
    ruim = _chamar(ponte, {"id": 26, "metodo": "jogo.salvar", "params": {"dados": "x"}})
    afirmar(ruim["ok"] is False and "dados" in ruim["erro"], ruim)
    tipo_ruim = _chamar(ponte, {"id": 27, "metodo": "jogo.salvar",
                                "params": {"id": "3", "dados": {}}})
    afirmar(tipo_ruim["ok"] is False and "inteiro" in tipo_ruim["erro"], tipo_ruim)


def teste_ponte_favorito_por_perfil():
    from servicos_ui import ServicoBiblioteca
    tmp = Path(tempfile.mkdtemp(prefix="suite-favorito-"))
    db = tmp / "hub.db"
    _semear_banco(db)
    servico = ServicoBiblioteca(db)
    ponte = Ponte(servico)
    criado = _chamar(ponte, {"id": 28, "metodo": "jogo.salvar",
                             "params": {"dados": {"titulo": "Favorito de Prova"}}})["resultado"]
    ident = criado["id"]
    ativo = servico.preferencias()["ativo"]
    outro = "Isa" if ativo == "Tuco" else "Tuco"
    try:
        marco = _chamar(ponte, {"id": 29, "metodo": "jogo.favoritar", "params": {"id": ident}})
        afirmar(marco["ok"] is True and marco["resultado"]["favorito"] is True, marco)
        servico.trocar_perfil(outro)
        dele = _chamar(ponte, {"id": 30, "metodo": "jogo.ler", "params": {"id": ident}})
        afirmar(dele["resultado"]["favorito"] is False, dele)
        alterno = _chamar(ponte, {"id": 31, "metodo": "jogo.favoritar", "params": {"id": ident}})
        afirmar(alterno["resultado"]["favorito"] is (not dele["resultado"]["favorito"]), alterno)
    finally:
        servico.trocar_perfil(ativo)
    volta = _chamar(ponte, {"id": 32, "metodo": "jogo.ler", "params": {"id": ident}})
    afirmar(volta["resultado"]["favorito"] is True, volta)


def teste_ponte_observacoes_trunca():
    from servicos_ui import ServicoBiblioteca
    tmp = Path(tempfile.mkdtemp(prefix="suite-obs-"))
    db = tmp / "hub.db"
    _semear_banco(db)
    ponte = Ponte(ServicoBiblioteca(db))
    criado = _chamar(ponte, {"id": 33, "metodo": "jogo.salvar",
                             "params": {"dados": {"titulo": "Diario de Prova"}}})["resultado"]
    r = _chamar(ponte, {"id": 34, "metodo": "jogo.observacoes",
                        "params": {"id": criado["id"], "texto": "x" * 5000}})
    afirmar(r["ok"] is True, r)
    afirmar(r["resultado"]["observacoes"] == "x" * 4000, len(r["resultado"]["observacoes"]))
    ruim = _chamar(ponte, {"id": 35, "metodo": "jogo.observacoes",
                           "params": {"id": criado["id"], "texto": 5}})
    afirmar(ruim["ok"] is False and "texto" in ruim["erro"], ruim)


def teste_ponte_excluir_desfazer_e_lixeira():
    from servicos_ui import ServicoBiblioteca
    tmp = Path(tempfile.mkdtemp(prefix="suite-lixeira-"))
    db = tmp / "hub.db"
    _semear_banco(db)
    ponte = Ponte(ServicoBiblioteca(db))
    criado = _chamar(ponte, {"id": 36, "metodo": "jogo.salvar",
                             "params": {"dados": {"titulo": "Jogo da Lixeira"}}})["resultado"]
    recibo = _chamar(ponte, {"id": 37, "metodo": "item.excluir",
                             "params": {"categoria": "jogos", "id": criado["id"]}})
    afirmar(recibo["ok"] is True, recibo)
    afirmar(recibo["resultado"]["desfazer"]["titulo"] == "Jogo da Lixeira", recibo)
    estado = _chamar(ponte, {"id": 38, "metodo": "lixeira.estado"})
    afirmar(estado["resultado"]["disponivel"] is True, estado)
    afirmar(estado["resultado"]["titulo"] == "Jogo da Lixeira", estado)
    voltou = _chamar(ponte, {"id": 39, "metodo": "item.desfazer"})
    afirmar(voltou["ok"] is True and voltou["resultado"]["titulo"] == "Jogo da Lixeira", voltou)
    depois = _chamar(ponte, {"id": 40, "metodo": "lixeira.estado"})
    afirmar(depois["resultado"]["titulo"] != "Jogo da Lixeira", depois)
    titulos = [j["titulo"] for j in
               _chamar(ponte, {"id": 41, "metodo": "nucleo.snapshot"})["resultado"]["jogos"]]
    afirmar("Jogo da Lixeira" in titulos, titulos)
    categoria_ruim = _chamar(ponte, {"id": 42, "metodo": "item.excluir",
                                     "params": {"categoria": "x", "id": 1}})
    afirmar(categoria_ruim["ok"] is False and "categoria" in categoria_ruim["erro"], categoria_ruim)


def teste_ponte_filtro_padrao_e_por_perfil():
    from servicos_ui import ServicoBiblioteca
    tmp = Path(tempfile.mkdtemp(prefix="suite-filtro-"))
    db = tmp / "hub.db"
    _semear_banco(db)
    servico = ServicoBiblioteca(db)
    ponte = Ponte(servico)
    padrao = _chamar(ponte, {"id": 43, "metodo": "preferencias.filtro"})
    afirmar(padrao["ok"] is True, padrao)
    afirmar(padrao["resultado"] == {"filtro": "todos", "ordem": "titulo"}, padrao)
    ativo = servico.preferencias()["ativo"]
    outro = "Isa" if ativo == "Tuco" else "Tuco"
    salvo = _chamar(ponte, {"id": 44, "metodo": "preferencias.salvar_filtro",
                            "params": {"filtro": "favoritos", "ordem": "horas"}})
    afirmar(salvo["ok"] is True, salvo)
    afirmar(salvo["resultado"] == {"filtro": "favoritos", "ordem": "horas"}, salvo)
    servico.trocar_perfil(outro)
    do_outro = _chamar(ponte, {"id": 45, "metodo": "preferencias.filtro"})
    afirmar(do_outro["resultado"] == {"filtro": "todos", "ordem": "titulo"}, do_outro)
    servico.trocar_perfil(ativo)
    de_volta = _chamar(ponte, {"id": 46, "metodo": "preferencias.filtro"})
    afirmar(de_volta["resultado"] == {"filtro": "favoritos", "ordem": "horas"}, de_volta)
    ruim = _chamar(ponte, {"id": 47, "metodo": "preferencias.salvar_filtro",
                           "params": {"filtro": "qualquer", "ordem": "titulo"}})
    afirmar(ruim["ok"] is False and "Filtro" in ruim["erro"], ruim)
    tipo = _chamar(ponte, {"id": 48, "metodo": "preferencias.salvar_filtro",
                           "params": {"filtro": 7, "ordem": "titulo"}})
    afirmar(tipo["ok"] is False and "texto" in tipo["erro"], tipo)
