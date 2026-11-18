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

from pathlib import Path

from ponte_params import ident, opcao, texto

_MSG_JOGO_ABERTO = ("Feche o jogo aberto antes de mudar mods, texturas, cheats, "
                    "presets, controles ou arquivos da coleção.")


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
        return servico.emulacao_jogo(ident(params))

    def emulacao_mod(servico, params):
        acao = opcao(params, "acao", ("alternar", "desligar_todos", "remover", "importar"))
        nome = texto(params, "nome", obrigatorio=acao in ("alternar", "remover"))
        arquivo = texto(params, "arquivo", obrigatorio=acao == "importar")
        return servico.emulacao_mod(ident(params), acao, nome, arquivo)

    def emulacao_cheat(servico, params):
        acao = opcao(params, "acao", ("alternar", "adicionar", "remover"))
        nome = texto(params, "nome")
        codigo = texto(params, "codigo", obrigatorio=acao == "adicionar")
        return servico.emulacao_cheat(ident(params), acao, nome, codigo)

    def emulacao_textura(servico, params):
        acao = opcao(params, "acao", ("alternar", "instalar"))
        arquivo = texto(params, "arquivo", obrigatorio=acao == "instalar")
        return servico.emulacao_textura(ident(params), acao, arquivo)

    def emulacao_preset(servico, params):
        acao = opcao(params, "acao", ("aplicar", "salvar"))
        return servico.emulacao_preset(acao, texto(params, "nome"))

    def emulacao_atualizar(servico, params):
        """Instala o release já consultado (rede + escrita) como trabalho."""
        chave = texto(params, "chave")
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
        r = servico.controle_fotografar(texto(params, "nome"))
        return {**dict(r), **servico.controles_presets()}

    def controles_aplicar(servico, params):
        return dict(servico.controle_aplicar(texto(params, "nome")))

    def controles_gerar(servico, params):
        r = servico.controle_gerar(texto(params, "tipo"))
        return {**dict(r), **servico.controles_presets()}

    def controles_estado(servico, params):
        return servico.controle_estado()

    # -- música: equalização (FFmpeg gera faixa nova) e volume do PC --------
    def musicas_eq_presets(servico, params):
        from bib_nucleo import apps_externos, baixar
        return {"presets": sorted(apps_externos.PRESETS_EQ), "ffmpeg": bool(baixar.ffmpeg_pronto())}

    def musicas_eq(servico, params):
        """Renderiza a faixa com o preset numa cópia nova (trabalho: pode passar de 30 s)."""
        from bib_nucleo import apps_externos
        caminho = texto(params, "caminho")
        preset = texto(params, "preset")
        if preset not in apps_externos.PRESETS_EQ:
            raise ValueError(f"preset deve ser um de: {', '.join(sorted(apps_externos.PRESETS_EQ))}")

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
        from bib_nucleo import volume as nucleo_volume
        # indisponível (ex.: fora do Windows) volta ok=false: a interface esconde o controle
        return dict(nucleo_volume.ler_volume_pc())

    def volume_definir(servico, params):
        from bib_nucleo import volume as nucleo_volume
        nivel = params.get("nivel")
        if isinstance(nivel, bool) or not isinstance(nivel, (int, float)):
            raise ValueError("nivel deve ser um número de 0 a 100")
        r = dict(nucleo_volume.definir_volume_pc(nivel))
        if not r.get("ok"):
            raise ValueError(r.get("erro") or "Volume do PC indisponível.")
        return r

    def volume_mudo(servico, params):
        from bib_nucleo import volume as nucleo_volume
        r = dict(nucleo_volume.alternar_mudo_pc())
        if not r.get("ok"):
            raise ValueError(r.get("erro") or "Volume do PC indisponível.")
        return r

    # -- manutenção de jogos (saneamento, religar, UAC, disco) ---------------
    def manutencao_plano(servico, params):
        """O que o saneamento faria na pasta. Só leitura."""
        return servico.sanear_plano(texto(params, "caminho"))

    def manutencao_sanear(servico, params):
        """Aplica o saneamento (instaladores vão para .hub-lixo, reversível)."""
        return dict(servico.sanear_pasta(texto(params, "caminho")))

    def jogo_religar(servico, params):
        campo = opcao(params, "campo", ("launch_options", "executable_path", "exe_win", "exe_linux"))
        servico.religar_jogo(ident(params), campo, texto(params, "caminho"))
        return servico.diagnosticar_jogo(ident(params))

    def jogo_jogar_elevado(servico, params):
        """Abre como administrador (UAC do Windows). Sem rastreio automático de
        horas: o núcleo abre uma sessão manual para registrar ao terminar."""
        return dict(servico.iniciar_jogo_elevado(ident(params)))

    # -- ferramentas de mídia externas (editores, equalizadores, players) ----
    def ferramentas_listar(servico, params):
        from bib_nucleo import apps_externos

        def lista(status):
            return [{"chave": chave, **{k: v for k, v in dict(info).items() if k != "exe"}}
                    for chave, info in status().items()]
        return {"imagens": lista(apps_externos.status_editores),
                "equalizadores": lista(apps_externos.status_equalizadores),
                "videos": lista(apps_externos.status_reprodutores)}

    # -- importar por arrastar e soltar: prévia → seleção → importação -------
    def jogos_prever(servico, params):
        """Prévia só-leitura: pasta varre PC+ROMs; arquivo é classificado."""
        caminho = texto(params, "caminho")
        if Path(caminho).is_dir():
            r = servico.prever_pasta(caminho)
            return {"ok": bool(r.get("ok")), "itens": list(r.get("itens") or []),
                    "erro": r.get("erro", ""), "avisos": []}
        r = servico.analisar_arquivo(caminho)
        item = r.get("item")
        avisos = [r["aviso"]] if r.get("aviso") else []
        if not r.get("ok") or not isinstance(item, dict):
            return {"ok": False, "itens": [], "avisos": avisos,
                    "erro": r.get("detalhe") or "Não reconheci este arquivo como jogo ou ROM."}
        return {"ok": True, "itens": [dict(item)], "erro": "", "avisos": avisos}

    def jogos_importar_selecionados(servico, params):
        itens = params.get("itens")
        if not isinstance(itens, list) or not all(isinstance(i, dict) for i in itens):
            raise ValueError("itens deve ser uma lista de objetos")
        return servico.importar_selecionados(itens)

    # -- coleção: backup manual, sessões abertas e erros recentes -----------
    def colecao_backup(servico, params):
        return servico.fazer_backup_agora()

    def sessoes_listar(servico, params):
        """Sessões manuais abertas (ex.: jogo aberto como administrador)."""
        return [{"arquivo": str(s.get("_arquivo", "")), "gid": s.get("gid"),
                 "titulo": str(s.get("titulo") or ""), "inicio": str(s.get("inicio") or "")}
                for s in servico.sessoes() if s.get("_arquivo")]

    def sessoes_encerrar(servico, params):
        horas = params.get("horas")
        if isinstance(horas, bool) or not isinstance(horas, (int, float)):
            raise ValueError("horas deve ser um número")
        return dict(servico.encerrar_sessao(texto(params, "arquivo"), float(horas)))

    def sistema_erros(servico, params):
        linhas = params.get("linhas", 40)
        if isinstance(linhas, bool) or not isinstance(linhas, int) or not 1 <= linhas <= 500:
            raise ValueError("linhas deve ser um inteiro de 1 a 500")
        return {"texto": servico.log_cauda(linhas)}

    # -- saves do jogo: snapshot agora e restaurar --------------------------
    def saves_snapshot(servico, params):
        return dict(servico.backup_pos_sessao(ident(params)))

    def saves_restaurar(servico, params):
        return dict(servico.restaurar_saves(ident(params), texto(params, "caminho")))

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
        "manutencao.plano": manutencao_plano,
        "manutencao.sanear": sem_jogo_aberto(manutencao_sanear),
        "jogo.religar": sem_jogo_aberto(jogo_religar),
        "jogo.jogar_elevado": sem_jogo_aberto(jogo_jogar_elevado),
        "ferramentas.listar": ferramentas_listar,
        "jogos.prever": jogos_prever,
        "jogos.importar_selecionados": jogos_importar_selecionados,
        "colecao.backup": colecao_backup,
        "sessoes.listar": sessoes_listar,
        "sessoes.encerrar": sessoes_encerrar,
        "sistema.erros": sistema_erros,
        # snapshot e restauração mexem nos saves: nunca com o jogo aberto
        "saves.snapshot": sem_jogo_aberto(saves_snapshot),
        "saves.restaurar": sem_jogo_aberto(saves_restaurar),
    }
    return novos


__all__ = ["metodos_paridade"]
