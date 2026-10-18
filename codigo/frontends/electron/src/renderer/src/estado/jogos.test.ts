import { describe, expect, it } from 'vitest'
import { filtrarJogos, ordenarJogos } from './jogos'

const jogo = (campos: Record<string, unknown>) => ({ titulo: 'Jogo', ...campos })

const colecao = [
  jogo({
    id: 1,
    titulo: 'Hollow Knight',
    plataforma: 'PC',
    horas: 42.5,
    ultima_execucao: '2026-10-15 20:10:00',
    favorito: true,
    status: 'zerado',
    etiquetas_lista: ['metroidvania'],
  }),
  jogo({
    id: 2,
    titulo: 'Celeste',
    plataforma: 'PC',
    horas: 11.25,
    ultima_execucao: '2026-10-17 21:40:00',
    favorito: false,
    status: 'jogando',
  }),
  jogo({
    id: 3,
    titulo: 'Coração de Ferro',
    plataforma: 'NDS',
    horas: 0,
    status: 'pendente',
    etiquetas: 'rpg, canon',
  }),
  jogo({
    id: 4,
    titulo: 'Zelda: A Link Between Worlds',
    plataforma: '3DS',
    horas: 30,
    ultima_execucao: '',
    favorito: true,
    status: 'jogando',
  }),
]

const titulos = (jogos: Array<Record<string, unknown>>) => jogos.map((j) => j.titulo)

describe('filtrarJogos', () => {
  it('sem filtro devolve tudo em cópia e aguenta lista ausente/vazia', () => {
    const tudo = filtrarJogos(colecao, {})
    expect(titulos(tudo)).toHaveLength(4)
    expect(tudo).not.toBe(colecao)
    expect(filtrarJogos(undefined, {})).toEqual([])
    expect(filtrarJogos([], { filtro: 'favoritos' })).toEqual([])
  })

  it('filtra por plataforma (PC/3DS/NDS)', () => {
    expect(titulos(filtrarJogos(colecao, { filtro: 'NDS' }))).toEqual(['Coração de Ferro'])
    expect(titulos(filtrarJogos(colecao, { filtro: '3DS' }))).toEqual([
      'Zelda: A Link Between Worlds',
    ])
    expect(titulos(filtrarJogos(colecao, { filtro: 'PC' }))).toEqual([
      'Hollow Knight',
      'Celeste',
    ])
  })

  it('filtra favoritos e jogando', () => {
    expect(titulos(filtrarJogos(colecao, { filtro: 'favoritos' }))).toEqual([
      'Hollow Knight',
      'Zelda: A Link Between Worlds',
    ])
    expect(titulos(filtrarJogos(colecao, { filtro: 'jogando' }))).toEqual([
      'Celeste',
      'Zelda: A Link Between Worlds',
    ])
  })

  it('pendencias usa os ids da saúde da coleção', () => {
    expect(titulos(filtrarJogos(colecao, { filtro: 'pendencias', idsPendentes: [2, 3] }))).toEqual(
      ['Celeste', 'Coração de Ferro'],
    )
    expect(filtrarJogos(colecao, { filtro: 'pendencias', idsPendentes: [] })).toEqual([])
  })

  it('busca sem acento e multi-palavra em título/etiquetas/plataforma', () => {
    expect(titulos(filtrarJogos(colecao, { busca: 'knight' }))).toEqual(['Hollow Knight'])
    expect(titulos(filtrarJogos(colecao, { busca: 'hollow  KNIGHT' }))).toEqual(['Hollow Knight'])
    expect(titulos(filtrarJogos(colecao, { busca: 'coracao' }))).toEqual(['Coração de Ferro'])
    expect(titulos(filtrarJogos(colecao, { busca: 'rpg canon' }))).toEqual(['Coração de Ferro'])
    expect(titulos(filtrarJogos(colecao, { busca: 'nds' }))).toEqual(['Coração de Ferro'])
    expect(titulos(filtrarJogos(colecao, { busca: 'metroidvania' }))).toEqual(['Hollow Knight'])
  })

  it('combina filtro e busca', () => {
    expect(titulos(filtrarJogos(colecao, { filtro: 'jogando', busca: 'zelda' }))).toEqual([
      'Zelda: A Link Between Worlds',
    ])
    expect(filtrarJogos(colecao, { filtro: 'favoritos', busca: 'knight' })).toHaveLength(1)
  })
})

describe('ordenarJogos', () => {
  it('por título comparando sem acento', () => {
    expect(titulos(ordenarJogos([...colecao].reverse(), 'titulo'))).toEqual([
      'Celeste',
      'Coração de Ferro',
      'Hollow Knight',
      'Zelda: A Link Between Worlds',
    ])
  })

  it('por horas desc com empate estável por título', () => {
    const empate = [jogo({ titulo: 'Beta', horas: 10 }), jogo({ titulo: 'Alfa', horas: 10 })]
    expect(titulos(ordenarJogos(empate, 'horas'))).toEqual(['Alfa', 'Beta'])
    expect(titulos(ordenarJogos(colecao, 'horas'))).toEqual([
      'Hollow Knight',
      'Zelda: A Link Between Worlds',
      'Celeste',
      'Coração de Ferro',
    ])
  })

  it('por recentes desc, sem data por último e empate por título', () => {
    expect(titulos(ordenarJogos(colecao, 'recentes'))).toEqual([
      'Celeste',
      'Hollow Knight',
      'Coração de Ferro',
      'Zelda: A Link Between Worlds',
    ])
  })

  it('não altera a lista original', () => {
    const original = [...colecao]
    ordenarJogos(original, 'horas')
    expect(titulos(original)).toEqual(titulos(colecao))
  })
})
