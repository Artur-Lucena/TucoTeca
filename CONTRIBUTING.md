# Colaboração técnica

## Ambiente e primeiro ciclo

1. Use Python 3.10+ para o núcleo; o desktop principal é Qt/PySide6
   (`requirements-ui.txt`). `requirements-extras.txt` adiciona Chromium e
   QtMultimedia para a variante completa (não implementa gamepad).
   Tk é usado pelas ferramentas clássicas.
   O desenvolvimento local Windows usa Python oficial 3.14.
2. Abra o terminal na raiz do projeto.
3. Execute `python codigo/ferramentas/diagnosticar.py` e a suíte abaixo.
4. Use uma `BIBLIOTECA_HOME` de desenvolvimento para experimentar a UI.

```powershell
$env:BIBLIOTECA_HOME = Join-Path $env:TEMP "tucoteca-dev"
py -3.14 -m pip install -e '.[dev,ui]'
py -3.14 -B codigo/frontends/app_qt.py --selftest
py -3.14 -B codigo/frontends/app_win.py --selftest
py -3.14 -B -m pytest --cobertura
py -3.14 codigo/ferramentas/testes/executar.py --json "$env:TEMP\tucoteca-testes.json"
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
Para a TUI interativa Linux, execute `./BibliotecaHub.sh` em um terminal.
Matriz de compatibilidade e procedimentos: [revisão Linux](docs/REVISAO_LINUX_W11.md).

## Pontos de entrada para mudanças

- Banco/CRUD/migrações: `codigo/bib_nucleo/banco.py`.
- Importação/dedup/ROMs: `scans.py`.
- Lançamento/presets/mods: `emuladores.py`.
- Coleção portátil: `pacotes.py`.
- Áudio/download: `musicas.py`, `baixar.py`, `player.py`.
- Volume geral Windows: `volume.py`.
- Integração remota: `codigo/bib_nucleo/rede/`, sob `BIBLIOTECA_REDE`.
- Recursos pessoais: `saves.py`, `preferencias_pessoais.py`, `estatisticas.py`,
  `sessoes_manuais.py`; domínios de arquivos independentes da UI.
- GUI/TUI: `codigo/frontends/`; thread dispatch: `despacho.py`.
- Desktop Qt: `app_qt.py`, `qt_bridge.py`, `servicos_ui.py` e `qml/`.
  Instale `requirements-ui.txt`; arquitetura e matriz de migração em
  [DESKTOP_QT](docs/DESKTOP_QT.md). Testes: `executar.py --modulo test_qt`.
- Layout dos bundles: `montar_portatil.copiar_app`, usado pelos três builders.

O índice detalhado está em [ARQUITETURA](docs/ARQUITETURA.md).

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
- Tk só na thread da UI. Workers usam `DespachanteUi.enviar`/`App._depois`.
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

- Casos são funções `teste_*` em `codigo/ferramentas/testes/test_*.py`.
- A suíte cria a sandbox automaticamente, inclusive com `--caso`.
- Pytest coleta por AST e usa o mesmo subprocesso/sandbox por caso.
  `--cobertura` mede os casos, não só o coletor; HTML/JSON em `.provas/cobertura/`.
- Lint: `ruff check codigo conftest.py` está limpo (0 achados desde a revisão
  R4). As exceções (`E402`, `F403`, `F401` em testes de tkinter) estão
  declaradas em `pyproject.toml` com justificativa, não escondidas no diff.
- Simule rede/subprocessos e use arquivos locais pequenos em fixtures.
- Executáveis falsos nativos Linux/macOS precisam de `chmod(0o755)`; use
  nomes sem `.exe`. Ao simular Linux no Windows, injete `sys.platform`
  ou um proxy `os` no módulo-alvo; trocar `os.name` global altera `pathlib`.
- Prova opcional de shell isolada: `python codigo/ferramentas/provar_linux_shell.py`.
  No Windows usa Git Bash; `--ffmpeg` valida os seis presets com WAV sintético.
- Testes de GUI usam root oculto e pulam sem Tk/display.
- Não execute jogos nem áudio real pela suíte; provas manuais ficam fora
  dos testes herméticos e devem descrever SO, duração e resultado.
- Preserve os ramos Linux/macOS; casos Mac simulados não substituem um Mac real.

### Provas e bundles locais

```powershell
py -3.14 -B codigo/ferramentas/provar_qt_runtime.py --extras completo --saida .provas/qt --ffmpeg C:\caminho\ffmpeg.exe
py -3.14 -B codigo/ferramentas/provar_integracoes_locais.py --saida .provas/locais
py -3.14 -B codigo/ferramentas/montar_superhub.py --extras essencial --formato zip
py -3.14 -B codigo/ferramentas/montar_superhub.py --extras completo --formato zip
```

Chromium recebe HTML local com rede bloqueada; áudio/vídeo são sintéticos.
O builder confere hashes, presença/ausência real dos Addons, perfis vazios,
reprodução e API local na árvore montada e no ZIP extraído. Não pula a prova
de áudio quando MCI falha. Smokes remotos ficam fora da suíte e registram
versão/data/limites; contrato mockado não prova disponibilidade de um host.

Lint: `ruff check codigo conftest.py` completo está **limpo** (revisão R4).
O gate crítico continua como exigência mínima:
`ruff check codigo conftest.py --select E9,F63,F7,F82`.

Três exceções estão declaradas em `pyproject.toml`, com justificativa no
próprio arquivo — nenhuma regra foi silenciada sem registrar o motivo:

- `E402`: imports no meio do arquivo quebram ciclos de importação de propósito
  (`banco`↔`banco_desejos`, `scans`↔`scans_hydra`, `emuladores`↔
  `sessoes_manuais`, `musicas`↔`rede.metadados`, `baixar`↔`rede.binarios`);
- `F403` em `bib_core.py`: a fachada reexporta a API via `__all__` de cada
  módulo justamente para preservar consumidores antigos;
- `F401` em testes de tkinter: o import é a prova de disponibilidade do
  módulo (`try: import tkinter`), não código morto.

Um `--fix` automático não é neutro: `F841` remove ligações locais, `I001`
reordena imports e `F401` apaga imports usados só em tipos anotados. Rode a
suíte depois de qualquer `--fix`.

## Fluxo de trabalho em conjunto

Combine um responsável por cada mudança antes de editar os mesmos arquivos.
Revise status/diff e execute os testes sobre uma versão estável da árvore.
Registre no relatório/PR: problema reproduzido, alteração, verificações e
limites ainda existentes. Use commits focados e revisão do diff completo;
uma alteração na UI não deve absorver silenciosamente trabalho paralelo.

A entrega ZIP representa **arquivos atuais**, não só o HEAD do Git. Para
comparar uma entrega, verifique `MANIFESTO-FONTES.json`; para inspecionar
histórico e branches, use o repositório Git fornecido pelo responsável.
Use worktrees separados para implementação, testes e Windows. Congele os
fontes por manifesto antes dos gates/builds; confirme os arquivos do app no
bundle contra essa mesma revisão. Entregas são pessoais/locais, sem workflow
de release pública, force-push ou reescrita adicional de histórico.
