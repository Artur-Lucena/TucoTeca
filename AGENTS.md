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

- Núcleo Python stdlib; a única interface é o app Electron
  (`codigo/frontends/electron`, ponte NDJSON em `ponte.py`), no Windows e no
  macOS (Intel e Apple Silicon). A TUI saiu na 2.0. Não reintroduzir
  tkinter, Qt/PySide6, curses nem um "modo clássico".
- Código importa o módulo dono (`from bib_nucleo import banco`); a fachada
  `bib_core` saiu na 2.0. Nos testes, `patch.object` mira esse módulo.
- Diferenças de SO ficam atrás de `sys.platform`/`eh_mac()` no núcleo e de
  `window.tucoteca.plataforma` (`ehMac()`) no renderer; testes de caminho
  passam a plataforma explicitamente (rodam em Windows e macOS no CI).
- Raiz enxuta: só README, LICENSE, AGENTS.md, pyproject.toml, `.git*`,
  `TucoTeca.bat` e as pastas `.github`, `codigo`, `docs`.
- Não reescrever o domínio para implementar a paridade visual.
- Testes: `py -3.14 -B codigo/ferramentas/testes/executar.py --alterados` durante o
  trabalho (só os casos afetados); `-k`, `--modulo`, `--falhas`; sem argumentos =
  tudo, em paralelo. Camadas só dependem para baixo (`test_arquitetura.py`).
  Electron: `npm --prefix codigo/frontends/electron run typecheck` e `npm test`.
  Gates juntos: `py -3.14 -B codigo/ferramentas/validar.py`. O CI
  (`.github/workflows/testes.yml`) roda a suíte em Windows, Linux e macOS e
  gera/testa as `.dmg`; prova de Mac é o CI ou um Mac real, nunca simulação.
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
