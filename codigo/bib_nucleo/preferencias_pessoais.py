"""Perfis Tuco/Isa e atalhos internos; não instala hooks globais."""
from __future__ import annotations

import threading
import re

from bib_nucleo.base import DADOS_DIR
from bib_nucleo.arquivos import gravar_json, ler_json

PERFIS = ("Tuco", "Isa")
ATALHOS = {"tela_cheia": "F11", "buscar": "Ctrl+F", "paleta": "Ctrl+K",
           **{s: f"Ctrl+{i}" for i, s in enumerate(
               ("inicio", "jogos", "musicas", "desejos", "downloads", "integracoes", "videos", "youtube"), 1)}}
_LOCK = threading.RLock()


def ler_preferencias():
    dados = ler_json(DADOS_DIR / "preferencias-pessoais.json", {})
    dados = dados if isinstance(dados, dict) else {}
    perfis = dados.get("perfis", {})
    perfis = perfis if isinstance(perfis, dict) else {}
    atalhos = dados.get("atalhos")
    atalhos = atalhos if isinstance(atalhos, dict) else {}
    return {"ativo": dados.get("ativo") if dados.get("ativo") in PERFIS else "Tuco",
            "perfis": {p: dict(perfis[p]) if isinstance(perfis.get(p), dict) else {} for p in PERFIS},
            "atalhos": {**ATALHOS, **{k: v for k, v in atalhos.items()
                                    if k in ATALHOS and isinstance(v, str)}},
            "watch": str(dados.get("watch") or ""), "watch_auto": bool(dados.get("watch_auto", False)),
            "sponsorblock": bool(dados.get("sponsorblock", False))}


def atualizar(**mudancas):
    with _LOCK:
        dados = ler_preferencias()
        dados.update(mudancas)
        gravar_json(DADOS_DIR / "preferencias-pessoais.json", dados, backup=True)
        return dados


def trocar_perfil(nome):
    if nome not in PERFIS:
        raise ValueError("Perfil precisa ser Tuco ou Isa.")
    return atualizar(ativo=nome)


def salvar_favorito(jogo, favorito):
    with _LOCK:
        dados = ler_preferencias()
        perfil = dados["perfis"][dados["ativo"]]
        favoritos = dict(perfil.get("favoritos") or {})
        favoritos[str(jogo["uuid"])] = bool(favorito)
        perfil["favoritos"] = favoritos
        return atualizar(perfis=dados["perfis"])


def aplicar_perfil(jogos):
    dados = ler_preferencias()
    favoritos = dados["perfis"][dados["ativo"]].get("favoritos") or {}
    # Tuco herda o estado legado até a primeira alteração; Isa começa independente.
    return [dict(j, favorito=favoritos.get(str(j["uuid"]),
                 bool(j.get("favorito")) if dados["ativo"] == "Tuco" else False)) for j in jogos]


def salvar_filtro(filtro, ordem):
    if filtro not in ("todos", "favoritos", "jogando", "PC", "3DS", "NDS", "pendencias"):
        raise ValueError("Filtro inválido.")
    if ordem not in ("titulo", "recentes", "horas"):
        raise ValueError("Ordenação inválida.")
    with _LOCK:
        dados = ler_preferencias()
        dados["perfis"][dados["ativo"]].update(filtro=filtro, ordem=ordem)
        return atualizar(perfis=dados["perfis"])


def salvar_atalhos(mapeamento):
    novos = {**ATALHOS, **mapeamento}
    if any(k not in ATALHOS for k in mapeamento):
        raise ValueError("Ação desconhecida nos atalhos.")
    vistos = set()
    for acao, seq in novos.items():
        if not isinstance(seq, str) or not seq.strip() or len(seq) > 60:
            raise ValueError(f"Atalho inválido: {acao}")
        seq = seq.strip()
        partes = seq.split("+")
        if (len(partes) > 4 or any(p not in ("Ctrl", "Alt", "Shift", "Meta") for p in partes[:-1])
                or len(set(partes[:-1])) != len(partes[:-1])
                or not re.fullmatch(r"F(?:[1-9]|[12]\d|3[0-5])|[A-Za-z0-9]|Space|Escape|Tab|Return|Enter|Backspace|Delete|Home|End|Left|Right|Up|Down|PgUp|PgDown", partes[-1])):
            raise ValueError("Use uma combinação como Ctrl+K ou F11.")
        identidade = (tuple(sorted(p.casefold() for p in partes[:-1])), partes[-1].casefold())
        if identidade in vistos:
            raise ValueError("Duas ações não podem usar o mesmo atalho.")
        vistos.add(identidade)
        novos[acao] = seq
    return atualizar(atalhos=novos)
