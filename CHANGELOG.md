# Changelog

Todas as mudanças relevantes do TucoTeca. Formo: [SemVer](https://semver.org/),
seções inspiradas em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não lançado]

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
