"""Métodos da ponte para as fontes de download (formato do Hydra).

Cadastrar/atualizar uma fonte baixa uma lista que pode passar de 20 MB e o
download direto de um jogo leva minutos: os dois rodam como trabalho (com
progresso no rodapé). Buscar é local (cache) e entregar um magnet ao
qBittorrent é imediato.
"""
from __future__ import annotations

from ponte_params import texto


def metodos_fontes(trabalhos) -> dict:
    def listar(servico, params):
        return servico.fontes_listar()

    def adicionar(servico, params):
        url = texto(params, "url", maximo=2000).strip()

        def tarefa(progresso, cancelado):
            progresso(10)
            fonte = servico.fontes_adicionar(url)
            progresso(100)
            return {"fonte": fonte, "aviso": f"Fonte “{fonte['nome']}” adicionada ({fonte['total']} downloads)."}
        return {"trabalho": trabalhos.iniciar("Adicionar fonte de download", tarefa, escopo="fontes")}

    def atualizar(servico, params):
        ident = str(params.get("id") or "").strip()

        def tarefa(progresso, cancelado):
            progresso(10)
            r = servico.fontes_atualizar(ident)
            progresso(100)
            aviso = f"{r['atualizadas']} fonte(s) atualizada(s)."
            return {**r, "aviso": aviso + (f" Falhas: {'; '.join(r['erros'])}" if r["erros"] else "")}
        return {"trabalho": trabalhos.iniciar("Atualizar fontes de download", tarefa, escopo="fontes")}

    def remover(servico, params):
        return servico.fontes_remover(texto(params, "id", maximo=32))

    def buscar(servico, params):
        return servico.fontes_buscar(texto(params, "titulo", maximo=300))

    def baixar(servico, params):
        uri = texto(params, "uri", maximo=8000).strip()
        titulo = texto(params, "titulo", maximo=300).strip()
        if uri.startswith("magnet:?"):
            return servico.baixar_da_fonte(uri, titulo)
        if not uri.startswith("https://"):
            raise ValueError("uri deve ser magnet: ou https://")

        def tarefa(progresso, cancelado):
            return servico.baixar_da_fonte(uri, titulo, progresso, cancelado.is_set)
        return {"trabalho": trabalhos.iniciar(f"Baixar {titulo}", tarefa, cancelavel=True, grupo="download")}

    return {
        "fontes.listar": listar,
        "fontes.adicionar": adicionar,
        "fontes.atualizar": atualizar,
        "fontes.remover": remover,
        "fontes.buscar": buscar,
        "fontes.baixar": baixar,
    }


__all__ = ["metodos_fontes"]
