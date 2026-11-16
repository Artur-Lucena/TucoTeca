import { describe, expect, it } from 'vitest'
import { analisar, chaveLegada, formatar, podeAvancar, podeVoltar, reduzirHistorico, type Historico } from './rota'

describe('rota', () => {
  it('analisa seções, abas e o jogo aberto', () => {
    expect(analisar('#/jogos')).toEqual({ secao: 'jogos', aba: 'biblioteca', jogo: null })
    expect(analisar('#/jogos/desejos')).toEqual({ secao: 'jogos', aba: 'desejos', jogo: null })
    expect(analisar('#/jogo/12')).toEqual({ secao: 'jogos', aba: 'visao', jogo: 12 })
    expect(analisar('#/jogo/12/conquistas')).toEqual({ secao: 'jogos', aba: 'conquistas', jogo: 12 })
    expect(analisar('#/jogo/12/xyz').aba).toBe('visao')
    expect(analisar('#/musicas')).toEqual({ secao: 'musicas', aba: '', jogo: null })
  })

  it('o que não reconhece vira Início ou a aba padrão', () => {
    expect(analisar('')).toEqual({ secao: 'inicio', aba: '', jogo: null })
    expect(analisar('#/nada')).toEqual({ secao: 'inicio', aba: '', jogo: null })
    expect(analisar('#/jogo/abc').secao).toBe('inicio')
    expect(analisar('#/jogo/0').secao).toBe('inicio')
    expect(analisar('#/midia/xyz')).toEqual({ secao: 'midia', aba: 'videos', jogo: null })
  })

  it('aceita as chaves antigas como apelidos', () => {
    expect(formatar(analisar('desejos'))).toBe('#/jogos/desejos')
    expect(formatar(analisar('#/desejos'))).toBe('#/jogos/desejos')
    expect(formatar(analisar('integracoes'))).toBe('#/configuracoes/integracoes')
    expect(formatar(analisar('videos'))).toBe('#/midia')
    expect(formatar(analisar('youtube'))).toBe('#/midia/youtube')
    expect(formatar(analisar('notificacoes'))).toBe('#/notificacoes')
    expect(formatar(analisar('jogos'))).toBe('#/jogos')
  })

  it('formata omitindo a aba padrão', () => {
    expect(formatar({ secao: 'jogos', aba: 'biblioteca', jogo: null })).toBe('#/jogos')
    expect(formatar({ secao: 'configuracoes', aba: 'integracoes', jogo: null })).toBe('#/configuracoes/integracoes')
    expect(formatar({ secao: 'jogos', aba: 'visao', jogo: 3 })).toBe('#/jogo/3')
    expect(formatar({ secao: 'jogos', aba: 'saves', jogo: 3 })).toBe('#/jogo/3/saves')
  })

  it('chave legada para busca e atalhos', () => {
    expect(chaveLegada(analisar('#/jogos/desejos'))).toBe('desejos')
    expect(chaveLegada(analisar('#/midia/youtube'))).toBe('youtube')
    expect(chaveLegada(analisar('#/midia'))).toBe('videos')
    expect(chaveLegada(analisar('#/jogos'))).toBe('jogos')
    expect(chaveLegada(analisar('#/jogo/4'))).toBe('jogo')
  })
})

describe('histórico', () => {
  const vazio: Historico = { pilha: ['#/inicio'], posicao: 0 }

  it('ir empilha, voltar/avançar andam e ir no meio corta o futuro', () => {
    let h = reduzirHistorico(vazio, { tipo: 'ir', hash: 'jogos' })
    h = reduzirHistorico(h, { tipo: 'ir', hash: '#/musicas' })
    expect(h).toEqual({ pilha: ['#/inicio', '#/jogos', '#/musicas'], posicao: 2 })
    h = reduzirHistorico(h, { tipo: 'voltar' })
    expect(h.posicao).toBe(1)
    expect(podeAvancar(h)).toBe(true)
    h = reduzirHistorico(h, { tipo: 'ir', hash: 'downloads' })
    expect(h.pilha).toEqual(['#/inicio', '#/jogos', '#/downloads'])
    expect(podeAvancar(h)).toBe(false)
  })

  it('não empilha o mesmo destino nem passa dos limites', () => {
    expect(reduzirHistorico(vazio, { tipo: 'ir', hash: '#/inicio' })).toBe(vazio)
    expect(reduzirHistorico(vazio, { tipo: 'voltar' })).toBe(vazio)
    expect(reduzirHistorico(vazio, { tipo: 'avancar' })).toBe(vazio)
    expect(podeVoltar(vazio)).toBe(false)
  })

  it('guarda no máximo 50 entradas', () => {
    let h = vazio
    for (let i = 1; i <= 60; i += 1) h = reduzirHistorico(h, { tipo: 'ir', hash: `#/jogo/${i}` })
    expect(h.pilha.length).toBe(50)
    expect(h.pilha.at(-1)).toBe('#/jogo/60')
    expect(h.posicao).toBe(49)
  })
})
