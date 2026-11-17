import type { JogoResumo } from './derivacoes'
import { semAcento } from './formato'

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

interface OpcoesFiltroJogos {
  filtro?: FiltroJogo
  busca?: string
  idsPendentes?: number[]
}

function etiquetasDe(jogo: JogoDaLista): string {
  if (Array.isArray(jogo.etiquetas_lista)) return jogo.etiquetas_lista.join(' ')
  return String(jogo.etiquetas ?? '')
}

/**
 * Aplica filtro e busca. A busca exige todas as palavras (sem acento) em
 * título/etiquetas/plataforma (mesma regra do antigo filtro do desktop Qt).
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

/** Status de jogo do núcleo (mesma lista do formulário do Qt). */
export const STATUS_JOGOS = ['backlog', 'jogando', 'zerado', 'pausado', 'abandonado'] as const

/** Limites de etiqueta do núcleo (`banco/jogos.py`): 30 chars, 20 etiquetas. */
const ETIQUETA_MAX = 30
const ETIQUETAS_MAX = 20

function numeroNaFaixa(texto: unknown, minimo: number, maximo: number): number | null {
  if (typeof texto === 'number') {
    return Number.isFinite(texto) && texto >= minimo && texto <= maximo ? texto : null
  }
  const bruto = String(texto ?? '').trim().replace(',', '.')
  if (bruto === '' || !/^-?\d+(\.\d+)?$/.test(bruto)) return null
  const valor = Number(bruto)
  return Number.isFinite(valor) && valor >= minimo && valor <= maximo ? valor : null
}

/** Nota do formulário: inteiro 0–10 (o núcleo recusa decimal em `banco/jogos.py`). */
export function validarNota(texto: unknown): number | null {
  const valor = numeroNaFaixa(texto, 0, 10)
  return valor !== null && Number.isInteger(valor) ? valor : null
}

/** Horas registradas na mão: número finito > 0 (aceita vírgula). */
export function validarHoras(texto: unknown): number | null {
  if (typeof texto === 'number') {
    return Number.isFinite(texto) && texto > 0 ? texto : null
  }
  const bruto = String(texto ?? '').trim().replace(',', '.')
  if (bruto === '' || !/^\d+(\.\d+)?$/.test(bruto)) return null
  const valor = Number(bruto)
  return Number.isFinite(valor) && valor > 0 ? valor : null
}

/** Espelha `normalizar_etiquetas` do núcleo: split, dedup casefold, ordem e limites. */
export function normalizarEtiquetas(valor: unknown): string {
  const partes = Array.isArray(valor) ? valor : [valor]
  const vistas = new Map<string, string>()
  for (const parte of partes) {
    for (const bruta of String(parte ?? '').split(/[;,]+/)) {
      let etiqueta = bruta.replace(/\u0000/g, '').trim().replace(/\s+/g, ' ')
      if (etiqueta === '') continue
      etiqueta = etiqueta.slice(0, ETIQUETA_MAX).trim()
      if (etiqueta === '') continue
      const chave = etiqueta.toLocaleLowerCase()
      if (!vistas.has(chave)) vistas.set(chave, etiqueta)
      if (vistas.size >= ETIQUETAS_MAX) break
    }
  }
  return [...vistas.values()]
    .sort((a, b) => a.toLocaleLowerCase().localeCompare(b.toLocaleLowerCase()))
    .join(', ')
}
