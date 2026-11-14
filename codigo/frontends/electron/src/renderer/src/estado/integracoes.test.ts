import { describe, expect, it } from 'vitest'

import { acaoDaIntegracao, selosDaIntegracao, type IntegracaoDTO } from './integracoes'

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
      .toEqual({ tipo: 'navegar', rotulo: 'Ir para Downloads', secao: 'downloads' })
  })

  it('emulador, músicas online e provedores levam à tela que faz isso', () => {
    expect(acaoDaIntegracao({ ...base, tipo: 'emulador', capacidades: ['emulador', 'config'] }))
      .toEqual({ tipo: 'navegar', rotulo: 'Emuladores e controles', secao: 'configuracoes' })
    expect(acaoDaIntegracao({ ...base, tipo: 'musicas_online', capacidades: ['midia'] }))
      .toMatchObject({ tipo: 'navegar', secao: 'musicas' })
    expect(acaoDaIntegracao({ ...base, tipo: 'provedores', capacidades: ['midia'] }))
      .toMatchObject({ tipo: 'navegar', secao: 'configuracoes' })
  })

  it('sem URL e sem tipo conhecido fica indisponível com motivo', () => {
    expect(acaoDaIntegracao(base).tipo).toBe('indisponivel')
  })
})

describe('selosDaIntegracao', () => {
  it('rótulos legíveis e sem repetir o tipo nas capacidades', () => {
    expect(selosDaIntegracao({ ...base, tipo: 'emulador', capacidades: ['emulador', 'config'] }))
      .toEqual(['emulador', 'configuração'])
    expect(selosDaIntegracao({ ...base, tipo: 'musicas_online', capacidades: ['midia'] }))
      .toEqual(['músicas online', 'mídia'])
    expect(selosDaIntegracao({ ...base, tipo: 'catalogo', capacidades: ['busca'], personalizada: true }))
      .toEqual(['catálogo', 'busca', 'personalizada'])
  })
})
