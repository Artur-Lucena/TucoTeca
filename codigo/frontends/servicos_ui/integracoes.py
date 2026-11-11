"""Contratos de integracao do desktop, independentes de Qt e de widgets.

Registro explicito: instalar um servico nao implica executar plugins
arbitrarios.

Contrato
--------
Cada integracao e um `Integracao` com identidade (`chave`/`nome`), um `tipo`
de `INTEGRACAO_TIPOS`, o visual (`inicial`/`cor`) e, opcionalmente, um
callable de busca (`buscar`) e/ou uma `url` com `{q}`. O campo `capacidades`
declara, num vocabulario fixo (`CAPACIDADES`), o que a integracao faz:

    "busca"    -> oferece pesquisa de catalogo (callable `buscar`)
    "abrir"    -> abre um destino externo (campo `url`)
    "midia"    -> trabalha com musica/video/capas
    "download" -> gerencia downloads (torrentes, repacks)
    "emulador" -> integra emulador/ROMs
    "config"   -> expoe presets/opcoes de configuracao

`apresentar()` devolve um DTO serializavel com todas as chaves, inclusive
`capacidades` como lista ordenada (a interface itera chaves genericas). Nomes,
exports e formatos atuais continuam validos: `capacidades` tem default `()`.

Para adicionar uma integracao em 3 passos (modulo de rede -> registro aqui ->
teste hermetico), copie `bib_nucleo/rede/_modelo.py` e siga
`docs/INTEGRACOES.md`.
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
    capacidades: tuple[str, ...] = ()

    def apresentar(self):
        dados = {k: v for k, v in asdict(self).items() if k != "buscar"}
        dados["capacidades"] = list(self.capacidades)
        return dados


INTEGRACAO_TIPOS = ("catalogo", "emulador", "download", "musicas_online",
                    "provedores", "link")
# Vocabulario fixo de capacidades (ver docstring do modulo).
CAPACIDADES = ("busca", "abrir", "midia", "download", "emulador", "config")
_CORES = ("#62d4ad", "#b5a0ff", "#f0bb77", "#7eaaff", "#67cff1", "#7ce3b8", "#6cd5f5")


def _capacidades_para(tipo: str, tem_url: bool = False) -> tuple[str, ...]:
    """Deriva capacidades coerentes para integracoes personalizadas.

    O usuario nao digita capacidades: elas saem do `tipo` e da presenca de
    `url`, no mesmo vocabulario de `CAPACIDADES`.
    """
    caps = ["abrir"] if tem_url else []
    if tipo == "emulador":
        caps.append("emulador")
    elif tipo == "download":
        caps.append("download")
    elif tipo in ("musicas_online", "provedores"):
        caps.append("midia")
    return tuple(dict.fromkeys(caps))



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
                   "catalogo", "SR", "#62d4ad", core.buscar_steamrip, capacidades=("busca",)),
        Integracao("fitgirl", "FitGirl", "Descubra títulos no catálogo conectado.",
                   "catalogo", "FG", "#b5a0ff", core.buscar_fitgirl, capacidades=("busca",)),
        Integracao("azahar", "Azahar", "Emulação 3DS, presets, mods e texturas.",
                   "emulador", "3D", "#f0bb77", capacidades=("emulador", "config")),
        Integracao("desmume", "DeSmuME", "Sua coleção Nintendo DS, no mesmo lugar.",
                   "emulador", "DS", "#7eaaff", capacidades=("emulador",)),
        Integracao("qbittorrent", "qBittorrent", "Cliente local com progresso, pausa e retomada.",
                   "download", "qb", "#67cff1", capacidades=("download",)),
        Integracao("spotify", "Spotify", "Escolha faixas/playlists e envie à fila de música local.",
                   "musicas_online", "SP", "#7ce3b8", capacidades=("midia",)),
        Integracao("capas", "Capas online", "Steam, SteamGridDB, Wikipedia, iTunes, MusicBrainz e Deezer.",
                   "provedores", "AR", "#6cd5f5", capacidades=("midia",)),
    ):
        registro.registrar(item)
    for d in carregar_personalizadas():
        try:
            item = _validar_personalizada(d)
        except ValueError:
            continue
        caps = _capacidades_para(item["tipo"], tem_url=bool(item["url"]))
        try:
            registro.registrar(Integracao(url=item.pop("url"), personalizada=True,
                                          capacidades=caps, **item))
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


__all__ = ["Integracao", "INTEGRACAO_TIPOS", "CAPACIDADES", "_CORES",
           "_arquivo_personalizadas", "_capacidades_para",
           "carregar_personalizadas", "_validar_personalizada", "CHAVES_PADRAO",
           "salvar_personalizada", "remover_personalizada", "RegistroIntegracoes",
           "integracoes_padrao", "url_integracao"]
