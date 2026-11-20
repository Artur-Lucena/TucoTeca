import { arquivoBaixado } from './downloads'
import type { Trabalho } from './trabalhos'

/** Resposta de `app.verificar_atualizacao`. */
export interface Verificacao {
  atual: string
  ultima: string
  nova: boolean
  notas: string
  pagina: string
  publicada_em: string
  instalador: { nome: string; url: string; tamanho: number; sha256: string } | null
}

export function resumoDaVerificacao(v: Verificacao): string {
  if (!v.nova) return `Você está na versão mais recente (${v.atual}).`
  const data = /^(\d{4})-(\d{2})-(\d{2})$/.exec(v.publicada_em)
  return `TucoTeca ${v.ultima} disponível${data ? ` desde ${data[3]}/${data[2]}/${data[1]}` : ''} (você tem a ${v.atual}).`
}

/** O download de atualização mais recente desta sessão (rodando ou terminado), se houver. */
export function downloadDaAtualizacao(lista: Trabalho[]): Trabalho | null {
  const daAtualizacao = lista.filter((t) => t.escopo === 'atualizacao')
  return daAtualizacao[daAtualizacao.length - 1] ?? null
}

/** Instalador pronto para abrir (download terminado e conferido). */
export function instaladorPronto(lista: Trabalho[]): string {
  const t = downloadDaAtualizacao(lista)
  return t === null ? '' : arquivoBaixado(t)
}
