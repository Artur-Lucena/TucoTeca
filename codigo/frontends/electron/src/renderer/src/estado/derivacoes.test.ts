import { describe, expect, it } from 'vitest'
import { continuarJogando, type JogoResumo } from './derivacoes'

const jogo = (titulo: string, extras: Partial<JogoResumo> = {}): JogoResumo => ({ titulo, ...extras })

describe('continuarJogando', () => {
  it('prioriza os jogados por último, mais recente primeiro', () => {
    const lista = [
      jogo('Antigo', { ultima_execucao: '2026-10-01 10:00:00' }),
      jogo('Novo', { ultima_execucao: '2026-10-17 09:00:00' }),
      jogo('Meio', { ultima_execucao: '2026-10-10 20:00:00' }),
    ]
    expect(continuarJogando(lista).map((j) => j.titulo)).toEqual(['Novo', 'Meio', 'Antigo'])
  })

  it('completa com os mais jogados quando falta histórico', () => {
    const lista = [
      jogo('Sem histórico A', { horas: 5 }),
      jogo('Sem histórico B', { horas: 90 }),
      jogo('Recente', { ultima_execucao: '2026-10-17 09:00:00', horas: 1 }),
    ]
    expect(continuarJogando(lista).map((j) => j.titulo)).toEqual([
      'Recente',
      'Sem histórico B',
      'Sem histórico A',
    ])
  })

  it('limita a seis cartões', () => {
    const lista = Array.from({ length: 9 }, (_, i) =>
      jogo(`Jogo ${i}`, {
        ultima_execucao: `2026-10-${String(i + 1).padStart(2, '0')} 10:00:00`,
      }),
    )
    const escolhidos = continuarJogando(lista)
    expect(escolhidos).toHaveLength(6)
    expect(escolhidos[0].titulo).toBe('Jogo 8')
  })

  it('aceita menos de seis, lista vazia e indefinida', () => {
    expect(continuarJogando([jogo('Solo')]).map((j) => j.titulo)).toEqual(['Solo'])
    expect(continuarJogando([])).toEqual([])
    expect(continuarJogando(undefined)).toEqual([])
  })

  it('ignora entradas sem título', () => {
    const lista = [jogo('Válido'), { horas: 10 } as JogoResumo, jogo('   ')]
    expect(continuarJogando(lista).map((j) => j.titulo)).toEqual(['Válido'])
  })
})
