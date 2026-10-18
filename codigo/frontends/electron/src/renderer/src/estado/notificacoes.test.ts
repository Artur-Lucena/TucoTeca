import { describe, expect, it } from 'vitest'
import { avisosDoResumo, dispensarAviso, juntarAvisos } from './notificacoes'

describe('avisosDoResumo', () => {
  it('avisa sessões pendentes com plural correto', () => {
    expect(avisosDoResumo({ pendentes: 1 }).map((a) => a.id)).toEqual(['sessoes-pendentes'])
    const dois = avisosDoResumo({ pendentes: 2 })
    expect(dois[0].texto).toContain('2 sessões pendentes')
    expect(dois[0].tom).toBe('atencao')
  })

  it('avisa backup ausente e backup velho (>14 dias), silencia quando ok', () => {
    expect(avisosDoResumo({ backup: 'sem backup' }).map((a) => a.id)).toEqual(['backup-ausente'])
    expect(avisosDoResumo({ backup: 'biblioteca-x.db', backup_idade_dias: 30 }).map((a) => a.id)).toEqual([
      'backup-velho',
    ])
    expect(avisosDoResumo({ backup: 'biblioteca-x.db', backup_idade_dias: 3 })).toEqual([])
  })

  it('avisa disco baixo e ignora campos ausentes', () => {
    expect(avisosDoResumo({ disco_livre_gb: 2.5 }).map((a) => a.id)).toEqual(['disco-baixo'])
    expect(avisosDoResumo({})).toEqual([])
  })
})

describe('juntarAvisos / dispensarAviso', () => {
  it('deduplica por id mantendo o mais novo primeiro', () => {
    const atual = [{ id: 'a', texto: 'antigo', tom: 'info' as const }]
    const juntos = juntarAvisos(atual, [{ id: 'a', texto: 'novo', tom: 'info' }])
    expect(juntos).toEqual([{ id: 'a', texto: 'novo', tom: 'info' }])
  })

  it('dispensa por id e não quebra com id ausente', () => {
    const lista = [{ id: 'a', texto: 'x', tom: 'info' as const }]
    expect(dispensarAviso(lista, 'a')).toEqual([])
    expect(dispensarAviso(lista, 'z')).toEqual(lista)
  })
})
