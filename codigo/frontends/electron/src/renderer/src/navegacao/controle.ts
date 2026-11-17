export interface EstadoPad {
  cima: boolean
  baixo: boolean
  a: boolean
  b: boolean
  esquerda?: boolean
  direita?: boolean
  /** LB/RB: aba anterior/seguinte. */
  lb?: boolean
  rb?: boolean
  /** Start: busca (paleta). */
  start?: boolean
}

export type Direcao = 'cima' | 'baixo' | 'esquerda' | 'direita'
type AcaoControle = Direcao | 'ativar' | 'voltar' | 'aba-anterior' | 'aba-seguinte' | 'busca'

interface OpcoesControle {
  primeiroAtrasoMs?: number
  repeticaoMs?: number
}

const DIRECOES: Direcao[] = ['cima', 'baixo', 'esquerda', 'direita']
const BOTOES: Array<[keyof EstadoPad, AcaoControle]> = [
  ['a', 'ativar'],
  ['b', 'voltar'],
  ['lb', 'aba-anterior'],
  ['rb', 'aba-seguinte'],
  ['start', 'busca'],
]

const ligado = (e: EstadoPad, k: keyof EstadoPad) => e[k] === true

/**
 * Leitor de gamepad com a semântica do desktop Qt: só o direcional repete
 * (primeiro atraso + intervalo), botões disparam uma vez por pressão e todo
 * pad recém-ligado (ou janela refocada) exige neutro antes de agir.
 */
export class LeitorControle {
  private readonly primeiroAtrasoMs: number
  private readonly repeticaoMs: number
  private exigeNeutro = false
  private antes: EstadoPad = { cima: false, baixo: false, a: false, b: false }
  private direcao: Direcao | null = null
  private proximaEm = 0

  constructor(opcoes: OpcoesControle = {}) {
    this.primeiroAtrasoMs = opcoes.primeiroAtrasoMs ?? 350
    this.repeticaoMs = opcoes.repeticaoMs ?? 140
  }

  private algumLigado(estado: EstadoPad): boolean {
    return DIRECOES.some((d) => ligado(estado, d)) || BOTOES.some(([k]) => ligado(estado, k))
  }

  reiniciar(estado: EstadoPad): void {
    this.exigeNeutro = this.algumLigado(estado)
    this.antes = { ...estado }
    this.direcao = null
    this.proximaEm = 0
  }

  avaliar(estado: EstadoPad, agoraMs: number): AcaoControle | null {
    if (this.exigeNeutro) {
      this.antes = { ...estado }
      if (this.algumLigado(estado)) return null
      this.exigeNeutro = false
      return null
    }
    const acao = this.avaliarDirecoes(estado, agoraMs)
    const anterior = this.antes
    this.antes = { ...estado }
    if (acao !== null) return acao
    for (const [k, nome] of BOTOES) {
      if (ligado(estado, k) && !ligado(anterior, k)) return nome
    }
    return null
  }

  private avaliarDirecoes(estado: EstadoPad, agoraMs: number): Direcao | null {
    const pedidas = DIRECOES.filter((d) => ligado(estado, d))
    if (pedidas.length !== 1) {
      // nenhuma ou diagonal/opostas juntas: não anda (e rearma a repetição)
      this.direcao = null
      return null
    }
    const solicitada = pedidas[0]
    if (this.direcao !== null && solicitada !== this.direcao) this.direcao = null
    if (this.direcao === null) {
      if (ligado(this.antes, solicitada)) return null // já estava apertada (ex.: saiu de uma diagonal)
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
}
