import { describe, expect, it } from 'vitest'
import { indiceLinha, normalizarLetra, pedidoLetra } from './letras'

describe('normalizarLetra', () => {
  it('ordena linhas e descarta tempos inválidos', () => {
    const l = normalizarLetra({
      ok: true,
      sincronizadas: true,
      linhas: [{ t: 12.5, texto: 'b' }, { t: 'x', texto: 'lixo' }, { t: 3, texto: 'a' }],
    })
    expect(l.linhas).toEqual([{ t: 3, texto: 'a' }, { t: 12.5, texto: 'b' }])
    expect(l.sincronizadas).toBe(true)
  })

  it('sincronizada sem linhas vira texto puro', () => {
    expect(normalizarLetra({ ok: true, sincronizadas: true, linhas: [], texto: 'oi' }).sincronizadas).toBe(false)
    expect(normalizarLetra(null)).toMatchObject({ ok: false, linhas: [], texto: '' })
  })
})

describe('indiceLinha', () => {
  const linhas = [{ t: 2 }, { t: 5 }, { t: 9 }]
  it('acha a última linha iniciada', () => {
    expect(indiceLinha(linhas, 0)).toBe(-1)
    expect(indiceLinha(linhas, 2)).toBe(0)
    expect(indiceLinha(linhas, 8.9)).toBe(1)
    expect(indiceLinha(linhas, 100)).toBe(2)
    expect(indiceLinha([], 3)).toBe(-1)
  })
})

describe('pedidoLetra', () => {
  it('exige artista e título; arredonda a duração', () => {
    expect(pedidoLetra({ titulo: 'Só título' }, 10)).toBeNull()
    expect(pedidoLetra({ artista: ' A ', titulo: ' T ', album: 'X' }, 201.6)).toEqual({
      artista: 'A',
      titulo: 'T',
      album: 'X',
      duracao_s: 202,
    })
    expect(pedidoLetra({ artista: 'A', titulo: 'T' }, NaN)?.duracao_s).toBe(0)
  })
})
