"""Métodos da ponte do app em si: núcleo, preferências, aparência, backups e coleção."""
from __future__ import annotations

from ponte_params import texto


def _ping(servico, params) -> dict:
    from bib_nucleo import base
    from bib_nucleo.versao import versao_app
    return {"pong": True, "versao": versao_app(),
            "home": str(base.HOME_DIR), "db": str(getattr(servico, "db_path", ""))}


def _snapshot(servico, params) -> dict:
    partes = params.get("partes")
    if partes is None:
        return servico.snapshot()
    validas = ("jogos", "musicas", "desejos", "videos", "fila_musicas", "colecoes")
    if not isinstance(partes, list) or any(p not in validas for p in partes):
        raise ValueError("partes deve ser uma lista com: " + ", ".join(validas))
    return servico.snapshot(partes=partes)


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


def _trocar_perfil(servico, params) -> dict:
    nome = params.get("nome", "")
    if not isinstance(nome, str):
        raise ValueError("nome deve ser texto")
    return servico.trocar_perfil(nome)


def _salvar_filtro(servico, params) -> dict:
    filtro = params.get("filtro", "")
    ordem = params.get("ordem", "")
    if not isinstance(filtro, str) or not isinstance(ordem, str):
        raise ValueError("filtro e ordem devem ser texto")
    return servico.salvar_filtro(filtro, ordem)


def _abrir_ferramenta(servico, params) -> dict:
    tipo = params.get("tipo")
    if tipo not in ("imagens", "equalizadores", "videos"):
        raise ValueError("tipo deve ser imagens, equalizadores ou videos")
    nome = texto(params, "nome")
    caminho = params.get("caminho", "")
    if not isinstance(caminho, str):
        raise ValueError("caminho deve ser um texto")
    return servico.abrir_ferramenta_midia(tipo, nome.strip(), caminho)


def _definir_aparencia(servico, params) -> dict:
    tema = params.get("tema", "")
    densidade = params.get("densidade", "")
    auto_backup = params.get("auto_backup", None)
    if not isinstance(tema, str) or not isinstance(densidade, str):
        raise ValueError("tema e densidade devem ser texto")
    escala = params.get("escala_texto", None)
    if escala is not None and (isinstance(escala, bool) or not isinstance(escala, (int, float))):
        raise ValueError("escala_texto deve ser um número")
    return servico.definir_aparencia(tema, densidade, auto_backup, escala_texto=escala)


def _configurar_provedores(servico, params) -> dict:
    steam = params.get("steam", "")
    steamgrid = params.get("steamgrid", "")
    spotify_id = params.get("spotify_id", "")
    spotify_secret = params.get("spotify_secret", "")
    for v in (steam, steamgrid, spotify_id, spotify_secret):
        if not isinstance(v, str):
            raise ValueError("todos os campos devem ser texto")
    return servico.configurar_provedores(steam, steamgrid, spotify_id, spotify_secret)


def _backups(servico, params) -> dict:
    manter = params.get("manter", 10)
    if isinstance(manter, bool) or not isinstance(manter, int):
        raise ValueError("manter deve ser inteiro")
    return servico.backups(manter)


def _exportar_colecao(servico, params) -> dict:
    pasta = texto(params, "pasta")
    r = servico.exportar_colecao_para(pasta.strip())
    # o domínio devolve ok=false em vez de levantar: a interface diria "exportada"
    if isinstance(r, dict) and r.get("ok") is False:
        raise ValueError(r.get("erro") or "Não foi possível exportar a coleção.")
    return r


def _importar_colecao(servico, params) -> dict:
    caminho = texto(params, "caminho")
    restaurar_saves = bool(params.get("restaurar_saves", False))
    r = servico.importar_colecao(caminho.strip(), restaurar_saves)
    if isinstance(r, dict) and r.get("ok") is False:
        raise ValueError(r.get("erro") or "Não foi possível importar a coleção.")
    return r


def metodos_sistema(trabalhos) -> dict:
    return {
        "nucleo.ping": _ping,
        "nucleo.snapshot": _snapshot,
        "nucleo.revisao": lambda servico, params: servico.revisao(),
        "nucleo.buscar": _buscar,
        "nucleo.saude": lambda servico, params: servico.saude(),
        "modulos.listar": _modulos,
        "preferencias.ler": lambda servico, params: servico.preferencias(),
        "preferencias.trocar_perfil": _trocar_perfil,
        "preferencias.filtro": lambda servico, params: servico.filtro(),
        "preferencias.salvar_filtro": _salvar_filtro,
        "ferramentas.abrir": _abrir_ferramenta,
        "aparencia.ler": lambda servico, params: servico.aparencia(),
        "aparencia.salvar": _definir_aparencia,
        "provedores.configurar": _configurar_provedores,
        "estatisticas.ler": lambda servico, params: servico.estatisticas(),
        "backups.listar": _backups,
        "colecao.exportar": _exportar_colecao,
        "colecao.importar": _importar_colecao,
    }


__all__ = ["metodos_sistema"]
