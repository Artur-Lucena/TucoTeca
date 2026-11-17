import { describe, expect, it } from 'vitest'
import { bytes, data, dataHora, duracao, hojeISO, horas, iniciais, moeda, relativo, semAcento } from './formato'

describe('formato', () => {
  it('iniciais, sem acento e data local', () => {
    expect(iniciais('Hollow Knight')).toBe('HK')
    expect(iniciais('')).toBe('?')
    expect(semAcento('Ação É')).toBe('acao e')
    expect(hojeISO(new Date(2026, 0, 5, 23, 59))).toBe('2026-01-05')
  })

  it('horas em pt-BR', () => {
    expect(horas(1.25)).toBe('1,3 h')
    expect(horas(12)).toBe('12 h')
    expect(horas(Number.NaN)).toBe('0 h')
  })

  it('bytes escala as unidades', () => {
    expect(bytes(512)).toBe('512 B')
    expect(bytes(1536)).toBe('1,5 KB')
    expect(bytes(42 * 1024 ** 3)).toBe('42 GB')
    expect(bytes(-1)).toBe('—')
    expect(bytes(Number.NaN)).toBe('—')
  })

  it('duração com e sem horas', () => {
    expect(duracao(187)).toBe('3:07')
    expect(duracao(3723)).toBe('1:02:03')
    expect(duracao(undefined)).toBe('0:00')
    expect(duracao(-5)).toBe('0:00')
  })

  it('datas curtas; inválida vira vazio', () => {
    const d = new Date(2026, 10, 14, 17, 5)
    expect(data(d)).toBe('14/11/2026')
    expect(dataHora(d)).toBe('14/11, 17:05')
    expect(data('xyz')).toBe('')
    expect(dataHora('')).toBe('')
  })

  it('tempo relativo nos dois sentidos', () => {
    const agora = new Date(2026, 10, 14, 12, 0, 0)
    const menos = (s: number) => new Date(agora.getTime() - s * 1000)
    expect(relativo(menos(10), agora)).toBe('agora')
    expect(relativo(menos(5 * 60), agora)).toBe('há 5 min')
    expect(relativo(menos(3 * 3600), agora)).toBe('há 3 h')
    expect(relativo(menos(30 * 3600), agora)).toBe('ontem')
    expect(relativo(menos(4 * 86400), agora)).toBe('há 4 dias')
    expect(relativo(menos(-2 * 86400), agora)).toBe('em 2 dias')
    expect(relativo(menos(-26 * 3600), agora)).toBe('amanhã')
    expect(relativo(new Date(2026, 0, 2), agora)).toBe('02/01/2026')
    expect(relativo('nada', agora)).toBe('')
  })

  it('moeda a partir de centavos', () => {
    expect(moeda(1999, 'brl')).toBe('R$ 19,99')
    expect(moeda(500, 'USD')).toBe('US$ 5,00')
    expect(moeda(100, 'CHF')).toBe('CHF 1,00')
    expect(moeda(100)).toBe('1,00')
    expect(moeda(Number.NaN, 'BRL')).toBe('')
  })
})
