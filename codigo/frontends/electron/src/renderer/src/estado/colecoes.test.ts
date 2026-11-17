import { describe, expect, it } from 'vitest'
import { jogosDaColecao, normalizarColecoes, validarNomeColecao } from './colecoes'

describe('coleções', () => {
  it('normaliza e descarta itens ruins', () => {
    expect(normalizarColecoes([{ id: 1, nome: ' RPG ', uuids: ['a', 3] }, { id: 0, nome: 'x' }, null, { id: 2, nome: '' }])).toEqual([
      { id: 1, nome: 'RPG', uuids: ['a'] },
    ])
    expect(normalizarColecoes('nada')).toEqual([])
  })

  it('jogos na ordem da coleção, ignorando os que sumiram', () => {
    const jogos = [{ uuid: 'a', titulo: 'A' }, { uuid: 'b', titulo: 'B' }]
    expect(jogosDaColecao(jogos, { id: 1, nome: 'x', uuids: ['b', 'z', 'a'] }).map((j) => j.titulo)).toEqual(['B', 'A'])
    expect(jogosDaColecao(jogos, undefined)).toEqual([])
  })

  it('valida nome: vazio, longo e repetido (sem caixa)', () => {
    const existentes = [{ id: 1, nome: 'Zerados', uuids: [] }]
    expect(validarNomeColecao('  Para   jogar ', existentes)).toBe('Para jogar')
    expect(validarNomeColecao('   ', existentes)).toEqual({ erro: 'Dê um nome à coleção.' })
    expect(validarNomeColecao('x'.repeat(61), existentes)).toHaveProperty('erro')
    expect(validarNomeColecao('ZERADOS', existentes)).toHaveProperty('erro')
    expect(validarNomeColecao('zerados', existentes, 1)).toBe('zerados')
  })
})
