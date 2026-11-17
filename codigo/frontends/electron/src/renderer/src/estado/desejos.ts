import { moeda, semAcento } from './formato'

/** Item de desejo vindo do snapshot (`listar_desejos`); campos extras passam. */
interface DesejoResumo {
  id?: number
  appid?: string | number
  titulo?: string
  [campo: string]: unknown
}

/** Preço do cache Steam (`precos_steam`): centavos e moeda ISO. */
export interface PrecoSteam {
  appid?: string
  gratis?: boolean
  moeda?: string
  final?: number
  inicial?: number
  desconto_pct?: number
  [campo: string]: unknown
}

/** Centavos → "R$ 19,99 (-50%)"; código desconhecido sai prefixado; vazio sem dado. */
export function formatarPreco(preco: PrecoSteam | null | undefined): string {
  if (!preco || typeof preco !== 'object') return ''
  if (preco.gratis === true) return 'Grátis'
  const centavos = Number(preco.final)
  if (!Number.isFinite(centavos)) return ''
  const valor = moeda(centavos, String(preco.moeda ?? ''))
  const pct = Number(preco.desconto_pct ?? 0)
  return Number.isFinite(pct) && pct > 0 ? `${valor} (-${pct}%)` : valor
}

/** Busca local espelhando `listar_desejos` (só título, sem acento/caixa). */
export function filtrarDesejos<T extends DesejoResumo>(lista: T[], busca: string): T[] {
  const q = semAcento(String(busca ?? '').trim())
  if (q === '') return lista
  return lista.filter((d) => semAcento(String(d.titulo ?? '')).includes(q))
}

/** appid da Steam: só dígitos, espelhando `core.adicionar_desejo`. */
export function validarAppid(valor: string): string | null {
  const texto = String(valor ?? '').trim()
  return /^\d{1,20}$/.test(texto) ? null : 'appid deve ser um número (ex.: 504230)'
}

export function validarTituloDesejo(valor: string): string | null {
  return String(valor ?? '').trim() === '' ? 'título é obrigatório' : null
}
