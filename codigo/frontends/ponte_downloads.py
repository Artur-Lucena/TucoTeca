"""Métodos da ponte de lojas e downloads: integrações, torrents e pacotes baixados."""
from __future__ import annotations

from pathlib import Path

from ponte_params import texto


def _termo(params) -> str:
    termo = params.get("termo", "")
    if not isinstance(termo, str):
        raise ValueError("termo deve ser um texto")
    return termo


def _integracoes_adicionar(servico, params) -> dict:
    dados = params.get("dados")
    if not isinstance(dados, dict):
        raise ValueError("dados deve ser um objeto com chave, nome, tipo e url")
    return servico.adicionar_integracao(dados)


def _integracoes_remover(servico, params) -> dict:
    chave = texto(params, "chave").strip()
    servico.remover_integracao(chave)
    return {"ok": True, "chave": chave}


def _integracoes_url(servico, params) -> dict:
    chave = texto(params, "chave")
    return {"url": servico.url_integracao(chave.strip(), _termo(params))}


def _integracoes_buscar(servico, params) -> dict:
    chave = texto(params, "chave")
    return servico.integracoes.buscar(chave.strip(), _termo(params))


def _fora_destino(servico, caminho) -> bool:
    """Download fora da pasta de jogos (candidato a "Organizar"); erro = False."""
    if not caminho:
        return False
    try:
        return bool(servico.fora_do_destino(caminho))
    except Exception:
        return False


def _torrents_listar(servico, params) -> dict:
    leitura = servico.listar_torrents()
    torrents = leitura.get("torrents") if isinstance(leitura, dict) else []
    erros = list(leitura.get("erros") or []) if isinstance(leitura, dict) else []
    itens = []
    for t in (torrents or []):
        if not isinstance(t, dict):
            continue
        try:
            pct = float(t.get("pct", 0) or 0)
        except (TypeError, ValueError):
            pct = 0.0
        pct = min(max(pct, 0.0), 100.0)
        completo = bool(t.get("completo"))
        itens.append({
            "hash": t.get("hash", ""),
            "nome": t.get("nome", ""),
            "estado": "completo" if completo else "baixando",
            "pct": round(pct, 1),
            "feito": t.get("feito", 0),
            "total": t.get("total", 0),
            "fonte_progresso": t.get("fonte_progresso", ""),
            "velocidade": t.get("velocidade", 0),
            "eta": t.get("eta", None),
            "save_path": t.get("save_path", ""),
            "fora_destino": _fora_destino(servico, t.get("save_path", "")),
        })
    return {"itens": itens, "erros": erros}


def _torrents_controlar(servico, params) -> dict:
    ident = params.get("ident")
    acao = params.get("acao")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("ident deve ser o hash do torrent")
    if acao not in ("pausar", "retomar", "remover"):
        raise ValueError("acao deve ser pausar, retomar ou remover")
    return servico.torrent_controlar(ident.strip(), acao)


def _pacotes_importar(servico, params) -> dict:
    pasta = texto(params, "pasta")
    exe = params.get("exe", "")
    if not isinstance(exe, str):
        raise ValueError("exe deve ser um texto")
    return servico.importar_pacote(pasta.strip(), exe)


def metodos_downloads(trabalhos) -> dict:
    def torrents_importar(servico, params) -> dict:
        caminho = texto(params, "caminho").strip()

        def tarefa(progresso, cancelado):
            if cancelado.is_set():
                raise ValueError("Importação cancelada.")
            progresso(10)
            resultado = servico.importar_torrent(caminho)
            progresso(100)
            detalhe = dict(resultado) if isinstance(resultado, dict) else {}
            detalhe.setdefault("aviso", "Download importado.")
            return detalhe

        titulo = Path(caminho).name or "download"
        return {"trabalho": trabalhos.iniciar(f"Importar download {titulo}", tarefa, escopo="torrents")}

    return {
        "integracoes.listar": lambda servico, params: servico.integracoes.listar(),
        "integracoes.adicionar": _integracoes_adicionar,
        "integracoes.remover": _integracoes_remover,
        "integracoes.url": _integracoes_url,
        "integracoes.buscar": _integracoes_buscar,
        "torrents.listar": _torrents_listar,
        "torrents.controlar": _torrents_controlar,
        "torrents.limpar_concluidos": lambda servico, params: servico.limpar_torrents_concluidos(),
        "torrents.organizar": lambda servico, params: servico.organizar_download(
            texto(params, "caminho").strip()),
        "torrents.importar": torrents_importar,
        "pacotes.importar": _pacotes_importar,
        "pacotes.abrir_instalador": lambda servico, params: servico.abrir_instalador_pacote(
            texto(params, "exe").strip()),
    }


__all__ = ["metodos_downloads"]
