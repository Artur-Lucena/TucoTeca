"""Modelo copiavel de integracao de rede (NAO e registrado em producao).

Este arquivo e o PASSO 1 do guia `docs/INTEGRACOES.md`: serve para copiar,
salvar como `codigo/bib_nucleo/rede/<fonte>.py`, trocar os exemplos e apagar o que nao
usar. Importar este modulo **nao faz rede** nem registra nada: os imports
externos sao locais as funcoes e a rede so acontece quando o usuario pede
(`rede_ativa()` + `BIBLIOTECA_REDE`).

Como escrever um provedor (resumo; o guia traz o passo a passo):

    PASSO 1 (aqui)  criar `bib_nucleo/rede/<fonte>.py` com `buscar`/`detalhes`.
                    Sem efeito colateral no import; falha vira ValueError claro.
                    Rede so sob acao do usuario, com `rede_ativa()`, timeout
                    curto, User-Agent e cache local.
    PASSO 2          registrar a integracao em
                    `codigo/frontends/servicos_ui/integracoes.py`
                    (`integracoes_padrao`) com tipo, capacidades e, se for o
                    caso, o callable `buscar`.
    PASSO 3          cobrir com um teste hermetico em
                    `codigo/ferramentas/testes/` (sem rede real, sem instalar
                    nada): valida entradas ruins, modo aviao e o DTO de saida.

Convencoes espelhadas dos provedores reais (`musica_online.py`,
`metadados.py`): stdlib apenas, `from __future__ import annotations`,
`USER_AGENT`/timeout em constantes, retorno simples (lista de dicts ou dict),
erros sempre `ValueError` com mensagem em portugues e sem vazar credenciais.
"""
from __future__ import annotations

import re

from bib_nucleo.versao import user_agent

# --- Constantes de identidade do provedor ---------------------------------
FONTE = "exemplo"                 # chave curta e estavel (slug)
NOME = "Exemplo"                  # rotulo humano exibido no Hub
BASE_URL = "https://api.exemplo.test/v1"  # sem barra final
USER_AGENT = user_agent("integracao exemplo")
TIMEOUT = 8                       # curto: a UI nao deve travar a espera
LIMITE = 10                       # maximo de itens por pagina
MAX_TERMO = 120                   # corta entradas absurdas antes da rede


def _limpar(texto) -> str:
    """Normaliza espacos e remove o que nao deve chegar na URL/JSON."""
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def validar_termo(termo) -> str:
    """Valida a entrada antes de qualquer I/O; `ValueError` e sempre claro."""
    limpo = _limpar(termo)
    if len(limpo) < 2:
        raise ValueError("Digite pelo menos dois caracteres para buscar.")
    return limpo[:MAX_TERMO]


def buscar(termo, limite: int = LIMITE) -> list[dict]:
    """Busca simples no provedor; lista de dicts, nunca excecao de rede crua.

    - entrada invalida: `ValueError` (valida antes de tocar a rede);
    - rede desligada (`BIBLIOTECA_REDE=0`): `[]`, sem tentar conexao;
    - falha/HTTP/JSON invalido: `ValueError` com mensagem amigavel;
    - cache: quem chama decide; veja `online.cache_path`/`online.ler_json`.
    """
    import urllib.parse

    from bib_nucleo import online
    from bib_nucleo.rede import rede_ativa

    alvo = validar_termo(termo)
    if not rede_ativa():
        return []
    try:
        limite = max(1, min(25, int(limite)))
    except (TypeError, ValueError):
        limite = LIMITE

    # `requisitar_json` ja valida https, aplica timeout e converte erros de
    # rede em ValueError. Passamos o User-Agent proprio por transparencia.
    query = urllib.parse.urlencode({"q": alvo, "limit": limite})
    dados = online.requisitar_json(f"{BASE_URL}/search?{query}", timeout=TIMEOUT,
                                   headers={"User-Agent": USER_AGENT})

    itens = []
    for bruto in (dados.get("results") or [])[:limite]:
        if not isinstance(bruto, dict):
            continue
        item_id = _limpar(bruto.get("id"))
        titulo = _limpar(bruto.get("title"))
        if not item_id or not titulo:
            continue
        itens.append({"id": item_id, "titulo": titulo,
                      "artista": _limpar(bruto.get("author")),
                      "fonte": FONTE, "nome_fonte": NOME})
    return itens


def detalhes(item_id) -> dict | None:
    """Detalhes de um item; `None` sem rede ou quando o id nao existe.

    Use para telas de ficha. Mantenha o retorno pequeno e serializavel; nunca
    devolva credenciais nem cabecalhos de autenticacao para a UI.
    """
    import urllib.parse

    from bib_nucleo import online
    from bib_nucleo.rede import rede_ativa

    limpo = _limpar(item_id)
    if not limpo:
        raise ValueError("Item invalido.")
    if not rede_ativa():
        return None
    dados = online.requisitar_json(
        f"{BASE_URL}/itens/{urllib.parse.quote(limpo)}", timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT})
    titulo = _limpar(dados.get("title"))
    if not titulo:
        return None
    return {"id": limpo, "titulo": titulo, "descricao": _limpar(dados.get("description")),
            "fonte": FONTE, "nome_fonte": NOME}


__all__ = ["FONTE", "NOME", "BASE_URL", "USER_AGENT", "TIMEOUT", "LIMITE",
           "validar_termo", "buscar", "detalhes"]
