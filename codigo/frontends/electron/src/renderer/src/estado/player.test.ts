import { describe, expect, it } from 'vitest'
import {
  alternar,
  anterior,
  cicloModo,
  faixaAtual,
  fimDaFaixa,
  parar,
  playerInicial,
  proxima,
  pularPara,
  tocarFila,
  type Faixa,
} from './player'

const FAIXAS: Faixa[] = [
  { id: 1, titulo: 'A', musica_path: 'C:/m/a.wav' },
  { id: 2, titulo: 'B', musica_path: 'C:/m/b.wav' },
  { id: 3, titulo: 'C', musica_path: 'C:/m/c.wav' },
]

describe('tocarFila', () => {
  it('copia a fila, clampa o índice e toca', () => {
    const estado = tocarFila(playerInicial, FAIXAS, 1)
    expect(estado.fila).toHaveLength(3)
    expect(estado.fila).not.toBe(FAIXAS)
    expect(estado.indice).toBe(1)
    expect(estado.estado).toBe('tocando')
    expect(faixaAtual(estado)?.titulo).toBe('B')
  })

  it('índice inválido vira o primeiro', () => {
    expect(tocarFila(playerInicial, FAIXAS, 99).indice).toBe(2)
    expect(tocarFila(playerInicial, FAIXAS, -5).indice).toBe(0)
    expect(tocarFila(playerInicial, FAIXAS, NaN).indice).toBe(0)
  })

  it('fila vazia para o player', () => {
    const estado = tocarFila(playerInicial, [], 0)
    expect(estado.fila).toEqual([])
    expect(estado.indice).toBe(-1)
    expect(estado.estado).toBe('parado')
    expect(faixaAtual(estado)).toBeNull()
  })
})

describe('transporte', () => {
  it('alternar vai e volta entre tocando e pausado', () => {
    let estado = tocarFila(playerInicial, FAIXAS, 0)
    estado = alternar(estado)
    expect(estado.estado).toBe('pausado')
    expect(estado.indice).toBe(0)
    estado = alternar(estado)
    expect(estado.estado).toBe('tocando')
  })

  it('alternar sem fila não muda nada', () => {
    expect(alternar(playerInicial)).toEqual(playerInicial)
  })

  it('próxima avança e para no fim (sem wrap)', () => {
    let estado = tocarFila(playerInicial, FAIXAS, 1)
    estado = proxima(estado)
    expect(estado.indice).toBe(2)
    expect(estado.estado).toBe('tocando')
    estado = proxima(estado)
    expect(estado.indice).toBe(2)
    expect(estado.estado).toBe('parado')
  })

  it('anterior volta e trava na primeira (sem wrap)', () => {
    let estado = tocarFila(playerInicial, FAIXAS, 2)
    estado = anterior(estado)
    expect(estado.indice).toBe(1)
    estado = anterior(estado)
    expect(estado.indice).toBe(0)
    estado = anterior(estado)
    expect(estado.indice).toBe(0)
    expect(estado.estado).toBe('tocando')
  })

  it('parar mantém fila e índice, só muda o estado', () => {
    const tocando = tocarFila(playerInicial, FAIXAS, 2)
    const estado = parar(tocando)
    expect(estado.estado).toBe('parado')
    expect(estado.fila).toHaveLength(3)
    expect(estado.indice).toBe(2)
  })

  it('pularPara clampa e volta a tocar', () => {
    const pausado = alternar(tocarFila(playerInicial, FAIXAS, 0))
    const estado = pularPara(pausado, 2)
    expect(estado.indice).toBe(2)
    expect(estado.estado).toBe('tocando')
    expect(pularPara(pausado, 99).indice).toBe(2)
  })
})

describe('modos', () => {
  it('cicloModo percorre sequência → repetir → aleatório → sequência', () => {
    let estado = playerInicial
    estado = cicloModo(estado)
    expect(estado.modo).toBe('repetir')
    estado = cicloModo(estado)
    expect(estado.modo).toBe('aleatorio')
    estado = cicloModo(estado)
    expect(estado.modo).toBe('sequencia')
  })

  it('fim da faixa em sequência vai para a próxima ou para na última', () => {
    const meio = fimDaFaixa({ ...tocarFila(playerInicial, FAIXAS, 0), modo: 'sequencia' })
    expect(meio.indice).toBe(1)
    expect(meio.estado).toBe('tocando')
    const fim = fimDaFaixa({ ...tocarFila(playerInicial, FAIXAS, 2), modo: 'sequencia' })
    expect(fim.indice).toBe(2)
    expect(fim.estado).toBe('parado')
  })

  it('fim da faixa em repetir toca a mesma de novo', () => {
    const estado = fimDaFaixa({ ...tocarFila(playerInicial, FAIXAS, 1), modo: 'repetir' })
    expect(estado.indice).toBe(1)
    expect(estado.estado).toBe('tocando')
  })

  it('fim da faixa em aleatório sorteia outra (nunca a atual)', () => {
    const estado = fimDaFaixa(
      { ...tocarFila(playerInicial, FAIXAS, 1), modo: 'aleatorio' },
      () => 0.99,
    )
    expect(estado.indice).toBe(2)
    expect(estado.estado).toBe('tocando')
    const soUma = fimDaFaixa(
      { ...tocarFila(playerInicial, [FAIXAS[1]!], 0), modo: 'aleatorio' },
      () => 0.0,
    )
    expect(soUma.indice).toBe(0)
  })

  it('fila vazia não muda no fim da faixa', () => {
    expect(fimDaFaixa(playerInicial)).toEqual(playerInicial)
  })
})
