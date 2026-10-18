import { app, BrowserWindow, dialog, ipcMain, protocol, shell } from 'electron'
import { existsSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { registrarProtocoloMidia } from './arquivos'
import { ClientePonte } from './ponte'

protocol.registerSchemesAsPrivileged([
  { scheme: 'tucoteca-img', privileges: { secure: true, standard: false, stream: true } },
])

// Provas não escrevem em %APPDATA%: o TUCOTECA_USERDATA manda o userData p/ outro lugar.
if (process.env.TUCOTECA_USERDATA) app.setPath('userData', resolve(process.env.TUCOTECA_USERDATA))

interface Flags {
  selftest: boolean
  screenshot: string | null
  db: string | null
  ignorarLock: boolean
}

function lerFlags(): Flags {
  const args = process.argv.slice(app.isPackaged ? 1 : 2)
  const flags: Flags = { selftest: false, screenshot: null, db: null, ignorarLock: false }
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i]
    if (arg === '--selftest') flags.selftest = true
    else if (arg === '--ignorar-lock') flags.ignorarLock = true
    else if (arg === '--screenshot' && args[i + 1]) flags.screenshot = resolve(args[i + 1])
    else if (arg === '--db' && args[i + 1]) flags.db = resolve(args[i + 1])
  }
  return flags
}

const flags = lerFlags()
const RAIZ = resolve(process.env.TUCOTECA_RAIZ || join(app.getAppPath(), '..', '..', '..'))
const HOME = process.env.BIBLIOTECA_HOME || RAIZ

let ponte: ClientePonte | null = null
let fechando = false

function falhar(mensagem: string, codigo: number): void {
  process.stderr.write(`[erro] ${mensagem}\n`)
  if (!flags.selftest) dialog.showErrorBox('TucoTeca', mensagem)
  app.exit(codigo)
}

function criarJanela(): BrowserWindow {
  const janela = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 960,
    minHeight: 640,
    show: false,
    autoHideMenuBar: true,
    backgroundColor: '#12141a',
    title: 'TucoTeca',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  janela.once('ready-to-show', () => {
    if (!flags.selftest || flags.screenshot) janela.show()
  })

  janela.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://') || url.startsWith('https://')) shell.openExternal(url)
    return { action: 'deny' }
  })

  const urlDev = process.env['ELECTRON_RENDERER_URL']
  if (!app.isPackaged && urlDev) {
    janela.loadURL(urlDev)
  } else {
    janela.loadFile(join(__dirname, '../renderer/index.html'))
  }
  return janela
}

async function finalizar(codigo: number): Promise<void> {
  if (fechando) return
  fechando = true
  if (ponte) await ponte.encerrar()
  app.exit(codigo)
}

async function principal(): Promise<void> {
  const script = join(RAIZ, 'codigo', 'frontends', 'ponte.py')
  if (!existsSync(script)) {
    falhar(`não achei a ponte em ${script}`, 1)
    return
  }

  const cliente = new ClientePonte({
    raiz: RAIZ,
    db: flags.db ?? undefined,
    ignorarLock: flags.ignorarLock,
  })
  ponte = cliente

  let bloqueio: string | null = null
  cliente.aoEvento((evento, dados) => {
    if (evento === 'bloqueio') {
      const erro = (dados as { erro?: string } | undefined)?.erro
      bloqueio = erro ?? 'A coleção já está aberta em outro programa.'
    }
    for (const janela of BrowserWindow.getAllWindows()) {
      janela.webContents.send(`ponte:evento:${evento}`, dados)
    }
  })

  cliente.iniciar()
  try {
    await cliente.chamar('nucleo.ping')
  } catch (erro) {
    if (bloqueio) {
      falhar(bloqueio, 2)
      return
    }
    falhar(`ponte indisponível: ${(erro as Error).message}`, 1)
    return
  }

  registrarProtocoloMidia(() => HOME)

  ipcMain.handle('ponte:chamar', (_evento, metodo: string, params?: Record<string, unknown>) =>
    cliente.chamar(metodo, params),
  )

  let aguardandoPronto: ((dados: unknown) => void) | null = null
  const pronto = new Promise<unknown>((resolver) => {
    aguardandoPronto = resolver
  })
  ipcMain.on('tucoteca:pronto', (_evento, dados: unknown) => {
    if (aguardandoPronto) {
      const resolver = aguardandoPronto
      aguardandoPronto = null
      resolver(dados)
    }
  })

  const janela = criarJanela()
  if (!flags.selftest) return

  const limite = setTimeout(() => falhar('selftest: o renderer não sinalizou pronto em 15 s', 1), 15000)
  const dados = (await pronto) as { jogos?: number } | null
  clearTimeout(limite)

  if (flags.screenshot) {
    await new Promise((resolver) => setTimeout(resolver, 500)) // deixa o primeiro paint terminar
    const imagem = await janela.webContents.capturePage()
    writeFileSync(flags.screenshot, imagem.toPNG())
  }

  const jogos = typeof dados?.jogos === 'number' ? dados.jogos : 0
  process.stdout.write(`[ok] selftest Electron: ${jogos} jogos; ponte, módulos e Início carregados\n`)
  app.exit(0)
}

// F12 abre o DevTools (dev e diagnostico local; sem menu visivel).
app.on('browser-window-created', (_evento, janela) => {
  janela.webContents.on('before-input-event', (_e, entrada) => {
    if (entrada.type === 'keyDown' && entrada.key === 'F12') janela.webContents.toggleDevTools()
  })
})

const primeira = app.requestSingleInstanceLock()
if (!primeira) {
  app.quit()
} else {
  app.on('second-instance', () => {
    const [janela] = BrowserWindow.getAllWindows()
    if (janela) {
      if (janela.isMinimized()) janela.restore()
      janela.focus()
    }
  })
  app
    .whenReady()
    .then(principal)
    .catch((erro) => falhar(String(erro), 1))
  // macOS esta fora do escopo por enquanto: fechar a janela encerra o app.
  app.on('window-all-closed', () => {
    void finalizar(0)
  })
}
