# Desktop Electron (em construção — fatia F1)

## Decisão de arquitetura

O desktop TucoTeca ganha uma segunda geração de interface: um app **Electron**
com renderer **Preact + TypeScript**, mantendo o motor em Python. O domínio
(banco SQLite, emulação, áudio, integrações) continua em `bib_nucleo` /
`servicos_ui`; o Electron substitui apenas a camada de apresentação, em fatias.
O Qt Quick (`docs/DESKTOP_QT.md`) segue como desktop atual no Windows até a F5.

```text
┌────────────────────────── Electron (Node) ────────────────────────────┐
│ main: BrowserWindow, instância única, IPC, protocolo tucoteca-img://  │
│   └ preload (contextBridge) → window.tucoteca                         │
│       └ renderer: Preact + TypeScript (só IPC, sem Node)              │
└───────────────────────────────┬───────────────────────────────────────┘
                     spawn + NDJSON em stdin/stdout (sem TCP)
┌───────────────────────────────▼───────────────────────────────────────┐
│ ponte.py: abrir_hub.preparar() → ServicoBiblioteca → bib_core/SQLite  │
└───────────────────────────────────────────────────────────────────────┘
```

Não existe porta TCP: o renderer fala só por IPC com o main, e o main fala
com o Python por NDJSON (uma linha JSON por mensagem) em stdin/stdout do
processo filho.

## Protocolo (NDJSON)

- Pedido: `{"id": 1, "metodo": "nucleo.ping", "params": {…}}` (`params` opcional).
- Resposta: `{"id": 1, "ok": true, "resultado": {…}}` ou
  `{"id": 1, "ok": false, "erro": "…"}`.
- Evento (sem `id`): `{"evento": "bloqueio", "dados": {"erro": "…"}}` — a
  coleção ocupada por outro programa vira evento e a ponte sai com código 2.

Métodos da ponte (F0/F1):

| Método | Resultado |
|---|---|
| `nucleo.ping` | `{pong: true, versao, home, db}` |
| `nucleo.snapshot` | jogos/músicas/desejos/vídeos/fila + `sistema` (contadores, backup, disco) |
| `nucleo.buscar` | busca global `{termo, limite?}` (1–50, padrão 12) em jogos/músicas/desejos, sem acento |
| `modulos.listar` | lista ordenada dos módulos do hub |
| `preferencias.ler` | `{ativo, perfis, atalhos}` (padrões quando ainda não há arquivo) |
| `preferencias.trocar_perfil` | grava `{nome}` (Tuco/Isa) e devolve o perfil ativo; nome inválido → `ok:false` |

## Contrato de módulos

`servicos_ui/modulos.py` define `Modulo` (chave, nome, descrição, ícone,
ordem) e `modulos_padrao()` — hoje 8 módulos (Início a YouTube), na ordem da
navegação. A barra lateral do renderer é gerada dessa lista, não de código JS
fixo: é a preparação para módulos de terceiros (F3).

## Shell da F1

- **Paleta (`Ctrl+K` / `Ctrl+F`)**: busca global pela ponte (`nucleo.buscar`);
  Enter navega para o item, `Esc` fecha; com a paleta aberta os atalhos de seção
  ficam suspensos e `Ctrl+K` fecha. Respostas atrasadas de um termo antigo são
  descartadas (guarda de termo).
- **Atalhos pessoais** (`preferencias.ler`): `Ctrl+1..8` (Início…YouTube),
  `Ctrl+K`/`Ctrl+F` paleta, `F11` tela cheia. O renderer normaliza a combinação
  (`combinacao`) e resolve contra o mapa pessoal; sem combinação o evento segue
  para o menu — é assim que `F11` chega ao `togglefullscreen` nativo.
- **Notificações**: sino na base da barra lateral com contador; avisos vêm do
  `sistema` do snapshot (e de eventos `aviso` da ponte, quando houver);
  dispensar remove só na sessão.
- **Perfis**: chip Tuco/Isa; a troca grava `dados/preferencias-pessoais.json`
  via `preferencias.trocar_perfil` e reflete no chip.
- **Gamepad**: `LeitorControle` no renderer usa a Gamepad API do Chromium (pads
  XInput); D-pad e analógico esquerdo navegam, botões A/B selecionam/voltam;
  a leitura reinicia em `gamepadconnected` e no retorno de foco. Sem controle
  físico na bancada, a prova é unitária (mesmo limite do desktop Qt).
- **Queda e reconexão da ponte**: se o Python morre, o main emite
  `ponte-estado` (`caiu` / `reabrindo` / `ok`), as chamadas passam a falhar com
  "a ponte encerrou — clique em Reconectar" e o banner do renderer traz
  **Reconectar**. A reabertura é single-flight, refaz o snapshot sem recarregar
  a página e, quando o lock no disco é órfão (mesmo host/SO e pid morto — sobra
  típica de crash/`taskkill /F`), assume a coleção; lock vivo de outra
  instância continua recusado com a mensagem do núcleo.
- **Menu do app**: barra com **TucoTeca** (Sobre… — versão, home da coleção e
  versão do Electron —, Sair), **Exibir** (Recarregar `CmdOrCtrl+R`, DevTools
  `F12`, zoom, Tela cheia `F11`) e **Ajuda** (Documentação e Aviso legal, que
  abrem os arquivos locais de `docs/`). `autoHideMenuBar` continua: `Alt` mostra
  a barra e os aceleradores valem sempre.

## Segurança

- `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`; o
  renderer só enxerga `window.tucoteca` (`chamar`, `assinar`, `pronto`,
  `imagemUrl`, `reabrir`) exposto por `contextBridge`.
- Capas locais são servidas por `tucoteca-img://` (protocolo próprio); o main
  valida cada caminho contra a pasta da coleção (fora dela, inclusive `..`,
  responde 403) — o renderer nunca carrega `file://` direto.
- Navegação para http/https abre no navegador do sistema; a janela não navega
  para fora do app.
- Instância única (`requestSingleInstanceLock`); o lock da coleção continua
  sendo o do núcleo (arquivo `.lock`), com mensagem clara e saída 2 quando
  ocupado. A reabertura só assume lock com pid morto no mesmo host/SO.
- Provas usam `BIBLIOTECA_HOME` temporário e `TUCOTECA_USERDATA` (userData do
  Electron redirecionado) — nunca a coleção real nem o `%APPDATA%` padrão.

## Desenvolvimento e verificação

```powershell
cd codigo/frontends/electron
npm install
npm run dev        # janela com hot reload (usa a coleção padrão do checkout)
npm run test       # vitest (ponte, shell, estado, menu, derivações)
npm run typecheck  # tsc --noEmit nos dois tsconfigs
npm run build      # electron-vite build → out/
npm run start      # roda o build (electron .)
```

Selftest (paridade com o Qt): `electron . --selftest [--screenshot x.png]
[--db X] [--ignorar-lock]`. Erros → `[erro] …` no stderr e saída 1; lock
ocupado → saída 2; sucesso imprime `[ok] selftest Electron: N jogos; ponte,
módulos e Início carregados`. Com `--screenshot`, a captura acontece após o
primeiro render estável.

Prova com dados sintéticos (nunca a coleção real):

```powershell
py -3.14 -B codigo/ferramentas/semear_prova_electron.py --destino .provas/electron/home-f0 --limpar
$env:BIBLIOTECA_HOME = "…\.provas\electron\home-f0"
$env:TUCOTECA_USERDATA = "…\.provas\electron\userdata-f0"
npx electron . --selftest --screenshot "…\.provas\electron\f0-inicio.png"
```

Provas E2E do shell (locais, em `.provas/electron/`): o app roda de verdade com
`--remote-debugging-port` e o CDP dirige paleta/atalhos/reload; `keybd_event`
com a janela em primeiro plano envia `F11`/`Alt` (atalhos de menu são nativos e
não chegam por CDP); `taskkill /T /F` no Python prova a queda e a reconexão;
`PrintWindow` captura a moldura (barra de menu) — tudo com home e userData de
prova.

Variáveis do app Electron:

| Variável | Uso |
|---|---|
| `TUCOTECA_RAIZ` | raiz do repositório/bundle (padrão: derivada do `appPath`) |
| `TUCOTECA_PYTHON` | intérprete explícito; ordem: env → runtime embutido `programa/windows-x64/python/python.exe` → `py -3.14` / `python3` |
| `TUCOTECA_USERDATA` | userData do Electron fora do padrão (provas) |

## O que a F0/F1 entregam (e o que ainda não)

Entregue na F0: ponte NDJSON com `nucleo.ping`/`nucleo.snapshot`/
`modulos.listar` (15 casos de teste hoje), registro de módulos, shell Electron
com barra lateral + boas-vindas, tela Início (contadores e "Continuar jogando"
com capas), selftest com screenshot e provas visuais revisadas.

Entregue na F1: paleta de busca global `Ctrl+K`/`Ctrl+F` (`nucleo.buscar`),
atalhos pessoais `Ctrl+1..8`, notificações com sino/contador, perfis Tuco/Isa
persistidos, gamepad por Gamepad API, hardening da queda da ponte (banner +
**Reconectar**, lock órfão assumido) e menu do app — 55 testes vitest e suíte
Python 526/526 na rodada completa, provas E2E de queda e do checklist do shell.

Ainda não (fatias seguintes): F2 telas Jogos/Músicas/Desejos/Downloads/
Integrações/Vídeos com a tabela de paridade do `docs/DESKTOP_QT.md`; F3 módulos
de terceiros; F4 empacotamento e assinatura (instalador único); F5 retirada do
Qt e do `BIBLIOTECA_WEBENGINE`; F6 release 1.2.0.

Limites honestos: a TUI curses continua para Linux/macOS e a plataforma macOS
segue fora do escopo; gamepad provado só por unidade (sem controle físico na
máquina); a paleta busca em memória (12 itens/limite — coleções grandes podem
querer FTS depois); o selftest não substitui prova física de áudio nem serviços
remotos; a F1 não empacota, não assina e não substitui o Qt como desktop padrão.
