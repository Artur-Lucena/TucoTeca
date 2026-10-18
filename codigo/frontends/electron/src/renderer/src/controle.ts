export interface EstadoPad {
  cima: boolean
  baixo: boolean
  a: boolean
  b: boolean
}

export type AcaoControle = 'cima' | 'baixo' | 'ativar' | 'voltar'

export interface OpcoesControle {
  primeiroAtrasoMs?: number
  repeticaoMs?: number
}

const SOLTO: EstadoPad = { cima: false, baixo: false, a: false, b: false }

/**
 * Leitor de gamepad com a semântica do desktop Qt: só o direcional repete
 * (primeiro atraso + intervalo), botões disparam uma vez por pressão e todo
 * pad recém-ligado (ou janela refocada) exige neutro antes de agir.
 */
export class LeitorControle {
  private readonly primeiroAtrasoMs: number
  private readonly repeticaoMs: number
  private exigeNeutro = false
  private antes: EstadoPad = { ...SOLTO }
  private direcao: 'cima' | 'baixo' | null = null
  private proximaEm = 0

  constructor(opcoes: OpcoesControle = {}) {
    this.primeiroAtrasoMs = opcoes.primeiroAtrasoMs ?? 350
    this.repeticaoMs = opcoes.repeticaoMs ?? 140
  }

  reiniciar(estado: EstadoPad): void {
    this.exigeNeutro = estado.cima || estado.baixo || estado.a || estado.b
    this.antes = { ...estado }
    this.direcao = null
    this.proximaEm = 0
  }

  avaliar(estado: EstadoPad, agoraMs: number): AcaoControle | null {
    if (this.exigeNeutro) {
      this.antes = { ...estado }
      if (estado.cima || estado.baixo || estado.a || estado.b) return null
      this.exigeNeutro = false
      return null
    }

    const acao = this.avaliarDirecoes(estado, agoraMs)
    const anterior = this.antes
    this.antes = { ...estado }
    if (acao !== null) return acao
    return this.avaliarBotoes(estado, anterior)
  }

  private avaliarDirecoes(estado: EstadoPad, agoraMs: number): AcaoControle | null {
    if (estado.cima && estado.baixo) {
      this.direcao = null
      return null
    }
    const solicitada = estado.cima ? 'cima' : estado.baixo ? 'baixo' : null
    if (this.direcao !== null && solicitada !== this.direcao) this.direcao = null
    if (this.direcao === null) {
      if (solicitada === null) return null
      if (solicitada === 'cima' ? this.antes.cima : this.antes.baixo) return null
      this.direcao = solicitada
      this.proximaEm = agoraMs + this.primeiroAtrasoMs
      return solicitada
    }
    if (agoraMs >= this.proximaEm) {
      this.proximaEm = agoraMs + this.repeticaoMs
      return this.direcao
    }
    return null
  }

  private avaliarBotoes(estado: EstadoPad, anterior: EstadoPad): AcaoControle | null {
    if (estado.a && !anterior.a) return 'ativar'
    if (estado.b && !anterior.b) return 'voltar'
    return null
  }
}
