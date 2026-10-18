import { app, BrowserWindow, shell } from 'electron'
import { join } from 'node:path'

const URL_DEV = process.env['ELECTRON_RENDERER_URL']

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

  janela.once('ready-to-show', () => janela.show())

  janela.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://') || url.startsWith('https://')) shell.openExternal(url)
    return { action: 'deny' }
  })

  if (!app.isPackaged && URL_DEV) {
    janela.loadURL(URL_DEV)
  } else {
    janela.loadFile(join(__dirname, '../renderer/index.html'))
  }
  return janela
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
  app.whenReady().then(() => {
    criarJanela()
    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) criarJanela()
    })
  })
  // macOS esta fora do escopo por enquanto: fechar a janela encerra o app.
  app.on('window-all-closed', () => app.quit())
}
