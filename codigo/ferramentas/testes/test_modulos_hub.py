"""Registro de módulos do desktop (F0): contrato do HUD dirigido por módulos."""
import json

from executar import afirmar
from servicos_ui.modulos import modulos_padrao

CHAVES = ["inicio", "jogos", "musicas", "desejos",
          "downloads", "integracoes", "videos", "youtube"]


def teste_modulos_padrao_chaves_e_ordem():
    modulos = modulos_padrao()
    afirmar([m.chave for m in modulos] == CHAVES, [m.chave for m in modulos])
    ordens = [m.ordem for m in modulos]
    afirmar(ordens == sorted(ordens), ordens)
    afirmar(len(set(ordens)) == len(ordens), ordens)
    afirmar(len(set(CHAVES)) == len(CHAVES))


def teste_apresentar_json_safe():
    dto = [m.apresentar() for m in modulos_padrao()]
    texto = json.dumps(dto, ensure_ascii=False)
    afirmar(isinstance(texto, str) and texto.startswith("["), texto)
    campos = {"chave", "nome", "descricao", "icone", "ordem"}
    for item in dto:
        afirmar(set(item) == campos, set(item))
        for chave in ("chave", "nome", "descricao", "icone"):
            afirmar(isinstance(item[chave], str), item)
        afirmar(isinstance(item["ordem"], int) and item["ordem"] > 0, item)


def teste_nomes_descricoes_e_icones_presentes():
    for m in modulos_padrao():
        afirmar(m.nome.strip() != "", m)
        afirmar(m.descricao.strip() != "", m)
        afirmar(m.icone.strip() != "", m)
