import { describe, expect, it } from 'vitest'
import {
  jogoEmAndamento,
  reduzirTrabalhos,
  type EventoTrabalho,
  type Trabalho,
} from './trabalhos'

const trabalho = (campos: Partial<Trabalho> = {}): Trabalho => ({
  id: 1,
  rotulo: 'Jogar Celeste',
  estado: 'rodando',
  pct: null,
  cancelavel: false,
  escopo: 'jogo',
  ...campos,
})

const evento = (campos: Partial<EventoTrabalho> = {}): EventoTrabalho => ({
  ...trabalho(),
  motivo: 'inicio',
  ...campos,
})

describe('reduzirTrabalhos', () => {
  it('inicio insere; progresso e fim substituem pelo id', () => {
    let lista = reduzirTrabalhos([], evento())
    expect(lista).toHaveLength(1)
    lista = reduzirTrabalhos(lista, evento({ motivo: 'progresso', pct: 40 }))
    expect(lista).toHaveLength(1)
    expect(lista[0].pct).toBe(40)
    lista = reduzirTrabalhos(
      lista,
      evento({ motivo: 'fim', estado: 'ok', detalhe: { horas: 0.01, rastreado: true } }),
    )
    expect(lista[0].estado).toBe('ok')
    expect(lista[0].detalhe?.horas).toBe(0.01)
  })

  it('mantém ids distintos na ordem de criação', () => {
    let lista = reduzirTrabalhos([], evento({ id: 1 }))
    lista = reduzirTrabalhos(lista, evento({ id: 2, rotulo: 'Baixar fila' }))
    expect(lista.map((t) => t.id)).toEqual([1, 2])
    lista = reduzirTrabalhos(lista, evento({ id: 1, motivo: 'fim', estado: 'ok' }))
    expect(lista.map((t) => t.id)).toEqual([1, 2])
    expect(lista[1].estado).toBe('rodando')
  })

  it('evento de id desconhecido entra no fim (reconexão não perde nada)', () => {
    const lista = reduzirTrabalhos([trabalho({ id: 1 })], evento({ id: 7, rotulo: 'Novo' }))
    expect(lista.map((t) => t.id)).toEqual([1, 7])
  })
})

describe('jogoEmAndamento', () => {
  it('acha só o job de jogo ainda ativo', () => {
    const lista = [trabalho({ id: 1 }), trabalho({ id: 2, escopo: 'musicas' })]
    expect(jogoEmAndamento(lista)?.id).toBe(1)
    expect(jogoEmAndamento([trabalho({ estado: 'ok' })])).toBeNull()
    expect(jogoEmAndamento([trabalho({ estado: 'cancelando', escopo: null })])).toBeNull()
    expect(jogoEmAndamento([])).toBeNull()
  })
})
