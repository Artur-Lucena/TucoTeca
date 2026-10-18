# Desktop Electron (em construção — fatia F0)

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

Métodos da F0:

| Método | Resultado |
|---|---|
| `nucleo.ping` | `{pong: true, versao, home, db}` |
| `nucleo.snapshot` | jogos/músicas/desejos/vídeos/fila + `sistema` (contadores, backup, disco) |
| `modulos.listar` | lista ordenada dos módulos do hub |

## Contrato de módulos

`servicos_ui/modulos.py` define `Modulo` (chave, nome, descrição, ícone,
ordem) e `modulos_padrao()` — hoje 8 módulos (Início a YouTube), na ordem da
navegação. A barra lateral do renderer é gerada dessa lista, não de código JS
fixo: é a preparação para módulos de terceiros (F3).

## Segurança

- `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`; o
  renderer só enxerga `window.tucoteca` (`chamar`, `assinar`, `pronto`,
  `imagemUrl`) exposto por `contextBridge`.
- Capas locais são servidas por `tucoteca-img://` (protocolo próprio); o main
  valida cada caminho contra a pasta da coleção (fora dela, inclusive `..`,
  responde 403) — o renderer nunca carrega `file://` direto.
- Navegação para http/https abre no navegador do sistema; a janela não navega
  para fora do app.
- Instância única (`requestSingleInstanceLock`); o lock da coleção continua
  sendo o do núcleo (arquivo `.lock`), com mensagem clara e saída 2 quando
  ocupado.
- Provas usam `BIBLIOTECA_HOME` temporário e `TUCOTECA_USERDATA` (userData do
  Electron redirecionado) — nunca a coleção real nem o `%APPDATA%` padrão.

## Desenvolvimento e verificação

```powershell
cd codigo/frontends/electron
npm install
npm run dev        # janela com hot reload (usa a coleção padrão do checkout)
npm run test       # vitest (ponte, caminhos, mídia, derivações)
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

Variáveis do app Electron:

| Variável | Uso |
|---|---|
| `TUCOTECA_RAIZ` | raiz do repositório/bundle (padrão: derivada do `appPath`) |
| `TUCOTECA_PYTHON` | intérprete explícito; ordem: env → runtime embutido `programa/windows-x64/python/python.exe` → `py -3.14` / `python3` |
| `TUCOTECA_USERDATA` | userData do Electron fora do padrão (provas) |

## O que a F0 entrega (e o que ainda não)

Entregue: ponte NDJSON com `nucleo.ping`/`nucleo.snapshot`/`modulos.listar`
(11 casos de teste), registro de módulos (3 casos), shell Electron com barra
lateral + boas-vindas, tela Início (contadores e "Continuar jogando" com
capas), selftest com screenshot e provas visuais revisadas.

Ainda não (fatias seguintes): F1 shell completo (busca global Ctrl+K,
notificações, perfis, gamepad, hardening de queda da ponte, menu); F2 telas
Jogos/Músicas/Desejos/Downloads/Integrações/Vídeos; F3 módulos de terceiros;
F4 empacotamento e assinatura (instalador único); F5 retirada do Qt e do
`BIBLIOTECA_WEBENGINE`; F6 release 1.2.0.

Limites honestos: a TUI curses continua para Linux/macOS e a plataforma macOS
segue fora do escopo; o selftest não substitui prova física de gamepad, áudio
ou serviços remotos; a F0 não empacota, não assina e não substitui o Qt como
desktop padrão.
