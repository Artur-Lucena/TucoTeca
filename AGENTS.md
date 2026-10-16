# TucoTeca — regras de trabalho

## Antes de editar

Confirme o diretório e `git status --short --branch`. Trabalhe só neste
repositório; `dados/`, `programa/`, `dist/` e `.provas/` são locais e nunca
entram no Git.

## Dados e privacidade

- Não abrir/copiar/mover/apagar dados pessoais, coleção, saves, jogos, ROMs,
  credenciais ou históricos de instalações antigas.
- Não seguir junctions como se fossem cópias independentes.
- Não instalar/reconfigurar serviços, Everything, emuladores ou runtimes reais.
- Sem elevação UAC, execução de jogos, downloads reais ou escrita fora da área
  de desenvolvimento durante testes. Use subprocessos/rede simulados.
- Segredos recusados devem ser atualizados pelo usuário no Hub, nunca no chat.
- Repositório e releases continuam privados. Não anexar provas/dados locais.
- Steam é catálogo/wishlist/referência, não launcher nem sync de conquistas.
- Entrega Windows sem assinatura é decisão do usuário; comunicar, não bloquear.

## Código e validação

- Núcleo Python stdlib; Qt/PySide6 é o único desktop (Qt Quick). A TUI curses
  atende Linux/macOS. Não reintroduzir tkinter nem um "modo clássico".
- Preserve aliases legados (`BibliotecaHub.*`) e a integração S0–S8/R4/R5.
- Não reescrever o domínio para implementar a paridade visual.
- Testes: `py -3.14 -B codigo/ferramentas/testes/executar.py [--modulo <modulo>]`.
  Suíte completa: sem argumentos. Pytest/cobertura quando disponíveis.
- Lint: `ruff check codigo conftest.py` (venv própria em `.provas/venv-ruff` se
  o Python global não tiver) e `git diff --check`.
- Provas e caches ficam em `.provas/`.
- Não reduzir gates, mascarar falhas, inventar provas físicas/remotas ou tratar
  uma simulação como validação de hardware/serviço vivo.
- Declare resultados, limitações e pendências no relatório final do trabalho.

## Git e publicação

- Commits focados, staging por caminhos explícitos; não usar `git add .`.
- Push, merge, tags e releases só com pedido explícito do usuário.
- Nunca resetar, sobrescrever ou apagar alterações que você não criou.
- `VERSION`, `README.md`, `CHANGELOG.md`, lock de release e publicação: por
  pedido explícito.
