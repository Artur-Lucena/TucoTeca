export interface JogoResumo {
  titulo?: string
  capa_url?: string
  horas?: number
  ultima_execucao?: string
  [campo: string]: unknown
}

export interface SistemaResumo {
  jogos?: number
  musicas?: number
  desejos?: number
  downloads?: number
  pendentes?: number
  backup?: string
  disco_livre_gb?: number
  [campo: string]: unknown
}

export interface Snapshot {
  jogos?: JogoResumo[]
  musicas?: JogoResumo[]
  desejos?: JogoResumo[]
  sistema?: SistemaResumo
  [campo: string]: unknown
}

/** Cartões de "Continuar jogando": recentes primeiro, completa pelos mais jogados. */
export function continuarJogando(jogos: JogoResumo[] | undefined, limite = 6): JogoResumo[] {
  const validos = (jogos ?? []).filter((jogo) => String(jogo.titulo ?? '').trim() !== '')
  const recentes: JogoResumo[] = []
  const semHistorico: JogoResumo[] = []
  for (const jogo of validos) {
    if (String(jogo.ultima_execucao ?? '').trim() !== '') recentes.push(jogo)
    else semHistorico.push(jogo)
  }
  const porRecencia = [...recentes].sort(
    (a, b) => String(b.ultima_execucao).localeCompare(String(a.ultima_execucao)) || porHoras(a, b),
  )
  return [...porRecencia, ...[...semHistorico].sort(porHoras)].slice(0, limite)
}

function porHoras(a: JogoResumo, b: JogoResumo): number {
  return Number(b.horas ?? 0) - Number(a.horas ?? 0)
}
