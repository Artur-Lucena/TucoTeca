import { describe, expect, it } from 'vitest'

import { filtrarDesejos, formatarPreco, validarAppid, validarTituloDesejo } from './desejos'

describe('formatarPreco', () => {
  it('marca gratuitos', () => {
    expect(formatarPreco({ gratis: true })).toBe('Grátis')
  })

  it('converte centavos em moeda local com desconto', () => {
    expect(formatarPreco({ gratis: false, moeda: 'BRL', final: 1999, inicial: 3999, desconto_pct: 50 }))
      .toBe('R$ 19,99 (-50%)')
  })

  it('sem desconto mostra só o valor', () => {
    expect(formatarPreco({ gratis: false, moeda: 'BRL', final: 3200, inicial: 3200, desconto_pct: 0 }))
      .toBe('R$ 32,00')
  })

  it('mapeia outras moedas e cai no código quando desconhecida', () => {
    expect(formatarPreco({ gratis: false, moeda: 'USD', final: 999, desconto_pct: 0 })).toBe('US$ 9,99')
    expect(formatarPreco({ gratis: false, moeda: 'XYZ', final: 100, desconto_pct: 0 })).toBe('XYZ 1,00')
  })

  it('sem dados não inventa preço', () => {
    expect(formatarPreco(null)).toBe('')
    expect(formatarPreco({ gratis: false })).toBe('')
  })
})

describe('filtrarDesejos', () => {
  const lista = [
    { titulo: 'Hollow Knight: Silksong' },
    { titulo: 'Celeste' },
    { titulo: 'Röda Test' },
  ]

  it('vazio devolve tudo', () => {
    expect(filtrarDesejos(lista, '')).toHaveLength(3)
    expect(filtrarDesejos(lista, '   ')).toHaveLength(3)
  })

  it('busca sem acento e sem caixa', () => {
    expect(filtrarDesejos(lista, 'CELESTE').map((d) => d.titulo)).toEqual(['Celeste'])
    expect(filtrarDesejos(lista, 'roda').map((d) => d.titulo)).toEqual(['Röda Test'])
  })

  it('sem resultado devolve lista vazia', () => {
    expect(filtrarDesejos(lista, 'zelda')).toEqual([])
  })
})

describe('validarAppid', () => {
  it('aceita só dígitos', () => {
    expect(validarAppid('504230')).toBeNull()
    expect(validarAppid(' 42 ')).toBeNull()
    expect(validarAppid('abc')).not.toBeNull()
    expect(validarAppid('')).not.toBeNull()
    expect(validarAppid('12 3')).not.toBeNull()
  })
})

describe('validarTituloDesejo', () => {
  it('exige título não vazio', () => {
    expect(validarTituloDesejo('Celeste')).toBeNull()
    expect(validarTituloDesejo('   ')).not.toBeNull()
  })
})
