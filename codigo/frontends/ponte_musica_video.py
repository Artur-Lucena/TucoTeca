"""Métodos da ponte de músicas e vídeos: busca online, fila, downloads e reprodução."""
from __future__ import annotations

import math
import re
from pathlib import Path

from ponte_params import inteiro, lista, objeto, texto


def _termo_obrigatorio(params) -> str:
    termo = params.get("termo", "")
    if not isinstance(termo, str) or not termo.strip():
        raise ValueError("termo deve ser um texto")
    return termo.strip()


def _pasta(params) -> str:
    pasta = params.get("pasta")
    if not isinstance(pasta, str) or not pasta.strip():
        raise ValueError("pasta deve ser um caminho de texto")
    return pasta.strip()


def _videos_versao_musica(servico, params) -> dict:
    video = objeto(params, "video")
    if not str(video.get("titulo") or "").strip():
        raise ValueError("video.titulo é obrigatório")
    return servico.versao_musica(video)


def _videos_local(servico, params) -> dict:
    ident = inteiro(params, "id")
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


def _videos_reproduzir(servico, params) -> dict:
    ident = inteiro(params, "id")
    reprodutor = params.get("reprodutor", "auto")
    if not isinstance(reprodutor, str) or not reprodutor.strip():
        raise ValueError("reprodutor deve ser um texto")
    return servico.reproduzir_video(ident, reprodutor.strip())


def _videos_buscar_online(servico, params) -> list:
    termo = _termo_obrigatorio(params)
    limite = params.get("limite", 10)
    if isinstance(limite, bool) or not isinstance(limite, int) or limite <= 0:
        raise ValueError("limite deve ser um inteiro positivo")
    return servico.buscar_videos_online(termo, limite)


def _musicas_buscar_online(servico, params) -> list:
    termo = _termo_obrigatorio(params)
    fonte = params.get("fonte", "todas")
    if fonte not in ("todas", "spotify", "youtube"):
        raise ValueError("fonte deve ser todas, spotify ou youtube")
    atualizar = bool(params.get("atualizar", False))
    return servico.buscar_musicas_online(termo, fonte, atualizar)


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


def _tarefa_simples(executar, aviso_padrao, erro_cancelado):
    """Trabalho de um passo: 10% → executar(progresso) → 100%, com aviso padrão."""
    def tarefa(progresso, cancelado):
        if cancelado.is_set():
            raise ValueError(erro_cancelado)
        progresso(10)
        resultado = executar(progresso)
        progresso(100)
        detalhe = dict(resultado) if isinstance(resultado, dict) else {}
        detalhe.setdefault("aviso", aviso_padrao)
        return detalhe
    return tarefa


def metodos_musica_video(trabalhos) -> dict:
    def musicas_importar(servico, params) -> dict:
        pasta = _pasta(params)
        rotulo = "Importar músicas: " + (Path(pasta).name or pasta)

        def tarefa(progresso, cancelado):
            resultado = servico.importar_musicas(pasta)
            detalhe = dict(resultado) if isinstance(resultado, dict) else {}
            detalhe["aviso"] = (f'{detalhe.get("novos", 0)} nova(s), '
                                f'{detalhe.get("ignorados", 0)} ignorada(s).')
            return detalhe

        return {"trabalho": trabalhos.iniciar(rotulo, tarefa, escopo="musicas")}

    def musicas_baixar_fila(servico, params) -> dict:
        def tarefa(progresso, cancelado):
            def cb(dados):
                # `baixar_musicas` chama o progresso com um dict {pct, rotulo, id}.
                progresso(dados.get("pct", 0) if isinstance(dados, dict) else dados)

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

        return {"trabalho": trabalhos.iniciar("Baixar fila de músicas", tarefa,
                                              cancelavel=True, escopo="musicas")}

    def videos_importar(servico, params) -> dict:
        pasta = _pasta(params)
        tarefa = _tarefa_simples(lambda progresso: servico.importar_videos(pasta),
                                 "Vídeos importados.", "Importação cancelada.")
        titulo = Path(pasta).name or "pasta"
        return {"trabalho": trabalhos.iniciar(f"Importar vídeos {titulo}", tarefa, escopo="videos")}

    def videos_baixar(servico, params) -> dict:
        video_id = texto(params, "video_id").strip()
        tarefa = _tarefa_simples(lambda progresso: servico.baixar_video_online(video_id, progresso),
                                 "Vídeo baixado.", "Download cancelado.")
        return {"trabalho": trabalhos.iniciar(f"Baixar vídeo {video_id}", tarefa, escopo="videos")}

    def videos_baixar_mp3(servico, params) -> dict:
        video = objeto(params, "video")
        musica = params.get("musica")
        if musica is not None and not isinstance(musica, dict):
            raise ValueError("musica deve ser um objeto (faixa do Spotify) ou ausente")
        tarefa = _tarefa_simples(lambda progresso: servico.baixar_mp3(video, progresso, musica),
                                 "MP3 baixado.", "Download cancelado.")
        titulo = str(video.get("titulo") or "video")
        return {"trabalho": trabalhos.iniciar(f"Baixar MP3 {titulo}", tarefa, escopo="videos")}

    return {
        "musicas.buscar_online": _musicas_buscar_online,
        "musicas.enfileirar": lambda servico, params: servico.enfileirar_musicas(lista(params, "itens")),
        "musicas.limpar_fila": lambda servico, params: servico.limpar_fila_musicas(),
        "musicas.letras": _musicas_letras,
        "musicas.importar": musicas_importar,
        "musicas.baixar_fila": musicas_baixar_fila,
        "videos.local": _videos_local,
        "videos.salvar_posicao": _videos_salvar_posicao,
        "videos.reproduzir": _videos_reproduzir,
        "videos.buscar_online": _videos_buscar_online,
        "videos.versao_musica": _videos_versao_musica,
        "videos.importar": videos_importar,
        "videos.baixar": videos_baixar,
        "videos.baixar_mp3": videos_baixar_mp3,
    }


__all__ = ["metodos_musica_video"]
