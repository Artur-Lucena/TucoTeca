"""Integracoes modulares: template de rede, registro e capacidades.

Hermetico: sem rede real (modo aviao via BIBLIOTECA_REDE=0), sem instalar
nada. Cada caso roda no sandbox do runner (dados em diretorio temporario),
por isso salvar/remover personalizada nao toca a instalacao real.
"""
import os

from executar import afirmar

PADRAO = {"steamrip", "fitgirl", "azahar", "desmume", "qbittorrent",
          "spotify", "capas"}


def _modo_aviao():
    """Contexto simples: desliga a rede e devolve o valor anterior."""
    anterior = os.environ.get("BIBLIOTECA_REDE")

    class _Ctx:
        def __enter__(self):
            os.environ["BIBLIOTECA_REDE"] = "0"
            return self

        def __exit__(self, *info):
            if anterior is None:
                os.environ.pop("BIBLIOTECA_REDE", None)
            else:
                os.environ["BIBLIOTECA_REDE"] = anterior
            return False

    return _Ctx()


def teste_modelo_rede_importavel_e_valida_entrada_sem_efeito_colateral():
    from bib_nucleo.rede import _modelo
    from servicos_ui.integracoes import CAPACIDADES, integracoes_padrao
    afirmar(callable(_modelo.buscar) and callable(_modelo.detalhes), "template sem funcoes")
    afirmar(_modelo.FONTE and _modelo.NOME, "template sem identidade")
    # O template nao pode virar integracao de producao por acidente.
    chaves = {i["chave"] for i in integracoes_padrao().listar()}
    afirmar(_modelo.FONTE not in chaves, "template registrou integracao em producao")
    afirmar(_modelo.FONTE not in PADRAO and set(PADRAO) <= chaves)
    for ruim in ("", " ", "  ", "a", None, 7):
        try:
            _modelo.validar_termo(ruim)
        except ValueError:
            pass
        else:
            raise AssertionError(f"template aceitou termo invalido: {ruim!r}")
    try:
        _modelo.detalhes("")
    except ValueError:
        pass
    else:
        raise AssertionError("template aceitou id vazio")
    afirmar("busca" in CAPACIDADES and "emulador" in CAPACIDADES)


def teste_modelo_rede_respeita_modo_aviao():
    from bib_nucleo.rede import _modelo
    with _modo_aviao():
        afirmar(_modelo.buscar("jogo legal") == [], "busca tentou rede no modo aviao")
        afirmar(_modelo.detalhes("abc-123") is None, "detalhes tentou rede no modo aviao")
        # Entrada invalida continua sendo invalidada ANTES do curto-circuito.
        try:
            _modelo.buscar("x")
        except ValueError:
            pass
        else:
            raise AssertionError("modo aviao mascarou entrada invalida")


def teste_registro_integracoes_capacidades_duplicata_e_busca_minima():
    from servicos_ui.integracoes import Integracao, RegistroIntegracoes
    registro = RegistroIntegracoes()
    registro.registrar(Integracao(
        "minha-fonte", "Minha Fonte", "Adaptador de teste", "catalogo", "MF", "#123456",
        lambda q: {"itens": [{"titulo": q}], "erros": []}, capacidades=("busca", "abrir")))
    dto = registro.listar()[0]
    afirmar(isinstance(dto["capacidades"], list), "capacidades nao e lista no DTO")
    afirmar(dto["capacidades"] == ["busca", "abrir"], dto["capacidades"])
    afirmar("buscar" not in dto and isinstance(dto["capacidades"], list))
    for curto in ("", " ", "a", " b "):
        try:
            registro.buscar("minha-fonte", curto)
        except ValueError:
            pass
        else:
            raise AssertionError(f"busca aceitou termo curto: {curto!r}")
    afirmar(registro.buscar("minha-fonte", "ab")["itens"][0]["titulo"] == "ab")
    for duplicado in (Integracao("minha-fonte", "Outra", "", "catalogo", "", ""),
                      Integracao("", "Sem chave", "", "catalogo", "", "")):
        try:
            registro.registrar(duplicado)
        except ValueError:
            pass
        else:
            raise AssertionError(f"registro aceitou invalido/duplicado: {duplicado!r}")


def teste_registro_integracoes_sem_busca_nao_pesquisa():
    from servicos_ui.integracoes import Integracao, RegistroIntegracoes
    registro = RegistroIntegracoes()
    registro.registrar(Integracao("somente-link", "Link", "", "link", "L", "#fff",
                                  url="https://exemplo.test/"))
    try:
        registro.buscar("somente-link", "jogo")
    except ValueError:
        pass
    else:
        raise AssertionError("integracao sem callable ofereceu busca")
    try:
        registro.buscar("inexistente", "jogo")
    except ValueError:
        pass
    else:
        raise AssertionError("chave inexistente ofereceu busca")


def teste_integracoes_padrao_capacidades_coerentes():
    from servicos_ui.integracoes import CAPACIDADES, integracoes_padrao
    itens = integracoes_padrao().listar()
    por_chave = {i["chave"]: i for i in itens}
    afirmar(set(por_chave) == PADRAO, sorted(por_chave))
    for dto in itens:
        caps = dto["capacidades"]
        afirmar(isinstance(caps, list), f"{dto['chave']}: capacidades nao e lista")
        afirmar(set(caps) <= set(CAPACIDADES), f"{dto['chave']}: vocabulario invalido {caps}")
    afirmar(por_chave["steamrip"]["capacidades"] == ["busca"])
    afirmar(por_chave["fitgirl"]["capacidades"] == ["busca"])
    afirmar(por_chave["azahar"]["capacidades"] == ["emulador", "config"])
    afirmar(por_chave["desmume"]["capacidades"] == ["emulador"])
    afirmar(por_chave["qbittorrent"]["capacidades"] == ["download"])
    afirmar(por_chave["spotify"]["capacidades"] == ["midia"])
    afirmar(por_chave["capas"]["capacidades"] == ["midia"])
    # Coerencia por campo: callable de busca -> "busca"; url -> "abrir".
    from servicos_ui.integracoes import integracoes_padrao as _padrao
    for item in _padrao()._itens.values():
        if item.buscar is not None:
            afirmar("busca" in item.capacidades, item.chave)
        if item.url:
            afirmar("abrir" in item.capacidades, item.chave)


def teste_personalizada_salva_remove_e_deriva_capacidade_abrir():
    from servicos_ui.integracoes import (
        carregar_personalizadas,
        integracoes_padrao,
        remover_personalizada,
        salvar_personalizada,
    )
    for ruim in ({"chave": "steamrip", "nome": "Clone", "descricao": "", "tipo": "link",
                  "url": "https://exemplo.test/"},
                 {"chave": "meu-blog", "nome": "B", "descricao": "", "tipo": "link",
                  "url": "http://inseguro.test/"}):
        try:
            salvar_personalizada(ruim)
        except ValueError:
            pass
        else:
            raise AssertionError(f"salvou personalizada invalida: {ruim}")
    item = salvar_personalizada({"chave": "meu-blog", "nome": "Meu Blog", "descricao": "",
                                 "tipo": "link", "url": "https://exemplo.test/busca?q={q}"})
    afirmar(item["chave"] == "meu-blog" and item["url"].startswith("https://"))
    try:
        salvar_personalizada({"chave": "meu-blog", "nome": "Duplicado", "descricao": "",
                              "tipo": "link", "url": "https://outro.test/"})
    except ValueError:
        pass
    else:
        raise AssertionError("aceitou personalizada duplicada")
    dto = {i["chave"]: i for i in integracoes_padrao().listar()}["meu-blog"]
    afirmar(dto["personalizada"] is True)
    afirmar(dto["capacidades"] == ["abrir"], dto["capacidades"])
    remover_personalizada("meu-blog")
    afirmar(all(d.get("chave") != "meu-blog" for d in carregar_personalizadas()))
    afirmar("meu-blog" not in {i["chave"] for i in integracoes_padrao().listar()})
    try:
        remover_personalizada("steamrip")
    except ValueError:
        pass
    else:
        raise AssertionError("removeu integracao padrao")
