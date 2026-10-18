"""Ponte NDJSON (F0): protocolo do desktop Electron, exercitado em processo.

O runner da suíte bloqueia processos externos; por isso a ponte é importada
direto (`import ponte`) e dirigida com entrada/saída de texto em memória.
"""
import io
import json
import tempfile
import threading
import time
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


def _esperar(condicao, limite=5.0):
    """Aguarda um estado assíncrono (jobs) sem depender de sleep fixo."""
    fim = time.time() + limite
    while time.time() < fim:
        if condicao():
            return True
        time.sleep(0.03)
    return condicao()


def _linhas(saida):
    return [json.loads(t) for t in saida.getvalue().splitlines() if t.strip()]


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


def teste_ponte_trabalhos_eventos_e_cancelamento():
    saida = io.StringIO()
    ponte = Ponte(ServicoFalso())

    def tarefa(progresso, cancelado):
        for pct in (0, 40, 80):
            progresso(pct)
            if cancelado.wait(1.0):
                return {"parou": True}
        progresso(100)
        return {"feito": True}

    def iniciar(servico, params):
        return {"trabalho": ponte.trabalhos.iniciar("Tarefa de teste", tarefa,
                                                    cancelavel=True, escopo="teste")}

    ponte.metodos["t.iniciar"] = iniciar
    ponte.servir(io.StringIO('{"id": 50, "metodo": "t.iniciar"}\n'), saida)
    resposta = next(e for e in _linhas(saida) if e.get("id") == 50)
    afirmar(resposta["ok"] is True, resposta)
    trabalho = resposta["resultado"]["trabalho"]
    ident = trabalho["id"]
    afirmar(trabalho["estado"] == "rodando" and trabalho["cancelavel"] is True, trabalho)
    afirmar(_esperar(lambda: any(
        e.get("evento") == "trabalho" and e["dados"]["id"] == ident
        and e["dados"].get("motivo") == "progresso" and e["dados"]["pct"] == 80
        for e in _linhas(saida))), saida.getvalue())
    lista = ponte.despachar("trabalhos.listar", {})
    afirmar(lista["ok"] is True and lista["resultado"][0]["id"] == ident, lista)
    cancelado = ponte.despachar("trabalhos.cancelar", {"id": ident})
    afirmar(cancelado["ok"] is True, cancelado)
    afirmar(cancelado["resultado"]["estado"] in ("rodando", "cancelando"), cancelado)
    afirmar(_esperar(lambda: any(
        e.get("evento") == "trabalho" and e["dados"]["id"] == ident
        and e["dados"]["estado"] == "cancelado" for e in _linhas(saida))), saida.getvalue())
    eventos = [e["dados"] for e in _linhas(saida) if e.get("evento") == "trabalho"]
    pcts = [d["pct"] for d in eventos if d.get("motivo") == "progresso"]
    afirmar(pcts == [0, 40, 80], pcts)
    afirmar(eventos[-1]["estado"] == "cancelado", eventos[-1])
    afirmar(eventos[-1]["detalhe"] == {"parou": True}, eventos[-1])


def teste_ponte_trabalhos_cancelar_invalido():
    saida = io.StringIO()
    ponte = Ponte(ServicoFalso())
    soltar = threading.Event()

    def tarefa(progresso, cancelado):
        soltar.wait(3)
        return {"ok": True}

    def iniciar(servico, params):
        return {"trabalho": ponte.trabalhos.iniciar("Tarefa firme", tarefa)}

    ponte.metodos["t.iniciar"] = iniciar
    ponte.servir(io.StringIO('{"id": 55, "metodo": "t.iniciar"}\n'), saida)
    resposta = next(e for e in _linhas(saida) if e.get("id") == 55)
    ident = resposta["resultado"]["trabalho"]["id"]
    firme = ponte.despachar("trabalhos.cancelar", {"id": ident})
    afirmar(firme["ok"] is False and "cancelada" in firme["erro"], firme)
    desconhecido = ponte.despachar("trabalhos.cancelar", {"id": 999})
    afirmar(desconhecido["ok"] is False and "não existe" in desconhecido["erro"], desconhecido)
    invalido = ponte.despachar("trabalhos.cancelar", {"id": "x"})
    afirmar(invalido["ok"] is False and "inteiro" in invalido["erro"], invalido)
    soltar.set()
    afirmar(_esperar(lambda: any(
        e.get("evento") == "trabalho" and e["dados"]["estado"] == "ok"
        for e in _linhas(saida))), saida.getvalue())


class ServicoJogo(ServicoFalso):
    """Serviço fake que simula o ciclo de jogo sem abrir processo nenhum."""

    auto_backup = True
    rastreado = True
    horas = 2.5

    def __init__(self):
        self.soltar = threading.Event()
        self.registros = {}

    def jogo(self, gid):
        return {"id": gid, "titulo": "Jogo de Mentira", "executable_path": "x.cmd"}

    def iniciar_jogo(self, gid, ao_fim):
        ao_fim(self.horas, self.rastreado)
        self.soltar.wait(5)
        return {"ok": True, "aviso": "Jogo iniciado. Boa diversão!"}

    def registrar_sessao(self, gid, horas):
        self.registros["sessao"] = (gid, horas)
        return {"ok": True}

    def aparencia(self):
        return {"auto_backup": self.auto_backup}

    def backup_pos_sessao(self, gid):
        self.registros["backup"] = gid
        return {"ok": True, "saves": {"ok": True, "arquivos": 2}}


def _jogar_ate_o_fim(ponte, saida, pedido_id):
    resposta = next(e for e in _linhas(saida) if e.get("id") == pedido_id)
    afirmar(resposta["ok"] is True, resposta)
    ident = resposta["resultado"]["trabalho"]["id"]
    ponte.servico.soltar.set()
    afirmar(_esperar(lambda: any(
        e.get("evento") == "trabalho" and e["dados"]["id"] == ident
        and e["dados"]["estado"] in ("ok", "erro", "cancelado") for e in _linhas(saida))),
        saida.getvalue())
    fim = next(e["dados"] for e in _linhas(saida)
               if e.get("evento") == "trabalho" and e["dados"]["id"] == ident
               and e["dados"]["estado"] in ("ok", "erro", "cancelado"))
    return fim


def teste_ponte_jogar_em_thread():
    saida = io.StringIO()
    servico = ServicoJogo()
    ponte = Ponte(servico)
    ponte.servir(io.StringIO('{"id": 51, "metodo": "jogo.jogar", "params": {"id": 7}}\n'),
                 saida)
    resposta = next(e for e in _linhas(saida) if e.get("id") == 51)
    afirmar(resposta["ok"] is True, resposta)
    trabalho = resposta["resultado"]["trabalho"]
    afirmar(trabalho["estado"] == "rodando", trabalho)
    afirmar(trabalho["rotulo"] == "Jogar Jogo de Mentira", trabalho)
    segundo = ponte.despachar("jogo.jogar", {"id": 8})
    afirmar(segundo["ok"] is False and "andamento" in segundo["erro"], segundo)
    fim = _jogar_ate_o_fim(ponte, saida, 51)
    afirmar(fim["estado"] == "ok", fim)
    afirmar(servico.registros["sessao"] == (7, 2.5), servico.registros)
    afirmar(servico.registros.get("backup") == 7, servico.registros)
    afirmar("arquivo(s)" in fim["detalhe"]["aviso"], fim["detalhe"])
    afirmar(fim["detalhe"]["horas"] == 2.5 and fim["detalhe"]["rastreado"] is True, fim["detalhe"])
    invalido = ponte.despachar("jogo.jogar", {"id": "x"})
    afirmar(invalido["ok"] is False and "inteiro" in invalido["erro"], invalido)


def teste_ponte_jogar_opt_out_backup():
    saida = io.StringIO()
    servico = ServicoJogo()
    servico.auto_backup = False
    ponte = Ponte(servico)
    ponte.servir(io.StringIO('{"id": 56, "metodo": "jogo.jogar", "params": {"id": 9}}\n'),
                 saida)
    fim = _jogar_ate_o_fim(ponte, saida, 56)
    afirmar("backup" not in servico.registros, servico.registros)
    afirmar(servico.registros["sessao"] == (9, 2.5), servico.registros)
    afirmar(fim["estado"] == "ok", fim)


def teste_ponte_jogar_sem_rastreio_avisa():
    saida = io.StringIO()
    servico = ServicoJogo()
    servico.rastreado = False
    ponte = Ponte(servico)
    ponte.servir(io.StringIO('{"id": 57, "metodo": "jogo.jogar", "params": {"id": 10}}\n'),
                 saida)
    fim = _jogar_ate_o_fim(ponte, saida, 57)
    afirmar("sessao" not in servico.registros, servico.registros)
    afirmar("sem rastreio" in fim["detalhe"]["aviso"], fim["detalhe"])


def teste_ponte_jogar_erro_vira_trabalho_erro():
    saida = io.StringIO()
    servico = ServicoJogo()

    def quebrar(gid, ao_fim):
        ao_fim(0.0, False)
        raise ValueError("Não foi possível iniciar o jogo.")

    servico.iniciar_jogo = quebrar
    ponte = Ponte(servico)
    ponte.servir(io.StringIO('{"id": 58, "metodo": "jogo.jogar", "params": {"id": 11}}\n'),
                 saida)
    fim = _jogar_ate_o_fim(ponte, saida, 58)
    afirmar(fim["estado"] == "erro", fim)
    afirmar("Não foi possível iniciar" in fim["erro"], fim)


def teste_ponte_jogar_espera_o_fim_assincrono():
    saida = io.StringIO()
    servico = ServicoJogo()

    def iniciar_jogo(gid, ao_fim):
        def depois():
            time.sleep(0.3)
            ao_fim(1.25, True)

        threading.Thread(target=depois, daemon=True).start()
        return {"ok": True, "aviso": ""}

    servico.iniciar_jogo = iniciar_jogo
    ponte = Ponte(servico)
    ponte.servir(io.StringIO('{"id": 59, "metodo": "jogo.jogar", "params": {"id": 12}}\n'),
                 saida)
    resposta = next(e for e in _linhas(saida) if e.get("id") == 59)
    afirmar(resposta["ok"] is True, resposta)
    ident = resposta["resultado"]["trabalho"]["id"]
    lista = ponte.despachar("trabalhos.listar", {})
    em_curso = next(t for t in lista["resultado"] if t["id"] == ident)
    afirmar(em_curso["estado"] == "rodando", em_curso)
    afirmar(_esperar(lambda: any(
        e.get("evento") == "trabalho" and e["dados"]["id"] == ident
        and e["dados"]["estado"] == "ok" for e in _linhas(saida))), saida.getvalue())
    afirmar(servico.registros["sessao"] == (12, 1.25), servico.registros)
    afirmar(servico.registros.get("backup") == 12, servico.registros)


class ServicoMusicas(ServicoFalso):
    """Serviço fake dos jobs de música (importação e fila de downloads)."""

    def __init__(self):
        self.pastas = []
        self.baixar_erro = ""
        self.vistos = []

    def importar_musicas(self, pasta):
        self.pastas.append(str(pasta))
        return {"novos": 2, "ignorados": 1, "erros": [], "capas": 0}

    def baixar_musicas(self, cancelar, progresso=None):
        if self.baixar_erro:
            raise ValueError(self.baixar_erro)
        for pct in (10, 50, 90):
            if cancelar.is_set():
                break
            self.vistos.append(pct)
            if progresso:
                progresso({"pct": pct, "rotulo": "1/2 · Banda — Faixa"})
            time.sleep(0.05)
        return {"novas": 0, "erros": [], "cancelado": cancelar.is_set()}


def teste_ponte_musicas_importar_cria_job():
    saida = io.StringIO()
    servico = ServicoMusicas()
    ponte = Ponte(servico)
    linha = json.dumps({"id": 60, "metodo": "musicas.importar",
                        "params": {"pasta": "C:\\Provas\\musicas"}})
    ponte.servir(io.StringIO(linha + "\n"), saida)
    resposta = next(e for e in _linhas(saida) if e.get("id") == 60)
    afirmar(resposta["ok"] is True, resposta)
    trabalho = resposta["resultado"]["trabalho"]
    afirmar(trabalho["escopo"] == "musicas" and trabalho["cancelavel"] is False, trabalho)
    afirmar(_esperar(lambda: any(
        e.get("evento") == "trabalho" and e["dados"]["id"] == trabalho["id"]
        and e["dados"]["estado"] == "ok" for e in _linhas(saida))), saida.getvalue())
    fim = next(e["dados"] for e in _linhas(saida)
               if e.get("evento") == "trabalho" and e["dados"]["id"] == trabalho["id"]
               and e["dados"]["motivo"] == "fim")
    afirmar(fim["detalhe"]["novos"] == 2, fim)
    afirmar("2 nova" in fim["detalhe"]["aviso"], fim)
    afirmar(servico.pastas == ["C:\\Provas\\musicas"], servico.pastas)


def teste_ponte_musicas_importar_pasta_invalida():
    ponte = Ponte(ServicoMusicas())
    for ruim in ({}, {"pasta": ""}, {"pasta": "   "}, {"pasta": 7}):
        r = _chamar(ponte, {"id": 61, "metodo": "musicas.importar", "params": ruim})
        afirmar(r["ok"] is False and "pasta" in r["erro"], r)


def teste_ponte_musicas_importar_real_copia_wav():
    import wave

    from servicos_ui import ServicoBiblioteca

    tmp = Path(tempfile.mkdtemp(prefix="suite-musicas-"))
    origem = tmp / "origem"
    origem.mkdir()
    with wave.open(str(origem / "sintetica.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * 800)
    db = tmp / "hub.db"
    core.get_db(db).close()

    saida = io.StringIO()
    ponte = Ponte(ServicoBiblioteca(db))
    linha = json.dumps({"id": 62, "metodo": "musicas.importar",
                        "params": {"pasta": str(origem)}})
    ponte.servir(io.StringIO(linha + "\n"), saida)
    resposta = next(e for e in _linhas(saida) if e.get("id") == 62)
    afirmar(resposta["ok"] is True, resposta)
    ident = resposta["resultado"]["trabalho"]["id"]
    afirmar(_esperar(lambda: any(
        e.get("evento") == "trabalho" and e["dados"]["id"] == ident
        and e["dados"]["estado"] in ("ok", "erro", "cancelado") for e in _linhas(saida))),
        saida.getvalue())
    fim = next(e["dados"] for e in _linhas(saida)
               if e.get("evento") == "trabalho" and e["dados"]["id"] == ident
               and e["dados"]["motivo"] == "fim")
    afirmar(fim["estado"] == "ok" and fim["detalhe"]["novos"] == 1, fim)
    snap = ponte.despachar("nucleo.snapshot", {})
    titulos = [str(m["titulo"]).lower() for m in snap["resultado"]["musicas"]]
    afirmar(any("sintetica" in t for t in titulos), titulos)


def teste_ponte_musicas_baixar_fila_progresso_e_cancelamento():
    saida = io.StringIO()
    servico = ServicoMusicas()
    ponte = Ponte(servico)
    ponte.servir(io.StringIO('{"id": 63, "metodo": "musicas.baixar_fila"}\n'), saida)
    resposta = next(e for e in _linhas(saida) if e.get("id") == 63)
    afirmar(resposta["ok"] is True, resposta)
    trabalho = resposta["resultado"]["trabalho"]
    afirmar(trabalho["cancelavel"] is True and trabalho["escopo"] == "musicas", trabalho)
    ident = trabalho["id"]
    afirmar(_esperar(lambda: any(
        e.get("evento") == "trabalho" and e["dados"]["id"] == ident
        and e["dados"].get("motivo") == "progresso" and e["dados"]["pct"] == 10
        for e in _linhas(saida))), saida.getvalue())
    cancelado = ponte.despachar("trabalhos.cancelar", {"id": ident})
    afirmar(cancelado["ok"] is True, cancelado)
    afirmar(_esperar(lambda: any(
        e.get("evento") == "trabalho" and e["dados"]["id"] == ident
        and e["dados"]["estado"] == "cancelado" for e in _linhas(saida))), saida.getvalue())
    fim = next(e["dados"] for e in _linhas(saida)
               if e.get("evento") == "trabalho" and e["dados"]["id"] == ident
               and e["dados"]["motivo"] == "fim")
    afirmar("ancelado" in fim["detalhe"]["aviso"], fim)


def teste_ponte_musicas_baixar_fila_erro_claro():
    saida = io.StringIO()
    servico = ServicoMusicas()
    servico.baixar_erro = "Instale yt-dlp em Dependências de áudio antes de baixar a fila."
    ponte = Ponte(servico)
    ponte.servir(io.StringIO('{"id": 64, "metodo": "musicas.baixar_fila"}\n'), saida)
    resposta = next(e for e in _linhas(saida) if e.get("id") == 64)
    afirmar(resposta["ok"] is True, resposta)
    ident = resposta["resultado"]["trabalho"]["id"]
    afirmar(_esperar(lambda: any(
        e.get("evento") == "trabalho" and e["dados"]["id"] == ident
        and e["dados"]["estado"] == "erro" for e in _linhas(saida))), saida.getvalue())
    fim = next(e["dados"] for e in _linhas(saida)
               if e.get("evento") == "trabalho" and e["dados"]["id"] == ident
               and e["dados"]["motivo"] == "fim")
    afirmar("yt-dlp" in fim["erro"], fim)


def teste_ponte_musicas_jobs_concorrentes_bloqueados():
    saida = io.StringIO()
    servico = ServicoMusicas()
    soltar = threading.Event()

    def importar_lento(pasta):
        soltar.wait(3)
        return {"novos": 1, "ignorados": 0, "erros": [], "capas": 0}

    servico.importar_musicas = importar_lento
    ponte = Ponte(servico)
    linha = json.dumps({"id": 65, "metodo": "musicas.importar", "params": {"pasta": "x"}})
    ponte.servir(io.StringIO(linha + "\n"), saida)
    resposta = next(e for e in _linhas(saida) if e.get("id") == 65)
    afirmar(resposta["ok"] is True, resposta)
    ident = resposta["resultado"]["trabalho"]["id"]
    segundo = _chamar(ponte, {"id": 66, "metodo": "musicas.baixar_fila"})
    afirmar(segundo["ok"] is False and "andamento" in segundo["erro"], segundo)
    soltar.set()
    afirmar(_esperar(lambda: any(
        e.get("evento") == "trabalho" and e["dados"]["id"] == ident
        and e["dados"]["estado"] == "ok" for e in _linhas(saida))), saida.getvalue())


def teste_ponte_registrar_horas():
    class ServicoHoras(ServicoFalso):
        def registrar_sessao(self, gid, horas):
            return {"ok": True, "gid": gid, "horas": horas}

    ponte = Ponte(ServicoHoras())
    r = _chamar(ponte, {"id": 53, "metodo": "jogo.registrar_horas",
                        "params": {"id": 3, "horas": 1.5}})
    afirmar(r["ok"] is True and r["resultado"]["horas"] == 1.5, r)
    for ruim in ({"id": 3, "horas": 0}, {"id": 3, "horas": -1}, {"id": 3, "horas": "x"},
                 {"id": "x", "horas": 1}):
        erro = _chamar(ponte, {"id": 54, "metodo": "jogo.registrar_horas", "params": ruim})
        afirmar(erro["ok"] is False, erro)
