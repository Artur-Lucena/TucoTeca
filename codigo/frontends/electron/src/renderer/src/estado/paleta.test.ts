import { describe, expect, it } from 'vitest'
import { paletaInicial, reduzirPaleta } from './paleta'

const abrir = (estado = paletaInicial) => reduzirPaleta(estado, { tipo: 'abrir' })

describe('reduzirPaleta', () => {
  it('abre limpa, alterna e fecha', () => {
    const aberta = abrir(reduzirPaleta(paletaInicial, { tipo: 'digitou', termo: 'z' }))
    expect(aberta.termo).toBe('')
    expect(reduzirPaleta(aberta, { tipo: 'alternar' }).aberta).toBe(false)
  })

  it('ignora resposta de termo obsoleto (resposta fora de ordem)', () => {
    const digitouZelda = reduzirPaleta(abrir(), { tipo: 'digitou', termo: 'zelda' })
    const esperada = reduzirPaleta(digitouZelda, {
      tipo: 'resultados',
      termo: 'zelda',
      itens: [{ tipo: 'jogo', id: 1, titulo: 'Zelda' }],
    })
    const obsoleta = reduzirPaleta(esperada, {
      tipo: 'resultados',
      termo: 'zel',
      itens: [{ tipo: 'jogo', id: 9, titulo: 'Zé' }],
    })
    expect(obsoleta.itens.map((i) => i.id)).toEqual([1])
  })

  it('navega com wrap-around e seleciona com clamp', () => {
    let estado = reduzirPaleta(abrir(), {
      tipo: 'resultados',
      termo: '',
      itens: [
        { tipo: 'jogo', id: 1, titulo: 'A' },
        { tipo: 'jogo', id: 2, titulo: 'B' },
      ],
    })
    estado = reduzirPaleta(estado, { tipo: 'cima' })
    expect(estado.selecionado).toBe(1)
    estado = reduzirPaleta(estado, { tipo: 'baixo' })
    expect(estado.selecionado).toBe(0)
    expect(reduzirPaleta(estado, { tipo: 'selecionar', indice: 99 }).selecionado).toBe(1)
    expect(reduzirPaleta(estado, { tipo: 'selecionar', indice: -3 }).selecionado).toBe(0)
  })

  it('termo novo zera seleção e limpa itens; resultado vazio mantém paleta aberta', () => {
    let estado = reduzirPaleta(abrir(), {
      tipo: 'resultados',
      termo: 'a',
      itens: [{ tipo: 'jogo', id: 1, titulo: 'A' }],
    })
    estado = reduzirPaleta(estado, { tipo: 'digitou', termo: 'ab' })
    expect(estado.itens).toEqual([])
    expect(estado.selecionado).toBe(0)
    estado = reduzirPaleta(estado, { tipo: 'resultados', termo: 'ab', itens: [] })
    expect(estado.aberta).toBe(true)
  })
})
