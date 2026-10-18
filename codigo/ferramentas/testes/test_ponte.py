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
