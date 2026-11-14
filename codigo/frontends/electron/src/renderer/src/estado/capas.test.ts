import { describe, expect, it } from 'vitest'
import { candidatosDeCapa, errosDeCapa } from './capas'

describe('candidatosDeCapa', () => {
  it('lê `itens` (formato do núcleo) e usa preview_url quando há cache', () => {
    const r = {
      itens: [
        { provedor: 'steam', fonte: 'Steam', titulo: 'Celeste', url: 'https://a/x.jpg', preview_url: 'file:///C:/cache/x.img' },
        { provedor: 'wikipedia', titulo: 'Celeste', url: 'https://b/y.png' },
      ],
      erros: ['SteamGridDB: sem chave'],
      cache: true,
    }
    const lista = candidatosDeCapa(r)
    expect(lista).toHaveLength(2)
    expect(lista[0]).toMatchObject({ url: 'https://a/x.jpg', preview: 'file:///C:/cache/x.img', fonte: 'Steam' })
    expect(lista[1]).toMatchObject({ preview: 'https://b/y.png', fonte: 'wikipedia' })
    expect(lista[0].original).toBe(r.itens[0])
    expect(errosDeCapa(r)).toEqual(['SteamGridDB: sem chave'])
  })

  it('o formato antigo (`candidatos`) e lixo dão lista vazia', () => {
    expect(candidatosDeCapa({ candidatos: [{ url: 'https://x' }] })).toEqual([])
    expect(candidatosDeCapa({ itens: [{ titulo: 'sem url' }, null, 3] })).toEqual([])
    expect(candidatosDeCapa(null)).toEqual([])
  })
})
