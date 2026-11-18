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
- Repositório e releases são públicos: nunca anexar provas, dados locais,
  capas comerciais ou dados pessoais (e-mail, caminhos, nomes) a commits.
- Steam é catálogo/wishlist/referência, não launcher nem sync de conquistas.
- Rede só por ação do usuário. Exceções aprovadas: o Calendário de Filmes e
  Séries renova as séries seguidas ao abrir a aba (no máximo a cada 12 h) e o
  RetroAchievements lê o progresso da conta do próprio usuário, com a chave
  que ele informou. Abrir Catálogo/Descobrir conta como pedido do usuário.
- Filmes e Séries: só os arquivos do usuário + catálogo Cinemeta; nada de
  streams, torrents ou addons. O indexador só lê nomes, tamanhos e 2 MB por
  arquivo dentro das pastas escolhidas.
- Entrega Windows sem assinatura é decisão do usuário; comunicar, não bloquear.

## Código e validação

- Núcleo Python stdlib; o desktop é o app Electron (`codigo/frontends/electron`,
  ponte NDJSON em `ponte.py`). A TUI curses atende Linux/macOS. Não
  reintroduzir tkinter, Qt/PySide6 nem um "modo clássico".
- Raiz enxuta: só README, LICENSE, AGENTS.md, pyproject.toml, `.git*`, um
  lançador por SO (`TucoTeca.bat`, `tucoteca.sh`) e as pastas `.github`,
  `codigo`, `docs`. Os aliases `BibliotecaHub.*` foram removidos na 1.4.7.
- Não reescrever o domínio para implementar a paridade visual.
- Testes: `py -3.14 -B codigo/ferramentas/testes/executar.py [--modulo <modulo>]`.
  Suíte completa: sem argumentos. Pytest/cobertura quando disponíveis.
  Electron: `npm --prefix codigo/frontends/electron run typecheck` e `npm test`.
  Gates juntos: `py -3.14 -B codigo/ferramentas/validar.py`.
- Lint: `ruff check codigo` (venv própria em `.provas/venv-ruff` se
  o Python global não tiver) e `git diff --check`.
- Provas e caches ficam em `.provas/`.
- Não reduzir gates, mascarar falhas, inventar provas físicas/remotas ou tratar
  uma simulação como validação de hardware/serviço vivo.
- Declare resultados, limitações e pendências no relatório final do trabalho.

## Git e publicação

- Commits focados, staging por caminhos explícitos; não usar `git add .`.
- Push, merge, tags e releases só com pedido explícito do usuário.
- Nunca resetar, sobrescrever ou apagar alterações que você não criou.
- `codigo/VERSION`, `README.md`, `docs/CHANGELOG.md`, lock de release e
  publicação: por pedido explícito. A versão vive em `codigo/VERSION`, `pyproject.toml` e
  `codigo/frontends/electron/package.json` — sempre as três juntas.
