# Integrações do TucoTeca

Como o Hub declara, busca e abre serviços externos — e como adicionar uma
integração nova **em 3 passos**, sem reescrever o domínio e sem dependências
novas (stdlib puro).

## O que é uma integração

Uma integração é um item de `Integracao`
(`codigo/frontends/servicos_ui/integracoes.py`) com:

| Campo | Para que serve |
|---|---|
| `chave` | Identificador estável (slug) usado no registro, na URL e no JSON. |
| `nome` / `descricao` | Texto exibido no Hub. |
| `tipo` | Um de `INTEGRACAO_TIPOS`: `catalogo`, `emulador`, `download`, `musicas_online`, `provedores`, `link`. |
| `inicial` / `cor` | Avatar e cor no cartão. |
| `buscar` | Callable opcional `(termo) -> {"itens": [...], "erros": [...]}`. |
| `url` | Destino opcional; `{q}` vira o termo escapado. |
| `personalizada` | `True` quando o usuário criou pelo Hub (JSON local). |
| `capacidades` | Vocabulário fixo que descreve o que a integração faz. |

Integrações são **registradas explicitamente** em `integracoes_padrao()`.
Instalar um serviço nunca executa plugin arbitrário. O consumo na interface é
genérico: `RegistroIntegracoes.listar()` devolve DTOs serializáveis (via
`apresentar()`), e o QML apenas itera as chaves — por isso adicionar uma
capacidade nova não exige mexer no QML.

## Os 3 passos

### Passo 1 — criar o módulo de rede

Copie `codigo/bib_nucleo/rede/_modelo.py` para
`codigo/bib_nucleo/rede/<fonte>.py` e ajuste. Ele já traz o esqueleto de
`buscar`/`detalhes` com validação de entrada, `rede_ativa()`, timeout curto,
User-Agent e retorno simples — e é **importável sem efeito colateral**
(nenhuma rede no import).

```python
# codigo/bib_nucleo/rede/minha_fonte.py
from __future__ import annotations

from bib_nucleo import online
from bib_nucleo.rede import rede_ativa

def buscar(termo, limite=10):
    termo = (termo or "").strip()
    if len(termo) < 2:
        raise ValueError("Digite pelo menos dois caracteres.")
    if not rede_ativa():
        return []
    dados = online.requisitar_json("https://api.exemplo.test/search?q=" + termo)
    return [{"titulo": item["title"], "url": item["url"]}
            for item in (dados.get("results") or [])[:limite]]
```

### Passo 2 — registrar a integração

Em `integracoes_padrao()` (`codigo/frontends/servicos_ui/integracoes.py`):

```python
Integracao("minha-fonte", "Minha Fonte", "Catálogo conectado.",
           "catalogo", "MF", "#62d4ad",
           buscar=bib_nucleo.rede.minha_fonte.buscar,
           capacidades=("busca",)),
```

Nada mais em QML/bridge é necessário: `listar()`, `buscar()` e `url_integracao()`
já operam sobre qualquer item registrado.

### Passo 3 — teste hermético

Adicione um caso `teste_*` em `codigo/ferramentas/testes/` (padrão do runner;
o sandbox já isola dados e bloqueia rede/processos). Valide entrada inválida,
modo avião (`BIBLIOTECA_REDE=0`) e o DTO. Sem rede real, sem instalar nada.

```powershell
py -3.14 -B codigo/ferramentas/testes/executar.py --modulo test_integracoes_modulares
```

## Vocabulário de capacidades

Fixo, em `CAPACIDADES`. Uma integração pode ter várias, sempre ordenadas.

| Capacidade | Significado | Sinal no código |
|---|---|---|
| `busca` | Pesquisa catálogo/provedor. | `buscar is not None` |
| `abrir` | Abre destino externo no navegador. | `url` preenchida |
| `midia` | Trabalha com música/vídeo/capas. | tipo `musicas_online`/`provedores` |
| `download` | Gerencia downloads/torrentes. | tipo `download` |
| `emulador` | Integra emulador/ROMs. | tipo `emulador` |
| `config` | Expõe presets/opções. | (decisão de produto) |

As 7 integrações padrão: `steamrip`/`fitgirl` → `busca`;
`azahar` → `emulador`, `config`; `desmume` → `emulador`;
`qbittorrent` → `download`; `spotify`/`capas` → `midia`. Personalizadas
derivam a capacidade do `tipo` e da presença de `url` (`_capacidades_para`).

## Segurança e privacidade

- **Rede sob ação do usuário.** Provedor só é consultado quando o usuário
  pesquisa/abre; o import do módulo não faz I/O.
- **`BIBLIOTECA_REDE=0`** é o modo avião: `rede_ativa()` desliga tudo e
  `exigir_rede()` levanta erro claro. Respeite a flag em todo módulo de rede.
- **Timeout curto** (a UI não deve travar) e **User-Agent** identificável.
- **Cache local** para resultados e imagens (`online.cache_path`,
  `online.ler_json`/`gravar_json`); falha de rede não é cacheada como sucesso.
- **Nunca logar segredos.** Credenciais ficam em `dados/provedores-online.json`
  ou variáveis de ambiente; nunca vão para a UI, logs ou relatórios. Segredos
  recusados são regravados pelo usuário no Hub, nunca pelo chat.
- **Testes sintéticos.** Use fixtures/dados de mentira e o runner hermético;
  nenhum teste abre rede, joga ou escreve fora do sandbox.
- **URLs** precisam ser `https` válidas e sem credenciais embutidas
  (`online.url_https`).

## Ponteiros

- Template copiável: `codigo/bib_nucleo/rede/_modelo.py`.
- Registro e capacidades: `codigo/frontends/servicos_ui/integracoes.py`.
- Provedores reais de referência: `codigo/bib_nucleo/rede/musica_online.py`,
  `metadados.py`.
- Testes: `codigo/ferramentas/testes/test_integracoes_modulares.py`.
