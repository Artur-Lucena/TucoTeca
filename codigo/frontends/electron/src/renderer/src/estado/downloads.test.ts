import { describe, expect, it } from 'vitest'
import { arquivoBaixado, downloadsNoApp, ehAtualizacao, estadoDoDownload, pastaDe } from './downloads'
import type { Trabalho } from './trabalhos'

const t = (extra: Partial<Trabalho>): Trabalho => ({ id: 1, rotulo: 'Baixar', estado: 'rodando', pct: null, cancelavel: true, ...extra })

describe('downloads no app', () => {
  it('só o grupo download, mais novos primeiro', () => {
    const lista = [t({ id: 1, grupo: 'download' }), t({ id: 2, escopo: 'jogo' }), t({ id: 3, grupo: 'download' })]
    expect(downloadsNoApp(lista).map((x) => x.id)).toEqual([3, 1])
  })

  it('arquivo só quando terminou bem (path do jogo ou arquivo da atualização)', () => {
    expect(arquivoBaixado(t({ estado: 'ok', detalhe: { path: 'D:\\Jogos\\a.zip' } }))).toBe('D:\\Jogos\\a.zip')
    expect(arquivoBaixado(t({ estado: 'ok', detalhe: { arquivo: '/x/TucoTeca.AppImage' } }))).toBe('/x/TucoTeca.AppImage')
    expect(arquivoBaixado(t({ estado: 'erro', detalhe: { path: 'a' } }))).toBe('')
    expect(arquivoBaixado(t({ estado: 'ok', detalhe: { path: 3 } }))).toBe('')
  })

  it('pasta do arquivo nos dois sistemas', () => {
    expect(pastaDe('D:\\Jogos\\a.zip')).toBe('D:\\Jogos')
    expect(pastaDe('/home/x/a.zip')).toBe('/home/x')
    expect(pastaDe('a.zip')).toBe('a.zip')
  })

  it('texto do estado', () => {
    expect(estadoDoDownload(t({ pct: 40 }))).toBe('Baixando · 40%')
    expect(estadoDoDownload(t({}))).toBe('Baixando…')
    expect(estadoDoDownload(t({ estado: 'erro', erro: 'sem rede' }))).toBe('Falhou: sem rede')
    expect(estadoDoDownload(t({ estado: 'cancelado' }))).toBe('Cancelado')
    expect(estadoDoDownload(t({ estado: 'ok' }))).toBe('Concluído')
    expect(ehAtualizacao(t({ escopo: 'atualizacao' }))).toBe(true)
  })
})
