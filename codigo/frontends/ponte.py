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
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import threading
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def preparar_ambiente() -> None:
    """Mesmo ambiente do checkout (`abrir_hub.preparar`): home, runtime e sys.path."""
    for caminho in (str(RAIZ / "codigo/frontends"), str(RAIZ / "codigo")):
        if caminho not in sys.path:
            sys.path.insert(0, caminho)
    from ferramentas import abrir_hub
    abrir_hub.preparar()


def ler_versao() -> str:
    try:
        return (RAIZ / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def _ping(servico, params) -> dict:
    from bib_nucleo import base
    return {"pong": True, "versao": ler_versao(),
            "home": str(base.HOME_DIR), "db": str(getattr(servico, "db_path", ""))}


def _snapshot(servico, params) -> dict:
    return servico.snapshot()


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


def _preferencias(servico, params) -> dict:
    return servico.preferencias()


def _trocar_perfil(servico, params) -> dict:
    nome = params.get("nome", "")
    if not isinstance(nome, str):
        raise ValueError("nome deve ser texto")
    return servico.trocar_perfil(nome)


def _inteiro(params, chave) -> int:
    valor = params.get(chave)
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError(f"{chave} deve ser um inteiro")
    return valor


def _com_perfil(jogo):
    """Aplica o perfil ativo (favorito por pessoa) ao dicionário do jogo."""
    from bib_nucleo.preferencias_pessoais import aplicar_perfil
    return aplicar_perfil([jogo])[0]


def _saude(servico, params) -> dict:
    return servico.saude()


def _jogo_ler(servico, params) -> dict:
    return _com_perfil(servico.jogo(_inteiro(params, "id")))


def _jogo_salvar(servico, params) -> dict:
    dados = params.get("dados", {})
    if not isinstance(dados, dict):
        raise ValueError("dados deve ser um objeto JSON")
    ident = params.get("id")
    if ident is not None:
        ident = _inteiro(params, "id")
    return _com_perfil(servico.salvar_jogo(ident, dados))


def _jogo_favoritar(servico, params) -> dict:
    ident = _inteiro(params, "id")
    servico.favorito(ident)
    return _com_perfil(servico.jogo(ident))


def _jogo_observacoes(servico, params) -> dict:
    ident = _inteiro(params, "id")
    texto = params.get("texto", "")
    if not isinstance(texto, str):
        raise ValueError("texto deve ser texto")
    return _com_perfil(servico.salvar_observacoes(ident, texto))


def _item_excluir(servico, params) -> dict:
    categoria = params.get("categoria", "")
    if categoria not in ("jogos", "desejos", "videos", "musicas"):
        raise ValueError("categoria deve ser jogos, desejos, videos ou musicas")
    return servico.excluir(categoria, _inteiro(params, "id"))


def _item_desfazer(servico, params) -> dict:
    return servico.desfazer_exclusao()


def _lixeira_estado(servico, params) -> dict:
    return servico.lixeira()


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


def _integracoes_listar(servico, params) -> list:
    return servico.integracoes.listar()


def _integracoes_adicionar(servico, params) -> dict:
    dados = params.get("dados")
    if not isinstance(dados, dict):
        raise ValueError("dados deve ser um objeto com chave, nome, tipo e url")
    return servico.adicionar_integracao(dados)


def _integracoes_remover(servico, params) -> dict:
    chave = params.get("chave")
    if not isinstance(chave, str) or not chave.strip():
        raise ValueError("chave deve ser um texto")
    servico.remover_integracao(chave.strip())
    return {"ok": True, "chave": chave.strip()}


def _integracoes_url(servico, params) -> dict:
    chave = params.get("chave")
    if not isinstance(chave, str) or not chave.strip():
        raise ValueError("chave deve ser um texto")
    termo = params.get("termo", "")
    if not isinstance(termo, str):
        raise ValueError("termo deve ser um texto")
    return {"url": servico.url_integracao(chave.strip(), termo)}


def _integracoes_buscar(servico, params) -> dict:
    chave = params.get("chave")
    if not isinstance(chave, str) or not chave.strip():
        raise ValueError("chave deve ser um texto")
    termo = params.get("termo", "")
    if not isinstance(termo, str):
        raise ValueError("termo deve ser um texto")
    return servico.integracoes.buscar(chave.strip(), termo)


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


def _fora_destino(servico, caminho) -> bool:
    """Download fora da pasta de jogos (candidato a "Organizar"); erro = False."""
    if not caminho:
        return False
    try:
        return bool(servico.fora_do_destino(caminho))
    except Exception:
        return False


def _torrents_controlar(servico, params) -> dict:
    ident = params.get("ident")
    acao = params.get("acao")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("ident deve ser o hash do torrent")
    if acao not in ("pausar", "retomar"):
        raise ValueError("acao deve ser pausar ou retomar")
    return servico.torrent_controlar(ident.strip(), acao)


def _torrents_fora_destino(servico, params) -> dict:
    caminho = params.get("caminho")
    if not isinstance(caminho, str) or not caminho.strip():
        raise ValueError("caminho deve ser um texto")
    return {"fora": servico.fora_do_destino(caminho.strip())}


def _torrents_organizar(servico, params) -> dict:
    caminho = params.get("caminho")
    if not isinstance(caminho, str) or not caminho.strip():
        raise ValueError("caminho deve ser um texto")
    return servico.organizar_download(caminho.strip())


def _videos_local(servico, params) -> dict:
    ident = _inteiro(params, "id")
    dados = servico.video_local(ident)
    return {"id": dados.get("id", ident), "titulo": dados.get("titulo", ""),
            "posicao": dados.get("posicao", 0), "sha": dados.get("sha", "")}


def _videos_salvar_posicao(servico, params) -> dict:
    sha = params.get("sha")
    if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{64}", sha) is None:
        raise ValueError("sha deve ser hexadecimal de 64 caracteres")
    posicao = params.get("posicao")
    if isinstance(posicao, bool) or not isinstance(posicao, (int, float)):
        raise ValueError("posicao deve ser um número")
    posicao = float(posicao)
    if not math.isfinite(posicao) or posicao < 0:
        raise ValueError("posicao deve ser não-negativa")
    servico.salvar_posicao_video(sha, posicao)
    return {"ok": True}


def _musicas_buscar_online(servico, params) -> list:
    termo = params.get("termo", "")
    if not isinstance(termo, str) or not termo.strip():
        raise ValueError("termo deve ser um texto")
    fonte = params.get("fonte", "todas")
    if fonte not in ("todas", "spotify", "youtube"):
        raise ValueError("fonte deve ser todas, spotify ou youtube")
    atualizar = bool(params.get("atualizar", False))
    return servico.buscar_musicas_online(termo.strip(), fonte, atualizar)


def _musicas_enfileirar(servico, params) -> dict:
    itens = params.get("itens")
    if not isinstance(itens, list):
        raise ValueError("itens deve ser uma lista")
    return servico.enfileirar_musicas(itens)


def _musicas_letras(servico, params) -> dict:
    artista = params.get("artista", "")
    titulo = params.get("titulo", "")
    if not isinstance(artista, str) or not isinstance(titulo, str):
        raise ValueError("artista e titulo devem ser texto")
    album = params.get("album", "")
    if not isinstance(album, str):
        raise ValueError("album deve ser texto")
    duracao = params.get("duracao_s", 0)
    if isinstance(duracao, bool) or not isinstance(duracao, (int, float)):
        raise ValueError("duracao_s deve ser numero")
    return servico.buscar_letras(artista, titulo, album, duracao)


def _capas_importar_selecionados(servico, params) -> dict:
    itens = params.get("itens")
    if not isinstance(itens, list):
        raise ValueError("itens deve ser uma lista")
    return servico.importar_selecionados(itens)


def _pacotes_importar(servico, params) -> dict:
    pasta = params.get("pasta")
    if not isinstance(pasta, str) or not pasta.strip():
        raise ValueError("pasta deve ser um texto")
    exe = params.get("exe", "")
    if not isinstance(exe, str):
        raise ValueError("exe deve ser um texto")
    return servico.importar_pacote(pasta.strip(), exe)


def _pacotes_abrir_instalador(servico, params) -> dict:
    exe = params.get("exe")
    if not isinstance(exe, str) or not exe.strip():
        raise ValueError("exe deve ser um texto")
    return servico.abrir_instalador_pacote(exe.strip())


def _videos_reproduzir(servico, params) -> dict:
    ident = _inteiro(params, "id")
    reprodutor = params.get("reprodutor", "auto")
    if not isinstance(reprodutor, str) or not reprodutor.strip():
        raise ValueError("reprodutor deve ser um texto")
    return servico.reproduzir_video(ident, reprodutor.strip())


def _videos_buscar_online(servico, params) -> list:
    termo = params.get("termo", "")
    if not isinstance(termo, str) or not termo.strip():
        raise ValueError("termo deve ser um texto")
    limite = params.get("limite", 10)
    if isinstance(limite, bool) or not isinstance(limite, int) or limite <= 0:
        raise ValueError("limite deve ser um inteiro positivo")
    return servico.buscar_videos_online(termo.strip(), limite)


def _conquistas_avaliar(servico, params) -> dict:
    ident = _inteiro(params, "id")
    return servico.avaliar_conquistas(ident)


def _conquistas_sincronizar(servico, params) -> dict:
    ident = _inteiro(params, "id")
    appid = params.get("appid", "")
    if not isinstance(appid, str):
        raise ValueError("appid deve ser um texto")
    save = params.get("save", "")
    if not isinstance(save, str):
        raise ValueError("save deve ser um texto")
    return servico.sincronizar_conquistas(ident, appid, save)


def _conquistas_regras(servico, params) -> dict:
    ident = _inteiro(params, "id")
    texto = params.get("texto", "")
    if not isinstance(texto, str):
        raise ValueError("texto deve ser um texto")
    return servico.regras_conquistas(ident, texto)


def _capas_buscar(servico, params) -> dict:
    categoria = params.get("categoria")
    if categoria not in ("jogos", "musicas", "desejos"):
        raise ValueError("categoria deve ser jogos, musicas ou desejos")
    ident = _inteiro(params, "id")
    provedor = params.get("provedor", "")
    if not isinstance(provedor, str):
        raise ValueError("provedor deve ser um texto")
    atualizar = bool(params.get("atualizar", False))
    return servico.buscar_capas(categoria, ident, provedor, atualizar)


def _capas_aplicar(servico, params) -> dict:
    categoria = params.get("categoria")
    if categoria not in ("jogos", "musicas", "desejos"):
        raise ValueError("categoria deve ser jogos, musicas ou desejos")
    ident = _inteiro(params, "id")
    candidato = params.get("candidato")
    if not isinstance(candidato, dict):
        raise ValueError("candidato deve ser um objeto")
    return servico.aplicar_capa(categoria, ident, candidato)


def _capas_libretro(servico, params) -> dict:
    ident = _inteiro(params, "id")
    return servico.buscar_capa_libretro(ident)


def _emulacao_status(servico, params) -> dict:
    return servico.emus_status()


def _emulacao_consultar(servico, params) -> dict:
    chave = params.get("chave")
    if not isinstance(chave, str) or not chave.strip():
        raise ValueError("chave deve ser um texto")
    return servico.emu_consultar(chave.strip())


def _ferramentas_jogo(servico, params) -> dict:
    ident = _inteiro(params, "id")
    return servico.ferramentas_jogo(ident)


def _diagnosticar_jogo(servico, params) -> dict:
    ident = _inteiro(params, "id")
    return servico.diagnosticar_jogo(ident)


def _disco_jogo(servico, params) -> dict:
    ident = _inteiro(params, "id")
    return servico.disco_jogo(ident)


def _configurar_saves(servico, params) -> dict:
    ident = _inteiro(params, "id")
    caminhos = params.get("caminhos")
    if not isinstance(caminhos, list):
        raise ValueError("caminhos deve ser uma lista")
    return servico.configurar_saves(ident, caminhos)


def _abrir_ferramenta(servico, params) -> dict:
    tipo = params.get("tipo")
    if tipo not in ("imagens", "equalizadores", "videos"):
        raise ValueError("tipo deve ser imagens, equalizadores ou videos")
    nome = params.get("nome")
    if not isinstance(nome, str) or not nome.strip():
        raise ValueError("nome deve ser um texto")
    caminho = params.get("caminho", "")
    if not isinstance(caminho, str):
        raise ValueError("caminho deve ser um texto")
    return servico.abrir_ferramenta_midia(tipo, nome.strip(), caminho)


def _aparencia(servico, params) -> dict:
    return servico.aparencia()


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


def _estatisticas(servico, params) -> dict:
    return servico.estatisticas()


def _backups(servico, params) -> dict:
    manter = params.get("manter", 10)
    if isinstance(manter, bool) or not isinstance(manter, int):
        raise ValueError("manter deve ser inteiro")
    return servico.backups(manter)


def _exportar_colecao(servico, params) -> dict:
    pasta = params.get("pasta")
    if not isinstance(pasta, str) or not pasta.strip():
        raise ValueError("pasta deve ser um texto")
    r = servico.exportar_colecao_para(pasta.strip())
    # o domínio devolve ok=false em vez de levantar: a interface diria "exportada"
    if isinstance(r, dict) and r.get("ok") is False:
        raise ValueError(r.get("erro") or "Não foi possível exportar a coleção.")
    return r


def _importar_colecao(servico, params) -> dict:
    caminho = params.get("caminho")
    if not isinstance(caminho, str) or not caminho.strip():
        raise ValueError("caminho deve ser um texto")
    restaurar_saves = bool(params.get("restaurar_saves", False))
    r = servico.importar_colecao(caminho.strip(), restaurar_saves)
    if isinstance(r, dict) and r.get("ok") is False:
        raise ValueError(r.get("erro") or "Não foi possível importar a coleção.")
    return r


def _sincronizar_steam(servico, params) -> dict:
    return servico.sincronizar_desejos_steam()


def _importar_wishlist(servico, params) -> dict:
    caminho = params.get("caminho")
    if not isinstance(caminho, str) or not caminho.strip():
        raise ValueError("caminho deve ser um texto")
    return servico.importar_wishlist(caminho.strip())


def _buscar_fontes_desejo(servico, params) -> dict:
    titulo = params.get("titulo")
    if not isinstance(titulo, str) or not titulo.strip():
        raise ValueError("titulo deve ser um texto")
    return servico.buscar_fontes_desejo(titulo.strip())


def _filtro(servico, params) -> dict:
    return servico.filtro()


def _salvar_filtro(servico, params) -> dict:
    filtro = params.get("filtro", "")
    ordem = params.get("ordem", "")
    if not isinstance(filtro, str) or not isinstance(ordem, str):
        raise ValueError("filtro e ordem devem ser texto")
    return servico.salvar_filtro(filtro, ordem)


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


METODOS = {
    "nucleo.ping": _ping,
    "nucleo.snapshot": _snapshot,
    "nucleo.buscar": _buscar,
    "nucleo.saude": _saude,
    "modulos.listar": _modulos,
    "preferencias.ler": _preferencias,
    "preferencias.trocar_perfil": _trocar_perfil,
    "preferencias.filtro": _filtro,
    "preferencias.salvar_filtro": _salvar_filtro,
    "jogo.ler": _jogo_ler,
    "jogo.salvar": _jogo_salvar,
    "jogo.favoritar": _jogo_favoritar,
    "jogo.observacoes": _jogo_observacoes,
    "item.excluir": _item_excluir,
    "item.desfazer": _item_desfazer,
    "lixeira.estado": _lixeira_estado,
    "desejos.adicionar": _desejos_adicionar,
    "desejos.precos": _desejos_precos,
    "integracoes.listar": _integracoes_listar,
    "integracoes.adicionar": _integracoes_adicionar,
    "integracoes.remover": _integracoes_remover,
    "integracoes.url": _integracoes_url,
    "integracoes.buscar": _integracoes_buscar,
    "torrents.listar": _torrents_listar,
    "torrents.controlar": _torrents_controlar,
    "torrents.fora_destino": _torrents_fora_destino,
    "torrents.organizar": _torrents_organizar,
    "videos.local": _videos_local,
    "videos.salvar_posicao": _videos_salvar_posicao,
    "videos.reproduzir": _videos_reproduzir,
    "videos.buscar_online": _videos_buscar_online,
    "conquistas.avaliar": _conquistas_avaliar,
    "conquistas.sincronizar": _conquistas_sincronizar,
    "conquistas.regras": _conquistas_regras,
    "capas.buscar": _capas_buscar,
    "capas.aplicar": _capas_aplicar,
    "capas.libretro": _capas_libretro,
    "emulacao.status": _emulacao_status,
    "emulacao.consultar": _emulacao_consultar,
    "ferramentas.jogo": _ferramentas_jogo,
    "jogo.diagnosticar": _diagnosticar_jogo,
    "jogo.disco": _disco_jogo,
    "saves.configurar": _configurar_saves,
    "ferramentas.abrir": _abrir_ferramenta,
    "aparencia.ler": _aparencia,
    "aparencia.salvar": _definir_aparencia,
    "provedores.configurar": _configurar_provedores,
    "estatisticas.ler": _estatisticas,
    "backups.listar": _backups,
    "colecao.exportar": _exportar_colecao,
    "colecao.importar": _importar_colecao,
    "desejos.sincronizar_steam": _sincronizar_steam,
    "desejos.importar_wishlist": _importar_wishlist,
    "desejos.buscar_fontes": _buscar_fontes_desejo,
    "musicas.buscar_online": _musicas_buscar_online,
    "musicas.enfileirar": _musicas_enfileirar,
    "musicas.letras": _musicas_letras,
    "capas.importar_selecionados": _capas_importar_selecionados,
    "pacotes.importar": _pacotes_importar,
    "pacotes.abrir_instalador": _pacotes_abrir_instalador,
}


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

    def iniciar(self, rotulo, funcao, cancelavel=False, escopo=None) -> dict:
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
                    "pct": None, "cancelavel": bool(cancelavel), "escopo": escopo,
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
                item["estado"] = "erro"
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

    def cancelar(self, params) -> dict:
        ident = _inteiro(params, "id")
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


class Ponte:
    """Despachante NDJSON: cada linha vira uma resposta serializada."""

    def __init__(self, servico, metodos=None, trabalhos=None):
        self.servico = servico
        self._escrita = threading.RLock()
        self._saida = None
        self.trabalhos = trabalhos if trabalhos is not None else Trabalhos(self._publicar_evento)
        base = dict(METODOS) if metodos is None else dict(metodos)
        base.update({
            "trabalhos.listar": self._trabalhos_listar,
            "trabalhos.cancelar": self._trabalhos_cancelar,
            "jogo.jogar": self._jogo_jogar,
            "jogo.registrar_horas": self._jogo_registrar_horas,
            "musicas.importar": self._musicas_importar,
            "musicas.baixar_fila": self._musicas_baixar_fila,
            "torrents.importar": self._torrents_importar,
            "videos.importar": self._videos_importar,
            "videos.baixar": self._videos_baixar,
            "videos.baixar_mp3": self._videos_baixar_mp3,
            "jogos.importar": self._importar_jogos,
        })
        # paridade com o antigo desktop Qt (emulação, controles, manutenção…);
        # import tardio: no app instalado o sys.path só fica pronto em preparar_ambiente()
        from ponte_paridade import metodos_paridade
        base.update(metodos_paridade(self.trabalhos))
        self.metodos = base

    def _publicar_evento(self, evento: dict) -> None:
        with self._escrita:
            if self._saida is None:
                return
            self._saida.write(json.dumps(evento, ensure_ascii=False, default=str) + "\n")
            self._saida.flush()

    def _trabalhos_listar(self, servico, params) -> list:
        return self.trabalhos.listar()

    def _trabalhos_cancelar(self, servico, params) -> dict:
        return self.trabalhos.cancelar(params)

    def _jogo_jogar(self, servico, params) -> dict:
        ident = _inteiro(params, "id")
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

        return {"trabalho": self.trabalhos.iniciar(f"Jogar {titulo}", tarefa, escopo="jogo")}

    def _musicas_importar(self, servico, params) -> dict:
        pasta = params.get("pasta")
        if not isinstance(pasta, str) or not pasta.strip():
            raise ValueError("pasta deve ser um caminho de texto")
        pasta = pasta.strip()
        rotulo = "Importar músicas: " + (Path(pasta).name or pasta)

        def tarefa(progresso, cancelado):
            resultado = servico.importar_musicas(pasta)
            detalhe = dict(resultado) if isinstance(resultado, dict) else {}
            detalhe["aviso"] = (f'{detalhe.get("novos", 0)} nova(s), '
                                f'{detalhe.get("ignorados", 0)} ignorada(s).')
            return detalhe

        return {"trabalho": self.trabalhos.iniciar(rotulo, tarefa, escopo="musicas")}

    def _musicas_baixar_fila(self, servico, params) -> dict:
        def tarefa(progresso, cancelado):
            def cb(dados):
                # `baixar_musicas` chama o progresso com um dict {pct, rotulo, id}.
                if isinstance(dados, dict):
                    progresso(dados.get("pct", 0))
                else:
                    progresso(dados)

            resultado = servico.baixar_musicas(cancelado, cb)
            detalhe = dict(resultado) if isinstance(resultado, dict) else {}
            novas = detalhe.get("novas", 0)
            erros = [str(e) for e in (detalhe.get("erros") or [])]
            if cancelado.is_set():
                detalhe["aviso"] = f"Download cancelado. {novas} nova(s) até aqui."
            else:
                aviso = f"{novas} nova(s) baixada(s)."
                if erros:
                    aviso += " " + erros[0] + (f" (+{len(erros) - 1})" if len(erros) > 1 else "")
                detalhe["aviso"] = aviso
            return detalhe

        return {"trabalho": self.trabalhos.iniciar("Baixar fila de músicas", tarefa,
                                                    cancelavel=True, escopo="musicas")}

    def _torrents_importar(self, servico, params) -> dict:
        caminho = params.get("caminho")
        if not isinstance(caminho, str) or not caminho.strip():
            raise ValueError("caminho deve ser um texto")
        caminho = caminho.strip()

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
        return {"trabalho": self.trabalhos.iniciar(f"Importar download {titulo}", tarefa,
                                                  escopo="torrents")}

    def _videos_importar(self, servico, params) -> dict:
        pasta = params.get("pasta")
        if not isinstance(pasta, str) or not pasta.strip():
            raise ValueError("pasta deve ser um caminho de texto")
        pasta = pasta.strip()

        def tarefa(progresso, cancelado):
            if cancelado.is_set():
                raise ValueError("Importação cancelada.")
            progresso(10)
            resultado = servico.importar_videos(pasta)
            progresso(100)
            detalhe = dict(resultado) if isinstance(resultado, dict) else {}
            detalhe.setdefault("aviso", "Vídeos importados.")
            return detalhe

        titulo = Path(pasta).name or "pasta"
        return {"trabalho": self.trabalhos.iniciar(f"Importar vídeos {titulo}", tarefa,
                                                  escopo="videos")}

    def _importar_jogos(self, servico, params) -> dict:
        pasta = params.get("pasta")
        if not isinstance(pasta, str) or not pasta.strip():
            raise ValueError("pasta deve ser um texto")
        pasta = pasta.strip()

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
        return {"trabalho": self.trabalhos.iniciar(f"Importar jogos {titulo}", tarefa,
                                                  escopo="jogos")}

    def _videos_baixar(self, servico, params) -> dict:
        video_id = params.get("video_id")
        if not isinstance(video_id, str) or not video_id.strip():
            raise ValueError("video_id deve ser um texto")
        video_id = video_id.strip()

        def tarefa(progresso, cancelado):
            if cancelado.is_set():
                raise ValueError("Download cancelado.")
            progresso(10)
            resultado = servico.baixar_video_online(video_id, progresso)
            progresso(100)
            detalhe = dict(resultado) if isinstance(resultado, dict) else {}
            detalhe.setdefault("aviso", "Vídeo baixado.")
            return detalhe

        return {"trabalho": self.trabalhos.iniciar(f"Baixar vídeo {video_id}", tarefa,
                                                  escopo="videos")}

    def _videos_baixar_mp3(self, servico, params) -> dict:
        video = params.get("video")
        if not isinstance(video, dict):
            raise ValueError("video deve ser um objeto")

        def tarefa(progresso, cancelado):
            if cancelado.is_set():
                raise ValueError("Download cancelado.")
            progresso(10)
            resultado = servico.baixar_mp3(video, progresso)
            progresso(100)
            detalhe = dict(resultado) if isinstance(resultado, dict) else {}
            detalhe.setdefault("aviso", "MP3 baixado.")
            return detalhe

        titulo = str(video.get("titulo") or "video")
        return {"trabalho": self.trabalhos.iniciar(f"Baixar MP3 {titulo}", tarefa,
                                                  escopo="videos")}

    def _jogo_registrar_horas(self, servico, params) -> dict:
        ident = _inteiro(params, "id")
        horas = params.get("horas")
        if isinstance(horas, bool) or not isinstance(horas, (int, float)):
            raise ValueError("horas deve ser um número")
        horas = float(horas)
        if not math.isfinite(horas) or horas <= 0:
            raise ValueError("horas deve ser maior que zero")
        return servico.registrar_sessao(ident, horas)

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
    import bib_core as core
    from servicos_ui import ServicoBiblioteca
    core.garantir_dirs()
    trava = core.adquirir_lock(ignorar=args.ignorar_lock)
    if not trava.get("ok"):
        evento = {"evento": "bloqueio",
                  "dados": {"erro": trava.get("erro", "TucoTeca já está aberto.")}}
        destino = saida or sys.stdout
        destino.write(json.dumps(evento, ensure_ascii=False) + "\n")
        destino.flush()
        return 2
    try:
        db = Path(args.db) if args.db else Path(core.DEFAULT_DB)
        Ponte(ServicoBiblioteca(db)).servir(entrada or sys.stdin, saida or sys.stdout)
        return 0
    finally:
        core.liberar_lock()


if __name__ == "__main__":
    raise SystemExit(iniciar(sys.argv[1:]))
