// Instaladores do TucoTeca: Windows (NSIS) e macOS (.dmg, Intel e Apple Silicon).
//
// O app instalado leva, em resources/tucoteca/, só o que a ponte precisa:
// núcleo Python (bib_nucleo), ponte.py + servicos_ui, abrir_hub,
// codigo/VERSION, LICENSE e os docs abertos pelo menu Ajuda. Coleção, dados e
// provas nunca entram (a coleção do instalado fica em Documentos/TucoTeca).
//
// Python: o runtime embutido vem de programa/<plataforma>/python
// (codigo/ferramentas/preparar_runtime_python.py --plataforma ...). Cada build
// roda no SO de destino: Windows no Windows, macOS no macOS (as duas
// arquiteturas saem do mesmo Mac). Sem runtime o build falha, a não ser com
// TUCOTECA_SEM_RUNTIME=1 — aí o app depende do Python 3.14 do sistema e isso
// deve constar nas notas da release.
const { existsSync, readFileSync } = require('node:fs')
const { join } = require('node:path')

const REPO = join(__dirname, '..', '..', '..')
const versao = readFileSync(join(REPO, 'codigo', 'VERSION'), 'utf8').trim()
const semRuntime = process.env.TUCOTECA_SEM_RUNTIME === '1'
const mac = process.platform === 'darwin'

const runtimeWin = join(REPO, 'programa', 'windows-x64', 'python')
const temRuntimeWin = existsSync(join(runtimeWin, 'python.exe'))
const archsMac = ['arm64', 'x64'].filter((arch) =>
  existsSync(join(REPO, 'programa', `macos-${arch}`, 'python', 'bin', 'python3')),
)

if (!semRuntime && (mac ? archsMac.length === 0 : !temRuntimeWin)) {
  const plataforma = mac ? 'macos-arm64 e/ou macos-x64' : 'windows-x64'
  throw new Error(
    `Runtime Python ausente em programa/${plataforma}. Rode ` +
      '`codigo/ferramentas/preparar_runtime_python.py --plataforma <...>` ou, ' +
      'conscientemente, TUCOTECA_SEM_RUNTIME=1.',
  )
}

const extraResources = [
  {
    from: join(REPO, 'codigo'),
    to: 'tucoteca/codigo',
    filter: [
      'VERSION',
      'bib_nucleo/**/*.py',
      'frontends/__init__.py',
      'frontends/ponte*.py',
      'frontends/servicos_ui/**/*.py',
      'ferramentas/__init__.py',
      'ferramentas/abrir_hub.py',
      '!**/__pycache__/**',
    ],
  },
  { from: join(REPO, 'docs'), to: 'tucoteca/docs', filter: ['LEGAL.md', 'DESKTOP_ELECTRON.md', 'SECURITY.md'] },
  { from: join(REPO, 'LICENSE'), to: 'tucoteca/LICENSE' },
]

const runtimeFiltro = ['**/*', '!**/__pycache__/**']

/** @type {import('electron-builder').Configuration} */
module.exports = {
  appId: 'com.tucoteca.app',
  productName: 'TucoTeca',
  copyright: 'Copyright © Tuco — MIT',
  extraMetadata: { version: versao },
  directories: { output: 'dist', buildResources: 'resources' },
  files: ['out/**/*', 'package.json'],
  extraResources,
  asar: true,
  win: {
    target: [{ target: 'nsis', arch: ['x64'] }],
    icon: 'resources/icon.ico',
    extraResources: temRuntimeWin
      ? [{ from: runtimeWin, to: 'tucoteca/programa/windows-x64/python', filter: runtimeFiltro }]
      : [],
  },
  nsis: {
    oneClick: false,
    perMachine: false,
    allowToChangeInstallationDirectory: true,
    // a coleção fica em Documentos\TucoTeca, fora da pasta do app; mesmo assim
    // nunca apagar dados do usuário ao desinstalar
    deleteAppDataOnUninstall: false,
    createDesktopShortcut: true,
    createStartMenuShortcut: true,
    shortcutName: 'TucoTeca',
    installerIcon: 'resources/icon.ico',
    uninstallerIcon: 'resources/icon.ico',
    artifactName: 'TucoTeca-Setup-${version}-x64.${ext}',
  },
  mac: {
    // uma .dmg por arquitetura presente em programa/ (sem runtime: as duas)
    target: [{ target: 'dmg', arch: archsMac.length ? archsMac : ['arm64', 'x64'] }],
    icon: 'resources/icon.icns',
    category: 'public.app-category.entertainment',
    darkModeSupport: true,
    // Electron 44 (Chromium) exige macOS 13 Ventura ou mais novo
    minimumSystemVersion: '13.0',
    // sem conta paga da Apple: assinatura ad-hoc (o Apple Silicon exige alguma)
    // e sem notarização — na 1ª vez, botão direito → Abrir
    identity: '-',
    hardenedRuntime: false,
    gatekeeperAssess: false,
    // ${arch} = arm64 | x64: cada .app leva só o Python da própria arquitetura
    extraResources: archsMac.length
      ? [{ from: join(REPO, 'programa', 'macos-${arch}', 'python'), to: 'tucoteca/programa/macos-${arch}/python', filter: runtimeFiltro }]
      : [],
    extendInfo: {
      NSDocumentsFolderUsageDescription: 'A coleção do TucoTeca fica em Documentos/TucoTeca.',
      NSDownloadsFolderUsageDescription: 'Para importar jogos, músicas e vídeos que você baixou.',
      NSDesktopFolderUsageDescription: 'Para importar arquivos que estão na Mesa.',
      NSRemovableVolumesUsageDescription: 'Para ler jogos, ROMs e vídeos em discos externos.',
      NSNetworkVolumesUsageDescription: 'Para ler jogos, ROMs e vídeos em pastas de rede.',
    },
  },
  dmg: {
    artifactName: 'TucoTeca-${version}-mac-${arch}.${ext}',
    writeUpdateInfo: false,
  },
  // releases sem auto-update: não gerar latest.yml/blockmap
  publish: null,
}
