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
  it('tem TucoTeca (Sobre + Sair), Exibir (recarregar/F12/tela cheia/zoom) e Ajuda', () => {
    const sobre = vi.fn()
    const menu = montarMenu({ raiz: 'C:/repo', aoAbrirSobre: sobre }) as Item[]
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
    expect(porRotulo(exibir, 'Aumentar zoom').role).toBe('zoomIn')
    expect(porRotulo(exibir, 'Diminuir zoom').role).toBe('zoomOut')
    expect(porRotulo(exibir, 'Zoom padrão').role).toBe('resetZoom')
  })

  it('Ajuda abre os documentos locais do repo', () => {
    const menu = montarMenu({ raiz: 'C:/repo', aoAbrirSobre: () => {} }) as Item[]
    const ajuda = porRotulo(menu, 'Ajuda').submenu ?? []
    porRotulo(ajuda, 'Documentação').click?.()
    expect(abrirCaminho).toHaveBeenCalledWith(join('C:/repo', 'docs', 'DESKTOP_ELECTRON.md'))
    porRotulo(ajuda, 'Aviso legal').click?.()
    expect(abrirCaminho).toHaveBeenCalledWith(join('C:/repo', 'docs', 'LEGAL.md'))
  })
})
