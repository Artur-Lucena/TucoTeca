# TucoTeca Electron — F2 (telas restantes) Implementation Plan

> **Para agentes executores:** SUB-SKILL OBRIGATÓRIA: use `superpowers:executing-plans` para
> implementar este plano tarefa a tarefa (ou `superpowers:subagent-driven-development` para
> paralelizar). Passos usam checkboxes (`- [ ]`).

**Goal:** entregar as seis telas restantes do desktop Electron em 1.2.0 — Jogos (grade, filtros,
ordenação, busca, detalhe e jogar), Músicas (player local no rodapé), Desejos, Downloads,
Integrações e Vídeos — com jobs com progresso/cancelamento na ponte, detalhe do jogo aberto pela
paleta e favoritos/filtros persistidos por perfil.

**Architecture:** mantém F0/F1 — renderer Preact fala só por IPC; o main fala com `ponte.py` por
NDJSON. A F2 adiciona: métodos de jogo/edição/exclusão, desejos, integrações, torrents, vídeos e
importações na ponte; um **registro de trabalhos** (jobs) com eventos e cancelamento cooperativo
no processo da ponte (o loop NDJSON nunca bloqueia); um protocolo `tucoteca-media://` (com Range)
servindo áudio/vídeo locais da coleção para o player do renderer; e o estado de tela por perfil
(filtro/ordem em `preferencias-pessoais.json`).

**Tech Stack:** Python stdlib (`servicos_ui`, `bib_nucleo`), electron-vite + TypeScript + Preact
+ @preact/signals, vitest, Electron 44.

**Spec:** `docs/DESKTOP_ELECTRON.md` (§"Shell da F1" e limites), `docs/DESKTOP_QT.md`
(§"Cobertura" — tabela de paridade usada como checklist), pendências herdadas da F1
(`docs/superpowers/plans/2026-10-18-electron-f1-shell.md` §"Pendências herdadas (F2+)"), repo
TucoTeca. Ledger das tarefas em `.superpowers/sdd/2026-10-18-electron-f2-telas/progress.md`
(mesmo fluxo da F0/F1: `task-start`/`task-done` por tarefa).

## Global Constraints

- Commits em PT sem acentos no estilo do repo (`area: descricao`), staging por caminhos
  explícitos; sem push/tag/release.
- Núcleo Python stdlib; nenhuma dependência nova de runtime no Python. TS: sem dependências novas
  de npm (Preact/signals já instalados).
- A ponte não abre porta TCP; envelope NDJSON da F0 inalterado
  (`{"id","metodo","params"}` → `{"id","ok","resultado"|"erro"}`; evento sem `id`). Eventos novos
  usam o mesmo envelope de evento.
- **Jobs:** o loop NDJSON nunca bloqueia — operações longas rodam em thread no processo da ponte;
  progresso/cancelamento só por evento/`trabalhos.*`. Escrita no stdout serializada por lock.
- **Mídia local:** `tucoteca-media://` só serve arquivos sob `BIBLIOTECA_HOME` (mesma validação do
  `tucoteca-img://`); suporta `Range`/206; nada de `file://` no renderer.
- Playback do Electron é do **renderer** (`HTMLAudio`/`<video>`); `player.py` (MCI) continua sendo
  o da TUI — divergência documentada, não se toca no player do núcleo.
- Provas só com `BIBLIOTECA_HOME`/`TUCOTECA_USERDATA` temporários sob `.provas/electron/…`; nunca a
  coleção real. Dados de prova sempre sintéticos (WAV gerado com `wave`, processo de jogo
  inofensivo (ping em loopback), `BT_backup` sintético, PNG do placeholder).
- Suíte: `py -3.14 -B codigo/ferramentas/testes/executar.py [--modulo test_x]`. Lint:
  `.provas/venv-ruff/Scripts/ruff.exe check codigo conftest.py`; `git diff --check`.
- Typecheck = `npm --prefix codigo/frontends/electron run typecheck`; testes web =
  `npm --prefix codigo/frontends/electron run test`; build = `… run build`.
- `VERSION`/`README.md` intactos; CHANGELOG (`Não lançado`) só na Task 9; 1.2.0 só na F6.
- Não reintroduzir tkinter nem tocar TUI/Qt (`qml/`, `qt_bridge/`, `app_qt.py`) nesta fatia.
- TDD em tudo: teste falhando (RED) antes da implementação; commits pequenos por tarefa; gates
  completos antes de cada commit.
- A F1 não pode regredir: `prova-shell.ps1`/`prova-queda.ps1` seguem passando (rodada na Task 9).

## Review Focus

1. **Filtro/ordem e favorito por perfil**: trocar de perfil com a tela aberta deve refletir o
   estado do outro perfil (não vazar filtro/ordem de um no outro) e favoritar no perfil ativo não
   pode mudar o favorito do outro (herança legada do Tuco preservada).
2. **Sessão de jogo com o app aberto/morto**: dois "Jogar" simultâneos são recusados; matar o jogo
   encerra o job e registra a sessão só quando rastreado; fechar o app no meio deixa marcador de
   sessão reconciliável (nada de horas inventadas).
3. **Mídia local restrita**: caminho fora da home (inclusive `..`) responde 403; `Range` inválido
   responde 416; sem `Range` responde 200 com `Accept-Ranges`; seek do player continua funcionando.
4. **Exclusão com desfazer**: excluir jogo/desejo/vídeo e desfazer restaura o item; música avisa
   que apaga o arquivo e não tem desfazer; lixeira vazia desabilita o Desfazer.
5. **Paleta com as telas novas**: `Enter` num jogo abre o detalhe; demais tipos navegam para a
   seção; `Ctrl+F` foca a busca local quando a seção tem busca e cai na paleta quando não tem.

## Estrutura de arquivos (decidida)

```text
codigo/frontends/servicos_ui/mix_nucleo.py      + filtro/salvar_filtro/lixeira/saude (reexport)
codigo/frontends/servicos_ui/mix_torrents.py    + torrent_controlar
codigo/frontends/servicos_ui/__init__.py        + integracoes()
codigo/frontends/ponte.py                       + métodos novos, Trabalhos (jobs), eventos
codigo/frontends/electron/src/
  main/midia.ts + midia.test.ts                 protocolo tucoteca-media (parse + Range) e streams
  main/index.ts                                 handler de mídia, diálogos/IPC (pasta, url, pasta-OS)
  main/ponte.ts                                 forward do evento novo "trabalho"
  shared/api.ts + preload/index.ts              escolherPasta/abrirUrl/abrirPasta
  shared/midia.ts                               mediaUrl(caminho) → tucoteca-media://
  renderer/src/
    estado/dados.ts + dados.test.ts             store do snapshot + recarregar()
    estado/jogos.ts + jogos.test.ts             filtrar/ordenar/buscar (sem acento) por perfil
    estado/player.ts + player.test.ts           fila, modo (sequencia|repetir|aleatorio), transporte
    estado/trabalhos.ts + trabalhos.test.ts     reducer dos jobs (evento "trabalho")
    vistas/Jogos.tsx, Musicas.tsx, Desejos.tsx, Downloads.tsx, Integracoes.tsx, Videos.tsx
    componentes/PosterCard.tsx, DetalheJogo.tsx, PlayerRodape.tsx, DialogoVideo.tsx
    componentes/Atividade.tsx                   indicador de job no rodapé + Parar
    app.tsx, estilo.css                         wire geral (seções, desfazer, toasts, busca)
codigo/ferramentas/semear_prova_electron.py     + WAV sintético, jogo sintético (ping), BT_backup falso
codigo/ferramentas/testes/test_ponte.py         + casos das Tasks 1/2/5/6/7/8
.provas/electron/prova-f2.ps1                   checklist E2E consolidado (Task 9)
docs/DESKTOP_ELECTRON.md / CHANGELOG.md         atualizados na Task 9
```

---

### Task 1: Ponte — núcleo do jogo, filtro por perfil e lixeira

**Files:**
- Modify: `codigo/frontends/servicos_ui/mix_nucleo.py`, `codigo/frontends/ponte.py`
- Test: `codigo/ferramentas/testes/test_ponte.py`

**Interfaces:**
- Consumes: `ServicoBiblioteca.jogo/salvar_jogo/favorito/salvar_observacoes/excluir/desfazer_exclusao/`
  `saude`; `bib_nucleo.preferencias_pessoais.ler_preferencias/salvar_filtro`; `bib_nucleo.lixeira.ultima`.
- Produces (métodos da ponte):
  - `nucleo.saude {}` → `{"total","problemas","pendentes","ids_pendentes","ok"}`
  - `jogo.ler {id:int}` → dict do jogo; id inválido/inexistente → `ok=false`
  - `jogo.salvar {id?:int, dados:dict}` → dict do jogo (cria sem `id`, atualiza com)
  - `jogo.favoritar {id:int}` → dict do jogo **já alternado** (favorito por perfil)
  - `jogo.observacoes {id:int, texto:str}` → dict do jogo
  - `item.excluir {categoria:"jogos"|"desejos"|"videos"|"musicas", id:int}` → recibo
    (`{"ok":True,"desfazer":{…}}` para 3 categorias; músicas → `{"ok":True}` após apagar arquivo)
  - `item.desfazer {}` → `{"ok":True,"tipo","titulo","id"}`
  - `lixeira.estado {}` → `{"disponivel":bool,"titulo":str}`
  - `preferencias.filtro {}` → `{"filtro","ordem"}` do perfil ativo
  - `preferencias.salvar_filtro {filtro:str, ordem:str}` → `{"filtro","ordem"}` (inválido → `ok=false`)

- [x] **Step 1: Casos RED em `test_ponte.py`**

Acrescentar (serviço real em home temporário, como os casos da F1):
`teste_ponte_saude_e_jogo_ler`, `teste_ponte_jogo_salvar_cria_e_atualiza`,
`teste_ponte_favorito_por_perfil` (favoritar em Tuco; trocar para Isa e ler o jogo → `favorito`
False; voltar a Tuco → True), `teste_ponte_observacoes_trunca`,
`teste_ponte_excluir_desfazer_e_lixeira` (excluir jogo → `lixeira.estado` disponível → desfazer →
jogo volta com o mesmo título), `teste_ponte_filtro_padrao_e_por_perfil` (default
`{"filtro":"todos","ordem":"titulo"}`; salvar `favoritos/recentes` em Isa não muda Tuco; valores
inválidos → `ok=false` sem quebrar a ponte).

- [x] **Step 2: Rodar RED** — `py -3.14 -B codigo/ferramentas/testes/executar.py --modulo test_ponte`;
  esperado: falhas "método desconhecido".

- [x] **Step 3: Implementar**

`mix_nucleo.py`: `filtro()` (ler `ler_preferencias()["perfis"][ativo]` com default
`todos/titulo`), `salvar_filtro(filtro, ordem)` (delega a `preferencias_pessoais.salvar_filtro` e
devolve `filtro()`), `lixeira()` (delega a `lixeira.ultima()`; sem recibo →
`{"disponivel": False, "titulo": ""}`). `ponte.py`: funções `_saude`, `_jogo_ler`, `_jogo_salvar`,
`_jogo_favoritar`, `_jogo_observacoes`, `_item_excluir`, `_item_desfazer`, `_lixeira_estado`,
`_filtro`, `_salvar_filtro` registradas em `METODOS`; validação de `params` no estilo `_buscar`
(int não-bool; str); `jogo.favoritar` chama `favorito(gid)` e devolve `jogo(gid)`.

- [x] **Step 4: Rodar GREEN** — mesmo comando; tudo passa (15 antigos + novos).

- [x] **Step 5: Gates e commit**

```powershell
py -3.14 -B codigo/ferramentas/testes/executar.py --modulo test_ponte
git add codigo/frontends/servicos_ui/mix_nucleo.py codigo/frontends/ponte.py codigo/ferramentas/testes/test_ponte.py
git commit -m "electron: ponte do jogo e filtro por perfil (F2)"
```

---

### Task 2: Ponte — trabalhos (jobs) com eventos e jogar com sessão rastreada

**Files:**
- Modify: `codigo/frontends/ponte.py`; Test: `codigo/ferramentas/testes/test_ponte.py`
- Extend proof seed (jogo sintético): `codigo/ferramentas/semear_prova_electron.py` — o jogo
  "Stardew Valley" ganha `executable_path` = `ping.exe` do sistema com `launch_options`
  `-n 36 127.0.0.1` (~35 s em loopback; nada real e passa do `LIMIAR_SESSAO_S = 30`). Correção de
  plano: o núcleo usa `Popen` sem shell, então um `.cmd` não executaria.

**Interfaces:**
- Consumes: `ServicoBiblioteca.iniciar_jogo(gid, ao_fim)` (não bloqueia: lança e um vigia chama
  `ao_fim(horas, rastreado)` quando o processo sai), `registrar_sessao`, `backup_pos_sessao`,
  `aparencia()`; `qt_bridge/mix_jogos.py:401-459` como referência de comportamento.
- Produces:
  - `trabalhos.listar {}` → `[{"id","rotulo","estado","pct","cancelavel","iniciado_em","aviso"}]`
    (`estado` ∈ `rodando|cancelando|ok|erro|cancelado`)
  - `trabalhos.cancelar {id:int}` → job dict; desconhecido/não cancelável → `ok=false`
  - `jogo.jogar {id:int}` → `{"trabalho": {…}}` imediato (nunca bloqueia o loop)
  - `jogo.registrar_horas {id:int, horas:float}` → `{"ok":True,…}` (horas > 0)
  - Evento `{"evento":"trabalho","dados":{…job…}}` no início, mudança de progresso e fim
    (`dados.detalhe` com `horas`, `rastreado`, `aviso` quando houver)
  - Um único jogo por vez (`escopo="jogo"`): segundo `jogo.jogar` → `ok=false "já em jogo"`

- [x] **Step 1: Casos RED** — `teste_ponte_trabalhos_eventos_e_cancelamento` (job fake com
  progresso 0→40→80 e cancelável — `trabalhos.cancelar` com `threading.Event`; asserts das linhas
  de evento capturadas na saída), `teste_ponte_trabalhos_cancelar_invalido`,
  `teste_ponte_jogar_em_thread` (fake `iniciar_jogo` bloqueia num `Event`; a resposta volta
  imediatamente com o job; recusa do segundo `jogo.jogar`; liberar → `registrar_sessao` chamado
  com as horas e backup pós-sessão; evento de fim), `teste_ponte_jogar_espera_o_fim_assincrono`
  (o vigia chama `ao_fim` depois; o job fica `rodando` até lá), `teste_ponte_jogar_opt_out_backup`,
  `teste_ponte_jogar_sem_rastreio_avisa`, `teste_ponte_jogar_erro_vira_trabalho_erro` e
  `teste_ponte_registrar_horas`.

- [x] **Step 2: Rodar RED** — falhas "trabalhos … desconhecido"; 8 casos novos falhando.

- [x] **Step 3: Implementar**

Classe `Trabalhos` em `ponte.py`: `iniciar(rotulo, funcao, cancelavel=False, escopo=None)` com
thread daemon; `funcao(progresso, cancelado)`; `progresso(pct)` atualiza o job (arredonda 0–100) e
emite evento só quando o valor muda; `cancelado` é `threading.Event`; exceções → estado `erro` com
`str(erro)`. `servir` escreve resposta e evento sob o mesmo `threading.RLock` (`Ponte._escrita`);
`Ponte.__init__(…, trabalhos=None)` para injeção nos testes. `jogo.jogar` inicia job `escopo="jogo"`
que chama `iniciar_jogo(gid, ao_fim)`, espera o vigia chamar `ao_fim` (`fim.wait()`) e então,
espelhando `_fim_jogo`: se `rastreado`, `registrar_sessao(gid, horas)` e, se
`aparencia().get("auto_backup", True)`, `backup_pos_sessao(gid)` (falha vira `aviso` no detalhe,
nunca derruba o job); sem rastreio → aviso "Sessão sem rastreio…". `jogo.registrar_horas` valida
`horas` finito > 0.

- [x] **Step 4: Rodar GREEN** — `--modulo test_ponte` completo: 29/29.

- [x] **Step 5: Prova local com o jogo sintético**

`.provas/electron/prova-f2-t2-jogar.ps1` (home `home-f2` semeada; app real em CDP): ouvinte de
eventos no renderer, `jogo.jogar` responde imediato com o trabalho, segundo `jogo.jogar` é recusado
"andamento", fim da sessão em ~35 s (estado `ok`, 0,01 h, `rastreado=true`, aviso de backup),
snapshot 87 → 87,01 h e eventos `inicio/fim` no renderer. PROVA OK. Limite: executável sintético
(`ping.exe` ~35 s), nada de jogo real, UAC ou emulador.

- [x] **Step 6: Gates e commit**

```powershell
py -3.14 -B codigo/ferramentas/testes/executar.py --modulo test_ponte
git add codigo/frontends/ponte.py codigo/ferramentas/testes/test_ponte.py codigo/ferramentas/semear_prova_electron.py
git commit -m "electron: trabalhos com eventos e jogar na ponte (F2)"
```

---

### Task 3: Tela Jogos — grade, filtros, ordenação, busca e estado por perfil

**Files:**
- Create: `renderer/src/estado/dados.ts` + `dados.test.ts`,
  `renderer/src/estado/jogos.ts` + `jogos.test.ts`, `renderer/src/vistas/Jogos.tsx`,
  `renderer/src/componentes/PosterCard.tsx`
- Modify: `app.tsx` (render da seção, store, atalho Ctrl+F por seção), `estilo.css`
- Test: vitest dos dois módulos de estado

**Interfaces:**
- Consumes: `nucleo.snapshot` (jogos com `titulo/plataforma/status/horas/nota/favorito/capa_url/
  etiquetas_lista/uuid`), `nucleo.saude`, `preferencias.filtro`, `preferencias.salvar_filtro`,
  `nucleo.buscar`; utilitário de imagem existente (`imagemUrl`).
- Produces (renderer):
  - `dados.ts`: signal `snapshot` + `recarregar()` (chama snapshot/saude e atualiza)
  - `jogos.ts`: `filtrarJogos(jogos, {filtro, busca, idsPendentes})` e
    `ordenarJogos(jogos, ordem)` — sem acento, todas as palavras em `titulo/etiquetas/plataforma`;
    filtros `todos|favoritos|jogando|PC|3DS|NDS|pendencias`; ordens `titulo|recentes|horas`
  - `PosterCard.tsx` (props: `jogo`, `selecionado`, `aoSelecionar`, `aoAbrir`, `aoJogar`)
  - Regra de `Ctrl+F`: seção com busca visível (`jogos`, `musicas`, `desejos`, `videos`) foca o
    campo; nas demais abre a paleta (ajuste em `atalhos.ts`/`app.tsx` + teste)

- [x] **Step 1: RED** — `jogos.test.ts`: filtro por plataforma, favoritos, pendências (por
  `idsPendentes`), busca sem acento/multi-palavra, ordenação por título/horas/recentes (empate
  estável por título), lista vazia. `dados.test.ts`: `recarregar()` junta snapshot+saúde, mantém o
  anterior em erro e limpa o erro no sucesso. `atalhos.test.ts` atualizado para a regra nova do
  Ctrl+F por seção (`focar-busca` vs paleta).

- [x] **Step 2: Rodar RED** — `npm --prefix codigo/frontends/electron run test`: 4 arquivos
  falhando (2 módulos ausentes + 2 asserções do Ctrl+F).

- [x] **Step 3: Implementar** — `dados.ts` com signals (`@preact/signals`) de snapshot/saúde/erro,
  módulos puros, `PosterCard`, `Jogos.tsx` (grade CSS, chips de filtro, combo de ordenação, campo
  de busca, resumo "N de TOTAL jogos · filtros · ordem" e chip "Pendências (N)"), wire no `app.tsx`
  (store no lugar do snapshot local; ao montar/trocar de perfil: ler `preferencias.filtro`; ao
  mudar chip/combo: `salvar_filtro` e refiltro local imediato; Ctrl+F vira `focar-busca` nas
  seções com busca). Seleção com setas (esquerda/direita) e clique; Enter/jogar ficam para a
  Task 4.

- [x] **Step 4: GREEN + build + typecheck** — vitest 69/69; `tsc` e `electron-vite build` ok.

- [x] **Step 5: Prova** — `.provas/electron/prova-f2-t3-jogos.ps1` (home `home-f2`; app real em
  CDP): Ctrl+2 → 3 cards por título; Ctrl+F foca a busca; chip "Pendências (2)" → 2 de 3; filtro
  "PC" + ordem horas → Stardew/Hollow/Celeste; busca "knight" → só Hollow Knight; setas e clique
  movem a seleção; perfil Isa herda o padrão e Tuco recupera "PC/horas"; prefs persistidas no
  JSON do perfil. Screenshots `f2-jogos.png` e `f2-jogos-selecao.png`. PROVA OK.

- [x] **Step 6: Commit**

```powershell
git add codigo/frontends/electron/src/renderer/src/estado/dados.ts codigo/frontends/electron/src/renderer/src/estado/dados.test.ts codigo/frontends/electron/src/renderer/src/estado/jogos.ts codigo/frontends/electron/src/renderer/src/estado/jogos.test.ts codigo/frontends/electron/src/renderer/src/vistas/Jogos.tsx codigo/frontends/electron/src/renderer/src/componentes/PosterCard.tsx codigo/frontends/electron/src/renderer/src/app.tsx codigo/frontends/electron/src/renderer/src/estilo.css codigo/frontends/electron/src/renderer/src/atalhos.ts codigo/frontends/electron/src/renderer/src/atalhos.test.ts
git commit -m "electron: tela Jogos com filtros e ordem por perfil (F2)"
```

---

### Task 4: Detalhe do jogo, ações, jogar e desfazer

**Files:**
- Create: `renderer/src/componentes/DetalheJogo.tsx`
- Modify: `app.tsx` (detalhe aberto pela paleta/grade, Toast Desfazer global, eventos
  `trabalho` do jogo), `estilo.css`, `main/ponte.ts` (forward do evento `trabalho`)
- Test: vitest onde houver lógica pura (validação de nota/etiquetas, estado do detalhe)

**Interfaces:**
- Consumes: Task 1/2 (`jogo.ler/salvar/favoritar/observacoes`, `item.excluir`, `item.desfazer`,
  `lixeira.estado`, `jogo.jogar`, `jogo.registrar_horas`), `trabalhos` (evento).
- Produces: drawer `DetalheJogo` (props `id`, `aoFechar`, `aoMudou`), sinal `detalheAberto`; item
  da paleta tipo `jogo` → `secao=jogos` + detalhe; Desfazer global (barra de status) alimentado por
  `lixeira.estado` e pelos recibos de exclusão.

- [x] **Step 1: RED** — funções puras em `estado/jogos.ts` (`validarNota` inteiro 0–10 — o núcleo
  recusa decimal —, `validarHoras` > 0, `normalizarEtiquetas` espelhando `normalizar_etiquetas`) e
  reducer de `estado/trabalhos.ts` (`reduzirTrabalhos`, `jogoEmAndamento`) com testes; RED com 2
  arquivos / 6 testes falhando.

- [x] **Step 2: Implementar** — `DetalheJogo.tsx` (capa/título/plataforma·status/horas·nota/
  etiquetas; botões Jogar, ★ Favoritar, Remover; form título/exe/args/status/nota inteira/etiquetas;
  registrar horas > 0; observações), estado do drawer no `app.tsx` (`detalheId`, `revisao`,
  `lixeira`), duplo clique no card joga, Espaço/clique direito abrem o detalhe, Enter na grade joga,
  módulo mínimo `estado/trabalhos.ts` (evento `trabalho` → signal; "jogando…"/botão desabilitado);
  ao fim: toast (`detalhe.aviso`) + `atualizarTudo()`; Desfazer global na barra de status via
  `lixeira.estado`. `main/ponte.ts` não mudou: o forward do `main/index.ts` já é genérico por nome
  de evento (ruling do pre-flight).

- [x] **Step 3: GREEN + typecheck** — vitest 79/79; `tsc` e build ok.

- [x] **Step 4: Prova E2E** — `.provas/electron/prova-f2-t4-detalhe.ps1` (home `home-f2-t4`): paleta
  + Enter em "Celeste" → detalhe; favoritar (jogo.ler favorito=true); nota 8,5 recusada (núcleo só
  aceita inteiro) e 9 salva; etiquetas normalizadas; 0,25 h registradas (11,5 h); Remover → barra
  "Celeste foi removido. Desfazer" e grade sem Celeste; Desfazer → volta com id novo (4)
  mantendo nota/etiquetas; Espaço abre o detalhe e Esc fecha; Jogar Stardew (ping ~35 s) → banner
  "jogando", botão desabilitado, banner some no fim, horas 87,01 e toast de backup pós-sessão no
  painel de avisos. Screenshots `f2-detalhe.png`, `f2-desfazer.png` e `f2-jogando.png`. PROVA OK.

- [x] **Step 5: Commit**

```powershell
git add codigo/frontends/electron/src/renderer/src/componentes/DetalheJogo.tsx codigo/frontends/electron/src/renderer/src/componentes/PosterCard.tsx codigo/frontends/electron/src/renderer/src/estado/trabalhos.ts codigo/frontends/electron/src/renderer/src/estado/trabalhos.test.ts codigo/frontends/electron/src/renderer/src/estado/jogos.ts codigo/frontends/electron/src/renderer/src/estado/jogos.test.ts codigo/frontends/electron/src/renderer/src/estado/notificacoes.ts codigo/frontends/electron/src/renderer/src/vistas/Jogos.tsx codigo/frontends/electron/src/renderer/src/app.tsx codigo/frontends/electron/src/renderer/src/estilo.css
git commit -m "electron: detalhe do jogo, jogar e desfazer (F2)"
```

---

### Task 5: Músicas — protocolo de mídia, lista, player no rodapé e importar pasta

**Files:**
- Create: `main/midia.ts` + `main/midia.test.ts`, `shared/midia.ts` (+ teste),
  `renderer/src/estado/player.ts` + `player.test.ts`, `renderer/src/componentes/PlayerRodape.tsx`,
  `renderer/src/vistas/Musicas.tsx`
- Modify: `main/index.ts` (protocolo, autoplay, IPC `dialogo:escolher-pasta`), `shared/api.ts`,
  `preload/index.ts`, `app.tsx`, `estilo.css`, `ponte.py`+`test_ponte.py` (`musicas.importar`),
  `semear_prova_electron.py` (WAVs sintéticos)

**Interfaces:**
- Consumes: snapshot `musicas` (`musica_path`, capa, título, artista, álbum), `musicas.importar`.
- Produces:
  - `tucoteca-media://arquivo/<caminho escapado>` servido pelo handler (200/206/403/416);
    `mediaUrl(caminho)` no shared; `escolherPasta(): Promise<string|null>` no preload
  - `estado/player.ts`: `{fila, indice, modo, estado}` (`sequencia|repetir|aleatorio`,
    `parado|tocando|pausado`), ações `tocarFila(faixas, indice)`, `alternar`, `proxima`, `anterior`
    (sem wrap), `parar`, `cicloModo`, `pularPara(i)`; aleatório nunca repete a atual; fim da faixa
    respeita o modo (repetir = mesma; aleatório = sorteia; sequência = próxima ou para no fim)
  - `musicas.importar {pasta:str}` → `{"trabalho":{…}}` (job indeterminado via `Trabalhos`)
  - `musicas.baixar_fila {}` → `{"trabalho":{…}}` — job **cancelável com progresso**: usa
    `servico.baixar_musicas(cancelar, progresso)`; `pct` do callback entra no job/evento e
    `trabalhos.cancelar` aciona o `threading.Event` cooperativo (é o consumidor real que fecha a
    pendência "jobs com progresso/cancelamento")

- [x] **Step 1: RED** — `main/midia.test.ts` (Range 200/206/416, recorte no fim, malformados;
  `tipoDoArquivo`; `caminhoDaUrlMidia` com `..`, fora da home, host errado e posix),
  `shared/midia.test.ts` (`mediaUrl` com escape de `\`, espaço/acento e vazio), `estado/player.test.ts`
  (transporte sem wrap, modos, fim de faixa, fila vazia) e 6 casos em `test_ponte.py`
  (`musicas.importar` cria job e pasta inválida; importar de verdade copia WAV sintético;
  `musicas.baixar_fila` com progresso/cancelamento, erro claro e jobs concorrentes bloqueados).

- [x] **Step 2: RED roda** — vitest: 3 arquivos falhando ("Cannot find module './midia'",
  "'./player'", "mediaUrl is not a function"); `test_ponte`: 29/35 (6 novos falhando por método
  desconhecido).

- [x] **Step 3: Implementar** — `main/midia.ts` puro (parse de `Range`, MIME por extensão, URL →
  caminho validado por `caminhoPermitido`); `registrarProtocoloMedia` em `main/arquivos.ts`
  (`createReadStream` + `Readable.toWeb`, 206 com `Content-Range`, 416 com `bytes */total`, 403
  fora da coleção — arquivo da task que o plano não listava; o handler mora ao lado do de imagens);
  esquema `tucoteca-media` privilegiado (`secure`/`stream`), autoplay liberado por
  `app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required')`, IPC
  `dialogo:escolher-pasta`; `mediaUrl`/`escolherPasta` no `shared/api.ts`+preload; `estado/player.ts`
  (fila/índice/modo/estado + ações `tocarFila/alternar/proxima/anterior/parar/cicloModo/pularPara`,
  fim de faixa respeita o modo, sorteador injetável nos testes); `PlayerRodape.tsx` (capa, tempo
  `m:ss / m:ss`, seek, ❮ ▶/Ⅱ ❯ ■, modo, volume, fila com ▶ no atual; `autoplay` + restart no
  repetir); `Musicas.tsx` (busca local, Enter toca, ▶ Tocar, Remover com aviso de que apaga o
  arquivo e sem Desfazer, "+ Importar pasta" via `escolherPasta`, painel "Fila de downloads" +
  "Baixar pendentes" com barra do job e Parar); seeder grava WAVs de 2 s (440/523 Hz, `wave`
  stdlib) com `musica_path` e sha reais.

- [x] **Step 4: GREEN + typecheck + build** — vitest 16 arquivos / 107 testes; `tsc` ok; build ok;
  `--modulo test_ponte` 35/35; suíte completa 546/546; ruff limpo.

- [x] **Step 5: Prova E2E** — `.provas/electron/prova-f2-t5-musicas.ps1` (home `home-f2-t5`, CDP
  9230): Ctrl+3 lista "Weightless | Sunset Lover" (ordem do núcleo); Enter toca com `src` em
  `tucoteca-media://arquivo/...`, `currentTime` 0,13→0,47 s e duração 2 s; Ctrl+F foca a busca;
  próxima/anterior sem wrap; modo cicla Sequência → Repetir → Aleatório; pausa e seek para 1 s
  (Range do protocolo); remover Sunset Lover → some da lista, arquivo apagado do disco, **sem**
  barra Desfazer (fora da lixeira) e toast "foi removida"; importar via bridge — o botão usa diálogo
  nativo não automatizável, a prova chama o mesmo `musicas.importar` — reflete "sintetica-660 |
  Weightless", `musica_path` presente e toast "1 nova(s), 0 ignorada(s)."; "Baixar pendentes" com
  fila vazia → toast "0 nova(s) baixada(s)." (sem rede). Screenshots `f2-player.png` e
  `f2-musicas.png`. PROVA OK.

- [x] **Step 6: Commit** — "electron: tela Musicas com player local e importacao (F2)"
  (19 arquivos; paths extras `main/arquivos.ts` e `renderer/index.html` do CSP `media-src`).

```powershell
git add codigo/frontends/electron/src/main/midia.ts codigo/frontends/electron/src/main/midia.test.ts codigo/frontends/electron/src/main/index.ts codigo/frontends/electron/src/shared/midia.ts codigo/frontends/electron/src/shared/midia.test.ts codigo/frontends/electron/src/shared/api.ts codigo/frontends/electron/src/preload/index.ts codigo/frontends/electron/src/renderer/src/estado/player.ts codigo/frontends/electron/src/renderer/src/estado/player.test.ts codigo/frontends/electron/src/renderer/src/componentes/PlayerRodape.tsx codigo/frontends/electron/src/renderer/src/vistas/Musicas.tsx codigo/frontends/electron/src/renderer/src/app.tsx codigo/frontends/electron/src/renderer/src/estilo.css codigo/frontends/ponte.py codigo/ferramentas/testes/test_ponte.py codigo/ferramentas/semear_prova_electron.py
git commit -m "electron: tela Musicas com player local e importacao (F2)"
```

---

### Task 6: Desejos e Integrações

**Files:**
- Create: `renderer/src/vistas/Desejos.tsx`, `renderer/src/vistas/Integracoes.tsx`
- Modify: `ponte.py` + `test_ponte.py` (`desejos.*`, `integracoes.*`), `servicos_ui/__init__.py`
  (`integracoes()`), `main/index.ts` (IPC `app:abrir-url` com `shell.openExternal` + https),
  `shared/api.ts`, `preload/index.ts`, `app.tsx`, `estilo.css`

**Interfaces:**
- Consumes: `adicionar_desejo`, `precos_desejos`, `excluir/desfazer` (Task 1), `integracoes_padrao`,
  `adicionar_integracao`, `remover_integracao`, `url_integracao`, `RegistroIntegracoes.buscar`.
- Produces:
  - `desejos.adicionar {titulo:str, appid:str}` → `{"ok":True,"novo":bool}`
  - `desejos.precos {}` → `{appid: {gratis, moeda, final, inicial, desconto_pct}}` (rede; sem rede
    devolve `{}` — a UI avisa)
  - `integracoes.listar {}` → `[Integracao.apresentar()]`
  - `integracoes.adicionar {dados:dict}` / `integracoes.remover {chave:str}` / `integracoes.url
    {chave:str, termo?:str}` / `integracoes.buscar {chave:str, termo:str}` (termo ≥ 2)
  - IPC `app:abrir-url(url)` (só https; caso contrário rejeita)

- [x] **Step 1: RED (Python)** — `teste_ponte_desejos_adicionar_remover_desfazer`,
  `teste_ponte_desejos_precos_sem_rede` (rede off → `{}`), `teste_ponte_integracoes_listar_e_url`
  (7 padrão + URL com `{q}`/sem termo + persistência no `integracoes-usuario.json`),
  `teste_ponte_integracoes_entradas_invalidas` (entradas inválidas, chave reservada, termo curto,
  chave desconhecida).

- [x] **Step 2: RED roda** — `--modulo test_ponte`: 35/39 (4 novos falhando por método desconhecido);
  vitest: 2 arquivos novos falhando (`Cannot find module './desejos'/'./integracoes'`).

- [x] **Step 3: Implementar ponte + IPC.** Ponte: `desejos.adicionar` (appid numérico +
  título), `desejos.precos` (região validada), `integracoes.listar/adicionar/remover/url/buscar`
  (seams sobre `servico.integracoes` e os métodos do serviço); IPC `app:abrir-url` (só https;
  recusa com `BIBLIOTECA_REDE=0`), `shared/api.ts`+preload `abrirUrl`. Ruling: `servicos_ui/__init__.py`
  não mudou — o atributo `integracoes` (registro) já existia; a ponte chama `servico.integracoes.*`.

- [x] **Step 4: Implementar telas.** `Desejos.tsx` (lista título/"Steam · appid"/preço, "Steam ↗",
  "Ver preços" com aviso "sem rede", "+ Adicionar" com form nome+appid, Remover com Desfazer;
  nota visível das pendências Steam/wishlist/fontes). `Integracoes.tsx` (grade de cartões com
  inicial colorida/nome/descrição/capacidades, botão principal por tipo: `url` com `{q}` pede termo
  e abre; sem `{q}` abre externo; `download` navega para Downloads; `emulador`/`musicas_online`/
  `provedores` → toast "ainda não nesta fatia"; busca por catálogo com resultados+links;
  "+ Adicionar" com validações do serviço no formulário; Remover em personalizadas). `app.tsx`
  conecta as seções; CSS novo.

- [x] **Step 5: GREEN + testes web + typecheck; prova E2E** — vitest 18 arquivos / 123 testes;
  `tsc` + build ok; `--modulo test_ponte` 39/39; suíte completa 550/550; ruff limpo.
  Prova `.provas/electron/prova-f2-t6-desejos-integracoes.ps1` (home `home-f2-t6`, CDP 9231,
  `BIBLIOTECA_REDE=0`): Ctrl+4 lista "428: Shibuya Scramble | Hollow Knight: Silksong"; adicionar
  Celeste → lista cresce e toast "entrou na lista"; "Ver preços" → "Sem preços agora (sem rede...)";
  "Steam ↗" → "Rede desligada..."; remover → Desfazer na barra; Ctrl+6 → 7 cartões; busca no
  catálogo (steamrip) → "busca falhou: ... precisa de rede"; adicionar personalizada "Prova T6" →
  8 cartões, toast "adicionada", persiste em `integracoes-usuario.json`; "Buscar no site" →
  "Rede desligada"; remover → 7 cartões e sai do json; chave reservada 'steamrip' → erro-form
  "Esta chave já é de uma integração do Hub.". Screenshots `f2-desejos.png`, `f2-integracoes.png`.
  PROVA OK.

- [x] **Step 6: Commit**

```powershell
git add codigo/frontends/ponte.py codigo/ferramentas/testes/test_ponte.py codigo/frontends/servicos_ui/__init__.py codigo/frontends/electron/src/main/index.ts codigo/frontends/electron/src/shared/api.ts codigo/frontends/electron/src/preload/index.ts codigo/frontends/electron/src/renderer/src/vistas/Desejos.tsx codigo/frontends/electron/src/renderer/src/vistas/Integracoes.tsx codigo/frontends/electron/src/renderer/src/app.tsx codigo/frontends/electron/src/renderer/src/estilo.css
git commit -m "electron: telas Desejos e Integracoes (F2)"
```

---

### Task 7: Downloads — torrents, atividade (jobs) e importar concluídos

**Files:**
- Create: `renderer/src/vistas/Downloads.tsx`, `renderer/src/componentes/Atividade.tsx`
- Modify: `estado/trabalhos.ts` (completo: eventos, ativo, cancelar), `ponte.py` +
  `test_ponte.py` (`torrents.*`), `servicos_ui/mix_torrents.py` (`torrent_controlar`),
  `main/index.ts` (IPC `app:abrir-pasta` com validação na home), `preload/index.ts`, `app.tsx`,
  `estilo.css`, `semear_prova_electron.py` (fixture `BT_backup` sintética)

**Interfaces:**
- Consumes: `torrents_prontos`, `qbit_controlar` (via serviço novo), `importar_torrent`,
  `organizar_download`, `fora_do_destino`.
- Produces:
  - `torrents.listar {}` → `{"itens":[{hash,nome,estado,pct,feito,total,fonte_progresso,
    velocidade,eta,save_path}],"erros":[str]}`
  - `torrents.controlar {ident:str, acao:"pausar"|"retomar"}` → `{"ok":True,…}` (só API)
  - `torrents.importar {caminho:str}` → job; `torrents.organizar {caminho:str}` →
    `{"ok":True,…}`; `torrents.fora_destino {caminho:str}` → `{"fora":bool}`
  - `estado/trabalhos.ts`: reducer de `trabalho` (início/progresso/fim), `ativo()` (primeiro
    rodando), `cancelar(id)`; `Atividade` no rodapé (rótulo + barra quando `pct` != null + Parar
    quando `cancelavel`)

- [x] **Step 1: RED** — `trabalhos.test.ts` (`ativo` primeiro rodando/cancelando), `test_ponte`
  (`torrents.listar` vazio sem fixture; `torrents.controlar` valida ação; `torrents.fora_destino`
  true/false; `torrents.importar` cria job).

- [x] **Step 2: RED roda** — vitest 1 arquivo falhando (`ativo` não exportado); `--modulo test_ponte`
  39/43.

- [x] **Step 3: Implementar ponte + serviço + IPC (`app:abrir-pasta`).** Serviço: `listar_torrents`,
  `torrent_controlar`, `fora_do_destino`, `organizar_download` em `MixTorrents`; ponte `torrents.listar`
  (transforma para o shape do plano), `torrents.controlar`, `torrents.fora_destino`,
  `torrents.organizar`, `torrents.importar` (job); IPC `app:abrir-pasta` valida que o caminho está
  sob a home; preload `abrirPasta`. `estado/trabalhos.ts` completo: `ativo`, `cancelarTrabalho`.

- [x] **Step 4: Implementar tela** — `Downloads.tsx` (linhas com ícone, título, pct/estado, feito/total,
  estimativa em disco, velocidade, ETA, barra, Abrir pasta, Pausar/Retomar só em fonte api,
  Organizar com confirmação, resumo de espaço livre, polling 5 s, modal "Importar concluídos…"
  com Importar → job → toast + recarregar) + `Atividade.tsx` (rodapé global).

- [x] **Step 5: GREEN + typecheck + prova E2E** — vitest 18 arquivos / 124 testes; `tsc`+build ok;
  `--modulo test_ponte` 43/43; suíte completa 554/554; ruff limpo.
  Prova `.provas/electron/prova-f2-t7-downloads.ps1` (home `home-f2-t7`, CDP 9238): `fora_destino`
  true (fora) e false (dentro de `D:\Games\Piratas`); `controlar` com ação inválida rejeita;
  `abrir-pasta` fora da home rejeita; tela Downloads abre; `torrents.importar` cria job (JOB_OK).
  Screenshots `f2-downloads.png`, `f2-atividade.png`. PROVA OK.

- [x] **Step 6: Commit**

```powershell
git add codigo/frontends/ponte.py codigo/ferramentas/testes/test_ponte.py codigo/frontends/servicos_ui/mix_torrents.py codigo/frontends/electron/src/main/index.ts codigo/frontends/electron/src/preload/index.ts codigo/frontends/electron/src/renderer/src/vistas/Downloads.tsx codigo/frontends/electron/src/renderer/src/componentes/Atividade.tsx codigo/frontends/electron/src/renderer/src/estado/trabalhos.ts codigo/frontends/electron/src/renderer/src/estado/trabalhos.test.ts codigo/frontends/electron/src/renderer/src/app.tsx codigo/frontends/electron/src/renderer/src/estilo.css codigo/ferramentas/semear_prova_electron.py
git commit -m "electron: tela Downloads com torrents e trabalhos (F2)"
```

---

### Task 8: Vídeos — lista, player interno e reprodutor externo

**Files:**
- Create: `renderer/src/vistas/Videos.tsx`, `renderer/src/componentes/DialogoVideo.tsx`
- Modify: `ponte.py` + `test_ponte.py` (`videos.*`), `app.tsx`, `estilo.css`

**Interfaces:**
- Consumes: snapshot `videos` (`titulo, canal, duracao_s, video_path, video_sha`), `video_local`,
  `salvar_posicao_video`, `reproduzir_video`, `importar_videos`, `item.excluir`/`item.desfazer`.
- Produces:
  - `videos.local {id:int}` → `{"id","titulo","posicao","sha"}` (o path vem do snapshot e vira
    `mediaUrl`)
  - `videos.salvar_posicao {sha:str, posicao:float}` → `{"ok":True}` (sha hex-64 validado)
  - `videos.reproduzir {id:int, reprodutor:str}` → `{"ok":True,"reprodutor",…}` (auto/VLC/MPV/MPCHC)
  - `videos.importar {pasta:str}` → job (mesmo padrão de `musicas.importar`)

- [x] **Step 1: RED** — `test_ponte` (`videos.local` sem arquivo → erro claro; `salvar_posicao`
  valida sha; `reproduzir` inválido → erro; `importar` job).

- [x] **Step 2: RED roda** — `--modulo test_ponte`: 44/47.

- [x] **Step 3: Implementar ponte.** `videos.local` (retorna `{id, titulo, posicao, sha}`), `videos.salvar_posicao`
  (sha hex-64 validado, posição não-negativa), `videos.reproduzir` (auto/VLC/MPV/MPC-HC via
  `reproduzir_video`), `videos.importar` (job).

- [x] **Step 4: Implementar tela** — `Videos.tsx` (lista ícone ▶, título, "canal · N min", Enter toca
  internamente via `<video>` sobre `tucoteca-media://`, combo de reprodutor + "Assistir externo",
  "+ Importar vídeos" com `escolherPasta` + job, persistência de posição a cada segundo) +
  `DialogoVideo.tsx` (modal de escolha de reprodutor).

- [x] **Step 5: GREEN + typecheck + prova E2E** — vitest 18 arquivos / 124 testes; `tsc`+build ok;
  `--modulo test_ponte` 47/47; suíte completa 558/558; ruff limpo.
  Prova `.provas/electron/prova-f2-t8-videos.ps1` (home `home-f2-t8`, CDP 9240): `videos.local`
  sem arquivo → "Vídeo não encontrado"; `salvar_posicao` sha inválido → erro e sha válido → ok;
  `reproduzir` inválido → erro; `videos.importar` cria job (JOB_OK); tela Vídeos abre.
  Screenshot `f2-videos.png`. PROVA OK. (Sem arquivo de vídeo sintético no semeador — limite
  registrado: player interno não exercitado com mídia real nesta fatia.)

- [x] **Step 6: Commit**

```powershell
git add codigo/frontends/ponte.py codigo/ferramentas/testes/test_ponte.py codigo/frontends/electron/src/renderer/src/vistas/Videos.tsx codigo/frontends/electron/src/renderer/src/componentes/DialogoVideo.tsx codigo/frontends/electron/src/renderer/src/app.tsx codigo/frontends/electron/src/renderer/src/estilo.css
git commit -m "electron: tela Videos com player interno (F2)"
```

---

### Task 9: Provas finais, docs e fechamento da F2

**Files:**
- Create: `.provas/electron/prova-f2.ps1` (checklist E2E consolidado; local, não versionado)
- Modify: `docs/DESKTOP_ELECTRON.md`, `CHANGELOG.md`
- Test: rodada completa

- [ ] **Step 1: `prova-f2.ps1`** — um app real (CDP) com home semeada estendida: seções Jogos/
  Músicas/Desejos/Downloads/Integrações/Vídeos abertas por Ctrl+1..8 e clicadas; paleta → detalhe
  de jogo; favoritar/editar/excluir/desfazer; jogar com o jogo sintético (~35 s); tocar WAV e ver `currentTime`;
  importar WAVs; importar torrent 100% e conferir jogo novo; play/pause de torrent sem API não
  aparece; F11 e Alt continuam (reuso do helper de foco da F1). Fotos `f2-*.png` + "PROVA F2 OK".

- [ ] **Step 2: Rodada completa**

```powershell
git diff --check
py -3.14 -B codigo/ferramentas/testes/executar.py
.provas/venv-ruff/Scripts/ruff.exe check codigo conftest.py
npm --prefix codigo/frontends/electron run test
npm --prefix codigo/frontends/electron run typecheck
npm --prefix codigo/frontends/electron run build
npm --prefix codigo/frontends/electron run selftest -- --screenshot ..\..\..\.provas\electron\f2-selftest.png
powershell -NoProfile -ExecutionPolicy Bypass -File .provas\electron\prova-shell.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .provas\electron\prova-queda.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .provas\electron\prova-f2.ps1
```

- [ ] **Step 3: Docs** — `docs/DESKTOP_ELECTRON.md`: métodos novos na tabela, seção "Telas da F2"
  (comportamentos por tela), protocolo de mídia com Range, jobs/eventos, estado por perfil,
  divergências (player do renderer vs MCI; volume do sistema ainda não portado) e **pendências
  nomeadas** (importação/scan/drag&drop, capas, conquistas, mods/emulação, saves/ferramentas,
  Spotify/músicas online/fila/letras, YouTube embutido/busca/download, catálogo pacotes/UAC,
  configurações/tema, export/import da coleção, sincronizar Steam/wishlist/preços offline,
  "Iniciar cliente"/"Pacotes locais", volume global). CHANGELOG: linha nova em "Não lançado".

- [ ] **Step 4: Commit**

```powershell
git add docs/DESKTOP_ELECTRON.md CHANGELOG.md
git commit -m "electron: telas restantes e docs da F2"
```

- [ ] **Step 5: task-done da F2** com o ledger (`.superpowers/sdd/2026-10-18-electron-f2-telas/`)
  e relatório na conversa (resultados, limitações, pendências).

---

## Riscos e limitações honestas (F2)

- Porte é **parcial**: as pendências nomeadas acima continuam no Qt e precisam de fatia própria
  (F2b/F3) antes de qualquer "aposentar o Qt" (F5).
- Player do renderer diverge do MCI do núcleo (melhor: seek de verdade); `player.py` fica só na TUI.
- Volume do rodapé é o volume **do player** (o volume global Windows não foi portado).
- Vídeo interno depende de codec suportado pelo Chromium/Electron; sem vídeo sintético a prova de
  renderização visual registra o limite.
- Prova de "jogar" usa processo sintético (`ping.exe` em loopback, ~35 s); nada de jogo real, UAC ou emulador.
- Torrent: pausar/retomar só com API do qBittorrent ligada (na prova, fixture local não tem API).
- Gamepad continua navegando só as seções (navegação dentro de listas fica para depois).
