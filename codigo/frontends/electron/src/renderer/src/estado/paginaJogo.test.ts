import { describe, expect, it } from 'vitest'
import { abasDoJogo, metricasDoJogo, normalizarPagina, origemDosDados } from './paginaJogo'

const agora = new Date(2026, 10, 16, 12, 0, 0)

describe('paginaJogo', () => {
  it('normaliza a resposta e tolera campos faltando ou com tipo errado', () => {
    const p = normalizarPagina({ jogo: { id: 1, titulo: 'X' }, meta: { generos: ['RPG', 3], retro: null } })
    expect(p.meta.generos).toEqual(['RPG'])
    expect(p.meta.retro).toBeNull()
    expect(p.meta.hero_url).toBe('')
    expect(p.enriquecido).toBe(false)
    expect(normalizarPagina(null).provedores).toEqual([])
  })

  it('métricas mostram só o que existe', () => {
    const base = normalizarPagina({ jogo: { horas: 12.5 }, meta: {} })
    expect(metricasDoJogo(base, agora)).toEqual([
      { rotulo: 'Jogado', valor: '12,5 h' },
      { rotulo: 'Última vez', valor: 'nunca' },
    ])
    const cheio = normalizarPagina({
      jogo: { horas: 3, ultima_execucao: new Date(2026, 10, 15, 11, 0).toISOString() },
      meta: {
        retro: { total: 40, ganhas: 7, conquistas: [{ id: 1, titulo: 'A', pontos: 5 }] },
      },
    })
    expect(metricasDoJogo(cheio, agora).map((m) => m.valor)).toEqual(['3 h', 'ontem', '7/40'])
  })

  it('Emulação só aparece para jogo emulado', () => {
    expect(abasDoJogo({ plataforma: 'PC' })).not.toContain('emulacao')
    expect(abasDoJogo({ plataforma: '3DS' })).toContain('emulacao')
    expect(abasDoJogo({ plataforma: 'PC' })[0]).toBe('visao')
  })

  it('origem dos dados cita provedores pelo nome e a data mais nova', () => {
    const p = normalizarPagina({
      provedores: [{ chave: 'steam', nome: 'Steam' }, { chave: 'sgdb', nome: 'SteamGridDB' }],
      meta: { fontes: { steam: '2026-11-13T12:00:00', sgdb: '2026-11-15T12:00:00' } },
    })
    expect(origemDosDados(p, agora)).toBe('Steam · SteamGridDB, ontem')
    expect(origemDosDados(normalizarPagina({}), agora)).toBe('')
  })
})
