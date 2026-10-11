# Changelog

Todas as mudanças relevantes do TucoTeca. Formo: [SemVer](https://semver.org/),
seções inspiradas em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não lançado]

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
