# Changelog

Todas as mudanças relevantes do TucoTeca. Formato: [SemVer](https://semver.org/),
seções inspiradas em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [1.4.6] - 2026-11-17

Arrumação, sem mudar o que o app faz.

### Alterado

- Código da interface reagrupado pelas mesmas seções do app: telas de Jogos,
  Filmes e Séries e Configurações em pastas próprias; componentes da janela,
  de cada área e genéricos separados; teclado, controle e foco juntos.
- Índice da documentação e mapa da arquitetura descrevem a nova organização.

### Removido

- Notas de sessões de trabalho antigas (`docs/arquivo/`), que seguem no
  histórico do Git.
- `TucoTeca-Electron.bat`, que duplicava o lançador de desenvolvimento
  (`frontends/desktop.py`) e o `TucoTeca.bat` da raiz.

## [1.4.5] - 2026-11-17

O hub em três pilares: Jogos à la Hydra, Filmes e Séries à la Stremio (com os
seus arquivos) e Músicas. Reúne as etapas 1.4.1–1.4.5, conferidas no app
instalado, sem rede, com dados de teste.

### Adicionado

- **Navegação nova**: seis seções (Início, Jogos, Filmes e Séries, Músicas,
  Downloads, Configurações) com abas; cada tela tem endereço (`#/jogos/desejos`,
  `#/jogo/12`), com voltar/avançar (botões, Alt+←/→, botões do mouse).
  Cabeçalho com busca e sino de notificações. Os atalhos antigos continuam
  valendo.
- **Biblioteca lateral** de jogos: filtro, Favoritos/Recentes, filtro por
  coleção e lista rápida mesmo com milhares de jogos.
- **Página do jogo**: arte de fundo, logo, horas, última vez, conquistas e
  horas para zerar; abas Visão geral, Conquistas, Emulação, Saves, Manutenção e
  Editar.
- **Dados dos jogos** (botão "Buscar dados" ou em lote): Steam (descrição em
  pt-BR, gêneros, estúdio, arte, screenshots), SteamGridDB (fundo, logo,
  ícone), RetroAchievements (seu progresso, com a sua chave) e HowLongToBeat
  (desligado por padrão). O que você corrigir à mão fica travado.
- **Coleções** de jogos, **Catálogo** da loja Steam (vitrine, busca, preço BR,
  página da loja com "Adicionar aos Desejos") e **Importar de lojas
  instaladas** (Steam, Epic, GOG, Hydra, Riot, Windows).
- **Filmes e Séries**: escolha as pastas; o app só lê os nomes (nada é copiado)
  e identifica cada título no Cinemeta. Página do título com temporadas e
  episódios, player interno que retoma de onde parou e lê legendas `.srt`/`.vtt`
  ao lado do arquivo (formatos sem suporte vão para o reprodutor externo),
  Continuar, Descobrir, Minha lista e Calendário das séries seguidas. Início
  ganha "Continuar assistindo".
- **Controle**: direcional/analógico movem o foco pela tela, A ativa, B fecha
  ou volta, LB/RB trocam de aba, Start abre a busca. **Big Picture** com anel
  de foco, setas que andam pela tela e casca mais simples.

### Alterado

- Desejos agora é aba de Jogos; Integrações, aba de Configurações; Vídeos e
  YouTube, abas de Filmes e Séries; Notificações, o sino do cabeçalho.
- O pacote de exportação leva coleções e os dados dos jogos (sem a arte, que é
  local).
- Depois de cada ação o app recarrega só o que mudou; a busca global não monta
  mais a coleção inteira.

### Segurança e privacidade

- O protocolo de mídia só serve a coleção e as pastas de Filmes e Séries que
  você escolheu (recusa disco inteiro, `..` e o resto).
- Rede só quando você pede. Exceções: o Calendário renova as séries seguidas
  ao abrir a aba (no máximo a cada 12 h) e o RetroAchievements lê o seu
  progresso com a chave que você informou. Modo avião (`BIBLIOTECA_REDE=0`)
  continua valendo para tudo.

### Limites conhecidos

- Steam, SteamGridDB, RetroAchievements, HowLongToBeat e Cinemeta foram
  provados com respostas simuladas; o primeiro uso real é a primeira prova
  com os serviços. Textos do Cinemeta vêm em inglês.
- Controle provado com um gamepad simulado no mapeamento padrão.

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
