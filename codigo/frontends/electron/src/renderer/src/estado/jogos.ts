import type { JogoResumo } from '../derivacoes'

/** Filtros da tela Jogos (mesmos nomes do Qt; `pendencias` usa a saúde da coleção). */
export const FILTROS_JOGOS = [
  'todos',
  'favoritos',
  'jogando',
  'PC',
  '3DS',
  'NDS',
  'pendencias',
] as const

export type FiltroJogo = (typeof FILTROS_JOGOS)[number]

export const ORDENS_JOGOS = ['titulo', 'recentes', 'horas'] as const

export type OrdemJogo = (typeof ORDENS_JOGOS)[number]

export interface JogoDaLista extends JogoResumo {
  id?: number
  plataforma?: string
  status?: string
  favorito?: boolean
  etiquetas?: string
  etiquetas_lista?: string[]
}

export interface OpcoesFiltroJogos {
  filtro?: FiltroJogo
  busca?: string
  idsPendentes?: number[]
}

/** Minúsculas sem acento — mesma tolerância da busca do Qt (NFD sem diacríticos). */
export function semAcento(texto: unknown): string {
  return String(texto ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
}

function etiquetasDe(jogo: JogoDaLista): string {
  if (Array.isArray(jogo.etiquetas_lista)) return jogo.etiquetas_lista.join(' ')
  return String(jogo.etiquetas ?? '')
}

/**
 * Aplica filtro e busca. A busca exige todas as palavras (sem acento) em
 * título/etiquetas/plataforma — como o `_filtrar` do qt_bridge.
 */
export function filtrarJogos(
  jogos: JogoDaLista[] | undefined,
  opcoes: OpcoesFiltroJogos = {},
): JogoDaLista[] {
  const lista = jogos ?? []
  const filtro = opcoes.filtro ?? 'todos'
  const pendentes = new Set(opcoes.idsPendentes ?? [])
  let itens = lista
  if (filtro === 'favoritos') itens = lista.filter((jogo) => jogo.favorito === true)
  else if (filtro === 'jogando') itens = lista.filter((jogo) => jogo.status === 'jogando')
  else if (filtro === 'PC' || filtro === '3DS' || filtro === 'NDS') {
    itens = lista.filter((jogo) => jogo.plataforma === filtro)
  } else if (filtro === 'pendencias') {
    itens = lista.filter((jogo) => pendentes.has(Number(jogo.id)))
  }
  const palavras = semAcento(opcoes.busca).split(/\s+/).filter(Boolean)
  if (palavras.length === 0) return [...itens]
  return itens.filter((jogo) => {
    const alvo = semAcento(
      [jogo.titulo, etiquetasDe(jogo), jogo.plataforma].map((valor) => String(valor ?? '')).join(' '),
    )
    return palavras.every((palavra) => alvo.includes(palavra))
  })
}

/** Ordena sem mexer na lista original; empates caem no título (sem acento). */
export function ordenarJogos(jogos: JogoDaLista[], ordem: OrdemJogo): JogoDaLista[] {
  const copia = [...jogos]
  const porTitulo = (a: JogoDaLista, b: JogoDaLista) =>
    semAcento(a.titulo).localeCompare(semAcento(b.titulo)) ||
    String(a.titulo ?? '').localeCompare(String(b.titulo ?? ''))
  if (ordem === 'recentes') {
    copia.sort(
      (a, b) =>
        String(b.ultima_execucao ?? '').localeCompare(String(a.ultima_execucao ?? '')) ||
        porTitulo(a, b),
    )
  } else if (ordem === 'horas') {
    copia.sort((a, b) => Number(b.horas ?? 0) - Number(a.horas ?? 0) || porTitulo(a, b))
  } else {
    copia.sort(porTitulo)
  }
  return copia
}
