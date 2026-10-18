import { describe, expect, it } from 'vitest'

import { acaoDaIntegracao, type IntegracaoDTO } from './integracoes'

const base: IntegracaoDTO = { chave: 'x', nome: 'X', tipo: 'link' }

describe('acaoDaIntegracao', () => {
  it('catálogo padrão (sem URL) pesquisa no catálogo', () => {
    expect(acaoDaIntegracao({ ...base, tipo: 'catalogo', capacidades: ['busca'] }))
      .toEqual({ tipo: 'buscar', rotulo: 'Buscar no catálogo' })
  })

  it('link com URL sem {q} abre o site', () => {
    expect(acaoDaIntegracao({ ...base, url: 'https://exemplo.test/', capacidades: ['abrir'] }))
      .toEqual({ tipo: 'abrir', rotulo: 'Abrir site' })
  })

  it('URL com {q} pede termo e pesquisa no site', () => {
    expect(acaoDaIntegracao({ ...base, url: 'https://exemplo.test/buscar?q={q}', capacidades: ['abrir'] }))
      .toEqual({ tipo: 'buscar', rotulo: 'Buscar no site' })
  })

  it('download leva para a fila de downloads', () => {
    expect(acaoDaIntegracao({ ...base, tipo: 'download', capacidades: ['download'] }))
      .toEqual({ tipo: 'download', rotulo: 'Ir para Downloads' })
  })

  it('emulador fica para a próxima fatia', () => {
    const r = acaoDaIntegracao({ ...base, tipo: 'emulador', capacidades: ['emulador', 'config'] })
    expect(r.tipo).toBe('indisponivel')
    if (r.tipo === 'indisponivel') expect(r.motivo).toContain('Emulação')
  })

  it('músicas online e provedores ficam para a próxima fatia', () => {
    expect(acaoDaIntegracao({ ...base, tipo: 'musicas_online', capacidades: ['midia'] }).tipo)
      .toBe('indisponivel')
    expect(acaoDaIntegracao({ ...base, tipo: 'provedores', capacidades: ['midia'] }).tipo)
      .toBe('indisponivel')
  })
})
