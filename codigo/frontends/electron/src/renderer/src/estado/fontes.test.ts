import { describe, expect, it } from 'vitest'
import { dataCurta, linksDaOpcao, type OpcaoDownload } from './fontes'

const base: OpcaoDownload = { titulo: 'Hades', uris: [], tamanho: '', data: '', fonte: 'F', fonte_id: 'x', nota: 1 }

describe('fontes de download', () => {
  it('torrent primeiro, depois diretos com o host; o resto some', () => {
    const links = linksDaOpcao({
      ...base,
      uris: ['https://www.cdn.test/a.zip', 'magnet:?xt=urn:btih:ABC', 'http://inseguro/x', 'https://%%%'],
    })
    expect(links.map((l) => [l.tipo, l.rotulo])).toEqual([
      ['torrent', 'Torrent'],
      ['direto', 'Direto · cdn.test'],
    ])
  })

  it('data curta em pt-BR', () => {
    expect(dataCurta('2025-02-01T10:00:00Z')).toBe('01/02/2025')
    expect(dataCurta('')).toBe('')
  })
})
