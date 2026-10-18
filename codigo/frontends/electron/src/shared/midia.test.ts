import { describe, expect, it } from 'vitest'
import { converterUrlMidia, mediaUrl } from './midia'

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

describe('mediaUrl', () => {
  it('gera URL do protocolo de mídia com o caminho escapado', () => {
    expect(mediaUrl('C:\\Tucoteca\\dados\\musicas\\a.wav')).toBe(
      'tucoteca-media://arquivo/C%3A%2FTucoteca%2Fdados%2Fmusicas%2Fa.wav',
    )
  })

  it('escapa espaços e acentos', () => {
    expect(mediaUrl('C:\\My Música\\a b.wav')).toBe(
      'tucoteca-media://arquivo/C%3A%2FMy%20M%C3%BAsica%2Fa%20b.wav',
    )
  })

  it('vazio ou só espaços vira string vazia', () => {
    expect(mediaUrl('')).toBe('')
    expect(mediaUrl('   ')).toBe('')
  })
})
