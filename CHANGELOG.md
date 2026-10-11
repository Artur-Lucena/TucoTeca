# Changelog

Todas as mudanças relevantes do TucoTeca. Formo: [SemVer](https://semver.org/),
seções inspiradas em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não lançado]

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
