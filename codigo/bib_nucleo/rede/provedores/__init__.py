"""Provedores de metadados de jogo (à la Hydra): quem fornece o quê, ligado ou não.

Cada provedor é um módulo com `buscar(jogo, meta) -> dict` que devolve campos
parciais (`descricao`, `generos`, ids…) e URLs de arte (`hero_url`,
`logo_url`, `icone_url`, `screenshots_urls`). `enriquecer` roda os ligados em
ordem — o primeiro que trouxer um campo vence — e `baixar_artes` grava as
imagens em `dados/artes/<uuid>/`. Rede só quando o usuário pede (um trabalho
da ponte), sempre com `exigir_rede`, timeout curto, cache e ritmo por host.

Para acrescentar um provedor: crie o módulo aqui, registre em `PROVEDORES` e
cubra com teste hermético (`test_provedores.py`).
"""
from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from bib_nucleo import base
from bib_nucleo.arquivos import gravar_atomico, gravar_json, ler_json
from bib_nucleo.rede import exigir_rede, online
from bib_nucleo.rede.provedores import hltb, retro, sgdb, steam


@dataclass(frozen=True)
class Provedor:
    chave: str
    nome: str
    descricao: str
    fornece: tuple[str, ...]
    buscar: Callable[[dict, dict], dict]
    credenciais: tuple[str, ...] = ()
    ligado_padrao: bool = True


PROVEDORES: tuple[Provedor, ...] = (
    Provedor("steam", "Steam", "Descrição, gêneros, estúdio, lançamento, arte e screenshots.",
             ("descricao", "generos", "desenvolvedora", "lancamento", "hero", "logo", "screenshots"),
             lambda j, m: steam.buscar(j, m)),
    Provedor("sgdb", "SteamGridDB", "Hero, logo e ícone feitos pela comunidade.",
             ("hero", "logo", "icone"), lambda j, m: sgdb.buscar(j, m), credenciais=("steamgriddb_key",)),
    Provedor("retro", "RetroAchievements", "Conquistas e o seu progresso (Nintendo DS e ids manuais).",
             ("conquistas",), lambda j, m: retro.buscar(j, m), credenciais=("retro_user", "retro_key")),
    Provedor("hltb", "HowLongToBeat", "Horas para zerar. API não oficial: pode falhar.",
             ("hltb",), lambda j, m: hltb.buscar(j, m), ligado_padrao=False),
)
_POR_CHAVE = {p.chave: p for p in PROVEDORES}
_lock = threading.RLock()
ARTES = ("hero", "logo", "icone")
LIMITE_ARTE = {"hero": 6_000_000, "logo": 3_000_000, "icone": 1_000_000, "screenshots": 1_000_000}


def _arquivo_config() -> Path:
    return base.DADOS_DIR / "provedores-metadados.json"


def ligados() -> dict[str, bool]:
    salvo = ler_json(_arquivo_config(), {})
    salvo = salvo if isinstance(salvo, dict) else {}
    return {p.chave: bool(salvo.get(p.chave, p.ligado_padrao)) for p in PROVEDORES}


def definir_ligados(novos: dict) -> dict[str, bool]:
    with _lock:
        atual = ligados()
        for chave, valor in (novos or {}).items():
            if chave not in _POR_CHAVE:
                raise ValueError(f"Provedor desconhecido: {chave}")
            if not isinstance(valor, bool):
                raise ValueError("ligado deve ser verdadeiro ou falso")
            atual[chave] = valor
        gravar_json(_arquivo_config(), atual)
    return atual


def configurado(p: Provedor) -> bool:
    return all(online.chave_provedor(c) for c in p.credenciais)


def estado() -> list[dict]:
    ativos = ligados()
    return [{"chave": p.chave, "nome": p.nome, "descricao": p.descricao, "fornece": list(p.fornece),
             "ligado": ativos[p.chave], "precisa_credencial": bool(p.credenciais),
             "configurado": configurado(p)} for p in PROVEDORES]


def enriquecer(jogo: dict, meta: dict, chaves=None, cancelado: Callable[[], bool] = lambda: False):
    """Roda os provedores (os ligados, ou só `chaves`) e junta o que trouxeram.

    Devolve (campos, artes, erros): `artes` = {tipo: [url, …]} em ordem de
    preferência e `screenshots` = [url, …]."""
    exigir_rede("Buscar dados do jogo")
    ativos = ligados()
    escolhidos = [p for p in PROVEDORES if (p.chave in chaves if chaves else ativos[p.chave])]
    campos: dict = {}
    artes: dict[str, list[str]] = {t: [] for t in ARTES}
    screenshots: list[str] = []
    fontes: dict[str, str] = {}
    erros: list[str] = []
    for p in escolhidos:
        if cancelado():
            break
        if not configurado(p):
            # ligado sem credencial: só reclama se o usuário pediu esse provedor
            if chaves:
                erros.append(f"{p.nome}: falta configurar a credencial em Configurações.")
            continue
        try:
            achado = p.buscar(jogo, {**meta, **campos}) or {}
        except ValueError as e:
            erros.append(f"{p.nome}: {e}")
            continue
        for tipo in ARTES:
            url = achado.pop(f"{tipo}_url", "")
            if url:
                artes[tipo].append(url)
        fotos = achado.pop("screenshots_urls", None) or []
        if fotos and not screenshots:
            screenshots = list(fotos)
        for chave, valor in achado.items():
            if valor not in ("", [], {}, None) and chave not in campos:
                campos[chave] = valor
        fontes[p.chave] = base.agora_iso()
    campos["fontes"] = fontes
    return campos, {**artes, "screenshots": screenshots}, erros


def pasta_artes(uuid: str) -> Path:
    seguro = "".join(c for c in str(uuid) if c.isalnum() or c in "-_")
    if not seguro:
        raise ValueError("Jogo sem identidade (uuid).")
    return base.DADOS_DIR / "artes" / seguro


def baixar_uma(uuid: str, tipo: str, url: str, nome: str | None = None) -> str:
    """Baixa uma imagem para a pasta de artes do jogo e devolve o caminho local."""
    raw, ext, _ = online.baixar_imagem(url, limite=LIMITE_ARTE.get(tipo, 2_000_000))
    alvo = pasta_artes(uuid) / f"{nome or tipo}{ext}"
    alvo.parent.mkdir(parents=True, exist_ok=True)
    for velho in alvo.parent.glob(f"{nome or tipo}.*"):
        if velho != alvo:
            velho.unlink(missing_ok=True)
    gravar_atomico(alvo, raw)
    return str(alvo)


def baixar_artes(uuid: str, artes: dict, travado=(), cancelado: Callable[[], bool] = lambda: False):
    """Para cada tipo, a primeira URL que baixar vence. Devolve ({campo: caminho}, erros)."""
    locais: dict = {}
    erros: list[str] = []
    for tipo in ARTES:
        if tipo in travado or cancelado():
            continue
        for url in artes.get(tipo) or []:
            try:
                locais[tipo] = baixar_uma(uuid, tipo, url)
                break
            except ValueError as e:
                erro = f"{tipo}: {e}"
        else:
            if artes.get(tipo):
                erros.append(erro)
    fotos = []
    if "screenshots" not in travado:
        for i, url in enumerate((artes.get("screenshots") or [])[:6]):
            if cancelado():
                break
            try:
                fotos.append(baixar_uma(uuid, "screenshots", url, nome=f"screenshot-{i + 1}"))
            except ValueError:
                continue
    if fotos:
        locais["screenshots"] = fotos
    return locais, erros


__all__ = ["Provedor", "PROVEDORES", "ARTES", "ligados", "definir_ligados", "configurado",
           "estado", "enriquecer", "pasta_artes", "baixar_uma", "baixar_artes"]
