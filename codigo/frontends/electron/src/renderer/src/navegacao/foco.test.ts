import { describe, expect, it } from 'vitest'
import { vizinho, type Retangulo } from './foco'

const r = (x: number, y: number, largura = 100, altura = 100): Retangulo => ({ x, y, largura, altura })

// grade 3×2 de cartões 100×100 com 20 px de espaço
const grade = [
  { item: 'a', ret: r(0, 0) },
  { item: 'b', ret: r(120, 0) },
  { item: 'c', ret: r(240, 0) },
  { item: 'd', ret: r(0, 120) },
  { item: 'e', ret: r(120, 120) },
  { item: 'f', ret: r(240, 120) },
]
const de = (nome: string) => grade.find((g) => g.item === nome)!.ret
const outros = (nome: string) => grade.filter((g) => g.item !== nome)

describe('vizinho (navegação espacial)', () => {
  it('anda em linha reta na grade', () => {
    expect(vizinho(de('a'), outros('a'), 'direita')).toBe('b')
    expect(vizinho(de('b'), outros('b'), 'baixo')).toBe('e')
    expect(vizinho(de('f'), outros('f'), 'esquerda')).toBe('e')
    expect(vizinho(de('e'), outros('e'), 'cima')).toBe('b')
  })

  it('na borda não há vizinho', () => {
    expect(vizinho(de('c'), outros('c'), 'direita')).toBeNull()
    expect(vizinho(de('a'), outros('a'), 'cima')).toBeNull()
  })

  it('prefere o alinhado ao mais perto na diagonal', () => {
    const atual = r(0, 0, 100, 40)
    const candidatos = [
      { item: 'diagonal', ret: r(110, 60, 100, 40) },
      { item: 'alinhado', ret: r(300, 0, 100, 40) },
    ]
    expect(vizinho(atual, candidatos, 'direita')).toBe('alinhado')
  })

  it('da barra lateral (alta e estreita) vai para o conteúdo à direita', () => {
    const lateral = r(0, 300, 200, 30)
    const conteudo = [
      { item: 'topo', ret: r(260, 20, 300, 30) },
      { item: 'meio', ret: r(260, 290, 150, 200) },
    ]
    expect(vizinho(lateral, conteudo, 'direita')).toBe('meio')
  })
})
