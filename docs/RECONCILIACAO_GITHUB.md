# Reconciliação do Projeto-Launcher com a TucoTeca

## Base e proveniência

O repositório canônico é
`https://github.com/Artur-Lucena/Projeto-Launcher`, mantido privado.

Na comparação de 11/10/2026:

- `origin/main` estava em `6466dbedfb5162f7a541834ed6030de96934e95e`;
- a revisão local validada era `b35bac9ec6b31ead3e3ec70b279cf91efd59fc70`;
- os históricos tinham raízes diferentes, sem ancestral comum;
- a contraparte local `598bff1` tinha os mesmos fontes e documentos de
  `6466dbe`, byte a byte por blob Git, exceto pelas dez capas antigas;
- depois dessa base local vieram 20 commits, incluindo os merges S0–S8,
  lint R4 e as correções e regressões R5.

A reconciliação parte do remoto e incorpora a linha local como segundo
histórico do merge. Nenhum commit existente é reescrito. Antes dos ajustes
documentais, a árvore resultante foi conferida contra a árvore de `b35bac9`
(`8c93323f881473664491e68bae5c888cf9efce4d`). No commit de reconciliação
`a50edac`, os fontes em `codigo/` são idênticos aos da R5; apenas a documentação
dessa integração foi atualizada.

O merge torna as duas linhas ancestrais da revisão final. Assim, `main`,
`feat/s7b`, `feat/youtube-embed`, `qa/testes` e `os/windows` podem ser alinhadas
e enviadas por push normal, sem `--force`.

## Árvore de fontes

```text
codigo/
  bib_core.py             fachada de compatibilidade
  bib_nucleo/             persistência, domínio e adaptadores locais
    rede/                  integrações remotas explícitas
  frontends/              Qt Quick, ferramentas clássicas e TUI
    qml/secoes/            telas Qt Quick
  ferramentas/            diagnóstico, provas e empacotamento
    testes/                fixtures sintéticas e testes em sandbox
docs/                      arquitetura, uso, revisões e responsabilidades
.github/                   testes automatizados e modelos de colaboração
```

Os sete módulos antigos de rede não voltam à raiz de `bib_nucleo/`: suas
versões atuais estão em `rede/`, com os aliases de compatibilidade existentes.
`docs/organizacao-local.json` permanece inalterado: registra movimentos antigos
de artefatos locais e não define o comportamento do organizador de jogos.

## O que pode ser enviado

Somente o projeto necessário para desenvolver, testar e empacotar o launcher:
fontes Python/QML, documentação, licença, launchers, dependências declaradas,
configuração de testes e empacotadores.

Não enviar:

- `dados/`, bancos SQLite, saves, perfis pessoais ou marcadores de sessões;
- executáveis de jogos, ROMs, músicas ou vídeos da coleção;
- `programa/`, runtimes locais, `dist/`, ZIPs ou backups pessoais;
- `.provas/`, `.build/`, `.cache/`, `codigo/historico/` e atalhos `.lnk`;
- credenciais, tokens ou arquivos de configuração de provedores pessoais.

A árvore atual e os objetos dos dois históricos são conferidos antes do push,
além da varredura de segredos. Os testes usam arquivos sintéticos; a integração
não executa jogos nem modifica a instalação pessoal, coleção ou atalho.

## Imagens históricas

As dez capas comerciais do remoto antigo ficam fora da árvore final.
Preservar o histórico significa preservar também seus blobs antigos; este
merge não apaga conteúdo histórico. Não há novas capas comerciais no envio
dos fontes atuais. O gerador de placeholders neutros continua disponível
opcionalmente, sem exigir uma pasta `midia/` em um clone limpo.

## Validação e artefatos de release

A referência R5 tinha 413 testes aprovados, seis pulos por ambiente e zero
falhas, com 63% de cobertura real dos subprocessos e Ruff configurado limpo.
Os gates são repetidos sobre a árvore reconciliada antes do envio.

Os empacotadores e instruções do [README](../README.md) continuam sendo a
entrada para preparar releases. Fazer push dos fontes não anexa runtimes nem
cria uma release automaticamente. A compilação deve começar com dados/perfis
vazios e seguir as licenças dos componentes de terceiros.

Os ZIPs R5 em `dist/marco-s0-s8/r5/` permanecem apenas locais, associados a
`b35bac9`. Não devem ser apresentados como builds de um commit posterior
sem nova geração e validação.

## Release privada v1.0.0

A release é montada a partir de uma revisão congelada por
`codigo/ferramentas/preparar_release.py`, que reúne pacote de fontes, bundles
Windows já validados, relatórios de verificação, notas e checksums. Nada é
publicado automaticamente: criar a release no GitHub é passo explícito, com o
repositório privado, e sem coleção, jogos, saves, perfis pessoais ou runtimes
de terceiros. A proveniência de cada bundle fica registrada no
`manifesto-runtime.json` (`revisao_git`, `tucoteca`) e conferida por SHA-256
no builder e na preparação da release.

## Complemento: portabilidade dos testes na CI

A primeira execução da `main` em `a50edac` foi
[38152335953](https://github.com/Artur-Lucena/Projeto-Launcher/actions/runs/38152335953).
Qt Linux e Gitleaks passaram; os quatro jobs stdlib e Qt Windows apontaram
quatro pressupostos dos testes: tamanho máximo do desktop virtual, ausência
de gerenciador de janelas no Xvfb, largura fixa em vez da largura disponível
da sidebar e resolução de symlinks em loop ao removê-los no Python 3.10.

O complemento altera apenas o harness, testes e configuração de CI. As
asserções de fullscreen/layout são mantidas, com espera limitada; Openbox
fornece fullscreen real no Linux. O sandbox verifica os pais resolvidos ao
remover uma entrada, mas continua seguindo o alvo de escritas e SQLite.
Quatro testes adicionais garantem remoção segura e veto a escapes, inclusive
por `..` ou links nos pais, sem realizar operações reais fora do sandbox.
Outro teste simula explicitamente o máximo de um desktop de 1024×768 para
garantir que ele não limite as geometrias da prova visual.

Os fontes de runtime e os artefatos R5 não mudam; a instalação pessoal não
recebe esse complemento de infraestrutura de testes.

Gates locais do complemento: runner com 424 casos, zero falhas e seis pulos;
pytest com 418 testes aprovados, seis pulos e 63% de cobertura real. Ruff
configurado, actionlint 1.7.12 e Gitleaks limpos. A conclusão da execução remota
deve ser conferida no GitHub Actions, não presumida a partir desses gates.
