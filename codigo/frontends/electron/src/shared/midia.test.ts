import { describe, expect, it } from 'vitest'
import { converterUrlMidia } from './midia'

describe('converterUrlMidia', () => {
  it('converte file:// do Windows para o protocolo da coleção', () => {
    expect(converterUrlMidia('file:///C:/dados/capas/a.png')).toBe(
      'tucoteca-img://local/C:/dados/capas/a.png',
    )
  })

  it('preserva escapes de espaço no caminho', () => {
    expect(converterUrlMidia('file:///C:/My%20Jogo/capa.png')).toBe(
      'tucoteca-img://local/C:/My%20Jogo/capa.png',
    )
  })

  it('converte caminhos posix', () => {
    expect(converterUrlMidia('file:///home/tuco/capa.png')).toBe(
      'tucoteca-img://local/home/tuco/capa.png',
    )
  })

  it('deixa http(s) e data: como estão', () => {
    expect(converterUrlMidia('https://exemplo.test/capa.png')).toBe('https://exemplo.test/capa.png')
    expect(converterUrlMidia('data:image/png;base64,AA')).toBe('data:image/png;base64,AA')
  })

  it('vazio e inválido viram string vazia', () => {
    expect(converterUrlMidia('')).toBe('')
    expect(converterUrlMidia('nao-e-url')).toBe('')
  })
})
