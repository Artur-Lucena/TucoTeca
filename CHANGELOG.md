# Changelog

Todas as mudanças relevantes do TucoTeca. Formo: [SemVer](https://semver.org/),
seções inspiradas em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não lançado]

### Portado da instalação real (revisão R5, 11/10/2026)

A instalação em `D:\Tuco-Compartilhado\Jogos\biblioteca` estava em `051e716`
com trabalho local **não commitado** e divergente de `main`. Todo ele foi
preservado antes de qualquer atualização: patch completo e cópia dos fontes
em `dist/marco-s0-s8/backup-instalacao-real/` (103 arquivos, 1,57 MB).

Portado para o `main` — nada foi descartado:

- `bib_nucleo/processos.opcoes_sem_janela()`: processos de fundo (yt-dlp,
  FFmpeg, 7z, busca) sobem sem janela de console, porque uma GUI iniciada
  com `pythonw` abre terminal próprio para cada console-app. Aplicado em
  `baixar.py`, `equalizadores.py`, `player.py`, `rede/repacks.py` e
  `rede/videos_youtube.py`.
- Fluxo de pacotes em `Pacotes em Piratas…`: `listar_pacotes_piratas`,
  `preparar_pacote` (idempotente, extrai e organiza sem apagar o archive),
  `instaladores_pacote`, `abrir_instalador` e `_estado_pasta`, com
  `importar_pasta` para jogo já instalado. Na UI: slots `atualizarPacotes`,
  `pacotesPiratas`, `tem7z`, `prepararPacote`, `abrirInstaladorPacote` e
  `importarPacote`, mais `PiratasDialog.qml` e o botão na seção Downloads.
- `_importar_exe` extraído de `importar_repack`: os dois caminhos de importação
  compartilham a mesma cauda (título/canonização/capa), em vez de duplicar.
- `opcoes_sem_janela` também no `abrir_instalador` (ramo não-Windows), onde a
  instalação usava a função sem importá-la no escopo — que só não quebrava
  porque o caminho Windows não chega lá.

Verificado: `ruff` limpo, fachada `bib_core` intacta (380 exportados) e
51 casos de repacks/UI/visual sem falha.

Os diálogos QML da instalação diferiam apenas em estilo e acentuação (uma
ferramenta havia reintroduzido `?` no lugar de `…`). Os contratos `hub.*` são
idênticos nos dois lados, portanto essa diferença não foi copiada.

### Higienizacao de lint (revisao R4, 11/10/2026)
- `ruff check codigo conftest.py` **limpo**: 246 achados → 0. Nenhuma regra
  silenciada sem justificativa registrada; as tres excecoes restantes estao
  declaradas em `pyproject.toml`.
- `E741` (18): `l` ambíguo renomeado para `linha`/`alvo`/`limpa` em `cheats.py`,
  `controles.py`, `emuladores.py`, `montar_superhub.py`, `test_s7b_externos.py`
  e `app_tui.py`. Duas correcoes incompletas deixaram `F821` (nome indefinido)
  em `controles.py`, pego na validacao seguinte.
- `F841` (16): variavel morta `troca` removida de `scans.py` (atribuida e
  nunca lida) e 15 atribuicoes `tmp`/`g` sem uso em testes.
- `F401` (29 automaticas): imports nao usados, incluindo o `PIL.Image` de
  `banco.py` (so `ImageFilter` era usado).
- `F811` (3): `from bib_nucleo import base` sombreado pela variavel local em
  `test_mac.py`, agora importado como `mbase`.
- `E702`/`E701`/`E731` (16): ponto-e-virgula e lambdas atribuidas quebradas
  em linhas proprias, `f.write(x); h.update(x)` de `atualizacao.py` incluido.
- `I001` (120): ordenacao de imports. Em `bib_core.py` a reodenacao
  reorganizou os reexports `*` da fachada; os 375 nomes de `__all__`
  continuam acessiveis, conferido por script.
- Excecoes declaradas (nao escondidas no diff): `E402` para imports no meio
  do arquivo que quebram ciculos de proposito; `F403` em `bib_core.py`, que e
  fachada de compatibilidade; `F401` em testes de tkinter, onde o import e a
  prova de disponibilidade do modulo.

### Validado e integrado (revisão R3, 11/10/2026)
- Suíte completa: 412 casos stdlib sem falha (6 pulos por ambiente) e
  406 passed/6 skipped no pytest, com 63% de cobertura real dos subprocessos.
- Rodada sem PySide6 (`python -S`): 14 casos, 0 falhas, 11 pulos — o núcleo
  continua utilizável e a UI degrada em vez de falhar.
- Lint crítico (`E9,F63,F7,F82`) limpo; o lint completo mantém 246 achados de
  estilo/import como pendência declarada, não como resultado verde.
- Gitleaks 8.30.1 sem segredos nos fontes empacotados e nos 79 commits locais.
- Bundles Windows validados na árvore e no ZIP extraído: essencial 215.73 MB
  (SHA-256 `338d3f6813983fd2d95d5558e2e93ec8d839c6cebdb18ded0b3e86704bb0ece6`)
  e completo 361.65 MB (SHA-256 `5db6ec4926a754d346f4924ed14335aeb8c3e6e0df6923aed2d610850c20ac2c`).
- Provas nativas: 12 capturas em 1440×920 e 960×640, áudio MCI com destaque
  LRC em caminho longo (190 → 104 caracteres, original intacto), Chromium com
  perfil privado e allowlist, vídeo sintético com retomada de 1000 ms.
- Integração local: `feat/s7b` mesclado em `main`; `qa/testes`, `os/windows` e
  `feat/youtube-embed` alinhados por fast-forward. Sem force-push.
- Entrega de revisão em `dist/marco-s0-s8/` (bundles, SHA256SUMS, relatórios
  de verificação e fontes R3, ZIP `be7e25ba…68c4`).

### QoL pessoal e correções de contratos
- Fluxo de desejos com fontes, SteamRip → importação e histórico de obtidos;
  falhas preservam o desejo/arquivo. FitGirl permanece página externa.
- LRCLIB com cache local, parsing LRC, solicitações sequenciais e destaque da
  linha durante a faixa correspondente; LibRetro como provedor de capas 3DS/NDS.
- Perfis Tuco/Isa, atalhos configuráveis, notas, galeria de screenshots,
  vigia de pacotes opt-in, API loopback de leitura autenticada e histórico anual.
- Saves configurados por jogo: snapshots reais e restauração com SHA-256 e
  cópia prévia dos saves atuais. Backup automático aguarda a gravação das horas.
- Player MCI prepara cópia em cache temporário curto para WAVs em caminhos
  longos, com publicação atômica e original preservado. Prova nativa cobre
  áudio/LRC nesses caminhos. Backup pós-sessão respeita o opt-out persistido.
- `montar_superhub.py` confere arquivo por arquivo (SHA-256) que o `app/` do
  runtime corresponde à revisão congelada e recusa arquivos obsoletos ou
  divergentes; a prova de runtime usa quarentena curta, porque `TEMP`
  profundamente aninhado quebra a descoberta de Known Folders no Windows.
- Casos de UI que dependem de PySide6 agora pulam explicitamente quando o
  módulo não existe, em vez de falhar; prova com `python -S` cobre esse caminho.
- IPS/BPS com CRC/limites, saída nova e original intacto; hardlinks opt-in com
  fallback de cópia, sem junctions automáticas.
- QtMultimedia opcional, retomada/velocidade, MP3 por URL/ID e SponsorBlock opt-in.
- Atualização de yt-dlp/FFmpeg com versões/sha fixados; erro de hash não substitui
  a instalação anterior. FTS5 não reconstrói o índice a cada abertura.
- Seções extraídas de `Main.qml` para `qml/secoes/`, carregadas por Loader.
- Pytest coleta sem importar os testes e executa cada caso no runner sandboxed;
  cobertura opcional mede os subprocessos. O resultado antigo 333/358 não
  descreve mais esta implementação.
- Bundles essencial/completo isolados, provas da variante correta após extração,
  capturas, Chromium local e reprodução de vídeo sintético (não só import de DLL).
- Pacotes com exportação atômica, limites de tamanho, recusa de links/nomes
  Windows reservados e backup dos presets/saves antes de sobrescrevê-los.
- Workflow de publicação pública removido: builds somente locais para Tuco/Isa.

### Adicionado
- **YouTube embutido** (variante completa): seção `YouTube` (Ctrl+8) com navegador
  QtWebEngine off-the-record, navegação restrita a https e hosts YouTube e download
  sempre explícito (⬇ Baixar este), validado no Python.
- Variante essencial sem Addons: a seção mostra o aviso e usa a busca/baixar
  existente; `webDisponivel` detecta a presença do motor web.
- `requirements-extras.txt` (PySide6-Addons==6.10.2) e `incluir_qt` que inclui
  os Addons quando `--extras completo`; `validar_runtime` prova o `webengine`
  nessa variante.
- Testes: 4 de validação de URL/hosts/baixar no bridge (hermético).
- Validado: selftest com Addons e simulação de variante essencial (import
  bloqueado) — ambos carregam o `Main.qml`.

### Adicionado
- **Tema claro e densidade** (`Theme.qml` + `bib_nucleo/aparencia_usuario.py`):
  escuro/claro e compacto/conforto/bigpicture, persistidos em
  `dados/aparencia.json` e aplicados pelo bridge ao vivo.
- **Diagnóstico no Hub**: `rodarDiagnostico()` reusa `ferramentas/diagnosticar.py`
  (somente-leitura) em worker e mostra o relatório em diálogo com “Copiar
  relatório”. `diagnosticar.py` passou a inserir o próprio diretório no
  `sys.path` (import de `empacotar_fontes` funcionava só no CLI).
- **Auto-backup pós-sessão** (opt-in, default ligado): ao encerrar sessão
  rastreada, o Hub cria backup da coleção e avisa. Configurável na mesma tela
  de aparência.
- Busca FTS5 (§ anterior) e testes novos: 4 de FTS5, 2 de aparência, 2 de
  bridge Qt (aparência/diagnóstico/auto-backup), 1 da paleta.

### Alterado
- **Capas comerciais removidas do repositório e do histórico.** `midia/fontes-capas/`
  agora contém apenas placeholders neutros gerados por
  `codigo/ferramentas/gerar_placeholders.py`. O histórico foi reescrito
   (filter-branch). O remoto não foi alterado; a publicação do histórico
   divergente exige uma decisão explícita. Nenhum force-push automático.
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
  Na implementação inicial, pytest e runner diferiam. O coletor foi substituído
  para usar processos separados e a mesma sandbox (ver correções acima).
- Governança: `VERSION`, templates de issue e PR, `SECURITY.md`, job de
  varredura de segredos (gitleaks) na CI.
- `frontends/desktop.py`: garante o próprio diretório no `sys.path`
  (entry point instalável).
