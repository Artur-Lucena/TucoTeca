# Changelog

Todas as mudanças relevantes do TucoTeca. Formo: [SemVer](https://semver.org/),
seções inspiradas em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não lançado]

### Alterado
- **Capas comerciais removidas do repositório e do histórico.** `midia/fontes-capas/`
  agora contém apenas placeholders neutros gerados por
  `codigo/ferramentas/gerar_placeholders.py`. O histórico foi reescrito
  (filter-branch) e os blobs antigos foram purgados. Publicar exige
  `git push --force` e um novo clone para quem já tinha cópia local.
- **Integrações de rede isoladas em `bib_nucleo/rede/`** (fontes, repacks,
  torrents, videos_youtube, musica_online, spotify, online). Nomes antigos
  continuam resolvendo por import preguiçoso.
- **Flag `BIBLIOTECA_REDE=0`** (modo avião): busca de capas, músicas online e
  vídeos devolve erro claro sem tocar a rede.
- **Pasta padrão de downloads: `Meus Jogos Locais`** (antes `Piratas`).
  `BIBLIOTECA_JOGOS_DIR` define a pasta; `BIBLIOTECA_PIRATAS` segue aceito.
  Pasta antiga existente é mantida automaticamente (nada é movido). Funções
  renomeadas com alias legado: `pasta_jogos`, `dentro_do_destino`,
  `organizar_no_destino`, `foraDoDestino` (QML).
- `docs/LEGAL.md`: aviso legal e responsabilidades de uso.

### Corrigido (adicional)
- `app_win.py` importava `bib_nucleo.repacks` (caminho antigo); o botão de
  organizar do clássico quebraria em runtime. Corrigido.

### Corrigido
- `repacks.achar_exe`: exe pequeno em subpasta tinha nota negativa
  (tamanho vale ≤1 ponto, profundidade cobra 3) e desaparecia da lista de
  candidatos. Pontuação agora tem piso 0; instaladores continuam barrados por
  `SKIP_EXE_RE`. Falha pré-existente exposta pelo teste de symlink no Windows.

### Adicionado
- `pyproject.toml`: metadados, extras `ui`/`extras`/`dev`, entry point
  `tucoteca`, configs de pytest/coverage/ruff.
- Suíte rodável via pytest (`conftest.py` + `python_functions = teste_*`);
  o runner sandboxed (`executar.py`) continua como fonte da verdade na CI.
  Nota honesta: sob pytest, 333/358 casos passam; os outros 25 dependem de
  isolamento por processo (caches de módulo que vazam entre testes no mesmo
  processo) e são cobertos integralmente pelo runner.
- Governança: `VERSION`, templates de issue e PR, `SECURITY.md`, job de
  varredura de segredos (gitleaks) na CI.
- `frontends/desktop.py`: garante o próprio diretório no `sys.path`
  (entry point instalável).
