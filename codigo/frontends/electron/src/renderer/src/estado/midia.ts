import { signal } from '@preact/signals'
import { hojeISO, semAcento } from './formato'

/** Arquivo aberto no player interno (o App desenha o player por cima de tudo). */
export const reproduzindo = signal<number | null>(null)

export interface Progresso {
  posicao: number
  duracao: number
  assistido: boolean
}

export interface TituloResumo {
  imdb_id: string
  tipo: 'movie' | 'series'
  nome: string
  ano: string
  poster: string
  arquivos?: number
  assistido?: boolean
  assistidos?: number
  adicionado?: string | null
}

export interface Episodio {
  chave: string
  temporada: number
  episodio: number
  nome: string
  estreia: string
  resumo: string
  miniatura: string
  arquivo: number | null
  progresso: Progresso | null
}

export interface Temporada {
  numero: number
  episodios: Episodio[]
}

export interface TituloCompleto extends Omit<TituloResumo, 'arquivos'> {
  fundo: string
  logo: string
  descricao: string
  generos: string[]
  nota: string
  duracao: string
  na_lista: boolean
  seguindo: boolean
  /** Filme: arquivos no disco (séries usam `temporadas`). */
  arquivos?: Array<{ id: number; caminho: string }>
  temporadas?: Temporada[]
  progresso?: Progresso | null
}

export type FiltroTipo = 'todos' | 'movie' | 'series'

/** "T1E02" curto para listas. */
export function rotuloEpisodio(temporada: number, episodio: number): string {
  return temporada === 0 ? `Especial ${episodio}` : `T${temporada}E${String(episodio).padStart(2, '0')}`
}

/** 0–1 do quanto já foi visto (assistido = 1). */
export function fracao(p: Progresso | null | undefined): number {
  if (p === null || p === undefined) return 0
  if (p.assistido) return 1
  return p.duracao > 0 ? Math.min(1, Math.max(0, p.posicao / p.duracao)) : 0
}

/** Biblioteca local filtrada por tipo e termo (sem acento/caixa). */
export function filtrarTitulos<T extends TituloResumo>(titulos: T[], tipo: FiltroTipo, termo: string): T[] {
  const q = semAcento(termo.trim())
  return titulos.filter((t) => (tipo === 'todos' || t.tipo === tipo) && (q === '' || semAcento(t.nome).includes(q)))
}

/** Episódio para o botão principal da série: o primeiro no disco ainda não visto (ou o 1º no disco). */
export function proximoParaAssistir(temporadas: Temporada[] | undefined): Episodio | null {
  const noDisco = (temporadas ?? []).filter((t) => t.numero > 0).flatMap((t) => t.episodios).filter((e) => e.arquivo !== null)
  return noDisco.find((e) => !(e.progresso?.assistido ?? false)) ?? noDisco[0] ?? null
}

export interface GrupoCalendario<T> {
  rotulo: string
  itens: T[]
}

/** Agrupa episódios por dia com rótulos "Hoje", "Amanhã", "Ontem" ou a data. */
export function agruparPorDia<T extends { data: string }>(itens: T[], hoje: Date = new Date()): GrupoCalendario<T>[] {
  const dia = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  const somar = (n: number) => dia(new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate() + n))
  const nomes: Record<string, string> = { [somar(0)]: 'Hoje', [somar(1)]: 'Amanhã', [somar(-1)]: 'Ontem' }
  const grupos: GrupoCalendario<T>[] = []
  for (const item of itens) {
    const chave = item.data.slice(0, 10)
    const [a, m, d] = chave.split('-')
    const rotulo = nomes[chave] ?? `${d}/${m}/${a}`
    const ultimo = grupos.at(-1)
    if (ultimo !== undefined && ultimo.rotulo === rotulo) ultimo.itens.push(item)
    else grupos.push({ rotulo, itens: [item] })
  }
  return grupos
}

/** Chaves de todos os episódios de uma temporada (para "marcar temporada como vista"). */
export function chavesDaTemporada(t: Temporada, apenasLancados = true, hoje: Date = new Date()): string[] {
  const limite = hojeISO(hoje)
  return t.episodios.filter((e) => !apenasLancados || (e.estreia !== '' && e.estreia <= limite) || e.arquivo !== null).map((e) => e.chave)
}
