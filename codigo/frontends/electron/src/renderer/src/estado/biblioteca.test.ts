import { describe, expect, it } from 'vitest'
import { itensBiblioteca, janelaVisivel } from './biblioteca'

const jogos = [
  { id: 3, titulo: 'Celeste', favorito: 1, ultima_execucao: '2026-11-10T10:00:00' },
  { id: 1, titulo: 'Ávida Jornada', favorito: 0 },
  { id: 2, titulo: 'balatro', favorito: true, ultima_execucao: '2026-11-12T09:00:00' },
  { id: 0, titulo: 'sem id' },
  { id: 4, titulo: '   ' },
]

describe('itensBiblioteca', () => {
  it('ordena em pt-BR, ignora caixa e acento e descarta itens inválidos', () => {
    expect(itensBiblioteca(jogos, '', 'todos').map((j) => j.id)).toEqual([1, 2, 3])
    expect(itensBiblioteca(jogos, 'avida', 'todos').map((j) => j.titulo)).toEqual(['Ávida Jornada'])
  })

  it('favoritos aceita 1/true; recentes só os já jogados, do mais novo', () => {
    expect(itensBiblioteca(jogos, '', 'favoritos').map((j) => j.id)).toEqual([2, 3])
    expect(itensBiblioteca(jogos, '', 'recentes').map((j) => j.id)).toEqual([2, 3])
    expect(itensBiblioteca(undefined, '', 'todos')).toEqual([])
  })

  it('aguenta 2 000 jogos', () => {
    const muitos = Array.from({ length: 2000 }, (_, i) => ({ id: i + 1, titulo: `Jogo ${i}` }))
    expect(itensBiblioteca(muitos, '199', 'todos').length).toBe(12) // 199, 1199, 1990–1999
  })
})

describe('janelaVisivel', () => {
  it('desenha só o que cabe mais a folga', () => {
    expect(janelaVisivel(2000, 32, 0, 320, 5)).toEqual({ inicio: 0, fim: 15, antes: 0, depois: 1985 * 32 })
    expect(janelaVisivel(2000, 32, 3200, 320, 5)).toEqual({ inicio: 95, fim: 115, antes: 95 * 32, depois: 1885 * 32 })
  })

  it('não passa do fim nem quebra com lista vazia', () => {
    expect(janelaVisivel(10, 32, 9999, 320).fim).toBe(10)
    expect(janelaVisivel(0, 32, 0, 320)).toEqual({ inicio: 0, fim: 0, antes: 0, depois: 0 })
  })
})
