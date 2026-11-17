import { describe, expect, it } from 'vitest'
import { LeitorControle, type EstadoPad } from './controle'

const pad = (parcial: Partial<EstadoPad> = {}): EstadoPad => ({
  cima: false,
  baixo: false,
  a: false,
  b: false,
  ...parcial,
})
const solto = pad()

describe('LeitorControle', () => {
  it('dispara na pressão e só o direcional repete', () => {
    const leitor = new LeitorControle({ primeiroAtrasoMs: 350, repeticaoMs: 140 })
    leitor.reiniciar(solto)
    leitor.avaliar(solto, 0)
    expect(leitor.avaliar(pad({ cima: true }), 100)).toBe('cima')
    expect(leitor.avaliar(pad({ cima: true }), 300)).toBeNull()
    expect(leitor.avaliar(pad({ cima: true }), 450)).toBe('cima')
    expect(leitor.avaliar(pad({ cima: true }), 590)).toBe('cima')
    expect(leitor.avaliar(pad({ a: true }), 600)).toBe('ativar')
    expect(leitor.avaliar(pad({ a: true }), 900)).toBeNull()
  })

  it('rearma a repetição ao soltar e não dispara com direções juntas', () => {
    const leitor = new LeitorControle({ primeiroAtrasoMs: 350, repeticaoMs: 140 })
    leitor.reiniciar(solto)
    expect(leitor.avaliar(pad({ baixo: true }), 0)).toBe('baixo')
    leitor.avaliar(solto, 50)
    expect(leitor.avaliar(pad({ baixo: true }), 60)).toBe('baixo')
    expect(leitor.avaliar(pad({ cima: true, baixo: true }), 500)).toBeNull()
  })

  it('b vira voltar uma vez por pressão', () => {
    const leitor = new LeitorControle()
    leitor.reiniciar(solto)
    expect(leitor.avaliar(pad({ b: true }), 0)).toBe('voltar')
    expect(leitor.avaliar(pad({ b: true }), 100)).toBeNull()
    leitor.avaliar(solto, 120)
    expect(leitor.avaliar(pad({ b: true }), 140)).toBe('voltar')
  })

  it('esquerda/direita repetem como cima/baixo; diagonal não anda', () => {
    const leitor = new LeitorControle({ primeiroAtrasoMs: 350, repeticaoMs: 140 })
    leitor.reiniciar(solto)
    expect(leitor.avaliar(pad({ direita: true }), 0)).toBe('direita')
    expect(leitor.avaliar(pad({ direita: true }), 400)).toBe('direita')
    leitor.avaliar(solto, 450)
    expect(leitor.avaliar(pad({ esquerda: true }), 460)).toBe('esquerda')
    leitor.avaliar(solto, 470)
    expect(leitor.avaliar(pad({ cima: true, direita: true }), 480)).toBeNull()
  })

  it('LB/RB trocam de aba e Start abre a busca, uma vez por pressão', () => {
    const leitor = new LeitorControle()
    leitor.reiniciar(solto)
    expect(leitor.avaliar(pad({ rb: true }), 0)).toBe('aba-seguinte')
    expect(leitor.avaliar(pad({ rb: true }), 100)).toBeNull()
    expect(leitor.avaliar(pad({ lb: true }), 200)).toBe('aba-anterior')
    leitor.avaliar(solto, 300)
    expect(leitor.avaliar(pad({ start: true }), 400)).toBe('busca')
  })

  it('pad recém-ligado exige neutro antes de qualquer ação (hotplug/foco)', () => {
    const leitor = new LeitorControle()
    leitor.reiniciar(pad({ cima: true }))
    expect(leitor.avaliar(pad({ cima: true }), 100)).toBeNull()
    expect(leitor.avaliar(solto, 200)).toBeNull()
    expect(leitor.avaliar(pad({ cima: true }), 300)).toBe('cima')
  })
})
