export interface PedidoPonte {
  id: number
  metodo: string
  params?: Record<string, unknown>
}

export interface RespostaPonte {
  id: number | null
  ok: boolean
  resultado?: unknown
  erro?: string
}

export interface EventoPonte {
  evento: string
  dados?: unknown
}

export interface ModuloDTO {
  chave: string
  nome: string
  descricao: string
  icone: string
  ordem: number
}
