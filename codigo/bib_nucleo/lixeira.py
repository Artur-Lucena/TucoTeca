#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lixeira local: snapshot de remoções com desfazer (jogos, desejos, vídeos).

Cada remoção arquivada vira `dados/lixeira/<stamp>-<tipo>.json` com a linha
bruta do banco (e a capa do jogo em base64, quando houver). `restaurar_ultimo`
recria o registro preservando uuid/campos; a capa é re-salva com o id novo.
Músicas ficam de fora de propósito: o áudio é apagado junto com a linha.
Sempre local, sem rede; nada restaura sozinho — desfazer é ação explícita.
"""
from __future__ import annotations

import base64
import datetime
import sqlite3
from pathlib import Path

_LIMITE = 20  # arquivos mantidos (LIFO; os mais antigos são podados)
_TIPOS = ("jogos", "desejos", "videos")


def _dir() -> Path:
    from bib_nucleo import base
    return base.DADOS_DIR / "lixeira"


def _stamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def _arquivos() -> list[Path]:
    try:
        return sorted(_dir().glob("*.json"))
    except OSError:
        return []


def _purgar() -> None:
    for velho in _arquivos()[:-_LIMITE]:
        try:
            velho.unlink()
        except OSError:
            pass


def arquivar(con: sqlite3.Connection, tipo: str, ident: int) -> dict:
    """Guarda a linha (e a capa do jogo) antes da exclusão.

    Levanta LookupError se o registro não existe; nada é escrito nesse caso.
    """
    if tipo not in _TIPOS:
        raise ValueError(f"categoria sem desfazer: {tipo}")
    row = con.execute(f"SELECT * FROM {tipo} WHERE id=?", (int(ident),)).fetchone()
    if row is None:
        raise LookupError("registro não encontrado para arquivar")
    dados = dict(row)
    pay = {"tipo": tipo,
           "em": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "titulo": str(dados.get("titulo") or ""),
           "dados": dados}
    if tipo == "jogos" and dados.get("capa"):
        from bib_nucleo.base import CAPAS_DIR
        try:
            raw = (CAPAS_DIR / Path(str(dados["capa"])).name).read_bytes()
        except OSError:
            raw = b""
        if raw and len(raw) <= 2_500_000:
            pay["capa_nome"] = Path(str(dados["capa"])).name
            pay["capa_b64"] = base64.b64encode(raw).decode("ascii")
    from bib_nucleo.arquivos import gravar_json
    destino = _dir() / f"{_stamp()}-{tipo}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    gravar_json(destino, pay)
    _purgar()
    return {"tipo": tipo, "titulo": pay["titulo"], "arquivo": destino.name}


def ultima() -> dict | None:
    """Recibo da remoção mais recente ainda restaurável (ou None)."""
    from bib_nucleo.arquivos import ler_json
    for alvo in reversed(_arquivos()):
        pay = ler_json(alvo, None)
        if isinstance(pay, dict) and pay.get("tipo") in _TIPOS:
            return {"disponivel": True, "tipo": pay["tipo"], "em": pay.get("em", ""),
                    "titulo": pay.get("titulo", ""), "arquivo": alvo.name}
    return None


def restaurar_ultimo(con: sqlite3.Connection) -> dict:
    """Recria a última remoção válida e consome o arquivo; ValueError se vazia.

    Arquivos corrompidos/vazios são descartados para não travar o desfazer.
    Falha ao recriar (ex.: registro já re-adicionado) preserva o arquivo.
    """
    from bib_nucleo.arquivos import ler_json
    for alvo in reversed(_arquivos()):
        pay = ler_json(alvo, None)
        valido = (isinstance(pay, dict) and pay.get("tipo") in _TIPOS
                  and isinstance(pay.get("dados"), dict))
        if not valido:
            try:
                alvo.unlink()
            except OSError:
                pass
            continue
        resultado = _restaurar(con, pay)
        try:
            alvo.unlink()
        except OSError:
            pass
        return resultado
    raise ValueError("Nada para desfazer.")


def _restaurar(con: sqlite3.Connection, pay: dict) -> dict:
    from bib_nucleo import banco as B
    tipo, dados = pay["tipo"], dict(pay["dados"])
    if tipo == "jogos":
        campos = {k: dados.get(k) for k in (
            "titulo", "executable_path", "exe_win", "exe_linux", "exe_mac",
            "wine_prefix", "launch_options", "status", "nota", "favorito",
            "horas", "observacoes", "origem", "shop", "object_id", "game_code",
            "regiao", "azahar_preset", "etiquetas", "save_path", "azahar_mods",
            "azahar_mods_off", "uuid") if k in dados}
        novo = B.criar_jogo(con, campos)
        if dados.get("ultima_execucao"):
            con.execute("UPDATE jogos SET ultima_execucao=? WHERE id=?",
                        (dados["ultima_execucao"], novo["id"]))
            con.commit()
        if pay.get("capa_b64"):
            try:
                raw = base64.b64decode(str(pay["capa_b64"]), validate=True)
            except Exception:
                raw = b""  # capa corrompida não impede a linha de voltar
            if raw:
                B.salvar_capa_bytes(con, novo["id"], pay.get("capa_nome") or "capa.png", raw)
        novo = B.row_to_dict(con.execute(
            "SELECT * FROM jogos WHERE id=?", (novo["id"],)).fetchone())
        return {"ok": True, "tipo": tipo, "titulo": novo.get("titulo", ""), "id": novo["id"]}
    if tipo == "desejos":
        try:
            con.execute(
                "INSERT INTO desejos(appid,titulo,ordem,manual,obtido_em,criado_em,atualizado_em)"
                " VALUES(?,?,?,?,?,?,?)",
                (str(dados.get("appid") or ""), str(dados.get("titulo") or ""),
                 int(dados.get("ordem") or 0), 1 if dados.get("manual") else 0,
                 dados.get("obtido_em"), dados.get("criado_em"), dados.get("atualizado_em")))
            con.commit()
        except sqlite3.IntegrityError:
            raise ValueError("este desejo já está na lista") from None
        return {"ok": True, "tipo": tipo, "titulo": str(dados.get("titulo") or ""), "id": None}
    # videos
    campos = {k: dados.get(k) for k in (
        "titulo", "canal", "video_id", "video_path", "video_sha", "thumb",
        "origem", "duracao_s") if k in dados}
    novo = B.criar_video(con, campos)
    return {"ok": True, "tipo": tipo, "titulo": novo.get("titulo", ""), "id": novo["id"]}


__all__ = ["arquivar", "ultima", "restaurar_ultimo"]
