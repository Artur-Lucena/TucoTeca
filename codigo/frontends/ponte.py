#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ponte NDJSON entre o Electron e o núcleo Python (F0).

Uma linha JSON entra pelo stdin, uma linha JSON sai pelo stdout. Sem porta
TCP e sem servidor: o processo principal do Electron sobe este script como
processo filho e conversa por stdin/stdout.

Envelope:
    pedido:  {"id": 1, "metodo": "nucleo.snapshot", "params": {}}
    ok:      {"id": 1, "ok": true, "resultado": ...}
    erro:    {"id": 1, "ok": false, "erro": "mensagem"}
    evento:  {"evento": "bloqueio", "dados": {...}}    (assíncrono, sem id)
             {"evento": "trabalho", "dados": {...}}    (jobs: início/progresso/fim)

A ponte nunca morre por erro de chamada: JSON inválido, método desconhecido e
exceção de serviço viram resposta ok=false. Contrato provado por
`codigo/ferramentas/testes/test_ponte.py`.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import threading
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def preparar_ambiente() -> None:
    """Mesmo ambiente do checkout (`abrir_hub.preparar`): home, runtime e sys.path."""
    for caminho in (str(RAIZ / "codigo/frontends"), str(RAIZ / "codigo")):
        if caminho not in sys.path:
            sys.path.insert(0, caminho)
    from ferramentas import abrir_hub
    abrir_hub.preparar()


def ler_versao() -> str:
    try:
        return (RAIZ / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def _ping(servico, params) -> dict:
    from bib_nucleo import base
    return {"pong": True, "versao": ler_versao(),
            "home": str(base.HOME_DIR), "db": str(getattr(servico, "db_path", ""))}


def _snapshot(servico, params) -> dict:
    return servico.snapshot()


def _modulos(servico, params) -> list:
    from servicos_ui.modulos import modulos_padrao
    return [m.apresentar() for m in modulos_padrao()]


def _buscar(servico, params) -> list:
    termo = params.get("termo", "")
    if not isinstance(termo, str):
        raise ValueError("termo deve ser texto")
    limite = params.get("limite", 12)
    if isinstance(limite, bool) or not isinstance(limite, int) or not 1 <= limite <= 50:
        raise ValueError("limite deve ser um inteiro entre 1 e 50")
    return servico.buscar(termo, limite)


def _preferencias(servico, params) -> dict:
    return servico.preferencias()


def _trocar_perfil(servico, params) -> dict:
    nome = params.get("nome", "")
    if not isinstance(nome, str):
        raise ValueError("nome deve ser texto")
    return servico.trocar_perfil(nome)


def _inteiro(params, chave) -> int:
    valor = params.get(chave)
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError(f"{chave} deve ser um inteiro")
    return valor


def _com_perfil(jogo):
    """Aplica o perfil ativo (favorito por pessoa) ao dicionário do jogo."""
    from bib_nucleo.preferencias_pessoais import aplicar_perfil
    return aplicar_perfil([jogo])[0]


def _saude(servico, params) -> dict:
    return servico.saude()


def _jogo_ler(servico, params) -> dict:
    return _com_perfil(servico.jogo(_inteiro(params, "id")))


def _jogo_salvar(servico, params) -> dict:
    dados = params.get("dados", {})
    if not isinstance(dados, dict):
        raise ValueError("dados deve ser um objeto JSON")
    ident = params.get("id")
    if ident is not None:
        ident = _inteiro(params, "id")
    return _com_perfil(servico.salvar_jogo(ident, dados))


def _jogo_favoritar(servico, params) -> dict:
    ident = _inteiro(params, "id")
    servico.favorito(ident)
    return _com_perfil(servico.jogo(ident))


def _jogo_observacoes(servico, params) -> dict:
    ident = _inteiro(params, "id")
    texto = params.get("texto", "")
    if not isinstance(texto, str):
        raise ValueError("texto deve ser texto")
    return _com_perfil(servico.salvar_observacoes(ident, texto))


def _item_excluir(servico, params) -> dict:
    categoria = params.get("categoria", "")
    if categoria not in ("jogos", "desejos", "videos", "musicas"):
        raise ValueError("categoria deve ser jogos, desejos, videos ou musicas")
    return servico.excluir(categoria, _inteiro(params, "id"))


def _item_desfazer(servico, params) -> dict:
    return servico.desfazer_exclusao()


def _lixeira_estado(servico, params) -> dict:
    return servico.lixeira()


def _filtro(servico, params) -> dict:
    return servico.filtro()


def _salvar_filtro(servico, params) -> dict:
    filtro = params.get("filtro", "")
    ordem = params.get("ordem", "")
    if not isinstance(filtro, str) or not isinstance(ordem, str):
        raise ValueError("filtro e ordem devem ser texto")
    return servico.salvar_filtro(filtro, ordem)


def _aviso_pos_sessao(servico, ident) -> str:
    """Backup pós-sessão opt-in (default ligado), espelhando o Qt; falha vira aviso."""
    try:
        aparencia = servico.aparencia()
    except Exception:
        aparencia = {}
    if aparencia.get("auto_backup", True) is False:
        return ""
    try:
        resultado = servico.backup_pos_sessao(ident)
    except Exception as erro:
        return "Backup pós-sessão falhou: " + (str(erro) or "falha")
    if not resultado.get("ok", True):
        return "Backup dos saves não foi concluído: " + str(resultado.get("erro") or "falha")
    saves = resultado.get("saves") or {}
    if saves.get("ok") and saves.get("arquivos"):
        return f"Backup pós-sessão criado. {saves['arquivos']} arquivo(s) de saves guardados."
    return ("Backup pós-sessão criado. "
            + str(saves.get("aviso") or saves.get("erro") or "Configure os saves deste jogo."))


METODOS = {
    "nucleo.ping": _ping,
    "nucleo.snapshot": _snapshot,
    "nucleo.buscar": _buscar,
    "nucleo.saude": _saude,
    "modulos.listar": _modulos,
    "preferencias.ler": _preferencias,
    "preferencias.trocar_perfil": _trocar_perfil,
    "preferencias.filtro": _filtro,
    "preferencias.salvar_filtro": _salvar_filtro,
    "jogo.ler": _jogo_ler,
    "jogo.salvar": _jogo_salvar,
    "jogo.favoritar": _jogo_favoritar,
    "jogo.observacoes": _jogo_observacoes,
    "item.excluir": _item_excluir,
    "item.desfazer": _item_desfazer,
    "lixeira.estado": _lixeira_estado,
}


class Trabalhos:
    """Operações longas fora do loop NDJSON: eventos e cancelamento cooperativo.

    Cada trabalho roda numa thread daemon; quem chama publica o resultado por
    `{"evento": "trabalho", "dados": {...}}` (sem id de pedido). O cancelamento
    é uma bandeira (`threading.Event`) que a própria operação precisa honrar.
    """

    def __init__(self, publicar):
        self._publicar_evento = publicar
        self._travas = threading.RLock()
        self._proximo = 1
        self._itens = {}

    def iniciar(self, rotulo, funcao, cancelavel=False, escopo=None) -> dict:
        with self._travas:
            if escopo:
                for outro in self._itens.values():
                    if (outro["escopo"] == escopo
                            and outro["estado"] in ("rodando", "cancelando")):
                        raise ValueError("Já existe uma tarefa desse tipo em andamento.")
            ident = self._proximo
            self._proximo += 1
            bandeira = threading.Event()
            item = {"id": ident, "rotulo": str(rotulo or "Tarefa"), "estado": "rodando",
                    "pct": None, "cancelavel": bool(cancelavel), "escopo": escopo,
                    "iniciado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "aviso": "", "erro": "", "detalhe": {}, "_bandeira": bandeira}
            self._itens[ident] = item
        self._publicar(item, "inicio")
        threading.Thread(target=self._rodar, args=(item, funcao, bandeira),
                         name=f"trabalho-{ident}", daemon=True).start()
        return self.publico(item)

    def _rodar(self, item, funcao, bandeira):
        def progresso(pct):
            try:
                novo = max(0, min(100, int(round(float(pct)))))
            except (TypeError, ValueError):
                return
            with self._travas:
                if item["estado"] != "rodando" or novo == item["pct"]:
                    return
                item["pct"] = novo
            self._publicar(item, "progresso")

        try:
            resultado = funcao(progresso, bandeira)
            with self._travas:
                item["estado"] = "cancelado" if bandeira.is_set() else "ok"
                if isinstance(resultado, dict):
                    item["detalhe"] = dict(resultado)
            self._publicar(item, "fim")
        except Exception as erro:
            with self._travas:
                item["estado"] = "erro"
                item["erro"] = str(erro) or type(erro).__name__
            self._publicar(item, "fim")

    def publico(self, item) -> dict:
        with self._travas:
            dados = {chave: valor for chave, valor in item.items()
                     if not chave.startswith("_")}
            dados["detalhe"] = dict(item["detalhe"])
            return dados

    def listar(self) -> list:
        with self._travas:
            return [self.publico(item) for item in self._itens.values()]

    def cancelar(self, params) -> dict:
        ident = _inteiro(params, "id")
        with self._travas:
            item = self._itens.get(ident)
            if item is None:
                raise LookupError(f"tarefa não existe: {ident}")
            if not item["cancelavel"]:
                raise ValueError("Esta tarefa não pode ser cancelada.")
            if item["estado"] not in ("rodando", "cancelando"):
                raise ValueError("Esta tarefa já terminou.")
            item["estado"] = "cancelando"
            item["_bandeira"].set()
        self._publicar(item, "cancelamento")
        return self.publico(item)

    def _publicar(self, item, motivo):
        self._publicar_evento({"evento": "trabalho",
                               "dados": {**self.publico(item), "motivo": motivo}})


class Ponte:
    """Despachante NDJSON: cada linha vira uma resposta serializada."""

    def __init__(self, servico, metodos=None, trabalhos=None):
        self.servico = servico
        self._escrita = threading.RLock()
        self._saida = None
        self.trabalhos = trabalhos if trabalhos is not None else Trabalhos(self._publicar_evento)
        base = dict(METODOS) if metodos is None else dict(metodos)
        base.update({
            "trabalhos.listar": self._trabalhos_listar,
            "trabalhos.cancelar": self._trabalhos_cancelar,
            "jogo.jogar": self._jogo_jogar,
            "jogo.registrar_horas": self._jogo_registrar_horas,
            "musicas.importar": self._musicas_importar,
            "musicas.baixar_fila": self._musicas_baixar_fila,
        })
        self.metodos = base

    def _publicar_evento(self, evento: dict) -> None:
        with self._escrita:
            if self._saida is None:
                return
            self._saida.write(json.dumps(evento, ensure_ascii=False, default=str) + "\n")
            self._saida.flush()

    def _trabalhos_listar(self, servico, params) -> list:
        return self.trabalhos.listar()

    def _trabalhos_cancelar(self, servico, params) -> dict:
        return self.trabalhos.cancelar(params)

    def _jogo_jogar(self, servico, params) -> dict:
        ident = _inteiro(params, "id")
        jogo = servico.jogo(ident)
        titulo = str(jogo.get("titulo") or ("jogo " + str(ident)))
        estado = {"horas": 0.0, "rastreado": False}

        def tarefa(progresso, cancelado):
            fim = threading.Event()

            def ao_fim(horas, rastreado):
                estado["horas"] = float(horas or 0.0)
                estado["rastreado"] = bool(rastreado)
                fim.set()

            resultado = servico.iniciar_jogo(ident, ao_fim)
            aviso = str(resultado.get("aviso") or "") if isinstance(resultado, dict) else ""
            fim.wait()  # o núcleo vigia o processo e chama ao_fim quando ele sai
            detalhe = {"horas": estado["horas"], "rastreado": estado["rastreado"],
                       "aviso": aviso}
            if estado["rastreado"]:
                servico.registrar_sessao(ident, estado["horas"])
                pos = _aviso_pos_sessao(servico, ident)
                if pos:
                    detalhe["aviso"] = pos
            else:
                detalhe["aviso"] = ("Sessão sem rastreio: registre as horas nas "
                                    "ferramentas clássicas.")
            return detalhe

        return {"trabalho": self.trabalhos.iniciar(f"Jogar {titulo}", tarefa, escopo="jogo")}

    def _musicas_importar(self, servico, params) -> dict:
        pasta = params.get("pasta")
        if not isinstance(pasta, str) or not pasta.strip():
            raise ValueError("pasta deve ser um caminho de texto")
        pasta = pasta.strip()
        rotulo = "Importar músicas: " + (Path(pasta).name or pasta)

        def tarefa(progresso, cancelado):
            resultado = servico.importar_musicas(pasta)
            detalhe = dict(resultado) if isinstance(resultado, dict) else {}
            detalhe["aviso"] = (f'{detalhe.get("novos", 0)} nova(s), '
                                f'{detalhe.get("ignorados", 0)} ignorada(s).')
            return detalhe

        return {"trabalho": self.trabalhos.iniciar(rotulo, tarefa, escopo="musicas")}

    def _musicas_baixar_fila(self, servico, params) -> dict:
        def tarefa(progresso, cancelado):
            def cb(dados):
                # `baixar_musicas` chama o progresso com um dict {pct, rotulo, id}.
                if isinstance(dados, dict):
                    progresso(dados.get("pct", 0))
                else:
                    progresso(dados)

            resultado = servico.baixar_musicas(cancelado, cb)
            detalhe = dict(resultado) if isinstance(resultado, dict) else {}
            novas = detalhe.get("novas", 0)
            erros = [str(e) for e in (detalhe.get("erros") or [])]
            if cancelado.is_set():
                detalhe["aviso"] = f"Download cancelado. {novas} nova(s) até aqui."
            else:
                aviso = f"{novas} nova(s) baixada(s)."
                if erros:
                    aviso += " " + erros[0] + (f" (+{len(erros) - 1})" if len(erros) > 1 else "")
                detalhe["aviso"] = aviso
            return detalhe

        return {"trabalho": self.trabalhos.iniciar("Baixar fila de músicas", tarefa,
                                                    cancelavel=True, escopo="musicas")}

    def _jogo_registrar_horas(self, servico, params) -> dict:
        ident = _inteiro(params, "id")
        horas = params.get("horas")
        if isinstance(horas, bool) or not isinstance(horas, (int, float)):
            raise ValueError("horas deve ser um número")
        horas = float(horas)
        if not math.isfinite(horas) or horas <= 0:
            raise ValueError("horas deve ser maior que zero")
        return servico.registrar_sessao(ident, horas)

    def despachar(self, metodo: str, params=None) -> dict:
        if params is None:
            params = {}
        if not isinstance(params, dict):
            return {"ok": False, "erro": "params deve ser um objeto JSON"}
        tarefa = self.metodos.get(metodo)
        if tarefa is None:
            return {"ok": False, "erro": f"método desconhecido: {metodo}"}
        try:
            return {"ok": True, "resultado": tarefa(self.servico, params)}
        except Exception as erro:  # erro de método não derruba a ponte
            return {"ok": False, "erro": str(erro) or type(erro).__name__}

    def executar_linha(self, linha: str) -> str | None:
        """Processa uma linha; devolve a resposta serializada (ou None se vazia)."""
        if not linha.strip():
            return None
        try:
            pedido = json.loads(linha)
        except ValueError:
            pedido = None
        if not isinstance(pedido, dict):
            return json.dumps({"id": None, "ok": False, "erro": "JSON inválido"},
                              ensure_ascii=False)
        metodo = pedido.get("metodo")
        resposta = self.despachar(metodo if isinstance(metodo, str) else "",
                                  pedido.get("params"))
        resposta = {"id": pedido.get("id"), **resposta}
        return json.dumps(resposta, ensure_ascii=False, default=str)

    def servir(self, entrada, saida) -> None:
        self._saida = saida
        for linha in entrada:
            resposta = self.executar_linha(linha)
            if resposta is None:
                continue
            with self._escrita:
                saida.write(resposta + "\n")
                saida.flush()


def _parse(argv):
    ap = argparse.ArgumentParser(prog="ponte", description="Ponte NDJSON do TucoTeca")
    ap.add_argument("--db", help="caminho do banco (padrão: o da instalação)")
    ap.add_argument("--ignorar-lock", action="store_true",
                    help="sobrescreve lock antigo (após crash)")
    return ap.parse_args(argv)


def iniciar(argv=None, entrada=None, saida=None, servico_factory=None) -> int:
    """Sobe a ponte. Retorna 0 no fim normal e 2 quando a coleção está ocupada."""
    args = _parse(argv)
    preparar_ambiente()
    if servico_factory is not None:  # testes em processo, sem lock nem disco real
        Ponte(servico_factory()).servir(entrada or sys.stdin, saida or sys.stdout)
        return 0
    import bib_core as core
    from servicos_ui import ServicoBiblioteca
    core.garantir_dirs()
    trava = core.adquirir_lock(ignorar=args.ignorar_lock)
    if not trava.get("ok"):
        evento = {"evento": "bloqueio",
                  "dados": {"erro": trava.get("erro", "TucoTeca já está aberto.")}}
        destino = saida or sys.stdout
        destino.write(json.dumps(evento, ensure_ascii=False) + "\n")
        destino.flush()
        return 2
    try:
        db = Path(args.db) if args.db else Path(core.DEFAULT_DB)
        Ponte(ServicoBiblioteca(db)).servir(entrada or sys.stdin, saida or sys.stdout)
        return 0
    finally:
        core.liberar_lock()


if __name__ == "__main__":
    raise SystemExit(iniciar(sys.argv[1:]))
