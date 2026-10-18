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

A ponte nunca morre por erro de chamada: JSON inválido, método desconhecido e
exceção de serviço viram resposta ok=false. Contrato provado por
`codigo/ferramentas/testes/test_ponte.py`.
"""
from __future__ import annotations

import argparse
import json
import sys
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


METODOS = {
    "nucleo.ping": _ping,
    "nucleo.snapshot": _snapshot,
    "modulos.listar": _modulos,
}


class Ponte:
    """Despachante NDJSON: cada linha vira uma resposta serializada."""

    def __init__(self, servico, metodos=None):
        self.servico = servico
        self.metodos = dict(METODOS if metodos is None else metodos)

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
        for linha in entrada:
            resposta = self.executar_linha(linha)
            if resposta is None:
                continue
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
