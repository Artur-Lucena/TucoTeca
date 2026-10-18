import { signal } from '@preact/signals'

/** Estado de um trabalho da ponte (`Trabalhos` do `ponte.py`). */
export type EstadoTrabalho = 'rodando' | 'cancelando' | 'ok' | 'erro' | 'cancelado'

export type MotivoTrabalho = 'inicio' | 'progresso' | 'cancelamento' | 'fim'

export interface Trabalho {
  id: number
  rotulo: string
  estado: EstadoTrabalho
  pct: number | null
  cancelavel: boolean
  escopo?: string | null
  iniciado_em?: string
  aviso?: string
  erro?: string
  detalhe?: Record<string, unknown>
}

/** Evento `trabalho` da ponte: o trabalho público + o motivo do evento. */
export interface EventoTrabalho extends Trabalho {
  motivo: MotivoTrabalho
}

/** Upsert por id preservando a ordem de criação (igual ao `trabalhos.listar`). */
export function reduzirTrabalhos(lista: Trabalho[], evento: EventoTrabalho): Trabalho[] {
  const { motivo, ...trabalho } = evento
  void motivo
  const indice = lista.findIndex((item) => item.id === trabalho.id)
  if (indice === -1) return [...lista, trabalho]
  const copia = [...lista]
  copia[indice] = trabalho
  return copia
}

/** O trabalho de jogo ainda ativo (só existe um por vez — regra da ponte). */
export function jogoEmAndamento(lista: Trabalho[]): Trabalho | null {
  return (
    lista.find(
      (item) =>
        item.escopo === 'jogo' && (item.estado === 'rodando' || item.estado === 'cancelando'),
    ) ?? null
  )
}

/** Lista viva dos trabalhos (os eventos da ponte alimentam este signal). */
export const listaTrabalhos = signal<Trabalho[]>([])

export function aplicarEventoTrabalho(evento: EventoTrabalho): void {
  listaTrabalhos.value = reduzirTrabalhos(listaTrabalhos.value, evento)
}
