# Changelog

Todas as mudanças relevantes do TucoTeca. Formato: [SemVer](https://semver.org/),
seções inspiradas em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [1.4.0] - 2026-11-14

Primeira etapa da 1.4 (hub de Jogos, Filmes e Séries e Músicas): correções e
limpeza antes das telas novas. Visual igual ao da 1.3.1 (conferido por
captura de tela do app instalado).

### Corrigido

- **Buscar capa** no detalhe do jogo nunca mostrava resultados (lia o campo
  errado da resposta).
- O exemplo de regras de conquista estava num formato que o app recusava;
  agora mostra o formato aceito e os operadores.
- Detalhe do jogo: botões "Avaliar" repetidos e duas seções de saves viraram
  uma só de cada.

### Alterado

- Tamanhos em Downloads seguem o formato do resto do app ("512 B", "1,5 KB").
- Vídeos com mais de uma hora mostram a duração como 1:02:03.

### Interno

- CSS dividido por área (`estilo/*.css`), seletores repetidos fundidos e
  espaçamentos com tokens; o teste falha se um seletor se repetir.
- Formatação pt-BR (horas, tamanhos, duração, datas, tempo relativo, preço)
  num módulo só, com testes.
- Validação de parâmetros da ponte num módulo comum (`ponte_params`), com as
  mesmas mensagens de erro.
- Colunas da tabela de jogos numa lista só; leitores de save das conquistas
  numa tabela.
- Removido `baixar_fonte_steamrip` do serviço de desejos (sem uso; a TUI
  segue com o próprio fluxo).

## [1.3.1] - 2026-11-14

Revisão completa da 1.3.0: segurança, recursos que não funcionavam e limpeza.

### Segurança

- Electron 44.9.0 → 44.11.3: a versão da 1.3.0 tinha alerta **alto**
  (mitigação de certificados intermediários eMudhra comprometidos).
- Python embutido 3.14.7 → 3.14.10 (SHA-256 fixado da página oficial).

### Corrigido

- Aviso "Sem backup local" apontava para uma tela que não existe e não havia
  como fazer backup: **Fazer backup agora** em Configurações › Coleção.
- **Importar coleção** abria seletor de pasta, mas o pacote é `.zip` — nunca
  funcionou; exportar/importar com falha diziam sucesso.
- A lista de backups nunca aparecia (formato de resposta lido errado).
- Sessões manuais (abrir como administrador) não tinham onde ser fechadas:
  **Sessões abertas** no Início registra as horas.
- **Tema** e **Densidade** eram gravados e nunca aplicados.
- Mensagens que citavam "ferramentas clássicas" e a "tela Sistema".

### Adicionado

- Tema claro; densidades compacta/confortável/Big Picture e tamanho do texto
  (80–150%) aplicados como zoom da janela.
- Configurações › Coleção: backups legíveis, horas do ano por mês, top jogos,
  exportar/importar `.zip` e erros recentes do log.
- Detalhe do jogo: saves (snapshot agora, restaurar com confirmação) e
  galeria de screenshots.
- Confirmações com o diálogo do app no lugar de `window.confirm`.

### Removido

- 12 componentes de interface nunca usados e 54 regras de CSS só deles;
  `DialogoVideo`, `Placeholder`, `atalho_jogo.py`.
- Métodos da ponte substituídos (`capas.importar_selecionados`,
  `torrents.fora_destino`) e 7 métodos de serviço sem chamador.

### Alterado

- Versão e User-Agent num lugar só (`bib_nucleo/versao.py`, lê `VERSION`).
- `DESKTOP_ELECTRON.md` reescrito como estado atual; CI com `setup-node` v7.

### Limitações conhecidas

- O alerta moderado do `minimatch` segue dentro do electron-builder (já na
  última versão); afeta só o build de binários universais do macOS.
- Validação no hardware do usuário (instalação limpa, controle, UAC, FFmpeg,
  atualização de emulador) segue pendente.

## [1.3.0] - 2026-11-14

Primeira release com o desktop Electron entregue como instalador Windows.
A tag `v1.2.0` já existe (na revisão das fatias F0–F6) e não é movida; por
isso a entrega instalável segue como 1.3.0.

### Adicionado

- Instalador Windows NSIS (`npm run dist`, `electron-builder.config.cjs`): por
  usuário, sem admin, atalhos no Menu Iniciar/Área de Trabalho e ícone próprio.
  Leva o núcleo Python, a ponte e o Python 3.14 embutido em `resources/tucoteca`.
- `preparar_runtime_python.py`: Python embeddable oficial com SHA-256 fixado.
- `gerar_icone.py`: ícone do app reproduzível, só com a stdlib.
- `validar.py` roda typecheck + vitest do Electron.
- CI (manual): job `electron` com typecheck, vitest, build e, opcionalmente,
  instalador + selftest do app empacotado.
- Paridade com o antigo desktop Qt (`ponte_paridade.py`): mods, cheats,
  texturas HD e presets do Azahar no detalhe do jogo; emuladores (verificar e
  atualizar) e controles/pads em Configurações; letra sincronizada e volume
  do PC no player; equalização de faixas; wishlist por JSON, sincronizar
  Steam e buscar fontes em Desejos; capa libretro; manutenção do jogo
  (verificar/religar exe e ROM, disco, abrir como administrador); sanear
  pasta; ferramentas de mídia; downloads fora da pasta de jogos; arrastar e
  soltar para importar com prévia. Mapa completo em `DESKTOP_ELECTRON.md`.

### Alterado

- App instalado usa a coleção em `Documentos\TucoTeca` (ou `BIBLIOTECA_HOME`),
  preservada ao atualizar/desinstalar; a ponte roda sem janela de console.
- `preparar_release.py` reescrito para o instalador: confere Git, versões
  (`VERSION`, `pyproject.toml`, `package.json`), runtime e ausência de dados
  pessoais no app; gera fontes, notas, `release.json` e `SHA256SUMS.txt`.
- Pacote de fontes inclui a interface Electron (sem `node_modules`/`out`/`dist`).
- `emulacao.atualizar` e `musicas.eq` viram trabalhos em segundo plano (a
  versão síncrona estourava o limite de 30 s da ponte).
- macOS: `BibliotecaHubMac.command` abre a TUI (como o Linux).
- Versões unificadas em 1.3.0; User-Agent aponta para o repositório TucoTeca.
- Documentação (README, ARQUITETURA, CONTRIBUTING, INDICE, AGENTS, templates)
  sem Qt; material de sessões antigas em `docs/arquivo/`.

### Corrigido

- `TucoTeca-Electron.bat` não apaga mais o lock da coleção sem conferir o dono.
- `desktop.py` acha o Electron em qualquer SO e avisa quando falta o build.
- Soltar um arquivo na janela navegava o app para `file://`; agora é bloqueado.
- Pacote de fontes saía com `docs/CONTRIBUTING.md` e `SECURITY.md` duplicados.
- Depois de crash, encerramento forçado ou queda de energia o app recusava a
  coleção por 24 h (lock de processo morto); agora assume só o lock órfão do
  mesmo PC ao abrir. Lock de processo vivo continua recusado.
- Tela Vídeos em branco (o carregador pegava a exportação errada do módulo) e
  troca de seção que desenhava a tela anterior com as props da nova (erro em
  Notificações → Configurações).
- 20 tokens de CSS da biblioteca de componentes nunca definidos: métricas,
  modais e abas perdiam espaçamento, fonte e camada; teste impede a volta.
- Textos sem acento e botões "ainda não nesta fatia" nas Integrações (agora
  levam às telas existentes); downloads 100% mostrados como "baixando".

### Removido

- `instalador.iss` (Inno), `montar_mac.py`, `montar_linux.py`,
  `provar_linux_shell.py` (dependiam do `montar_portatil` já removido) e
  `requirements-ui.txt`/`requirements-extras.txt` (PySide6).
- Extras `ui`/`extras` (PySide6) do `pyproject.toml` e variáveis Qt da suíte.

### Limitações conhecidas

- Instalador sem assinatura de código (SmartScreen na primeira execução).
- Download automático de repacks a partir das fontes não está na interface
  nova (a busca abre a página no navegador).
- Controles, UAC, volume e emuladores foram provados com simulação; falta a
  conferência com controle físico, emulador real e o UAC do Windows.
- macOS e Linux só pela TUI, a partir dos fontes.

## [1.2.0] - 2026-10-18

> Nota (registrada na 1.3.0): o texto abaixo descreve o Qt Quick como desktop
> único, mas a tag `v1.2.0` foi criada já com o desktop Electron (F0–F6) e o
> Qt removido. Mantido como estava, por ser registro histórico.

Planejamento da 1.1.0 segue no roadmap (`docs/ROADMAP.md`). Esta rodada remove o
modo clássico tkinter e passa a tratar o desktop Qt Quick como interface única
no Windows; a TUI curses continua para Linux/macOS.

### Adicionado

- Integrações modulares: `bib_nucleo/rede/_modelo.py` é um modelo copiável de
  provedor de rede (sem efeito colateral no import; rede só sob ação do usuário,
  com `rede_ativa()`, timeout curto, User-Agent e cache local).
  `docs/INTEGRACOES.md` documenta o contrato e o passo a passo em 3 passos
  (provedor, registro, teste hermético) e `test_integracoes_modulares.py`
  cobre 6 casos sem rede real nem instalação.
- Campo `capacidades` no `Integracao` de `servicos_ui/integracoes.py`
  (`busca`, `abrir`, `midia`, `download`, `emulador`, `config`), exposto como
  lista ordenada em `apresentar()`; as 7 integrações padrão foram classificadas
  e as personalizadas derivam do tipo + URL.
- `docs/ROADMAP.md` como fonte de planejamento da 1.1.0.
- Fundação do desktop Electron (F0): ponte NDJSON `codigo/frontends/ponte.py`
  (stdin/stdout, sem porta TCP) com `nucleo.ping`/`nucleo.snapshot`/
  `modulos.listar`; registro de módulos em `servicos_ui/modulos.py`; app
  electron-vite + Preact em `codigo/frontends/electron/` (instância única,
  preload isolado, protocolo `tucoteca-img://` restrito à coleção, selftest
  com screenshot) e tela Início com "Continuar jogando". Documentado em
  `docs/DESKTOP_ELECTRON.md`; o Qt Quick segue como desktop atual até a F5.
- Shell do desktop Electron (F1): paleta de busca global `Ctrl+K`/`Ctrl+F`
  (busca no núcleo via ponte, sem acento), atalhos pessoais `Ctrl+1..8`,
  notificações com sino/contador, perfis Tuco/Isa persistidos em
  `dados/preferencias-pessoais.json`, gamepad via Gamepad API do Chromium,
  menu do app (Sobre/Exibir/Ajuda, `F12` DevTools, `Alt` mostra a barra) e
  queda/reconexão da ponte sem reiniciar (banner com **Reconectar**; lock
  órfão de pid morto no mesmo host/SO é assumido, lock vivo segue recusado).

### Alterado

- Desktop Qt Quick (`codigo/frontends/desktop.py`) é a única GUI no Windows;
  `app_tui.py` (curses) atende Linux/macOS e aponta o usuário do Windows para o
  Qt quando curses não está disponível.
- Builders e utilitários sem referências ao modo clássico:
  `montar_portatil.py`, `montar_mac.py`, `montar_linux.py`,
  `montar_superhub.py`, `abrir_hub.py`, `diagnosticar.py`,
  `provar_linux_shell.py` e `executar.py` (que agora roda Qt offscreen).
- `BibliotecaHubMac.command` abre `codigo/frontends/desktop.py` (Qt) e o
  instalador do Mac avisa quando falta PySide6.
- `test_fase_a.py` passa a guardar a regressão inversa: falha se o modo clássico
  (`app_win*.py`, `aparencia.py`) voltar ou se o frontend Qt sumir.
- Documentação alinhada: `docs/ARQUITETURA.md`, `docs/CONTRIBUTING.md`,
  `docs/DESKTOP_QT.md`, `docs/INDICE.md` e `docs/VISAO_OS.md`.
- `pyproject.toml` sem os `per-file-ignores` de F401 dos testes do modo clássico.

### Removido

- Modo clássico tkinter: `codigo/frontends/app_win.py` e os 10 módulos
  `app_win_*.py`, mais `aparencia.py` (tema Tk) e `despacho.py`
  (despachante de callbacks da UI Tk). Todos os callbacks diferidos passaram a
  ser entregues à thread da UI por sinais do bridge Qt.
- Testes do modo clássico: `test_despacho.py`, `test_dialogo.py`,
  `test_varredura.py` e `test_visual.py`.
- Botão do modo clássico no QML; nenhuma ocorrência de "clássico" permanece em
  `codigo/frontends/qml`.

### Limitações conhecidas

- `bib_nucleo/rede/_modelo.py` aponta para uma API de exemplo fictícia de
  propósito: é template, não provedor vivo.
- A lista de capacidades de cada integração é política de design (vocabulário
  fixo), ajustável sem quebrar contrato.
- A validação visual/Hydra-like do Qt Quick foi verificada por testes
  offscreen; conferência em máquina com GPU real segue pendente.

## [1.0.2] — 14/10/2026

Segunda release privada. Inclui o trabalho dos três assistentes integrado em
`revisao/assistentes-1.1.0`, com gates locais verdes e CI aprovada no SHA
congelado (ver `release.json`). Sem assinatura de código, por decisão do
usuário (o Windows pode exibir o SmartScreen na primeira execução).

### Adicionado

- Navegação por controle XInput no desktop Qt (setas e analógico, A confirma,
  B volta, LB/RB trocam de seção, Start abre a busca global). A navegação foi
  testada com estados simulados; a validação com controle físico está pendente.
  Regressões A1-06: só o direcional repete; neutro após conexão/retorno de
  foco; pausa com jogo; sem troca atrás de modais.
- Mods, texturas HD, cheats e presets do Azahar no detalhe de jogos 3DS, pelo
  desktop Qt, usando as mesmas funções do modo clássico. Remoções e presets
  pedem confirmação; mutações bloqueadas com jogo aberto; origem das texturas
  preservada.
- Importação de wishlist a partir de JSON salvo, com backup antes de gravar.
  Leitura com BOM (`utf-8-sig`), teto local de 8 MB e falha explícita quando
  a Steam devolve HTML/erro; `sincronizar_desejos` preserva manual e obtido.
- Importação Qt com preview e seleção (A1-02): nada é gravado antes da
  confirmação; reutiliza o domínio existente.
- Saneamento com plano, reparo por religar e opção UAC com confirmação
  expressa (A1-03); o teste nunca eleva nem executa jogo real.
- Importação de torrents concluídos pelo Qt (A1-04): só 100%, origem
  preservada, incompleto nunca entra.
- Emuladores e controles avançados no Qt (A1-05): `emus_status` local sem
  rede, consulta remota sem instalar, atualização só com info consultada e
  confirmação; pads com fotografar/aplicar/gerar mapa e leitura de estado.
- Hierarquia visual e leitura (Lote 1): tokens `display`/`headline` por
  densidade, ordem no resumo, vazio com ação por seção; botões em pílula por
  tokens e inputs na escala dos botões.
- Everything endurecido: linha literal `-search*` com `shell=False`, sem
  `-utf8`/`-full-path` isolados nem `-argv`; Unicode/parênteses, instância
  configurável e fallback stdlib preservados.
- Suíte sempre em segundo plano: Qt offscreen, Tk fora da tela, nenhum
  diálogo modal durante os testes; índice temático `docs/INDICE.md`.

### Limitações conhecidas

- A leitura da wishlist pública da Steam não funciona: o endpoint devolve HTML.
  Use a importação de JSON.
- Integrações autenticadas precisam de credenciais válidas, configuradas em
  "Provedores online". Diagnósticos pessoais não fazem parte da release.

### Alterado

- CI com `actions/checkout`, `actions/setup-python` e `actions/upload-artifact`
  em v7 e `gitleaks/gitleaks-action` em v3. Ubuntu fixado em 24.04.
- Job macOS manual em `testes.yml`, ativado com `mac=true`.
- Cliente Everything local opcional, com consulta Unicode e instância separada;
  correção dos argumentos do ES 1.1.0.38, comprovada com índice nativo isolado.
- Testes Qt verificam a dependência opcional antes de importá-la na suíte stdlib.
- Controle exige posição neutra após conexão/retorno de foco, pausa durante
  jogos e não muda a seção por trás de diálogos modais.

## [1.0.1] — 11/10/2026

Primeira release privada publicada. A tag `v1.0.0` permanece intacta como
registro de preparação, sem release: a verificação final encontrou falhas
no empacotador antes de qualquer upload. A revisão exata desta entrega fica
em `release.json` e nos manifestos de fontes/runtime, sem SHA autorreferente
nos documentos versionados.

### Corrigido e organizado

- Preparação testada de ponta a ponta: inventário plano de anexos e
  `SHA256SUMS.txt` com todos os arquivos, exceto o próprio checksum.
- Recusa checkout sujo, SHA/versão/variante divergentes, fontes não rastreados,
  relatório incompleto, provas de extração ausentes e hashes divergentes.
- ZIPs conferidos por conteúdo, tamanhos, hashes e fontes `app/`; caminhos
  inseguros, entradas duplicadas e estado pessoal são rejeitados.
- Staging temporário e publicação local por renomeação: uma falha não deixa
  entrega parcial e um destino existente não é sobrescrito.
- Assets nomeados por versão; notas, `LICENCAS.md` e proveniência sem caminhos
  absolutos da máquina. Os pacotes anteriores continuam preservados localmente.
- Textos LGPL/GPL do Qt incluídos com versão e hashes fixados, além dos avisos
  das wheels. A versão real do FFmpeg passa ao manifesto e à nota de fonte.
- README corrigido e ampliado: download privado, escolha de variante,
  primeiro uso, atualização sem perder dados, diagnóstico e limites de rede.
  Procedimento de congelamento, CI, rascunho e publicação em `docs/RELEASES.md`.

Núcleo, interfaces e integração S0–S8/R4/R5 preservados. Esta release não
atualiza automaticamente a instalação pessoal, coleção ou atalho.

## [1.0.0] — 11/10/2026 (tag de preparação, não publicada como release)

Preparação inicial de uma release privada. Os itens abaixo registram o que
foi implementado nessa tag; as falhas de preparação foram corrigidas em 1.0.1.

### Adicionado

- `codigo/ferramentas/preparar_release.py`: monta a pasta de release com os
  bundles já validados, o pacote de fontes congelado na revisão, as notas
  (`NOTAS-RELEASE.md`), `SHA256SUMS.txt` e `release.json`. Confere hash por
  hash, recusa pacote com caminho de dado pessoal e **não publica nada** —
  criar a release no GitHub continua sendo passo explícito.
- Pacote de fontes passa a registrar `versao` (de `VERSION`) e `revisao_git`
  (quando informada) no `MANIFESTO-FONTES.json`; revisão inválida é recusada.
- `montar_superhub.py --revisao`: grava a revisão e a versão no manifesto do
  runtime, além de `VERSION` e `VERSAO.txt` dentro do pacote. Um runtime
  reutilizado não herda a revisão do build anterior.
- O pacote de fontes ignora `.provas/`, `.venv/`, `.pytest_cache/` e
  `.ruff_cache/`, e inclui os modelos de issue/PR de `.github/`.
- `TucoTeca.bat` virou a entrada principal; `BibliotecaHub.bat` continua
  funcionando exatamente como antes (alias), inclusive no bundle.
- Testes novos em `codigo/ferramentas/testes/test_release.py` (6 casos):
  revisão inválida, manifesto com versão/revisão, exclusão de caches e dados,
  recusa de pacote com banco pessoal, detecção de hash divergente e conteúdo
  das notas da release.

### Alterado

- **README reescrito** em linguagem mais direta e humana: o que o hub faz, o
  que não faz (gamepad, conquistas online, overlay, assinatura, macOS), como
  começar, como gerar pacotes e como a release é montada.
- `pytest` e `ruff` passam a guardar seus caches em `.provas/`, fora da raiz;
  `.venv/` entra no `.gitignore`. A raiz do projeto fica só com arquivos de
  entrada, configuração e documentação.

## Histórico de integração anterior à publicação

### Portabilidade dos testes na CI (11/10/2026)

- A primeira CI da reconciliação revelou quatro pressupostos de ambiente,
  afetando os quatro jobs stdlib e Qt Windows; Qt Linux e Gitleaks passaram.
- Sandbox remove a entrada de symlinks sem seguir o último componente,
  inclusive loops no Python 3.10; pais continuam resolvidos e escritas,
  SQLite, remoções externas e caminhos com `..` seguem bloqueados.
  Quatro regressões novas verificam essas proteções sem escrever fora do sandbox.
- Testes visuais permitem as geometrias solicitadas mesmo em desktops virtuais
  pequenos e aguardam os estados de layout/fullscreen com limite de tempo.
  A largura do volume é confrontada com a sidebar real, descontando suas margens.
  Uma regressão simula explicitamente o limite de um desktop de 1024×768.
- A suíte Tk Linux roda com Openbox no Xvfb, para que exista suporte real
  a fullscreen; nenhuma asserção foi removida e nenhum caso foi desativado.
- Somente harness, testes e configuração de CI alterados; fontes de runtime,
  instalação pessoal, coleção e bundles R5 permanecem intactos.
- Gates locais: runner 424 casos, zero falhas e seis pulos; pytest 418 passes,
  seis pulos e 63% de cobertura real. Ruff configurado, actionlint e Gitleaks
  limpos. Esses resultados locais não substituem a nova execução da CI.

### Reconciliação com o repositório GitHub (11/10/2026)

- Base remota `6466dbe` reconciliada com a revisão local `b35bac9`, mantendo
  ambos os históricos, sem force-push ou nova reescrita de commits.
- Conferência por blobs: `6466dbe` e a contraparte local `598bff1` possuem
  os mesmos fontes/documentos; diferem apenas nas dez capas antigas.
  `docs/organizacao-local.json` é idêntico e permanece como registro histórico
  de organização de artefatos, não como substituto de `organizacao_local.py`.
- Todas as melhorias S0–S8/R4/R5 mantidas na estrutura atual, com adaptadores
  remotos em `bib_nucleo/rede/` e seções QML em `frontends/qml/secoes/`.
- O repositório GitHub foi tornado privado por autorização do proprietário.
  O envio inclui fontes, testes, documentação, dependências e empacotadores;
  não inclui coleção, jogos, ROMs, saves, perfis pessoais, runtime, ZIPs,
  backups ou caches locais. A instalação pessoal e seu atalho não são alterados.
- As capas comerciais ficam ausentes da árvore atual. O histórico remoto
  antigo continua preservado, inclusive suas imagens; um merge não apaga
  blobs históricos. Placeholders neutros são opcionais e gerados localmente.
- Proveniência e limites registrados em `docs/RECONCILIACAO_GITHUB.md`.
  Os bundles R5 existentes continuam vinculados a `b35bac9`, não ao novo merge.

### Correções e regressões da revisão R5 (11/10/2026)

- Diálogo de pacotes usa o papel `modelData` do Qt, sem delegates vazios;
  abrir dispara uma única leitura. O executável detectado é preenchido na
  confirmação e o campo é limpo ao trocar para outro pacote.
- ZIP continua extraível sem 7-Zip. A interface usa `Pacotes locais…`, sem
  mudar o destino configurado ou mover a pasta legada `D:\Games\Piratas`.
- Importar jogo já instalado preserva instruções, mídias, saves e perfis;
  não aplica a limpeza de archives a pastas pessoais. Instaladores só vão
  para quarentena após cadastro bem-sucedido de um jogo dentro dessa pasta.
  Um executável externo é aceito; escolher o próprio setup é rejeitado.
- Processos de download com progresso, extração de mods e sondagem da GPU
  usam as opções sem console no Windows; Linux mantém o grupo de processos
  para timeout. Emuladores e aplicativos visíveis não são ocultados.
- Importação pela UI segue o mesmo lock de escrita e backup das demais
  alterações da coleção. Archives preparados são preservados.
- Regressões dedicadas usam apenas arquivos sintéticos e mocks; prova da
  instalação usa cópia SQLite consistente e configurações pequenas, sem
  copiar jogos ou saves. A prova inicial preservou 27 jogos, 68 músicas,
  2 desejos e 18 downloads; o SHA-256 do banco real permaneceu idêntico.

### Portado da instalação real (revisão R5, 11/10/2026)

A instalação em `D:\Tuco-Compartilhado\Jogos\biblioteca` estava em `051e716`
com trabalho local **não commitado** e divergente de `main`. Os fontes locais
e o diff rastreado foram preservados antes da atualização: patch e cópia dos fontes
em `dist/marco-s0-s8/backup-instalacao-real/` (103 arquivos, 1,57 MB).

Funcionalidades portadas para o `main`:

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

Os demais diálogos QML mantêm os contratos `hub.*` usados na instalação.
Diferenças de apresentação não foram copiadas automaticamente; os fontes
originais permanecem no backup para comparação, que não inclui runtime,
cache, jogos ou saves. A revisão R5 dos pacotes corrige também os problemas
de integração encontrados após a portação inicial.

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


### Adicionado (F2 — telas restantes do desktop Electron)

- Telas Jogos, Musicas, Desejos, Downloads, Integracoes e Videos no shell Electron,
  com paleta, atalhos Ctrl+1..8, notificacoes e perfis Tuco/Isa.
- Protocolo de midia `tucoteca-media://arquivo/` com Range (200/206/403/416), player do
  rodape e importacao de pasta de musicas.
- Desejos com precos via cache Steam, adicionar/remover com desfazer e abrir na loja.
- Downloads com torrents (progresso, pausar/retomar via API, organizar, importar
  concluidos) e componente Atividade (jobs) no rodape.
- Integracoes com cartoes, busca por catalogo e personalizadas persistidas.
- Videos com lista, player interno e reprodutor externo (VLC/MPV/MPC-HC).
- IPCs `dialogo:escolher-pasta`, `app:abrir-url` (so https) e `app:abrir-pasta`.
- Trabalhos (jobs) com progresso/cancelamento na ponte; detalhe do jogo pela paleta.
