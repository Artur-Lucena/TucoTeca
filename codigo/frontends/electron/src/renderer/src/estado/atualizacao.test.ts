import { describe, expect, it } from 'vitest'
import { downloadDaAtualizacao, instaladorPronto, resumoDaVerificacao, type Verificacao } from './atualizacao'
import type { Trabalho } from './trabalhos'

const v: Verificacao = { atual: '2.2.0', ultima: '2.3.0', nova: true, notas: '', pagina: '', publicada_em: '2026-11-20', instalador: null }
const t = (extra: Partial<Trabalho>): Trabalho => ({ id: 1, rotulo: 'x', estado: 'rodando', pct: null, cancelavel: true, ...extra })

describe('atualização', () => {
  it('resumo da verificação', () => {
    expect(resumoDaVerificacao(v)).toBe('TucoTeca 2.3.0 disponível desde 20/11/2026 (você tem a 2.2.0).')
    expect(resumoDaVerificacao({ ...v, nova: false, atual: '2.3.0' })).toBe('Você está na versão mais recente (2.3.0).')
  })

  it('instalador pronto só quando o último download da atualização terminou', () => {
    const lista = [
      t({ id: 1, escopo: 'atualizacao', estado: 'erro' }),
      t({ id: 2, grupo: 'download' }),
      t({ id: 3, escopo: 'atualizacao', estado: 'ok', detalhe: { arquivo: 'C:\\h\\dados\\atualizacoes\\TucoTeca-Setup-2.3.0-x64.exe' } }),
    ]
    expect(downloadDaAtualizacao(lista)?.id).toBe(3)
    expect(instaladorPronto(lista)).toContain('TucoTeca-Setup-2.3.0-x64.exe')
    expect(instaladorPronto([t({ escopo: 'atualizacao' })])).toBe('')
    expect(instaladorPronto([])).toBe('')
  })
})
