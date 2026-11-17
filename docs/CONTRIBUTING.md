# Colaboração técnica

## Ambiente e primeiro ciclo

1. Python 3.10+ para o núcleo (desenvolvimento Windows usa o oficial 3.14) e
   Node 24 para o desktop Electron (`codigo/frontends/electron`).
2. Abra o terminal na raiz do projeto.
3. Execute `python codigo/ferramentas/diagnosticar.py` e a suíte abaixo.
4. Use uma `BIBLIOTECA_HOME` de desenvolvimento para experimentar a UI.

```powershell
$env:BIBLIOTECA_HOME = Join-Path $env:TEMP "tucoteca-dev"
py -3.14 -m pip install -e '.[dev]'
py -3.14 -B codigo/ferramentas/testes/executar.py
npm --prefix codigo/frontends/electron ci
npm --prefix codigo/frontends/electron run dev      # janela com hot reload
npm --prefix codigo/frontends/electron test
```

No Linux/macOS os mesmos scripts usam `python3`. Uma coleção descartável (a
variável aponta para a pasta-mãe de `dados/`, não para o banco):

```sh
export BIBLIOTECA_HOME="$(mktemp -d)"
python3 codigo/frontends/app_tui.py --selftest
python3 codigo/ferramentas/testes/executar.py --modulo test_linux_portabilidade
```

`--selftest` usa tela simulada e também roda no Windows sem curses. A TUI
interativa abre com `./tucoteca.sh`.

## Pontos de entrada para mudanças

- Banco/CRUD/migrações: `codigo/bib_nucleo/banco/`.
- Importação/dedup/ROMs/lojas instaladas: `codigo/bib_nucleo/scans/`.
- Lançamento/presets/mods: `codigo/bib_nucleo/emuladores/`.
- Filmes e Séries: `codigo/bib_nucleo/midia/`.
- Coleção portátil: `pacotes.py`. Áudio/download: `musicas.py`, `baixar.py`,
  `player.py`. Volume do Windows: `volume.py`.
- Rede (sempre sob `BIBLIOTECA_REDE`): `codigo/bib_nucleo/rede/`; provedores de
  dados de jogo em `rede/provedores/` (como acrescentar: [INTEGRACOES](INTEGRACOES.md)).
- Desktop Electron: `electron/` (main, preload, renderer Preact) fala com
  `ponte.py`, que expõe os casos de uso de `servicos_ui/` (mixins por
  domínio). Método novo: implementar no serviço, registrar na ponte, cobrir
  em `test_ponte.py` e chamar no renderer ([DESKTOP_ELECTRON](DESKTOP_ELECTRON.md)).
- Terminal Linux/macOS: `app_tui.py` + mixins `tui_*.py`.
- Instalador: `electron/electron-builder.config.cjs` (o que entra em `resources/tucoteca`).

O mapa completo está em [ARQUITETURA](ARQUITETURA.md).

## Convenções

- Python stdlib no núcleo; dependências opcionais são importadas na
  fronteira da funcionalidade. Imports Win32 somente em ramos Windows.
- Português nos nomes/mensagens; imports stdlib antes dos locais.
- `__all__` explicita APIs públicas. `bib_core` é a fachada de compatibilidade
  (TUI e testes); código novo importa os módulos de origem.
- Caminhos locais são configuráveis por ambiente. `dados/` nunca é fonte.
- Alteração de coleção começa com backup; substituição de arquivos finais usa
  publicação atômica (`arquivos.py`).
- SQLite: conexão própria por worker; fechar em `finally`/`closing`.
- Renderer só fala por IPC (`window.tucoteca`); nada de Node/`file://` no renderer.
- MCI: preparar/hash/converter fora da UI, abrir/play/status/close na thread
  dona do dispositivo; caminho longo usa cópia em cache curto, nunca move o
  original.
- `.gitattributes`: `.py/.sh/.command/.md` em LF; `.bat` em CRLF.

## Testar a alteração

```powershell
py -3.14 codigo/ferramentas/testes/executar.py --modulo test_musica
py -3.14 codigo/ferramentas/testes/executar.py --caso test_fontes.py teste_steamrip_nome_e_download_incompleto
py -3.14 -B codigo/ferramentas/validar.py                 # todos os gates (~12 min)
py -3.14 -B codigo/ferramentas/validar.py --sem-pytest    # rápido (~2 min)
```

`validar.py` roda Ruff, o mypy dos builders (pula se ausente), a suíte, a
cobertura, typecheck + vitest do Electron e confere a árvore Git; o relatório
vai para `.provas/gates-local-<timestamp>.json`. A matriz hospedada
(`.github/workflows/testes.yml`) só roda manualmente (`workflow_dispatch`): o
billing da conta bloqueia jobs automáticos. Fora do alcance local: gitleaks,
Python 3.10, Ubuntu e macOS reais. Rode `validar.py` antes de commitar.

- Casos são funções `teste_*` em `codigo/ferramentas/testes/test_*.py`; a
  suíte cria a sandbox sozinha, inclusive com `--caso`. O pytest coleta pelo
  mesmo runner (`--cobertura` mede os casos; saída em `.provas/cobertura/`).
- Lint: `ruff check codigo` limpo; as exceções (`E501`, `E402` e
  `F403` nas fachadas de pacote) estão justificadas no `pyproject.toml`. Um
  `--fix` automático não é neutro (`F401`, `F841`, `I001`): rode a suíte depois.
- Simule rede/subprocessos e use arquivos pequenos em fixtures. Executáveis
  falsos de Linux/macOS precisam de `chmod(0o755)` e nomes sem `.exe`; para
  simular Linux no Windows, injete `sys.platform` ou um proxy `os` no módulo
  (trocar `os.name` global altera `pathlib`).
- Não execute jogos nem áudio real pela suíte. Provas nativas opcionais
  (`codigo/ferramentas/provar_runtime.py qbit|rede`) ficam fora dela; contrato
  simulado não prova disponibilidade de um serviço.

## Fluxo de trabalho em conjunto

Combine um responsável por cada mudança antes de editar os mesmos arquivos.
Revise status/diff e rode os testes sobre uma versão estável da árvore.
Registre no PR: problema reproduzido, alteração, verificações e limites.
Commits focados; uma alteração de UI não absorve trabalho paralelo.

Instalador, prova do app empacotado e publicação de uma release:
[RELEASES.md](RELEASES.md). A release nunca inclui a coleção pessoal; ela
viaja pelo pacote de coleção do próprio Hub.
