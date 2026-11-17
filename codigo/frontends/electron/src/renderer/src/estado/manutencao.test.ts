import { describe, expect, it } from 'vitest'
import { lerDiagnostico } from './manutencao'

describe('lerDiagnostico', () => {
  it('tudo ok não sugere reparo', () => {
    const r = lerDiagnostico({ exe: { estado: 'ok' }, rom: { estado: 'ok' } })
    expect(r).toEqual({ ok: true, linhas: ['Executável encontrado.', 'ROM encontrada.'], acoes: [] })
  })

  it('emulador trocado oferece usar o atual ou escolher', () => {
    const r = lerDiagnostico({
      exe: { estado: 'trocou-emulador', gravado: 'C:/velho/azahar.exe', atual: 'D:/novo/azahar.exe', nome: 'Azahar' },
      rom: { estado: 'nao-rom' },
    })
    expect(r.ok).toBe(false)
    expect(r.acoes).toEqual([{ tipo: 'usar-emulador-atual', caminho: 'D:/novo/azahar.exe' }, { tipo: 'escolher-exe' }])
    expect(r.linhas[0]).toMatch(/Azahar/)
  })

  it('ROM ausente leva os candidatos', () => {
    const r = lerDiagnostico({ exe: { estado: 'ok' }, rom: { estado: 'rom-ausente', candidatos: ['E:/roms/z.3ds'] } })
    expect(r.acoes).toEqual([{ tipo: 'escolher-rom', candidatos: ['E:/roms/z.3ds'] }])
    expect(r.linhas[1]).toMatch(/1 arquivo/)
  })

  it('sem exe e exe ausente pedem escolha', () => {
    expect(lerDiagnostico({ exe: { estado: 'sem-exe' }, rom: {} }).acoes).toEqual([{ tipo: 'escolher-exe' }])
    expect(lerDiagnostico({ exe: { estado: 'ausente', gravado: 'C:/x.exe' }, rom: {} }).linhas[0]).toBe(
      'Executável não encontrado: C:/x.exe',
    )
  })
})
