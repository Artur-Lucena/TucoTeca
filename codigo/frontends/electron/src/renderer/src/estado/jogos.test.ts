import { describe, expect, it } from 'vitest'
import { filtrarJogos, generosDaColecao, normalizarEtiquetas, ordenarJogos, validarHoras, validarNota } from './jogos'

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

describe('validarNota', () => {
  it('aceita inteiro 0–10', () => {
    expect(validarNota('7')).toBe(7)
    expect(validarNota(' 7 ')).toBe(7)
    expect(validarNota('0')).toBe(0)
    expect(validarNota('10')).toBe(10)
    expect(validarNota(8)).toBe(8)
  })

  it('recusa fora da faixa, decimal (núcleo é inteiro), texto e vazio', () => {
    expect(validarNota('')).toBeNull()
    expect(validarNota('   ')).toBeNull()
    expect(validarNota('abc')).toBeNull()
    expect(validarNota('-1')).toBeNull()
    expect(validarNota('11')).toBeNull()
    expect(validarNota('8,5')).toBeNull()
    expect(validarNota('8.5')).toBeNull()
    expect(validarNota(null)).toBeNull()
  })
})

describe('validarHoras', () => {
  it('aceita número positivo com vírgula ou ponto', () => {
    expect(validarHoras('1,5')).toBe(1.5)
    expect(validarHoras('0.25')).toBe(0.25)
    expect(validarHoras('3')).toBe(3)
  })

  it('recusa zero, negativo, texto e vazio', () => {
    expect(validarHoras('0')).toBeNull()
    expect(validarHoras('-2')).toBeNull()
    expect(validarHoras('')).toBeNull()
    expect(validarHoras('duas')).toBeNull()
    expect(validarHoras(undefined)).toBeNull()
  })
})

describe('normalizarEtiquetas', () => {
  it('separa por vírgula/ponto-e-vírgula, dedupa e ordena', () => {
    expect(normalizarEtiquetas('rpg, canon')).toBe('canon, rpg')
    expect(normalizarEtiquetas('  Metroidvania ;; rpg ,metroidvania ')).toBe('Metroidvania, rpg')
    expect(normalizarEtiquetas('ação, ação')).toBe('ação')
    expect(normalizarEtiquetas('')).toBe('')
    expect(normalizarEtiquetas(null)).toBe('')
  })

  it('limita tag a 30 chars e a 20 etiquetas', () => {
    const tags = Array.from({ length: 25 }, (_, i) => `tag${i}`).join(', ')
    expect(normalizarEtiquetas(tags).split(', ')).toHaveLength(20)
    expect(normalizarEtiquetas('x'.repeat(40))).toHaveLength(30)
  })
})

describe('gêneros da coleção', () => {
  const jogos = [
    jogo({ id: 1, generos: ['RPG', 'Ação'] }),
    jogo({ id: 2, generos: ['Ação', 'Ação'] }),
    jogo({ id: 3, generos: ['Aventura'] }),
    jogo({ id: 4 }),
  ]

  it('conta cada gênero uma vez por jogo, mais comuns primeiro', () => {
    expect(generosDaColecao(jogos)).toEqual([
      { nome: 'Ação', total: 2 },
      { nome: 'Aventura', total: 1 },
      { nome: 'RPG', total: 1 },
    ])
    expect(generosDaColecao(undefined)).toEqual([])
  })

  it('filtra pelo gênero junto com o resto', () => {
    expect(filtrarJogos(jogos, { genero: 'Ação' }).map((j) => j.id)).toEqual([1, 2])
    expect(filtrarJogos(jogos, { genero: '' }).length).toBe(4)
  })
})