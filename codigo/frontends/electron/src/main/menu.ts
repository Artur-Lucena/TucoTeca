import { shell } from 'electron'
import type { MenuItemConstructorOptions } from 'electron'
import { join } from 'node:path'

interface OpcoesMenu {
  raiz: string
  aoAbrirSobre: () => void
  plataforma?: NodeJS.Platform
}

/**
 * Template do menu do app. Windows: Alt mostra a barra; aceleradores valem
 * sempre. macOS: barra no topo da tela com os menus que o sistema espera —
 * sem o Editar, ⌘C/⌘V/⌘A não funcionam em nenhum campo.
 */
export function montarMenu(opcoes: OpcoesMenu): MenuItemConstructorOptions[] {
  const mac = (opcoes.plataforma ?? process.platform) === 'darwin'
  const sobre: MenuItemConstructorOptions = { label: 'Sobre o TucoTeca…', click: () => opcoes.aoAbrirSobre() }
  const ajuda: MenuItemConstructorOptions = {
    label: 'Ajuda',
    role: mac ? 'help' : undefined,
    submenu: [
      {
        label: 'Documentação',
        click: () => void shell.openPath(join(opcoes.raiz, 'docs', 'DESKTOP_ELECTRON.md')),
      },
      {
        label: 'Aviso legal',
        click: () => void shell.openPath(join(opcoes.raiz, 'docs', 'LEGAL.md')),
      },
    ],
  }
  const exibir: MenuItemConstructorOptions = {
    label: 'Exibir',
    submenu: [
      { label: 'Recarregar', role: 'reload', accelerator: 'CmdOrCtrl+R' },
      {
        label: 'Ferramentas de desenvolvedor',
        role: 'toggleDevTools',
        accelerator: mac ? 'Alt+Command+I' : 'F12',
      },
      { type: 'separator' },
      { label: 'Tela cheia', role: 'togglefullscreen', accelerator: mac ? 'Control+Command+F' : 'F11' },
    ],
  }
  if (!mac) {
    return [
      { label: 'TucoTeca', submenu: [sobre, { type: 'separator' }, { label: 'Sair', role: 'quit' }] },
      exibir,
      ajuda,
    ]
  }
  return [
    {
      label: 'TucoTeca',
      submenu: [
        sobre,
        { type: 'separator' },
        { label: 'Serviços', role: 'services' },
        { type: 'separator' },
        { label: 'Ocultar TucoTeca', role: 'hide' },
        { label: 'Ocultar outros', role: 'hideOthers' },
        { label: 'Mostrar tudo', role: 'unhide' },
        { type: 'separator' },
        { label: 'Sair do TucoTeca', role: 'quit' },
      ],
    },
    {
      label: 'Editar',
      submenu: [
        { label: 'Desfazer', role: 'undo' },
        { label: 'Refazer', role: 'redo' },
        { type: 'separator' },
        { label: 'Recortar', role: 'cut' },
        { label: 'Copiar', role: 'copy' },
        { label: 'Colar', role: 'paste' },
        { label: 'Colar e manter estilo', role: 'pasteAndMatchStyle' },
        { label: 'Apagar', role: 'delete' },
        { label: 'Selecionar tudo', role: 'selectAll' },
      ],
    },
    exibir,
    {
      label: 'Janela',
      role: 'window',
      submenu: [
        { label: 'Minimizar', role: 'minimize' },
        { label: 'Zoom', role: 'zoom' },
        { type: 'separator' },
        { label: 'Trazer tudo para a frente', role: 'front' },
      ],
    },
    ajuda,
  ]
}
