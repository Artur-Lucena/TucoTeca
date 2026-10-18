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
  coleção real. Dados de prova sempre sintéticos (WAV gerado com `wave`, `.cmd` de mentira,
  `BT_backup` sintético, PNG do placeholder).
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
codigo/ferramentas/semear_prova_electron.py     + WAV sintético, .cmd de jogo, BT_backup falso
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
- Extend proof seed (jogo com `.cmd`): `codigo/ferramentas/semear_prova_electron.py` — o jogo
  "Stardew Valley" ganha `executable_path` apontando para `jogar-teste.cmd` criado no destino
  (script de prova: `@echo off` + `ping -n 4 127.0.0.1 >nul`, encerra sozinho, nada real).

**Interfaces:**
- Consumes: `ServicoBiblioteca.iniciar_jogo(gid, ao_fim)` (bloqueia até o jogo sair; `ao_fim(horas,
  rastreado)`), `registrar_sessao`, `backup_pos_sessao`, `aparencia()`; `qt_bridge/mix_jogos.py:401-459`
  como referência de comportamento.
- Produces:
  - `trabalhos.listar {}` → `[{"id","rotulo","estado","pct","cancelavel","iniciado_em","aviso"}]`
    (`estado` ∈ `rodando|cancelando|ok|erro|cancelado`)
  - `trabalhos.cancelar {id:int}` → job dict; desconhecido/não cancelável → `ok=false`
  - `jogo.jogar {id:int}` → `{"trabalho": {…}}` imediato (nunca bloqueia o loop)
  - `jogo.registrar_horas {id:int, horas:float}` → `{"ok":True,…}` (horas > 0)
  - Evento `{"evento":"trabalho","dados":{…job…}}` no início, mudança de progresso e fim
    (`dados.detalhe` com `horas`, `rastreado`, `aviso` quando houver)
  - Um único jogo por vez (`escopo="jogo"`): segundo `jogo.jogar` → `ok=false "já em jogo"`

- [ ] **Step 1: Casos RED** — `teste_ponte_trabalhos_eventos_e_cancelamento` (serviço fake com
  função longa de mentira: job com progresso 0→50→100 e cancelável — `trabalhos.cancelar` com
  `threading.Event`; assert das linhas de evento capturadas na saída), `teste_ponte_jogar_em_thread`
  (fake `iniciar_jogo` bloqueia num `Event`; a resposta volta imediatamente com o job; liberar →
  `registrar_sessao` chamado com as horas e backup pós-sessão; evento de fim), e
  `teste_ponte_jogar_recusa_segundo`.

- [ ] **Step 2: Rodar RED** — falhas "trabalhos … desconhecido".

- [ ] **Step 3: Implementar**

Classe `Trabalhos` em `ponte.py`: `iniciar(rotulo, funcao, escopo=None, cancelavel=False)` com
thread daemon; `funcao(progresso, cancelado)`; `progresso(pct)` atualiza o job (arredonda 0–100) e
emite evento só quando o valor muda; `cancelado` é `threading.Event`; exceções → estado `erro` com
`str(erro)`. `servir` ganha `saida_lock` compartilhado (escrita de resposta e evento na mesma
seção crítica); `Ponte.__init__(…, trabalhos=None)` para injeção nos testes. `jogo.jogar` inicia
job `escopo="jogo"` que chama `iniciar_jogo(gid, ao_fim_capturador)`, e ao retornar (espelhando
`_fim_jogo`): se `rastreado`, `registrar_sessao(gid, horas)` e, se
`aparencia().get("auto_backup", True)`, `backup_pos_sessao(gid)` (falha vira `aviso` no detalhe,
nunca derruba o job). `jogo.registrar_horas` valida `horas` finito > 0.

- [ ] **Step 4: Rodar GREEN** — `--modulo test_ponte` completo.

- [ ] **Step 5: Prova local com o `.cmd`**

Semear home de prova (com o `.cmd`) e, com o app real em CDP, chamar
`window.tucoteca.chamar('jogo.jogar', {id: …})`; esperar evento de fim (~3 s) e confirmar horas
somadas no snapshot e jogo liberado para novo `jogo.jogar`. Registrar limite: prova com executável
sintético (nada de jogo real).

- [ ] **Step 6: Gates e commit**

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

- [ ] **Step 1: RED** — `jogos.test.ts`: filtro por plataforma, favoritos, pendências (por
  `idsPendentes`), busca sem acento/multi-palavra, ordenação por título/horas/recentes (empate
  estável por título), lista vazia. `dados.test.ts`: `recarregar()` junta snapshot+saúde e mantém o
  anterior em erro.

- [ ] **Step 2: Rodar RED** — `npm --prefix codigo/frontends/electron run test`.

- [ ] **Step 3: Implementar** — store, módulos puros, `PosterCard`, `Jogos.tsx` (grade CSS com
  `grid-template-columns: repeat(auto-fill, …)`, chips de filtro, combo de ordenação, campo de
  busca, resumo "N de TOTAL jogos · filtros · ordem" e chip "Pendências (N)"), wire no `app.tsx`
  (ao montar/trocar seção: ler `preferencias.filtro`; ao mudar chip/combo: `salvar_filtro` e
  refiltro local imediato). Seleção com seta/Enter navega a grade; clique seleciona.

- [ ] **Step 4: GREEN + build + typecheck.**

- [ ] **Step 5: Prova** — app real com home semeada; CDP: Ctrl+2, aplicar filtro "PC", ordenar
  por horas, digitar busca "knight" → só Hollow Knight; screenshot `f2-jogos.png`; conferir
  `preferencias-pessoais.json` com `filtro/ordem` do perfil.

- [ ] **Step 6: Commit**

```powershell
git add codigo/frontends/electron/src/renderer/src/estado/dados.ts codigo/frontends/electron/src/renderer/src/estado/dados.test.ts codigo/frontends/electron/src/renderer/src/estado/jogos.ts codigo/frontends/electron/src/renderer/src/estado/jogos.test.ts codigo/frontends/electron/src/renderer/src/vistas/Jogos.tsx codigo/frontends/electron/src/renderer/src/componentes/PosterCard.tsx codigo/frontends/electron/src/renderer/src/app.tsx codigo/frontends/electron/src/renderer/src/estilo.css
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

- [ ] **Step 1: RED** — `detalhe.test.tsx`? Manter simples: funções puras em
  `estado/jogos.ts` (`validarNota(texto) → number|null`, `normalizarEtiquetas(texto)`) com testes;
  estado do drawer em `app.tsx` testado via funções puras onde valer no módulo.

- [ ] **Step 2: Implementar** — drawer com capa/título/plataforma·status/horas·nota/etiquetas,
  botões Jogar, ★ Favoritar, Editar (form: título, exe, args/ROM, status, nota 0–10, etiquetas),
  Registrar horas (input > 0), Remover (confirm + aviso de músicas quando aplicável), Observações
  (textarea + Salvar). Duplo clique no card joga; Espaço/clique direito abrem o detalhe; Enter na
  grade joga. Estado "jogando…" enquanto o job existir (via `estado/trabalhos.ts` da Task 7 —
  **nesta tarefa criar já o módulo mínimo** para o jogo); ao fim: toast + `recarregar()`.
  Desfazer global na barra de status quando `lixeira.estado.disponivel`.

- [ ] **Step 3: GREEN + typecheck.**

- [ ] **Step 4: Prova E2E** — home de prova: abrir paleta, Enter em "Celeste" → detalhe; favoritar;
  editar nota/etiquetas (persistiu no `jogo.ler`); Remover → Desfazer e item volta; Jogar com o
  `.cmd` → banner "jogando" some em ~3 s, horas somadas, toast de backup pós-sessão. Screenshots
  `f2-detalhe.png`, `f2-desfazer.png`.

- [ ] **Step 5: Commit**

```powershell
git add codigo/frontends/electron/src/renderer/src/componentes/DetalheJogo.tsx codigo/frontends/electron/src/renderer/src/estado/trabalhos.ts codigo/frontends/electron/src/renderer/src/estado/trabalhos.test.ts codigo/frontends/electron/src/renderer/src/app.tsx codigo/frontends/electron/src/main/ponte.ts codigo/frontends/electron/src/renderer/src/estilo.css
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

- [ ] **Step 1: RED** — `midia.test.ts` (parse/validação de caminho dentro da home; `Range:
  bytes=0-99`→206 `{start:0,end:99}`; `bytes=100-`→ até o fim; fim além do tamanho → recorte;
  malformado → 416; sem Range → 200), `player.test.ts` (transporte, modos, fim de faixa, fila
  vazia), `test_ponte` (`musicas.importar` cria job e importa WAV sintético;
  `musicas.baixar_fila` sem yt-dlp/rede → job termina em erro claro; com serviço fake de
  progresso/cancelamento → eventos com pct e cancelado cooperativo — mesmo padrão da Task 2).

- [ ] **Step 2: RED roda.**

- [ ] **Step 3: Implementar** — handler com `fs.createReadStream`/`Readable.toWeb` e
  `Content-Type` por extensão; `app.commandLine.appendSwitch('autoplay-policy',
  'no-user-gesture-required')`; `PlayerRodape` (capa, título, artista, tempo `m:ss / m:ss`,
  barra clicável para seek, ❮ ▶/Ⅱ ❯ ■, modo, fila com ▶ no atual, volume do player);
  `Musicas.tsx` (lista com capa/título/artista·álbum, Enter toca, busca local, "Tocar",
  "Remover" com aviso de que apaga o arquivo, "+ Importar pasta" → `escolherPasta` +
  `musicas.importar` → toast + `recarregar`; painel "Fila de downloads" com a fila do snapshot e
  botão "Baixar pendentes" → `musicas.baixar_fila` (barra de progresso do job + Parar no
  `Atividade`; o `Atividade` completo chega na Task 7 — aqui basta o mínimo do job na lista);
  semear WAVs de 2 s (440 Hz, `wave` stdlib) e ligar `musica_path`.

- [ ] **Step 4: GREEN + typecheck + build.**

- [ ] **Step 5: Prova E2E** — clicar em "Weightless" → `<audio>` com `currentTime > 0`,
  rodapé com tempo andando, próximo/anterior/modo alternando (assert de estado), remover uma
  música → aviso; importar pasta sintética via bridge → lista cresce. Screenshots
  `f2-musicas.png`, `f2-player.png`.

- [ ] **Step 6: Commit**

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

- [ ] **Step 1: RED (Python)** — `teste_ponte_desejos_adicionar_remover_desfazer`,
  `teste_ponte_desejos_precos_sem_rede` (mock/off → `{}`), `teste_ponte_integracoes_listar_e_url`,
  `teste_ponte_integracoes_personalizada_adiciona_e_remove` (chave nova persiste no
  `integracoes-usuario.json` do home de prova), `teste_ponte_integracoes_buscar_termo_curto_erro`.

- [ ] **Step 2: RED roda.**

- [ ] **Step 3: Implementar ponte + IPC.**

- [ ] **Step 4: Implementar telas.** Desejos: lista (título, "Steam · appid", preço quando
  consultado), "Steam ↗" (abre `https://store.steampowered.com/app/<appid>`), "Ver preços"
  (spinner → tabela; vazio → toast "sem rede"), "+ Adicionar" (modal nome + appid numérico),
  Remover com Desfazer. Nota visível: sincronizar Steam/importar wishlist/buscar fonte ainda não
  nesta fatia (entra nas pendências). Integrações: grade de cartões (inicial colorida, nome,
  descrição, capacidades), botão principal por tipo (`url` com `{q}` pede termo; sem `{q}` abre
  externo; `download` navega para Downloads; `config`/`musicas_online` → toast "ainda não nesta
  fatia"), campo de busca por integração de catálogo (resultados com link), "+ Adicionar"
  (validações do serviço mostradas no formulário), Remover em personalizadas.

- [ ] **Step 5: GREEN + testes web + typecheck; prova E2E** (adicionar desejo, "Ver preços" com
  rede desligada avisa; adicionar/remover integração personalizada; screenshot `f2-desejos.png`,
  `f2-integracoes.png`).

- [ ] **Step 6: Commit**

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

- [ ] **Step 1: RED** — `trabalhos.test.ts` (eventos fora de ordem/duplicados; fim com erro vira
  toast; cancelamento marca `cancelando`); `test_ponte` (`torrents.listar` vazio sem fixture;
  `torrents.controlar` valida ação; `torrents.fora_destino` true/false; `torrents.importar` vira
  job e importa fixture sintética de pasta).

- [ ] **Step 2: RED roda.**

- [ ] **Step 3: Implementar ponte + serviço + IPC (`app:abrir-pasta`).**

- [ ] **Step 4: Implementar tela** — linha com ícone ↓, título, `pct% · estado`, `feito/total`
  (GB/MB), `· estimativa em disco` quando `fonte_progresso=="estimativa"`, velocidade e ETA;
  barra 0–100; botões Abrir pasta, Pausar/Retomar (só `fonte_progresso=="api"`), Organizar (só
  quando fora do destino; confirm); resumo com "· N GB livres" (do snapshot `sistema`); polling 5 s
  só com a seção ativa; "Importar concluídos…" (modal lista 100% com estados; Importar → job →
  toast + recarregar; "Só entra aqui o que chegou a 100%"). Nota: "Iniciar cliente" e "Pacotes
  locais…" ficam para as pendências.

- [ ] **Step 5: GREEN + typecheck + prova E2E** com `BT_backup` sintético (item 100% aparece;
  importar cria jogo; item incompleto não importa; screenshot `f2-downloads.png`,
  `f2-atividade.png`).

- [ ] **Step 6: Commit**

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

- [ ] **Step 1: RED** — `test_ponte` (`videos.local` sem arquivo → erro claro; `salvar_posicao`
  valida sha; `reproduzir` inválido → erro; `importar` job).

- [ ] **Step 2: RED roda.**

- [ ] **Step 3: Implementar ponte.**

- [ ] **Step 4: Implementar tela** — lista (ícone ▶, título, "canal · N min"), Enter/combo assistir
  (Interno padrão; combo Auto/VLC/MPV/MPC-HC), "+ Importar vídeos" (`escolherPasta` + job),
  Remover com Desfazer, busca local. `DialogoVideo`: `<video>` via `tucoteca-media://`, retoma na
  `posicao` (seek no `loadedmetadata`), slider de seek, play/pause, parar, velocidade 0.5–2×, ao
  fechar salva posição.

- [ ] **Step 5: GREEN + typecheck + prova E2E** — se houver ffmpeg no repo/`programa/`, gerar
  vídeo de 2 s sintético no semeador; senão provar com WAV (duration>0, currentTime avança) e
  registrar o limite "sem arquivo de vídeo sintético". Posição salva e retomada conferidas.
  Screenshots `f2-videos.png`, `f2-video-player.png`.

- [ ] **Step 6: Commit**

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
  de jogo; favoritar/editar/excluir/desfazer; jogar com o `.cmd`; tocar WAV e ver `currentTime`;
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
- Prova de "jogar" usa `.cmd` sintético; nada de jogo real, UAC ou emulador.
- Torrent: pausar/retomar só com API do qBittorrent ligada (na prova, fixture local não tem API).
- Gamepad continua navegando só as seções (navegação dentro de listas fica para depois).
