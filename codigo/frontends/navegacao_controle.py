"""Controle XInput no desktop: estados viram ações e o direcional repete ao ser segurado."""
from __future__ import annotations

import time

LIMIAR_ANALOGICO = 16000
ATRASO_REPETICAO = 0.45
INTERVALO_REPETICAO = 0.12
REPETIVEIS = frozenset({"cima", "baixo", "esquerda", "direita"})
BOTOES = {0: "cima", 1: "baixo", 2: "esquerda", 3: "direita", 4: "menu",
          8: "anterior", 9: "proxima", 12: "confirmar", 13: "voltar"}


def acoes_do_estado(estado: dict | None) -> frozenset[str]:
    if not estado:
        return frozenset()
    acoes = {BOTOES[b] for b in estado.get("botoes") or () if b in BOTOES}
    lx, ly = int(estado.get("lx") or 0), int(estado.get("ly") or 0)
    if ly >= LIMIAR_ANALOGICO:
        acoes.add("cima")
    elif ly <= -LIMIAR_ANALOGICO:
        acoes.add("baixo")
    if lx <= -LIMIAR_ANALOGICO:
        acoes.add("esquerda")
    elif lx >= LIMIAR_ANALOGICO:
        acoes.add("direita")
    return frozenset(acoes)


class Navegador:
    def __init__(self, relogio=time.monotonic):
        self._relogio = relogio
        self._antes: frozenset[str] = frozenset()
        self._proxima: dict[str, float] = {}
        self._aguarda_neutro = False

    def bloquear_ate_neutro(self):
        """Conexão/retorno de foco não transforma botão já segurado em clique."""
        self._antes = frozenset()
        self._proxima.clear()
        self._aguarda_neutro = True

    def atualizar(self, acoes) -> list[str]:
        agora, atuais = self._relogio(), frozenset(acoes)
        if self._aguarda_neutro:
            if not atuais:
                self._aguarda_neutro = False
            return []
        novas = sorted(atuais - self._antes)
        saida = list(novas)
        for acao in novas:
            if acao in REPETIVEIS:
                self._proxima[acao] = agora + ATRASO_REPETICAO
        for acao in list(self._proxima):
            if acao not in atuais:
                del self._proxima[acao]
            elif acao not in novas and agora >= self._proxima[acao]:
                saida.append(acao)
                self._proxima[acao] = agora + INTERVALO_REPETICAO
        self._antes = atuais
        return saida
