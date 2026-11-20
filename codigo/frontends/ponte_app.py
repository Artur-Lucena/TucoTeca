"""Métodos da ponte do app em si: notificações que ficam e verificar/baixar atualização."""
from __future__ import annotations

from ponte_params import objeto, texto


def _registrar(servico, params) -> list:
    avisos = params.get("avisos")
    if not isinstance(avisos, list) or len(avisos) > 50:
        raise ValueError("avisos deve ser uma lista (até 50)")
    return servico.avisos_registrar(avisos)


def metodos_app(trabalhos) -> dict:
    def baixar_atualizacao(servico, params) -> dict:
        instalador = objeto(params, "instalador")
        versao = str(params.get("versao") or "").strip()[:20]

        def tarefa(progresso, cancelado):
            r = servico.baixar_atualizacao(instalador, progresso, cancelado.is_set)
            r["aviso"] = (f"TucoTeca {versao} baixado. Abra em Configurações → Geral para instalar."
                          if versao else "Atualização baixada.")
            return r
        return {"trabalho": trabalhos.iniciar(f"Baixar TucoTeca {versao}".strip(), tarefa, cancelavel=True,
                                              escopo="atualizacao", grupo="download")}

    return {
        "avisos.listar": lambda servico, params: servico.avisos_listar(),
        "avisos.registrar": _registrar,
        "avisos.dispensar": lambda servico, params: servico.avisos_dispensar(texto(params, "id", maximo=200)),
        "avisos.limpar": lambda servico, params: servico.avisos_limpar(),
        "app.verificar_atualizacao": lambda servico, params: servico.verificar_atualizacao(),
        "app.baixar_atualizacao": baixar_atualizacao,
    }


__all__ = ["metodos_app"]
