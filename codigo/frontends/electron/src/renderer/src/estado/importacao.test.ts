import { describe, expect, it } from 'vitest'
import { detalheItem, juntarPrevias } from './importacao'

describe('juntarPrevias', () => {
  it('remove duplicatas entre arquivos soltos (sem diferenciar caixa)', () => {
    const a = { titulo: 'Celeste', executable_path: 'C:/J/Celeste.exe' }
    const b = { titulo: 'celeste', executable_path: 'c:/j/celeste.exe' }
    const c = { titulo: 'Zelda', launch_options: 'E:/roms/zelda.3ds', plataforma: '3DS' }
    expect(juntarPrevias([[a], [b, c]])).toEqual([a, c])
  })
})

describe('detalheItem', () => {
  it('mostra plataforma e nome do arquivo', () => {
    expect(detalheItem({ plataforma: '3DS', launch_options: 'E:\\roms\\zelda.3ds' })).toBe('3DS · zelda.3ds')
    expect(detalheItem({ executable_path: 'C:/J/jogo.exe' })).toBe('jogo.exe')
    expect(detalheItem({})).toBe('')
  })
})
