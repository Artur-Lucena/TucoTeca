"""Contratos de integracao do desktop, independentes de Qt e de widgets.

Registro explicito: instalar um servico nao implica executar plugins
arbitrarios.
"""
from __future__ import annotations

import urllib.parse
from dataclasses import asdict, dataclass
from typing import Callable

import bib_core as core
from bib_nucleo import online


@dataclass(frozen=True)
class Integracao:
    chave: str
    nome: str
    descricao: str
    tipo: str
    inicial: str
    cor: str
    buscar: Callable | None = None
    url: str = ""
    personalizada: bool = False

    def apresentar(self):
        return {k: v for k, v in asdict(self).items() if k != "buscar"}


INTEGRACAO_TIPOS = ("catalogo", "emulador", "download", "musicas_online",
                    "provedores", "link")
_CORES = ("#62d4ad", "#b5a0ff", "#f0bb77", "#7eaaff", "#67cff1", "#7ce3b8", "#6cd5f5")


def _arquivo_personalizadas():
    return core.DADOS_DIR / "integracoes-usuario.json"


def carregar_personalizadas() -> list[dict]:
    dados = online.ler_json(_arquivo_personalizadas(), [])
    return [d for d in dados] if isinstance(dados, list) else []


def _validar_personalizada(dados: dict) -> dict:
    import re
    chave = str(dados.get("chave") or "").strip().lower()
    nome = str(dados.get("nome") or "").strip()
    descricao = str(dados.get("descricao") or "").strip()
    tipo = str(dados.get("tipo") or "link").strip()
    url = str(dados.get("url") or "").strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,30}[a-z0-9]", chave):
        raise ValueError("Chave inválida: use 2–32 letras/números/hífens.")
    if not 2 <= len(nome) <= 60:
        raise ValueError("Nome precisa de 2–60 caracteres.")
    if len(descricao) > 200:
        raise ValueError("Descrição de até 200 caracteres.")
    if tipo not in INTEGRACAO_TIPOS:
        raise ValueError("Tipo inválido.")
    if url:
        if not online.url_https(url) or len(url) > 500:
            raise ValueError("URL precisa ser https válida.")
    elif tipo in ("catalogo", "link"):
        raise ValueError("Catálogo/link personalizado precisa da URL (use {q} p/ busca).")
    inicial = "".join(w[0] for w in nome.split()[:2]).upper() or "•"
    cor = _CORES[abs(hash(chave)) % len(_CORES)]
    return {"chave": chave, "nome": nome, "descricao": descricao or "Atalho personalizado.",
            "tipo": tipo, "inicial": inicial, "cor": cor, "url": url}


CHAVES_PADRAO = frozenset({"steamrip", "fitgirl", "azahar", "desmume",
                             "qbittorrent", "spotify", "capas"})


def salvar_personalizada(dados: dict) -> dict:
    item = _validar_personalizada(dados)
    if item["chave"] in CHAVES_PADRAO:
        raise ValueError("Esta chave já é de uma integração do Hub.")
    atual = carregar_personalizadas()
    if any(d.get("chave") == item["chave"] for d in atual):
        raise ValueError("Já existe uma integração com esta chave.")
    atual.append(item)
    online.gravar_json(_arquivo_personalizadas(), atual, backup=True)
    return item


def remover_personalizada(chave: str) -> None:
    atual = carregar_personalizadas()
    nova = [d for d in atual if d.get("chave") != chave]
    if len(nova) == len(atual):
        raise ValueError("Integração padrão não pode ser removida (ou já saiu).")
    online.gravar_json(_arquivo_personalizadas(), nova, backup=True)


class RegistroIntegracoes:
    def __init__(self):
        self._itens: dict[str, Integracao] = {}

    def registrar(self, item: Integracao):
        if not item.chave or item.chave in self._itens:
            raise ValueError(f"Integração duplicada/inválida: {item.chave}")
        self._itens[item.chave] = item

    def listar(self):
        return [i.apresentar() for i in self._itens.values()]

    def buscar(self, chave: str, termo: str):
        item = self._itens.get(chave)
        if item is None or item.buscar is None:
            raise ValueError("Esta integração não oferece pesquisa de catálogo.")
        termo = termo.strip()
        if len(termo) < 2:
            raise ValueError("Digite pelo menos dois caracteres.")
        return item.buscar(termo)


def integracoes_padrao():
    registro = RegistroIntegracoes()
    for item in (
        Integracao("steamrip", "SteamRip", "Pesquise o catálogo e abra a página do jogo.",
                   "catalogo", "SR", "#62d4ad", core.buscar_steamrip),
        Integracao("fitgirl", "FitGirl", "Descubra títulos no catálogo conectado.",
                   "catalogo", "FG", "#b5a0ff", core.buscar_fitgirl),
        Integracao("azahar", "Azahar", "Emulação 3DS, presets, mods e texturas.",
                   "emulador", "3D", "#f0bb77"),
        Integracao("desmume", "DeSmuME", "Sua coleção Nintendo DS, no mesmo lugar.",
                   "emulador", "DS", "#7eaaff"),
        Integracao("qbittorrent", "qBittorrent", "Cliente local com progresso, pausa e retomada.",
                   "download", "qb", "#67cff1"),
        Integracao("spotify", "Spotify", "Escolha faixas/playlists e envie à fila de música local.",
                   "musicas_online", "SP", "#7ce3b8"),
        Integracao("capas", "Capas online", "Steam, SteamGridDB, Wikipedia, iTunes, MusicBrainz e Deezer.",
                   "provedores", "AR", "#6cd5f5"),
    ):
        registro.registrar(item)
    for d in carregar_personalizadas():
        try:
            item = _validar_personalizada(d)
        except ValueError:
            continue
        try:
            registro.registrar(Integracao(url=item.pop("url"), personalizada=True, **item))
        except ValueError:
            continue
    return registro


def url_integracao(registro: RegistroIntegracoes, chave: str, termo="") -> str:
    item = registro._itens.get(chave)
    if item is None or not item.url:
        raise ValueError("Esta integração não tem URL configurada.")
    url = item.url.replace("{q}", urllib.parse.quote_plus((termo or "").strip()))
    if not online.url_https(url):
        raise ValueError("URL da integração inválida.")
    return url


__all__ = ["Integracao", "INTEGRACAO_TIPOS", "_CORES", "_arquivo_personalizadas",
           "carregar_personalizadas", "_validar_personalizada", "CHAVES_PADRAO",
           "salvar_personalizada", "remover_personalizada", "RegistroIntegracoes",
           "integracoes_padrao", "url_integracao"]
