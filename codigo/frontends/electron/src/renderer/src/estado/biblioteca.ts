import type { JogoResumo } from '../derivacoes'
import { semAcento } from './jogos'

/** Recorte da biblioteca lateral (à la Hydra): todos, favoritos ou jogados recentemente. */
export type ModoBiblioteca = 'todos' | 'favoritos' | 'recentes'

export interface ItemBiblioteca {
  id: number
  titulo: string
  capa_url: string
  favorito: boolean
}

const RECENTES = 12

function eFavorito(jogo: JogoResumo): boolean {
  const f = jogo.favorito
  return f === true || f === 1 || f === '1'
}

/**
 * Lista da barra lateral: filtra pelo termo (sem acento/caixa) e pelo modo.
 * `todos`/`favoritos` em ordem alfabética (pt-BR); `recentes` pela última
 * execução, só os que já rodaram.
 */
export function itensBiblioteca(
  jogos: JogoResumo[] | undefined,
  termo: string,
  modo: ModoBiblioteca,
): ItemBiblioteca[] {
  const q = semAcento(String(termo ?? '').trim())
  let lista = (jogos ?? []).filter((j) => {
    const id = Number(j.id)
    if (!Number.isInteger(id) || id <= 0 || String(j.titulo ?? '').trim() === '') return false
    return q === '' || semAcento(j.titulo).includes(q)
  })
  if (modo === 'favoritos') lista = lista.filter(eFavorito)
  if (modo === 'recentes') {
    lista = lista
      .filter((j) => String(j.ultima_execucao ?? '').trim() !== '')
      .sort((a, b) => String(b.ultima_execucao).localeCompare(String(a.ultima_execucao)))
      .slice(0, RECENTES)
  } else {
    lista = [...lista].sort((a, b) =>
      String(a.titulo).localeCompare(String(b.titulo), 'pt-BR', { sensitivity: 'base' }),
    )
  }
  return lista.map((j) => ({
    id: Number(j.id),
    titulo: String(j.titulo),
    capa_url: String(j.capa_url ?? ''), // file:// do núcleo; a vista passa por imagemUrl
    favorito: eFavorito(j),
  }))
}

export interface Janela {
  inicio: number
  fim: number
  /** Espaço (px) acima e abaixo dos itens desenhados. */
  antes: number
  depois: number
}

/** Virtualização simples de lista com itens de altura fixa. */
export function janelaVisivel(
  total: number,
  alturaItem: number,
  rolagem: number,
  alturaVisivel: number,
  folga = 6,
): Janela {
  if (total <= 0 || alturaItem <= 0) return { inicio: 0, fim: 0, antes: 0, depois: 0 }
  const primeiro = Math.floor(Math.max(0, rolagem) / alturaItem)
  const cabem = Math.ceil(Math.max(0, alturaVisivel) / alturaItem)
  const inicio = Math.min(total, Math.max(0, primeiro - folga))
  const fim = Math.min(total, primeiro + cabem + folga)
  return { inicio, fim, antes: inicio * alturaItem, depois: (total - fim) * alturaItem }
}
