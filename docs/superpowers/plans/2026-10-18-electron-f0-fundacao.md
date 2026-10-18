# Plano F0 — Fundação do desktop Electron (ponte Python + shell + Início)

> **Para agentes executores:** SUB-SKILL OBRIGATÓRIA: use `superpowers:executing-plans` para
> implementar este plano tarefa a tarefa (ou `superpowers:subagent-driven-development` para
> paralelizar). Passos usam checkboxes (`- [ ]`).

**Objetivo:** primeira fatia funcional do TucoTeca 1.2.0 em Electron — janela real abrindo,
falar com o núcleo Python existente via ponte NDJSON local (sem porta TCP), navegação dirigida
pelo registro de módulos, tela Início lendo a coleção e selftest com screenshot. Nada do núcleo
muda; nada portátil antigo é apagado ainda.

**Arquitetura:** o Electron é só interface. O processo principal (main) sobe o Python
(`codigo/frontends/ponte.py`) como processo filho e fala JSON-RPC de linha nova (NDJSON) por
stdin/stdout. O renderer (Preact) fala com o main via IPC; nunca vê o Python. A navegação vem
de `servicos_ui.modulos` — cada seção nasce como um módulo declarado, preparando a F3
(módulos de terceiros). Imagens locais (capas) são servidas por protocolo próprio
`tucoteca-img://`, restrito à pasta da coleção.

**Stack:** Python 3.14 (núcleo stdlib, intocado) + Electron + electron-vite + Vite +
TypeScript + Preact + @preact/signals; testes: runner stdlib (Python) e vitest (front); prova
física: `--selftest --screenshot` (padrão já usado pelo app Qt).

**Fora de escopo desta fatia:** portar as demais telas (F1/F2), instalar/baixar módulos (F3),
instalador (F4), aposentar Qt/portátil (F5), 1.2.0 (F6). Decisão registrada: `BIBLIOTECA_WEBENGINE`
morre junto com o Qt na F5; aqui ele nem é consultado.

---

## Contratos desta fatia (o que fica congelado)

### Protocolo NDJSON (linha por linha, UTF-8)

```
requisição:  {"id": 1, "metodo": "nucleo.snapshot", "params": {}}
resposta ok: {"id": 1, "ok": true,  "resultado": {...}}
resposta erro: {"id": 1, "ok": false, "erro": "mensagem curta"}
evento:      {"evento": "bloqueio", "dados": {...}}          # assíncrono, sem id (F0: só o de bloqueio)
```

- Linha em branco é ignorada; linha inválida vira `{"id": null, "ok": false, "erro": "JSON inválido"}`.
- Método desconhecido: `ok=false`, `erro="método desconhecido: X"` — a ponte nunca morre por erro de chamada.
- Exceção de método: `ok=false` com a mensagem, e a ponte continua servindo.

### Métodos F0

| Método | Resultado |
| --- | --- |
| `nucleo.ping` | `{"pong": true, "versao": "…", "home": "…", "db": "…"}` |
| `nucleo.snapshot` | exatamente `ServicoBiblioteca.snapshot()` |
| `modulos.listar` | `[{"chave","nome","descricao","icone","ordem"}, …]` |

### Registro de módulos F0 (`servicos_ui/modulos.py`)

Ordem/nome idênticos ao HUD atual do QML (`Main.qml` linhas 34-37):
`inicio, jogos, musicas, desejos, downloads, integracoes, videos, youtube` (ordem 10..80).
`Modulo` = dataclass congelado `(chave, nome, descricao="", icone="", ordem=100)` com
`apresentar() -> dict` JSON-safe. Grada de crescimento (F3): permissões, habilitado, origem.

### Descoberta do Python (main, em ordem)

1. env `TUCOTECA_PYTHON` (caminho ou comando);
2. `<raiz>/programa/windows-x64/python/python.exe` (runtime embutido, layout de entrega);
3. Windows: `py -3.14`; outros: `python3` (fallback `python`).

Spawn: `<python> -B <raiz>/codigo/frontends/ponte.py [--db X] [--ignorar-lock]` com
`PYTHONDONTWRITEBYTECODE=1`, `PYTHONIOENCODING=utf-8`, env herdado (o `BIBLIOTECA_HOME` do
chamador manda; se ausente, a ponte usa a raiz do repo — mesmo comportamento do `abrir_hub`).

### URL de mídia

`file:///C:/…/dados/capas/x.png` → `tucoteca-img://local/C:/…/dados/capas/x.png`
(conversão pura no renderer/preload; o main valida que o alvo resolvido está sob `BIBLIOTECA_HOME`
e serve somente leitura). URL `http(s)` passa direto; vazio vira `""`.

### Selftest (paridade com o `app_qt.py --selftest`)

`electron . --selftest [--screenshot arq.png] [--db x] [--ignorar-lock]`:
sobe a ponte, espera o renderer sinalizar `pronto` (timeout 15 s), grava screenshot se pedido e
imprime `[ok] selftest Electron: N jogos; ponte, módulos e Início carregados`; erros → stderr
`[erro] …`, código 1; bloqueio de lock → janela mínima com o motivo, código 2 (igual ao Qt).

### Higiene

- `TUCOTECA_USERDATA` (env): redireciona o userData do Chromium (provas usam
  `.provas/electron/userdata`; nunca `%APPDATA%` durante testes).
- Toda prova roda com `BIBLIOTECA_HOME` de temporário semeado — jamais a coleção real.
- `.gitignore` local em `codigo/frontends/electron/` (`node_modules/`, `out/`, `dist/`).

---

## Foco de revisão (falhas que este plano precisa pegar)

- Paridade de envelope entre `ponte.py` e `ClientePonte` (nomes `ok`/`resultado`/`erro` escorregam fácil) → provado pelo selftest ponta a ponta.
- Falha de spawn (Python não achado) sem travar a UI → erro claro no console e saída ≠ 0 no selftest.
- stdout chunkado/parcial → leitor por linha com buffer (teste unitário de `SeparadorLinhas`).
- Traversal no protocolo de mídia (`..`, caminho fora da home, `%2e%2e`) → teste unitário de `caminhoPermitido`.
- Respostas fora de ordem / id órfão / timeout → testes de `Pendentes`.
- Lock ocupado (Qt aberto) → caminho de código 2 com motivo na tela; teste manual + unitário da mensagem.
- Ponte caindo com app aberto → evento `ponte.encerrada` → aviso na UI (F0: console + badge; hardening na F1).

---

## Tarefas

### Task 1 — Branch, andaime npm e janela mínima

**Arquivos:** criar `codigo/frontends/electron/{package.json,electron.vite.config.ts,tsconfig*.json,.gitignore}`, `codigo/frontends/electron/src/main/index.ts`, `src/preload/index.ts`, `src/renderer/index.html`, `src/renderer/src/{main.tsx,app.tsx,estilo.css}`.

- [x] `git status --short --branch` limpo (só `.kilo/` e `kilo.json` alheios, untracked) e
      `git switch -c revisao/electron-1.2.0`.
- [x] Criar os arquivos do andaime (janela simples, sem ponte ainda): janela 1440×920, mínimo
      960×640, fundo `#12141a`, `autoHideMenuBar`, `contextIsolation: true`, `sandbox: true`,
      `nodeIntegration: false`; devtools só em dev (`app.commandLine`/atalho F12).
- [x] `npm install` no `codigo/frontends/electron` (electron, electron-vite, vite, typescript,
      preact, @preact/signals; vitest em devDependencies). `package-lock.json` versionado.
- [x] Scripts npm: `dev`, `build`, `typecheck` (tsc --noEmit nos dois tsconfig — ver ruling),
      `test` (vitest run) e `selftest` (`electron-vite build && electron . --selftest`).
- [x] Gate: `npm run typecheck` e `npm run build` verdes; janela abre e fecha limpa
      (conferido em `npm run start` e `npm run dev`: 4 processos Electron vivos, mortos sem sobra).

**Commit 1:** `electron: andaime do app (electron-vite + TS + Preact)`

### Task 2 — Registro de módulos no núcleo (TDD)

**Arquivos:** criar `codigo/frontends/servicos_ui/modulos.py`, `codigo/ferramentas/testes/test_modulos_hub.py`; editar `codigo/frontends/servicos_ui/__init__.py` (reexport).

- [x] Escrever `test_modulos_hub.py` primeiro, com o padrão de isolamento dos testes existentes
      (o 3º teste cobre nomes/descrições/ícones — superset do planejado):
      `teste_modulos_padrao_chaves_e_ordem` (8 módulos, chaves/ordem exatas do HUD),
      `teste_apresentar_json_safe` (`json.dumps` passa; campos `chave,nome,descricao,icone,ordem`),
      `teste_descricoes_presentes` (toda descrição não vazia — espelho do `Main.qml`).
- [x] Rodar e ver falhar: `py -3.14 -B codigo/ferramentas/testes/executar.py --modulo test_modulos_hub`
      → falhou 3/3 com `ModuleNotFoundError: servicos_ui.modulos` (motivo certo).
- [x] Implementar `modulos.py` (dataclass congelado + `modulos_padrao()`) e reexport no
      `__init__.py` (import + `__all__`). Textos de descrição vieram das "dicas" do `Main.qml`.
- [x] Gate: 3/3 PASS + `ruff check codigo conftest.py` limpo no repo inteiro
      (`ruff` roda da venv `.provas/venv-ruff` — o Python global não tem o pacote).

**Commit 2:** `frontend: registro de modulos do desktop (F0)`

### Task 3 — Ponte NDJSON em Python (TDD, em processo)

O runner bloqueia processos externos — os testes chamam a ponte **importada** (`import ponte`
com `codigo/frontends` no path), sem subprocesso.

**Arquivos:** criar `codigo/frontends/ponte.py`, `codigo/ferramentas/testes/test_ponte.py`.

- [x] `test_ponte.py` primeiro (11 testes — superset do previsto; `teste_servir_processa_varias_linhas`
      cobre a serialização linha a linha, no lugar do `teste_executar_linha_resposta_serializada`):
      `teste_ping_responde`, `teste_metodo_desconhecido`, `teste_linha_invalida_tem_id_null`,
      `teste_linha_em_branco_ignorada`, `teste_excecao_vira_erro_e_ponte_sobrevive`,
      `teste_executar_linha_resposta_serializada` (id ecoado),
      `teste_snapshot_real_em_home_temporario` (cria db com `core.get_db` + `core.criar_jogo`,
      monta `ServicoBiblioteca`, confere jogo no snapshot e `capa_url`),
      `teste_modulos_listar_via_ponte`.
- [x] Falhar primeiro (11/11 `ModuleNotFoundError: No module named 'ponte'`), depois implementar
      (tabela global `METODOS` + `Ponte(servico, metodos=None)` em vez do `registrar(ponte, servico)`
      — mesmo contrato, menos superfície):
      `Ponte(servico)` com `despachar(metodo, params) -> dict`, `executar_linha(linha) -> str|None`;
      `iniciar(argv=None, entrada=None, saida=None, servico_factory=None) -> int` (parse de
      `--db`, `--ignorar-lock`; `garantir_dirs`; `adquirir_lock`; bloqueio → evento
      `{"evento":"bloqueio","dados":{"erro":…}}` e retorno 2; senão `servir()` lendo
      `entrada` linha a linha, escrevendo e dando `flush` a cada resposta);
      `registrar(ponte, servico)` monta a tabela dos 3 métodos F0; `preparar_ambiente()` usa
      `ferramentas.abrir_hub.preparar()` (reuso, sem duplicar a leitura do manifesto de runtime).
- [x] `__main__`: `raise SystemExit(iniciar(sys.argv[1:]))` (feito; `main()` extra ficou de fora).
- [x] Gate: 11/11 PASS + `ruff check codigo conftest.py` limpo + prova manual real na pasta
      `.provas/electron/home-manual` (ping/snapshot/módulos/JSON inválido; `rc=0`; lock liberado;
      `dados/` criados na pasta de prova — incidente do `$home` registrado no ledger).

**Commit 3:** `frontend: ponte NDJSON entre Electron e o nucleo Python (F0)`

### Task 4 — Main + preload + cliente da ponte (vitest)

**Arquivos:** `src/main/ponte.ts`, `src/main/arquivos.ts`, `src/shared/midia.ts`,
`src/shared/protocolo.ts`, `src/preload/index.ts`, `src/main/index.ts` e o
`src/renderer/src/app.tsx` (chamada real de `nucleo.ping` + `nucleo.snapshot` e sinal `pronto`)
+ testes `ponte.test.ts`, `arquivos.test.ts`, `midia.test.ts`.

- [x] Testes vitest primeiro (funções puras, sem Electron real) — 23 verdes:
      `Pendentes` (resolve em ordem inversa, id órfão ignorado, timeout, rejeição em massa),
      `SeparadorLinhas` (chunk partido no meio da linha, várias por chunk, CRLF),
      `descobrirPython` (ordem env → runtime → py -3.14; `existe` injetado),
      `caminhoPermitido` (foi para `src/main/caminhos.test.ts` — ver ruling),
      `converterUrlMidia` (`file://` → `tucoteca-img://`, http passa, vazio → "").
- [x] Implementar `ClientePonte`: spawn, leitura NDJSON por buffer, `chamar<T>` com
      timeout (30 s default), eventos via `aoEvento` (wildcard; o preload mantém `assinar(evento)`);
      em fim de processo → rejeita pendentes e chama `aoEncerrar`; `encerrar()` = fecha stdin,
      espera 3 s, `taskkill /T` no Windows — provado ponta a ponta no selftest abaixo.
- [x] Implementar `arquivos.ts`: `registerSchemesAsPrivileged` (antes do ready) +
      `protocol.handle('tucoteca-img', …)` servindo via `net.fetch(pathToFileURL(…))` só sob a home
      (validação pura em `caminhos.ts`, testável sem Electron).
- [x] `main/index.ts`: instância única (`requestSingleInstanceLock`), janela, `TUCOTECA_USERDATA`,
      IPC `ponte:chamar`/eventos/`tucoteca:pronto`, ping de aquecimento antes da janela, bloqueio de
      lock → `dialog.showErrorBox` + exit 2 (equivalente à janela mínima do Qt), fluxo
      `--selftest/--screenshot` (captura `webContents.capturePage`), encerramento limpo da ponte.
- [x] `preload`: `window.tucoteca = { chamar, assinar, pronto, imagemUrl }` (contextBridge, sem Node no renderer).
- [x] Gate: 23/23 testes, `typecheck` e `build` verdes; smoke ponta a ponta real (home e userData
      em `.provas/electron/`): `[ok] selftest Electron: 0 jogos; ponte, módulos e Início carregados`
      com rc=0; caminho de falha com `TUCOTECA_PYTHON` inexistente →
      `[erro] ponte indisponível: … ENOENT`, rc=1 (sem travar).

**Commit 4:** `electron: processo principal, preload e cliente da ponte (F0)`

### Task 5 — Tela Início real + provas visuais

**Arquivos:** `src/renderer/src/{estado.ts,derivacoes.ts}`, `vistas/Inicio.tsx`,
`vistas/Placeholder.tsx`, `componentes/{BarraLateral,Cartao,Capa}.tsx`, testes
`derivacoes.test.ts`; ferramenta `codigo/ferramentas/semear_prova_electron.py`.

- [ ] Teste primeiro: `derivacoes.test.ts` (`continuarJogando`: ordena por `ultima_execucao`
      desc, completa por `horas` desc, limita 6, aceita menos, lida com vazio/sem capa).
- [ ] Implementar shell: barra lateral gerada de `modulos.listar` (ícone por chave com fallback,
      item ativo), área da seção com `<Placeholder>` honesto ("porta chega na F2") para as outras
      7, e `Inicio` com: faixa de números (Jogos/Músicas/Desejos), "Continuar jogando" (cards com
      capa via `imagemUrl`), estado vazio com texto claro. Após o primeiro render do snapshot,
      chamar `tucoteca.pronto({jogos: n})`.
- [ ] `semear_prova_electron.py`: cria home temporária com 3 jogos (título, `ultima_execucao`,
      horas), 2 músicas, 2 desejos e capas PNG reusando `gerar_placeholders._png/_cor`; imprime
      `{"home": …}`. Somente dados sintéticos.
- [ ] Prova: semear em `.provas/electron/home-f0`, rodar
      `electron . --selftest --screenshot .provas/electron/f0-inicio.png` com
      `BIBLIOTECA_HOME`/`TUCOTECA_USERDATA` apontados para `.provas/electron/…`
      → revisar o PNG (3 capas, contadores certos, sidebar com 8 módulos).
- [ ] Prova 2: mesma corrida com home vazia → estado vazio correto, sem erro.
- [ ] Gate: `npm run test` + `typecheck` verdes; screenshot conferido.

**Commit 5:** `electron: tela Inicio com dados reais e provas (F0)`

### Task 6 — Documento de arquitetura e rodada final

**Arquivos:** criar `docs/DESKTOP_ELECTRON.md`; editar `docs/ARQUITETURA.md` (ponteiro curto);
`CHANGELOG.md` (linha em "Não lançado" registrando a F0).

- [ ] Escrever o doc: diagrama (main/preload/renderer/ponte), protocolo NDJSON, métodos F0,
      contrato de módulos, segurança (isolamento de contexto, protocolo de mídia, sem TCP),
      fluxo dev (`npm install`, `dev`, `selftest`, provas), o que a F1..F6 ainda fará.
- [ ] Rodada completa: suíte Python inteira
      (`py -3.14 -B codigo/ferramentas/testes/executar.py`), `ruff check codigo conftest.py`,
      `git diff --check`, `npm run test/typecheck/build`.
- [ ] Relatório final da F0 no chat: resultados, limitações honestas, pendências (F1+).

**Commit 6:** `docs: arquitetura do desktop Electron (F0)`

---

## Pendências conhecidas (herdadas para as próximas fatias)

- F1: shell completo (Ctrl+K, notificações, perfis, gamepad), hardening da queda da ponte, menu.
- F2: telas restantes com a tabela de paridade do `docs/DESKTOP_QT.md` como checklist; jobs com
  progresso/cancelamento na ponte (eventos).
- F3: manifestos de módulos, permissões/consentimento, modo seguro, exemplo de terceiro.
- F4: electron-builder/NSIS, sidecar Python no pacote, aposentar ZIP portátil.
- F5: aposentar QML/`qt_bridge`/PySide6/builders Windows antigos; TUI permanece.
- F6: `VERSION`/`CHANGELOG` → 1.2.0 e commit final (sem push/tag sem pedido).

## Riscos e limitações honestas

- `npm install` baixa o binário do Electron (~100 MB, uma vez) — decisão já tomada pelo usuário.
- Screenshot do selftest exige sessão gráfica real (esta máquina tem); não é prova de CI headless.
- A ponte não tem sandbox de SO para módulos (F3 documentará os limites reais).
- macOS segue fora de escopo; TUI (Linux/macOS) permanece intocada.
