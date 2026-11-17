import { signal } from '@preact/signals'

/** Faixa da fila do player (mesma forma do item de `snapshot.musicas`). */
export interface Faixa {
  id?: number
  titulo?: string
  artista?: string
  album?: string
  musica_path?: string
  capa_url?: string
  [campo: string]: unknown
}

export type ModoPlayer = 'sequencia' | 'repetir' | 'aleatorio'

type EstadoFaixa = 'parado' | 'tocando' | 'pausado'

interface EstadoPlayer {
  fila: Faixa[]
  indice: number
  modo: ModoPlayer
  estado: EstadoFaixa
}

export const playerInicial: EstadoPlayer = {
  fila: [],
  indice: -1,
  modo: 'sequencia',
  estado: 'parado',
}

/** Faixa atual (null sem fila). */
export function faixaAtual(estado: EstadoPlayer): Faixa | null {
  return estado.fila[estado.indice] ?? null
}

/** Clampa um índice na fila (inválido cai em 0; fila vazia em -1). */
function clampar(fila: Faixa[], indice: unknown): number {
  if (fila.length === 0) return -1
  if (!Number.isInteger(indice)) return 0
  return Math.max(0, Math.min(fila.length - 1, Number(indice)))
}

/** Troca a fila, posiciona no índice e começa a tocar (fila vazia para tudo). */
export function tocarFila(estado: EstadoPlayer, faixas: Faixa[], indice = 0): EstadoPlayer {
  const fila = Array.isArray(faixas) ? faixas.slice() : []
  return { ...estado, fila, indice: clampar(fila, indice), estado: fila.length > 0 ? 'tocando' : 'parado' }
}

/** ▶/Ⅱ: alterna tocando ↔ pausado (parado retoma; sem fila não muda nada). */
export function alternar(estado: EstadoPlayer): EstadoPlayer {
  if (estado.fila.length === 0 || estado.indice < 0) return estado
  return { ...estado, estado: estado.estado === 'tocando' ? 'pausado' : 'tocando' }
}

/** ❯: próxima faixa; no fim da fila para (sem wrap). */
export function proxima(estado: EstadoPlayer): EstadoPlayer {
  if (estado.indice + 1 >= estado.fila.length) return { ...estado, estado: 'parado' }
  return { ...estado, indice: estado.indice + 1, estado: 'tocando' }
}

/** ❮: faixa anterior; travado na primeira (sem wrap). */
export function anterior(estado: EstadoPlayer): EstadoPlayer {
  if (estado.indice <= 0 || estado.fila.length === 0) return estado
  return { ...estado, indice: estado.indice - 1, estado: 'tocando' }
}

/** ■: para sem perder fila nem posição. */
export function parar(estado: EstadoPlayer): EstadoPlayer {
  return { ...estado, estado: 'parado' }
}

/** Vai direto para uma faixa da fila e toca. */
export function pularPara(estado: EstadoPlayer, indice: number): EstadoPlayer {
  const alvo = clampar(estado.fila, indice)
  if (alvo < 0) return estado
  return { ...estado, indice: alvo, estado: 'tocando' }
}

/** Modo cicla sequência → repetir → aleatório → sequência. */
export function cicloModo(estado: EstadoPlayer): EstadoPlayer {
  const modos: ModoPlayer[] = ['sequencia', 'repetir', 'aleatorio']
  const atual = modos.indexOf(estado.modo)
  return { ...estado, modo: modos[(atual + 1) % modos.length]! }
}

/** Índice sorteado diferente do atual (fila ≤ 1 mantém o atual). */
function indiceAleatorio(estado: EstadoPlayer, sorteio = Math.random): number {
  if (estado.fila.length <= 1) return estado.indice
  let alvo = estado.indice
  for (let tentativa = 0; tentativa < 20 && alvo === estado.indice; tentativa += 1) {
    alvo = Math.floor(sorteio() * estado.fila.length)
  }
  if (alvo === estado.indice) alvo = (estado.indice + 1) % estado.fila.length
  return Math.max(0, Math.min(estado.fila.length - 1, alvo))
}

/** Fim natural da faixa: repetir = mesma; aleatório = sorteia; sequência = próxima ou para. */
export function fimDaFaixa(estado: EstadoPlayer, sorteio = Math.random): EstadoPlayer {
  if (estado.fila.length === 0 || estado.indice < 0) return estado
  if (estado.modo === 'repetir') return { ...estado, estado: 'tocando' }
  if (estado.modo === 'aleatorio') {
    return { ...estado, indice: indiceAleatorio(estado, sorteio), estado: 'tocando' }
  }
  return proxima(estado)
}

/** Fila viva do rodapé (os componentes escrevem aqui via as ações puras). */
export const player = signal<EstadoPlayer>(playerInicial)
