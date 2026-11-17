import { shell } from 'electron'
import type { MenuItemConstructorOptions } from 'electron'
import { join } from 'node:path'

export interface OpcoesMenu {
  raiz: string
  aoAbrirSobre: () => void
}

/** Template do menu do app: Alt mostra a barra; aceleradores valem sempre. */
export function montarMenu(opcoes: OpcoesMenu): MenuItemConstructorOptions[] {
  return [
    {
      label: 'TucoTeca',
      submenu: [
        { label: 'Sobre o TucoTeca…', click: () => opcoes.aoAbrirSobre() },
        { type: 'separator' },
        { label: 'Sair', role: 'quit' },
      ],
    },
    {
      label: 'Exibir',
      submenu: [
        { label: 'Recarregar', role: 'reload', accelerator: 'CmdOrCtrl+R' },
        {
          label: 'Ferramentas de desenvolvedor',
          role: 'toggleDevTools',
          accelerator: 'F12',
        },
        { type: 'separator' },
        { label: 'Tela cheia', role: 'togglefullscreen', accelerator: 'F11' },
      ],
    },
    {
      label: 'Ajuda',
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
    },
  ]
}
