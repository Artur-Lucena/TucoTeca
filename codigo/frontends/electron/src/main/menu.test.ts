import { join } from 'node:path'
import { describe, expect, it, vi } from 'vitest'

const { abrirCaminho } = vi.hoisted(() => ({ abrirCaminho: vi.fn(async (_caminho: string) => '') }))
vi.mock('electron', () => ({
  shell: { openPath: abrirCaminho, openExternal: vi.fn() },
}))

import { montarMenu } from './menu'

interface Item {
  label?: string
  role?: string
  accelerator?: string
  submenu?: Item[]
  click?: () => void
}

function porRotulo(itens: Item[], rotulo: string): Item {
  const achado = itens.find((item) => item.label === rotulo)
  if (!achado) throw new Error(`sem item ${rotulo}`)
  return achado
}

describe('montarMenu', () => {
  it('tem TucoTeca (Sobre + Sair), Exibir (recarregar/F12/tela cheia, sem zoom) e Ajuda', () => {
    const sobre = vi.fn()
    const menu = montarMenu({ raiz: 'C:/repo', aoAbrirSobre: sobre, plataforma: 'win32' }) as Item[]
    expect(menu.map((item) => item.label)).toEqual(['TucoTeca', 'Exibir', 'Ajuda'])

    const tucoteca = porRotulo(menu, 'TucoTeca').submenu ?? []
    porRotulo(tucoteca, 'Sobre o TucoTeca…').click?.()
    expect(sobre).toHaveBeenCalledTimes(1)
    expect(porRotulo(tucoteca, 'Sair').role).toBe('quit')

    const exibir = porRotulo(menu, 'Exibir').submenu ?? []
    expect(porRotulo(exibir, 'Recarregar').role).toBe('reload')
    expect(porRotulo(exibir, 'Ferramentas de desenvolvedor').accelerator).toBe('F12')
    expect(porRotulo(exibir, 'Tela cheia').role).toBe('togglefullscreen')
    expect(porRotulo(exibir, 'Tela cheia').accelerator).toBe('F11')
    // o tamanho da interface fica só em Configurações → Aparência
    expect(exibir.some((item) => item.role === 'zoomIn' || item.role === 'resetZoom')).toBe(false)
  })

  it('Ajuda abre os documentos locais do repo', () => {
    const menu = montarMenu({ raiz: 'C:/repo', aoAbrirSobre: () => {}, plataforma: 'win32' }) as Item[]
    const ajuda = porRotulo(menu, 'Ajuda').submenu ?? []
    porRotulo(ajuda, 'Documentação').click?.()
    expect(abrirCaminho).toHaveBeenCalledWith(join('C:/repo', 'docs', 'DESKTOP_ELECTRON.md'))
    porRotulo(ajuda, 'Aviso legal').click?.()
    expect(abrirCaminho).toHaveBeenCalledWith(join('C:/repo', 'docs', 'LEGAL.md'))
  })

  it('macOS: menu do app, Editar (⌘C/⌘V), Exibir, Janela e Ajuda', () => {
    const sobre = vi.fn()
    const menu = montarMenu({ raiz: '/app', aoAbrirSobre: sobre, plataforma: 'darwin' }) as Item[]
    expect(menu.map((item) => item.label)).toEqual(['TucoTeca', 'Editar', 'Exibir', 'Janela', 'Ajuda'])
    const app = porRotulo(menu, 'TucoTeca').submenu ?? []
    porRotulo(app, 'Sobre o TucoTeca…').click?.()
    expect(sobre).toHaveBeenCalledTimes(1)
    expect(app.map((item) => item.role).filter(Boolean)).toEqual(['services', 'hide', 'hideOthers', 'unhide', 'quit'])
    const editar = porRotulo(menu, 'Editar').submenu ?? []
    for (const papel of ['undo', 'redo', 'cut', 'copy', 'paste', 'selectAll']) {
      expect(editar.some((item) => item.role === papel)).toBe(true)
    }
    const exibir = porRotulo(menu, 'Exibir').submenu ?? []
    expect(porRotulo(exibir, 'Tela cheia').accelerator).toBe('Control+Command+F')
    expect(porRotulo(menu, 'Janela').role).toBe('window')
  })
})
