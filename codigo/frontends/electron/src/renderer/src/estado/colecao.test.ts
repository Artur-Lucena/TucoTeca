import { describe, expect, it } from 'vitest'
import { alturasMeses, dataDoBackup, dataDoSnapshot, normalizarResumo } from './colecao'

describe('dataDoBackup', () => {
  it('lê a data do nome do arquivo', () => {
    expect(dataDoBackup('biblioteca-20261114-171503-123456.db')).toBe('14/11/2026 17:15')
    expect(dataDoBackup('outro.db')).toBe('')
    expect(dataDoSnapshot('saves-20261114-171503-1.zip')).toBe('14/11/2026 17:15')
  })
})

describe('resumo do ano', () => {
  it('normaliza meses (12, sem negativos) e jogos', () => {
    const r = normalizarResumo({ ano: 2026, meses: [1, -2, 'x'], total_horas: 3, jogos: [{ titulo: 'A', horas: 2 }] })
    expect(r.meses).toHaveLength(12)
    expect(r.meses.slice(0, 3)).toEqual([1, 0, 0])
    expect(r.jogos).toEqual([{ titulo: 'A', horas: 2 }])
  })

  it('alturas relativas ao maior mês; tudo zero não divide por zero', () => {
    expect(alturasMeses([5, 10, 0])).toEqual([50, 100, 0])
    expect(alturasMeses([0, 0])).toEqual([0, 0])
  })
})
