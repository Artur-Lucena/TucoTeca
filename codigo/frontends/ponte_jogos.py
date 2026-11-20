"""Métodos da ponte dos jogos: ficha, sessão (jogar), conquistas, capas, saves e desejos."""
from __future__ import annotations

import math
import threading
from pathlib import Path

from ponte_params import inteiro, lista, objeto, texto


def _com_perfil(jogo):
    """Aplica o perfil ativo (favorito por pessoa) ao dicionário do jogo."""
    from bib_nucleo.preferencias_pessoais import aplicar_perfil
    return aplicar_perfil([jogo])[0]


def _jogo_ler(servico, params) -> dict:
    return _com_perfil(servico.jogo(inteiro(params, "id")))


def _jogo_salvar(servico, params) -> dict:
    dados = params.get("dados", {})
    if not isinstance(dados, dict):
        raise ValueError("dados deve ser um objeto JSON")
    ident = params.get("id")
    if ident is not None:
        ident = inteiro(params, "id")
    return _com_perfil(servico.salvar_jogo(ident, dados))


def _jogo_favoritar(servico, params) -> dict:
    ident = inteiro(params, "id")
    servico.favorito(ident)
    return _com_perfil(servico.jogo(ident))


def _jogo_observacoes(servico, params) -> dict:
    ident = inteiro(params, "id")
    valor = params.get("texto", "")
    if not isinstance(valor, str):
        raise ValueError("texto deve ser texto")
    return _com_perfil(servico.salvar_observacoes(ident, valor))


def _item_excluir(servico, params) -> dict:
    categoria = params.get("categoria", "")
    if categoria not in ("jogos", "desejos", "videos", "musicas"):
        raise ValueError("categoria deve ser jogos, desejos, videos ou musicas")
    return servico.excluir(categoria, inteiro(params, "id"))


def _desejos_adicionar(servico, params) -> dict:
    titulo = params.get("titulo")
    appid = params.get("appid")
    if not isinstance(titulo, str) or not titulo.strip():
        raise ValueError("titulo deve ser um texto não vazio")
    if isinstance(appid, bool) or not isinstance(appid, (str, int)):
        raise ValueError("appid deve ser o número da loja")
    appid = str(appid).strip()
    if not appid.isdigit() or len(appid) > 20:
        raise ValueError("appid deve ser um número")
    return servico.adicionar_desejo(appid, titulo.strip())


def _desejos_precos(servico, params) -> dict:
    regiao = params.get("regiao", "")
    if not isinstance(regiao, str):
        raise ValueError("regiao deve ser um texto")
    return servico.precos_desejos(regiao)


def _conquistas_sincronizar(servico, params) -> dict:
    ident = inteiro(params, "id")
    appid = params.get("appid", "")
    if not isinstance(appid, str):
        raise ValueError("appid deve ser um texto")
    save = params.get("save", "")
    if not isinstance(save, str):
        raise ValueError("save deve ser um texto")
    return servico.sincronizar_conquistas(ident, appid, save)


def _conquistas_regras(servico, params) -> dict:
    ident = inteiro(params, "id")
    valor = params.get("texto", "")
    if not isinstance(valor, str):
        raise ValueError("texto deve ser um texto")
    return servico.regras_conquistas(ident, valor)


def _categoria_capa(params) -> str:
    categoria = params.get("categoria")
    if categoria not in ("jogos", "musicas", "desejos"):
        raise ValueError("categoria deve ser jogos, musicas ou desejos")
    return categoria


def _capas_buscar(servico, params) -> dict:
    categoria = _categoria_capa(params)
    ident = inteiro(params, "id")
    provedor = params.get("provedor", "")
    if not isinstance(provedor, str):
        raise ValueError("provedor deve ser um texto")
    atualizar = bool(params.get("atualizar", False))
    return servico.buscar_capas(categoria, ident, provedor, atualizar)


def _capas_aplicar(servico, params) -> dict:
    categoria = _categoria_capa(params)
    ident = inteiro(params, "id")
    candidato = objeto(params, "candidato")
    return servico.aplicar_capa(categoria, ident, candidato)


def _jogo_registrar_horas(servico, params) -> dict:
    ident = inteiro(params, "id")
    horas = params.get("horas")
    if isinstance(horas, bool) or not isinstance(horas, (int, float)):
        raise ValueError("horas deve ser um número")
    horas = float(horas)
    if not math.isfinite(horas) or horas <= 0:
        raise ValueError("horas deve ser maior que zero")
    return servico.registrar_sessao(ident, horas)


def _aviso_pos_sessao(servico, ident) -> str:
    """Backup pós-sessão opt-in (default ligado); falha vira aviso."""
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


def metodos_jogos(trabalhos) -> dict:
    def jogar(servico, params) -> dict:
        ident = inteiro(params, "id")
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
                detalhe["aviso"] = ("Sessão sem rastreio automático: registre as horas "
                                    "no detalhe do jogo (Registrar horas).")
            return detalhe

        return {"trabalho": trabalhos.iniciar(f"Jogar {titulo}", tarefa, escopo="jogo")}

    def importar(servico, params) -> dict:
        pasta = texto(params, "pasta").strip()

        def tarefa(progresso, cancelado):
            if cancelado.is_set():
                raise ValueError("Importação cancelada.")
            progresso(10)
            resultado = servico.importar_jogos(pasta)
            progresso(100)
            detalhe = dict(resultado) if isinstance(resultado, dict) else {}
            detalhe.setdefault("aviso", "Jogos importados.")
            return detalhe

        titulo = Path(pasta).name or "pasta"
        return {"trabalho": trabalhos.iniciar(f"Importar jogos {titulo}", tarefa, escopo="jogos")}

    return {
        "jogo.ler": _jogo_ler,
        "jogo.salvar": _jogo_salvar,
        "jogo.favoritar": _jogo_favoritar,
        "jogo.observacoes": _jogo_observacoes,
        "jogo.jogar": jogar,
        "jogo.registrar_horas": _jogo_registrar_horas,
        "jogo.diagnosticar": lambda servico, params: servico.diagnosticar_jogo(inteiro(params, "id")),
        "jogo.disco": lambda servico, params: servico.disco_jogo(inteiro(params, "id")),
        "jogos.importar": importar,
        "item.excluir": _item_excluir,
        "item.desfazer": lambda servico, params: servico.desfazer_exclusao(),
        "lixeira.estado": lambda servico, params: servico.lixeira(),
        "desejos.adicionar": _desejos_adicionar,
        "desejos.precos": _desejos_precos,
        "desejos.sincronizar_steam": lambda servico, params: servico.sincronizar_desejos_steam(),
        "desejos.importar_wishlist": lambda servico, params: servico.importar_wishlist(
            texto(params, "caminho").strip()),
        "desejos.buscar_fontes": lambda servico, params: servico.buscar_fontes_desejo(
            texto(params, "titulo").strip()),
        "conquistas.avaliar": lambda servico, params: servico.avaliar_conquistas(inteiro(params, "id")),
        "conquistas.sincronizar": _conquistas_sincronizar,
        "conquistas.regras": _conquistas_regras,
        "capas.buscar": _capas_buscar,
        "capas.aplicar": _capas_aplicar,
        "capas.libretro": lambda servico, params: servico.buscar_capa_libretro(inteiro(params, "id")),
        "emulacao.status": lambda servico, params: servico.emus_status(),
        "emulacao.consultar": lambda servico, params: servico.emu_consultar(texto(params, "chave").strip()),
        "ferramentas.jogo": lambda servico, params: servico.ferramentas_jogo(inteiro(params, "id")),
        "saves.configurar": lambda servico, params: servico.configurar_saves(
            inteiro(params, "id"), lista(params, "caminhos")),
    }


__all__ = ["metodos_jogos"]
