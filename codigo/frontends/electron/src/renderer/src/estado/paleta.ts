export interface ItemBusca {
  tipo: string
  id: unknown
  titulo: string
  sub?: string
  capa_url?: string
}

export interface EstadoPaleta {
  aberta: boolean
  termo: string
  carregando: boolean
  itens: ItemBusca[]
  selecionado: number
}

export const paletaInicial: EstadoPaleta = {
  aberta: false,
  termo: '',
  carregando: false,
  itens: [],
  selecionado: 0,
}

export type EventoPaleta =
  | { tipo: 'abrir' }
  | { tipo: 'fechar' }
  | { tipo: 'alternar' }
  | { tipo: 'digitou'; termo: string }
  | { tipo: 'resultados'; termo: string; itens: ItemBusca[] }
  | { tipo: 'cima' }
  | { tipo: 'baixo' }
  | { tipo: 'selecionar'; indice: number }

function prender(indice: number, total: number): number {
  if (!Number.isFinite(indice) || indice < 0) return 0
  if (total <= 0) return 0
  return Math.min(Math.trunc(indice), total - 1)
}

export function reduzirPaleta(estado: EstadoPaleta, evento: EventoPaleta): EstadoPaleta {
  switch (evento.tipo) {
    case 'abrir':
      return { ...paletaInicial, aberta: true }
    case 'fechar':
      return { ...paletaInicial }
    case 'alternar':
      return estado.aberta ? { ...paletaInicial } : { ...paletaInicial, aberta: true }
    case 'digitou':
      return { ...estado, termo: evento.termo, carregando: true, itens: [], selecionado: 0 }
    case 'resultados': {
      if (evento.termo !== estado.termo) return estado
      return {
        ...estado,
        carregando: false,
        itens: evento.itens,
        selecionado: prender(estado.selecionado, evento.itens.length),
      }
    }
    case 'cima': {
      const total = estado.itens.length
      if (total === 0) return estado
      return { ...estado, selecionado: (estado.selecionado - 1 + total) % total }
    }
    case 'baixo': {
      const total = estado.itens.length
      if (total === 0) return estado
      return { ...estado, selecionado: (estado.selecionado + 1) % total }
    }
    case 'selecionar':
      return { ...estado, selecionado: prender(evento.indice, estado.itens.length) }
  }
}
