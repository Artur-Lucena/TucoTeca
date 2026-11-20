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

Este arquivo só tem o protocolo; os métodos ficam em `ponte_<assunto>.py`,
cada um com uma função `metodos_<assunto>(trabalhos) -> dict` (ver MODULOS).
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
from pathlib import Path

# No app instalado o Python embutido (._pth) NÃO põe a pasta do script no
# sys.path; os módulos irmãos (ponte_*.py) precisam dela já no import, antes
# de preparar_ambiente().
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from ponte_trabalhos import Trabalhos  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]

# (módulo, função) de cada assunto; import tardio porque no app instalado o
# sys.path só fica pronto em preparar_ambiente().
MODULOS = (
    ("ponte_trabalhos", "metodos_trabalhos"),
    ("ponte_sistema", "metodos_sistema"),
    ("ponte_jogos", "metodos_jogos"),
    ("ponte_downloads", "metodos_downloads"),
    ("ponte_musica_video", "metodos_musica_video"),
    ("ponte_fontes", "metodos_fontes"),
    ("ponte_paridade", "metodos_paridade"),
    ("ponte_dominios", "metodos_meta"),
    ("ponte_dominios", "metodos_colecoes"),
    ("ponte_dominios", "metodos_midia"),
)


def preparar_ambiente() -> None:
    """Mesmo ambiente do checkout (`abrir_hub.preparar`): home, runtime e sys.path."""
    for caminho in (str(RAIZ / "codigo/frontends"), str(RAIZ / "codigo")):
        if caminho not in sys.path:
            sys.path.insert(0, caminho)
    from ferramentas import abrir_hub
    abrir_hub.preparar()


def todos_os_metodos(trabalhos) -> dict:
    import importlib
    metodos: dict = {}
    for modulo, funcao in MODULOS:
        metodos.update(getattr(importlib.import_module(modulo), funcao)(trabalhos))
    return metodos


class Ponte:
    """Despachante NDJSON: cada linha vira uma resposta serializada."""

    def __init__(self, servico, metodos=None, trabalhos=None):
        self.servico = servico
        self._escrita = threading.RLock()
        self._saida = None
        self.trabalhos = trabalhos if trabalhos is not None else Trabalhos(self._publicar_evento)
        self.metodos = {**todos_os_metodos(self.trabalhos), **(metodos or {})}

    def _publicar_evento(self, evento: dict) -> None:
        with self._escrita:
            if self._saida is None:
                return
            self._saida.write(json.dumps(evento, ensure_ascii=False, default=str) + "\n")
            self._saida.flush()
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
    from bib_nucleo import base
    from servicos_ui import ServicoBiblioteca
    base.garantir_dirs()
    trava = base.adquirir_lock(ignorar=args.ignorar_lock)
    if not trava.get("ok"):
        evento = {"evento": "bloqueio",
                  "dados": {"erro": trava.get("erro", "TucoTeca já está aberto.")}}
        destino = saida or sys.stdout
        destino.write(json.dumps(evento, ensure_ascii=False) + "\n")
        destino.flush()
        return 2
    try:
        db = Path(args.db) if args.db else Path(base.DEFAULT_DB)
        Ponte(ServicoBiblioteca(db)).servir(entrada or sys.stdin, saida or sys.stdout)
        return 0
    finally:
        base.liberar_lock()


if __name__ == "__main__":
    raise SystemExit(iniciar(sys.argv[1:]))
