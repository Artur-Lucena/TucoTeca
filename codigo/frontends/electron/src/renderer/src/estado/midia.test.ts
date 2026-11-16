import { describe, expect, it } from 'vitest'
import { agruparPorDia, chavesDaTemporada, filtrarTitulos, fracao, proximoParaAssistir, rotuloEpisodio, type Episodio, type TituloResumo } from './midia'

const ep = (temporada: number, episodio: number, arquivo: number | null, assistido = false, estreia = '2020-01-01'): Episodio => ({
  chave: `tt1:${temporada}:${episodio}`,
  temporada,
  episodio,
  nome: '',
  estreia,
  resumo: '',
  miniatura: '',
  arquivo,
  progresso: assistido ? { posicao: 0, duracao: 100, assistido: true } : null,
})

describe('midia', () => {
  it('rótulo de episódio e fração vista', () => {
    expect(rotuloEpisodio(1, 2)).toBe('T1E02')
    expect(rotuloEpisodio(0, 3)).toBe('Especial 3')
    expect(fracao({ posicao: 30, duracao: 120, assistido: false })).toBe(0.25)
    expect(fracao({ posicao: 0, duracao: 0, assistido: true })).toBe(1)
    expect(fracao(null)).toBe(0)
  })

  it('filtra por tipo e nome sem acento', () => {
    const t: TituloResumo[] = [
      { imdb_id: 'tt1', tipo: 'movie', nome: 'Cidade de Deus', ano: '', poster: '' },
      { imdb_id: 'tt2', tipo: 'series', nome: 'Pantanal', ano: '', poster: '' },
    ]
    expect(filtrarTitulos(t, 'series', '').map((x) => x.imdb_id)).toEqual(['tt2'])
    expect(filtrarTitulos(t, 'todos', 'CIDADE').map((x) => x.imdb_id)).toEqual(['tt1'])
  })

  it('próximo para assistir: primeiro no disco não visto; especiais ficam de fora', () => {
    const temps = [
      { numero: 0, episodios: [ep(0, 1, 9)] },
      { numero: 1, episodios: [ep(1, 1, 10, true), ep(1, 2, null), ep(1, 3, 11)] },
    ]
    expect(proximoParaAssistir(temps)?.chave).toBe('tt1:1:3')
    expect(proximoParaAssistir([{ numero: 1, episodios: [ep(1, 1, 10, true)] }])?.chave).toBe('tt1:1:1')
    expect(proximoParaAssistir([])).toBeNull()
  })

  it('agrupa o calendário por dia com rótulos relativos', () => {
    const hoje = new Date(2026, 10, 16)
    const g = agruparPorDia([{ data: '2026-11-15' }, { data: '2026-11-16' }, { data: '2026-11-16' }, { data: '2026-11-17' }, { data: '2026-12-01' }], hoje)
    expect(g.map((x) => [x.rotulo, x.itens.length])).toEqual([['Ontem', 1], ['Hoje', 2], ['Amanhã', 1], ['01/12/2026', 1]])
  })

  it('marcar temporada pega só episódios já lançados (ou no disco)', () => {
    const t = { numero: 1, episodios: [ep(1, 1, null, false, '2020-01-01'), ep(1, 2, null, false, '2999-01-01'), ep(1, 3, 5, false, '')] }
    expect(chavesDaTemporada(t, true, new Date(2026, 0, 1))).toEqual(['tt1:1:1', 'tt1:1:3'])
  })
})
