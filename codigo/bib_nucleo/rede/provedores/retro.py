"""RetroAchievements (usuário + chave Web API do próprio usuário): conquistas e progresso.

Só leitura do perfil do usuário. O jogo é casado pelo id informado na página
ou, para Nintendo DS, pelo nome na lista de jogos do console (cache de 7 dias).
"""
from __future__ import annotations

import urllib.parse

from bib_nucleo.rede import online
from bib_nucleo.rede.provedores._apoio import normalizar_titulo, obter, respeitar_ritmo

BASE = "https://retroachievements.org/API"
# plataforma do TucoTeca → ConsoleID do RetroAchievements (3DS não tem conquistas no RA)
CONSOLES = {"NDS": 18}
VALIDADE_LISTA = 7 * 86400


def credenciais() -> tuple[str, str]:
    return online.chave_provedor("retro_user"), online.chave_provedor("retro_key")


def _get(script: str, **params) -> dict | list:
    usuario, chave = credenciais()
    if not usuario or not chave:
        raise ValueError("Informe usuário e chave Web API do RetroAchievements em Configurações.")
    respeitar_ritmo("retroachievements.org", 0.5)
    q = urllib.parse.urlencode({"z": usuario, "y": chave, **params})
    return online.requisitar_json(f"{BASE}/{script}?{q}")


def resolver_id(jogo: dict, meta: dict) -> str:
    ident = str(meta.get("retro_id") or "")
    if ident.isdigit():
        return ident
    from bib_nucleo.banco import plataforma_jogo
    console = CONSOLES.get(plataforma_jogo(jogo))
    if console is None:
        return ""
    lista = obter("retro-jogos", str(console), VALIDADE_LISTA,
                  lambda: _get("API_GetGameList.php", i=console, f=1))
    alvo = normalizar_titulo(jogo.get("titulo") or "")
    for item in lista if isinstance(lista, list) else []:
        if isinstance(item, dict) and normalizar_titulo(item.get("Title") or "") == alvo:
            return str(item.get("ID") or "")
    return ""


def progresso(ident: str) -> dict:
    """Conquistas do jogo com a data em que o usuário ganhou cada uma (sem cache)."""
    usuario, _ = credenciais()
    dados = _get("API_GetGameInfoAndUserProgress.php", g=ident, u=usuario)
    if not isinstance(dados, dict) or not dados.get("ID"):
        raise ValueError("o RetroAchievements não conhece este jogo.")
    conquistas = []
    for c in (dados.get("Achievements") or {}).values():
        if not isinstance(c, dict):
            continue
        conquistas.append({
            "id": int(c.get("ID") or 0), "titulo": str(c.get("Title") or ""),
            "descricao": str(c.get("Description") or ""), "pontos": int(c.get("Points") or 0),
            "ordem": int(c.get("DisplayOrder") or 0),
            "ganha_em": str(c.get("DateEarnedHardcore") or c.get("DateEarned") or ""),
            "hardcore": bool(c.get("DateEarnedHardcore")),
        })
    conquistas.sort(key=lambda c: (c["ordem"], c["id"]))
    return {"id": str(dados.get("ID")), "titulo": str(dados.get("Title") or ""),
            "console": str(dados.get("ConsoleName") or ""),
            "total": len(conquistas), "ganhas": sum(1 for c in conquistas if c["ganha_em"]),
            "pontos_total": sum(c["pontos"] for c in conquistas),
            "pontos_ganhos": sum(c["pontos"] for c in conquistas if c["ganha_em"]),
            "conquistas": conquistas}


def buscar(jogo: dict, meta: dict) -> dict:
    ident = resolver_id(jogo, meta)
    if not ident:
        return {}
    return {"retro_id": ident, "retro": progresso(ident)}


__all__ = ["CONSOLES", "credenciais", "resolver_id", "progresso", "buscar"]
