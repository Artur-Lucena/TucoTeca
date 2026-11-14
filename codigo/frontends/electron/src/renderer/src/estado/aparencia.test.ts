import { describe, expect, it } from 'vitest'
import { fatorZoom, normalizarAparencia } from './aparencia'

describe('normalizarAparencia', () => {
  it('valores fora do vocabulário caem no padrão do núcleo', () => {
    expect(normalizarAparencia({ tema: 'neon', densidade: 'x', escala_texto: 'y' })).toEqual({
      tema: 'escuro',
      densidade: 'conforto',
      escala_texto: 1,
      auto_backup: true,
    })
  })

  it('preserva valores válidos e limita a escala a [0,8; 1,5]', () => {
    const a = normalizarAparencia({ tema: 'claro', densidade: 'bigpicture', escala_texto: 3, auto_backup: false })
    expect(a).toEqual({ tema: 'claro', densidade: 'bigpicture', escala_texto: 1.5, auto_backup: false })
    expect(normalizarAparencia({ escala_texto: 0.1 }).escala_texto).toBe(0.8)
  })
})

describe('fatorZoom', () => {
  it('densidade × escala', () => {
    expect(fatorZoom({ densidade: 'conforto', escala_texto: 1 })).toBe(1)
    expect(fatorZoom({ densidade: 'compacto', escala_texto: 1 })).toBe(0.9)
    expect(fatorZoom({ densidade: 'bigpicture', escala_texto: 1.2 })).toBe(1.5)
  })
})
