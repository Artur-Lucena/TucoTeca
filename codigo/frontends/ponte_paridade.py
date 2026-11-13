#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Métodos da ponte que devolvem ao desktop Electron o que o antigo Qt fazia.

Separados de `ponte.py` para manter o despachante enxuto. Cada método valida
os parâmetros e delega a `servicos_ui`; nenhuma regra de domínio mora aqui.
Ações que mexem em arquivos do emulador ou da coleção recusam com um jogo
aberto (mesma trava do Qt: "feche o jogo antes"). Confirmações de ações
destrutivas ficam na interface, antes da chamada.
"""
from __future__ import annotations

_MSG_JOGO_ABERTO = ("Feche o jogo aberto antes de mudar mods, texturas, cheats, "
                    "presets, controles ou arquivos da coleção.")


def _texto(params, chave, obrigatorio=True) -> str:
    valor = params.get(chave, "")
    if not isinstance(valor, str):
        raise ValueError(f"{chave} deve ser um texto")
    valor = valor.strip()
    if obrigatorio and not valor:
        raise ValueError(f"{chave} deve ser um texto")
    return valor


def _id(params) -> int:
    valor = params.get("id")
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise ValueError("id deve ser um inteiro positivo")
    return valor


def _opcao(params, chave, opcoes) -> str:
    valor = params.get(chave)
    if valor not in opcoes:
        raise ValueError(f"{chave} deve ser um de: {', '.join(opcoes)}")
    return valor


def metodos_paridade(trabalhos) -> dict:
    """Mapa nome → handler(servico, params).

    `trabalhos` (o `Trabalhos` da ponte) dá a trava de jogo aberto e roda as
    operações longas (download/instalação) fora do tempo limite de 30 s do
    pedido NDJSON, com progresso no rodapé do app.
    """

    def jogo_aberto() -> bool:
        return any(t.get("escopo") == "jogo" and t.get("estado") in ("rodando", "cancelando")
                   for t in trabalhos.listar())

    def sem_jogo_aberto(handler):
        def protegido(servico, params):
            if jogo_aberto():
                raise ValueError(_MSG_JOGO_ABERTO)
            return handler(servico, params)
        protegido.__name__ = handler.__name__
        return protegido

    # -- emulação por jogo (3DS/Azahar) ------------------------------------
    def emulacao_jogo(servico, params):
        return servico.emulacao_jogo(_id(params))

    def emulacao_mod(servico, params):
        acao = _opcao(params, "acao", ("alternar", "desligar_todos", "remover", "importar"))
        nome = _texto(params, "nome", obrigatorio=acao in ("alternar", "remover"))
        arquivo = _texto(params, "arquivo", obrigatorio=acao == "importar")
        return servico.emulacao_mod(_id(params), acao, nome, arquivo)

    def emulacao_cheat(servico, params):
        acao = _opcao(params, "acao", ("alternar", "adicionar", "remover"))
        nome = _texto(params, "nome")
        codigo = _texto(params, "codigo", obrigatorio=acao == "adicionar")
        return servico.emulacao_cheat(_id(params), acao, nome, codigo)

    def emulacao_textura(servico, params):
        acao = _opcao(params, "acao", ("alternar", "instalar"))
        arquivo = _texto(params, "arquivo", obrigatorio=acao == "instalar")
        return servico.emulacao_textura(_id(params), acao, arquivo)

    def emulacao_preset(servico, params):
        acao = _opcao(params, "acao", ("aplicar", "salvar"))
        return servico.emulacao_preset(acao, _texto(params, "nome"))

    def emulacao_atualizar(servico, params):
        """Instala o release já consultado (rede + escrita) como trabalho."""
        chave = _texto(params, "chave")
        info = params.get("info")
        if not isinstance(info, dict) or not info.get("tag"):
            raise ValueError("Consulte o release antes de atualizar.")

        def tarefa(progresso, cancelado):
            progresso(5)
            r = servico.emu_atualizar(chave, info)
            detalhe = dict(r) if isinstance(r, dict) else {}
            detalhe.setdefault("aviso", f"{chave} atualizado para {info.get('tag')}.")
            return detalhe

        return {"trabalho": trabalhos.iniciar(f"Atualizar emulador {chave}", tarefa,
                                              escopo="emulador")}

    # -- controles/pads (perfis [Controls] do Azahar) -----------------------
    def controles_listar(servico, params):
        """Pads detectados, presets salvos e tipos para gerar mapa. Só leitura."""
        return {**servico.controles_pads(), **servico.controles_presets(),
                **servico.controles_tipos()}

    def controles_fotografar(servico, params):
        r = servico.controle_fotografar(_texto(params, "nome"))
        return {**dict(r), **servico.controles_presets()}

    def controles_aplicar(servico, params):
        return dict(servico.controle_aplicar(_texto(params, "nome")))

    def controles_gerar(servico, params):
        r = servico.controle_gerar(_texto(params, "tipo"))
        return {**dict(r), **servico.controles_presets()}

    def controles_estado(servico, params):
        return servico.controle_estado()

    # -- música: equalização (FFmpeg gera faixa nova) e volume do PC --------
    def musicas_eq_presets(servico, params):
        import bib_core as core
        return {"presets": sorted(core.PRESETS_EQ), "ffmpeg": bool(core.ffmpeg_pronto())}

    def musicas_eq(servico, params):
        """Renderiza a faixa com o preset numa cópia nova (trabalho: pode passar de 30 s)."""
        import bib_core as core
        caminho = _texto(params, "caminho")
        preset = _texto(params, "preset")
        if preset not in core.PRESETS_EQ:
            raise ValueError(f"preset deve ser um de: {', '.join(sorted(core.PRESETS_EQ))}")

        def tarefa(progresso, cancelado):
            progresso(5)
            r = servico.aplicar_eq_musica(caminho, preset)
            detalhe = dict(r) if isinstance(r, dict) else {}
            detalhe.setdefault("aviso", f"Cópia equalizada ({preset}) adicionada às músicas.")
            return detalhe

        nome = caminho.replace("\\", "/").rsplit("/", 1)[-1]
        return {"trabalho": trabalhos.iniciar(f"Equalizar {nome} ({preset})", tarefa,
                                              escopo="equalizacao")}

    def volume_ler(servico, params):
        import bib_core as core
        # indisponível (ex.: fora do Windows) volta ok=false: a interface esconde o controle
        return dict(core.ler_volume_pc())

    def volume_definir(servico, params):
        import bib_core as core
        nivel = params.get("nivel")
        if isinstance(nivel, bool) or not isinstance(nivel, (int, float)):
            raise ValueError("nivel deve ser um número de 0 a 100")
        r = dict(core.definir_volume_pc(nivel))
        if not r.get("ok"):
            raise ValueError(r.get("erro") or "Volume do PC indisponível.")
        return r

    def volume_mudo(servico, params):
        import bib_core as core
        r = dict(core.alternar_mudo_pc())
        if not r.get("ok"):
            raise ValueError(r.get("erro") or "Volume do PC indisponível.")
        return r

    novos = {
        "emulacao.jogo": emulacao_jogo,
        "emulacao.mod": sem_jogo_aberto(emulacao_mod),
        "emulacao.cheat": sem_jogo_aberto(emulacao_cheat),
        "emulacao.textura": sem_jogo_aberto(emulacao_textura),
        "emulacao.preset": sem_jogo_aberto(emulacao_preset),
        # substitui a versão síncrona de ponte.py (estourava o limite de 30 s)
        "emulacao.atualizar": sem_jogo_aberto(emulacao_atualizar),
        "controles.listar": controles_listar,
        "controles.fotografar": controles_fotografar,
        # aplicar sobrescreve o perfil ativo do Azahar: nunca com jogo aberto
        "controles.aplicar": sem_jogo_aberto(controles_aplicar),
        "controles.gerar": controles_gerar,
        "controles.estado": controles_estado,
        "musicas.eq_presets": musicas_eq_presets,
        # substitui a versão síncrona de ponte.py (FFmpeg em faixa longa > 30 s)
        "musicas.eq": musicas_eq,
        "sistema.volume": volume_ler,
        "sistema.volume_definir": volume_definir,
        "sistema.volume_mudo": volume_mudo,
    }
    return novos


__all__ = ["metodos_paridade"]
