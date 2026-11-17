// Instalador Windows (NSIS) do TucoTeca.
//
// O app instalado leva, em resources/tucoteca/, só o que a ponte precisa:
// núcleo Python (bib_core + bib_nucleo), ponte.py + servicos_ui, abrir_hub,
// codigo/VERSION, LICENSE e os docs abertos pelo menu Ajuda. Coleção, dados e
// provas nunca entram (a coleção do instalado fica em Documentos\TucoTeca).
//
// Python: o runtime embutido vem de programa/windows-x64/python
// (codigo/ferramentas/preparar_runtime_python.py). Sem ele o build falha,
// a não ser com TUCOTECA_SEM_RUNTIME=1 — aí o app instalado depende do
// `py -3.14` do sistema e isso deve constar nas notas da release.
const { existsSync, readFileSync } = require('node:fs')
const { join } = require('node:path')

const REPO = join(__dirname, '..', '..', '..')
const versao = readFileSync(join(REPO, 'codigo', 'VERSION'), 'utf8').trim()
const runtime = join(REPO, 'programa', 'windows-x64', 'python')
const temRuntime = existsSync(join(runtime, 'python.exe'))
const semRuntime = process.env.TUCOTECA_SEM_RUNTIME === '1'

if (!temRuntime && !semRuntime) {
  throw new Error(
    'Runtime Python ausente em programa/windows-x64/python. Rode ' +
      '`py -3.14 -B codigo/ferramentas/preparar_runtime_python.py` ou, ' +
      'conscientemente, TUCOTECA_SEM_RUNTIME=1.',
  )
}

const extraResources = [
  {
    from: join(REPO, 'codigo'),
    to: 'tucoteca/codigo',
    filter: [
      'bib_core.py',
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
if (temRuntime) {
  extraResources.push({
    from: runtime,
    to: 'tucoteca/programa/windows-x64/python',
    filter: ['**/*', '!**/__pycache__/**'],
  })
}

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
  // releases privadas sem auto-update: não gerar latest.yml/blockmap
  publish: null,
}
