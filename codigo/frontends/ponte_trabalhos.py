"""Operações longas da ponte (trabalhos): thread própria, eventos e cancelamento."""
from __future__ import annotations

import threading
from datetime import datetime

from ponte_params import inteiro


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

    def iniciar(self, rotulo, funcao, cancelavel=False, escopo=None, grupo=None) -> dict:
        """`escopo`: um por vez (outro do mesmo escopo é recusado). `grupo`: só rótulo
        para a interface juntar (ex.: "download" aparece na tela Downloads)."""
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
                    "pct": None, "cancelavel": bool(cancelavel), "escopo": escopo, "grupo": grupo,
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
                # a operação costuma parar levantando ("Download cancelado."):
                # com a bandeira ligada foi o usuário que cancelou, não uma falha
                item["estado"] = "cancelado" if bandeira.is_set() else "erro"
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

    def limpar(self, grupo=None) -> int:
        """Tira da lista os trabalhos já terminados (do grupo, se informado)."""
        with self._travas:
            fim = [i for i, item in self._itens.items()
                   if item["estado"] not in ("rodando", "cancelando") and (grupo is None or item["grupo"] == grupo)]
            for i in fim:
                del self._itens[i]
        return len(fim)

    def cancelar(self, params) -> dict:
        ident = inteiro(params, "id")
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


def metodos_trabalhos(trabalhos) -> dict:
    return {
        "trabalhos.listar": lambda servico, params: trabalhos.listar(),
        "trabalhos.cancelar": lambda servico, params: trabalhos.cancelar(params),
        "trabalhos.limpar": lambda servico, params: {"removidos": trabalhos.limpar(params.get("grupo") or None)},
    }


__all__ = ["Trabalhos", "metodos_trabalhos"]
