import { describe, expect, it } from 'vitest'
import { reduzirConexao } from './conexao'

describe('reduzirConexao', () => {
  it('cai de qualquer estado, reabre só quando caiu e volta a ok', () => {
    expect(reduzirConexao('ok', { tipo: 'caiu' })).toBe('caiu')
    expect(reduzirConexao('caiu', { tipo: 'reabrindo' })).toBe('reabrindo')
    expect(reduzirConexao('ok', { tipo: 'reabrindo' })).toBe('ok')
    expect(reduzirConexao('reabrindo', { tipo: 'ok' })).toBe('ok')
    expect(reduzirConexao('caiu', { tipo: 'caiu' })).toBe('caiu')
  })
})
