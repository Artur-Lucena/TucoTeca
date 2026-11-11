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

No Linux/macOS, os mesmos scripts de núcleo/testes usam `python3`.
Uma instalação sem emuladores/coleção é válida para desenvolver o núcleo.

No Linux, para uma coleção descartável (a variável aponta para a pasta-mãe
de `dados/`, não para o banco):

```sh
export BIBLIOTECA_HOME="$(mktemp -d)"
python3 codigo/frontends/app_tui.py --selftest
python3 codigo/ferramentas/testes/executar.py --modulo test_linux_portabilidade
```

`--selftest` usa tela simulada e também pode rodar no Windows sem curses.
Para a TUI interativa no Linux/macOS, execute `./BibliotecaHub.sh` (ou
`BibliotecaHubMac.command`) em um terminal.

## Pontos de entrada para mudanças

- Banco/CRUD/migrações: `codigo/bib_nucleo/banco.py`.
- Importação/dedup/ROMs: `codigo/bib_nucleo/scans/` (pacote fatiado por
  contrato; `scans_hydra.py` é o adaptador Hydra).
- Lançamento/presets/mods: `codigo/bib_nucleo/emuladores/` (pacote).
- Coleção portátil: `pacotes.py`.
- Áudio/download: `musicas.py`, `baixar.py`, `player.py`.
- Volume geral Windows: `volume.py`.
- Integração remota: `codigo/bib_nucleo/rede/`, sob `BIBLIOTECA_REDE`.
- Recursos pessoais: `saves.py`, `preferencias_pessoais.py`, `estatisticas.py`,
  `sessoes_manuais.py`; domínios de arquivos independentes da UI.
- Desktop/TUI: `codigo/frontends/`.
- Desktop Electron: `electron/` (main, preload, renderer Preact) fala com
  `ponte.py`, que expõe os casos de uso de `servicos_ui/` (mixins por
  domínio). Método novo: implementar no serviço, registrar na ponte, cobrir
  em `test_ponte.py` e chamar no renderer. Detalhes em
  [DESKTOP_ELECTRON](DESKTOP_ELECTRON.md). Testes: `--modulo test_ponte` e `npm test`.
- Terminal Linux/macOS: `app_tui.py` + mixins `tui_*.py`.
- Instalador: `electron/electron-builder.config.cjs` (o que entra em `resources/tucoteca`).

O índice detalhado está em [ARQUITETURA](ARQUITETURA.md).

## Convenções

- Python stdlib no núcleo; dependências opcionais são importadas na
  fronteira da funcionalidade. Imports Win32 somente em ramos Windows.
- Português nos nomes/mensagens existentes; imports stdlib antes dos locais.
- `__all__` explicita APIs públicas. `bib_core` é compat; novos utilitários
  internos podem importar os módulos de origem diretamente.
- Caminhos locais são configuráveis por ambiente. `dados/` nunca é fonte.
- Alteração de coleção inicia com backup; substituição de arquivos finais
  usa publicação atômica quando aplicável (`arquivos.py`).
- SQLite: conexão própria por worker; fechar em `finally`/`closing`.
- Renderer só fala por IPC (`window.tucoteca`); nada de Node/`file://` no renderer.
- MCI: preparar/hash/converter fora da UI, abrir/play/status/close na thread
  dona do dispositivo. Caminhos longos usam cópia em cache temporário curto,
  nunca movem o original. Não interpretar erro de consulta como fim da faixa.
- `.gitattributes`: `.py/.sh/.command/.md` em LF; `.bat` em CRLF.

## Testar a alteração

```powershell
py -3.14 codigo/ferramentas/testes/executar.py --modulo test_musica
py -3.14 codigo/ferramentas/testes/executar.py --caso test_fontes.py teste_steamrip_nome_e_download_incompleto
py -3.14 codigo/ferramentas/testes/executar.py
```

### Validação completa em um comando (substitui a CI hospedada)

```powershell
py -3.14 -B codigo/ferramentas/validar.py                 # tudo (~12 min)
py -3.14 -B codigo/ferramentas/validar.py --sem-pytest    # rápido (~2 min)
py -3.14 -B codigo/ferramentas/validar.py --modulo test_ponte --sem-pytest
```

Roda Ruff (venv, PATH ou `python -m`; senão substituto `py_compile` +
trailing), o mypy dos builders (se disponível; pula sem falhar quando
ausente), a suíte completa, a cobertura dos subprocessos, typecheck + vitest
do Electron (quando há `node_modules`) e confere a árvore
Git; grava o relatório em
`.provas/gates-local-<timestamp>.json`. A matriz hospedada (`testes.yml`)
está **desativada** — `workflow_dispatch` manual, sem custo: o billing da
conta do GitHub bloqueia jobs automáticos e a validação local é equivalente
para stdlib e Electron. O que **não** existe localmente: gitleaks (binário
ausente no Windows), Python 3.10, Ubuntu e macOS — a suíte cobre caminhos
cross-SO por patches, mas uma rodada em WSL/Linux continua sendo a paridade
mais fiel quando disponível. Rode `validar.py` antes de commitar/mergear;
uma alteração que não passa localmente não deve ser empurrada.

- Casos são funções `teste_*` em `codigo/ferramentas/testes/test_*.py`.
- A suíte cria a sandbox automaticamente, inclusive com `--caso`.
- Pytest coleta por AST e usa o mesmo subprocesso/sandbox por caso.
  `--cobertura` mede os casos, não só o coletor; HTML/JSON em `.provas/cobertura/`.
- Lint: `ruff check codigo conftest.py` está limpo (0 achados desde a revisão
  R4). As exceções (`E402`, `F403`) estão declaradas em `pyproject.toml` com
  justificativa, não escondidas no diff.
- Tipos: `mypy` cobre hoje `codigo/ferramentas` (builders) em modo gradual —
  `[tool.mypy]` no `pyproject.toml`; o `validar.py` roda o passo quando
  `.provas/venv-tipos` ou o PATH tiverem mypy e pula (sem falhar) quando
  ausente. Ampliar o escopo ao núcleo é incremental, sem bloquear a rodada.
- Simule rede/subprocessos e use arquivos locais pequenos em fixtures.
- Executáveis falsos nativos Linux/macOS precisam de `chmod(0o755)`; use
  nomes sem `.exe`. Ao simular Linux no Windows, injete `sys.platform`
  ou um proxy `os` no módulo-alvo; trocar `os.name` global altera `pathlib`.
- Não execute jogos nem áudio real pela suíte; provas manuais ficam fora
  dos testes herméticos e devem descrever SO, duração e resultado.
- Preserve os ramos Linux/macOS; casos Mac simulados não substituem um Mac real.

### Provas do app empacotado

```powershell
py -3.14 -B codigo/ferramentas/preparar_runtime_python.py
npm --prefix codigo/frontends/electron run dist
py -3.14 -B codigo/ferramentas/semear_prova_electron.py --destino .provas/app/home --limpar
$env:BIBLIOTECA_HOME = "$PWD\.provas\app\home"; $env:TUCOTECA_USERDATA = "$PWD\.provas\app\ud"
codigo\frontends\electron\dist\win-unpacked\TucoTeca.exe --selftest --screenshot .provas\app\inicio.png
```

O selftest sobe a ponte com o Python embutido, carrega a coleção sintética e
sai com 0. Provas nativas opcionais (`provar_qbit_runtime.py`,
`provar_rede_runtime.py`) ficam fora da suíte e registram versão/data/limites;
contrato mockado não prova disponibilidade de um host.

Lint: `ruff check codigo conftest.py` completo está **limpo** (revisão R4).
O gate crítico continua como exigência mínima:
`ruff check codigo conftest.py --select E9,F63,F7,F82`.

Duas exceções estão declaradas em `pyproject.toml`, com justificativa no
próprio arquivo — nenhuma regra foi silenciada sem registrar o motivo:

- `E402`: imports no meio do arquivo quebram ciclos de importação de propósito
  (`banco`↔`banco_desejos`, `scans`↔`scans_hydra`, `emuladores`↔
  `sessoes_manuais`, `musicas`↔`rede.metadados`, `baixar`↔`rede.binarios`);
- `F403` em `bib_core.py`: a fachada reexporta a API via `__all__` de cada
  módulo justamente para preservar consumidores antigos.

Um `--fix` automático não é neutro: `F841` remove ligações locais, `I001`
reordena imports e `F401` apaga imports usados só em tipos anotados. Rode a
suíte depois de qualquer `--fix`.

## Fluxo de trabalho em conjunto

Combine um responsável por cada mudança antes de editar os mesmos arquivos.
Revise status/diff e execute os testes sobre uma versão estável da árvore.
Registre no relatório/PR: problema reproduzido, alteração, verificações e
limites ainda existentes. Use commits focados e revisão do diff completo;
uma alteração na UI não deve absorver silenciosamente trabalho paralelo.

## Preparar uma release privada

1. Atualize `VERSION`, `pyproject.toml`, `package.json` do Electron e a seção
   do `CHANGELOG.md` (o preparador recusa divergência). Árvore limpa e gates
   locais verdes (`python -B codigo/ferramentas/validar.py`) no SHA do commit.
2. Gere o instalador: `preparar_runtime_python.py` e `npm run dist`.
3. Monte a pasta da release:

   ```powershell
   py -3.14 codigo/ferramentas/preparar_release.py --revisao <SHA> --saida dist/release/v<versão>
   ```

   Sai o instalador, o pacote de fontes, `NOTAS-RELEASE.md`, `release.json` e
   `SHA256SUMS.txt`. O script recusa destino existente e não deixa entrega parcial.
4. Crie uma tag normal e uma release em **rascunho**, anexe os arquivos,
   confira tamanhos/hashes no servidor e só então publique. Nunca mova uma tag
   enviada nem use force-push. Nenhum script do projeto publica sozinho.

O procedimento detalhado está em [RELEASES.md](RELEASES.md).

O pacote de coleção do Hub continua sendo o caminho para levar a biblioteca
pessoal entre máquinas; a release nunca a inclui.

A entrega ZIP representa **arquivos atuais**, não só o HEAD do Git. Para
comparar uma entrega, verifique `MANIFESTO-FONTES.json`; para inspecionar
histórico e branches, use o repositório Git fornecido pelo responsável.
Congele os fontes antes dos gates/builds; o preparador confere o app
empacotado contra essa mesma revisão. Entregas são pessoais/locais, sem workflow
de release pública, force-push ou reescrita adicional de histórico.
