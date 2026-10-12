# Trabalho coordenado no TucoTeca

## Identificação obrigatória

Antes de editar, confirme o diretório e `git status --short --branch`.

| Pasta | Branch esperado | Responsabilidade |
|---|---|---|
| `assistentes/Assistente 1` | `assistentes/a1-1.1.0` | Interface Qt, controle e ferramentas dos emuladores |
| `assistentes/Assistente 2` | `assistentes/a2-1.1.0` | Núcleo, Everything e integrações |
| `assistentes/Assistente 3` | `assistentes/a3-1.1.0` | Testes, segurança, CI e documentação |

Nos worktrees acima, leia `.assistente/TAREFAS.md` e o roadmap compartilhado em
`../ROADMAP.md`. Leia também `CONTRIBUTING.md` e a arquitetura pertinente.
Se pasta/branch não coincidir, ou os arquivos de coordenação estiverem ausentes,
pare e peça orientação; não troque branch nem recrie a estrutura automaticamente.
Fora dessas três áreas, estas regras são gerais e a atribuição é do coordenador.

Duas outras pastas existem e **não** recebem prompt de assistente:
`revisao/` (branch `revisao/assistentes-1.1.0`, área de revisão do coordenador)
e `Dev/trabalho` (branch `dev/trabalho`, área de trabalho do coordenador).

Branches da rodada anterior — `assistentes/assistente-1`,
`assistentes/assistente-2`, `assistentes/assistente-3` e
`assistentes/base-1.1.0` — são histórico preservado: o trabalho delas já foi
integrado a `main` (`da163e7`). Use os branches novos acima como base; não
reposicione nem reutilize os antigos.

## Isolamento e coordenação

- Trabalhe somente no seu worktree e dentro do escopo de `TAREFAS.md`.
- Não editar fontes de outro assistente, a pasta oficial ou worktrees antigos.
- `../ROADMAP.md`, `../BASE.json` e `../INTEGRACAO.md` são somente leitura
  para os assistentes. Atualize apenas seus próprios relatórios locais.
- Pedidos fora do escopo vão em `.assistente/SOLICITACOES.md`; o coordenador
  encaminha ao outro chat. Não há comunicação automática entre os chats.
- Faça commits locais focados, quando a tarefa estiver validada, somente no
  branch próprio. Staging por caminhos explícitos; não usar `git add .`.
- Sem push, merge, rebase, tags, release ou dispatch de CI por conta própria.
- Nunca resetar, sobrescrever ou apagar alterações que você não criou.
- Não disparar outros agentes/subagentes sem solicitação explícita do usuário.

## Dados, instalação e privacidade

- Não abrir/copiar/mover/apagar dados pessoais, coleção, saves, jogos, ROMs,
  credenciais ou históricos da instalação antiga. Essa consolidação é central.
- Não seguir junctions como se fossem cópias independentes.
- Não instalar/reconfigurar serviços, Everything, emuladores ou runtimes reais.
- Sem elevação UAC, execução de jogos, downloads reais ou escrita fora da área
  de desenvolvimento durante testes. Use subprocessos/rede simulados.
- Segredos recusados devem ser atualizados pelo usuário no Hub, nunca no chat.
- Repositório e releases continuam privados. Não anexar provas/dados locais.
- Steam é catálogo/wishlist/referência, não launcher nem sync de conquistas.
- Entrega Windows sem assinatura é decisão do usuário; comunicar, não bloquear.

## Código e validação

- Preserve aliases legados e integração S0–S8/R4/R5.
- Núcleo Python stdlib; Qt/PySide6 opcional na fronteira da interface.
- Não reescrever o domínio para implementar a paridade visual.
- Use fixtures/dados sintéticos e o runner hermético existente:
  `python -B codigo/ferramentas/testes/executar.py --modulo <modulo>`.
- Suíte completa: `python -B codigo/ferramentas/testes/executar.py`.
  Pytest/cobertura, quando disponíveis: `python -B -m pytest --cobertura`.
- Lint: `ruff check codigo conftest.py`; confira também `git diff --check`.
- Provas e caches ficam em `.provas/` do próprio worktree.
- O Python global pode não ter Qt/pytest. Não instalar pacotes num ambiente
  compartilhado nem usar `pip install -e` apontando para outra área. Prepare
  ambiente próprio quando necessário e registre dependências/pulos.
- Não reduzir gates, mascarar falhas, inventar provas físicas/remotas ou tratar
  uma simulação como validação de hardware/serviço vivo.
- Declare resultados, limitações e pendências em `.assistente/ENTREGA.md`.
- `VERSION`, versão do pacote, `README.md`, `CHANGELOG.md`, lock de release e
  publicação ficam reservados ao coordenador, salvo atribuição expressa.
