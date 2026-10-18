export interface EventoTecla {
  key: string
  ctrlKey: boolean
  altKey: boolean
  shiftKey: boolean
  metaKey: boolean
}

const ESPECIAIS: Record<string, string> = {
  ' ': 'Space',
  ArrowUp: 'Up',
  ArrowDown: 'Down',
  ArrowLeft: 'Left',
  ArrowRight: 'Right',
  Escape: 'Escape',
  Enter: 'Enter',
  Tab: 'Tab',
  Backspace: 'Backspace',
  Delete: 'Delete',
  Home: 'Home',
  End: 'End',
  PageUp: 'PgUp',
  PageDown: 'PgDown',
}

const SIMPLES = /^[A-Za-z0-9]$/
const FUNCAO = /^F([1-9]|[12]\d|3[0-5])$/

function teclaNormalizada(key: string): string | null {
  if (ESPECIAIS[key] !== undefined) return ESPECIAIS[key]
  if (SIMPLES.test(key)) return key.toUpperCase()
  if (FUNCAO.test(key)) return key
  return null
}

/** Monta a combinação no formato do validador do núcleo (ex.: `Ctrl+Shift+K`). */
export function combinacao(evento: EventoTecla): string | null {
  const base = teclaNormalizada(evento.key)
  if (base === null) return null
  const partes: string[] = []
  if (evento.ctrlKey) partes.push('Ctrl')
  if (evento.altKey) partes.push('Alt')
  if (evento.shiftKey) partes.push('Shift')
  if (evento.metaKey) partes.push('Meta')
  return [...partes, base].join('+')
}

export type AcaoAtalho = { tipo: 'paleta' } | { tipo: 'secao'; chave: string }

const SECOES = [
  'inicio',
  'jogos',
  'musicas',
  'desejos',
  'downloads',
  'integracoes',
  'videos',
  'youtube',
]

/** Resolve uma combinação contra os atalhos pessoais (chave → combinação). */
export function acaoDoAtalho(
  comb: string | null,
  atalhos: Record<string, string>,
): AcaoAtalho | null {
  if (comb === null) return null
  for (const [acao, tecla] of Object.entries(atalhos)) {
    if (tecla !== comb) continue
    if (acao === 'paleta' || acao === 'buscar') return { tipo: 'paleta' }
    if (SECOES.includes(acao)) return { tipo: 'secao', chave: acao }
  }
  return null
}

export type DecisaoAtalho = AcaoAtalho | { tipo: 'fechar' } | null

/**
 * Regra do shell: com a paleta aberta, `Ctrl+K`/`Ctrl+F` fecham e atalhos de
 * seção são ignorados (o foco está no campo de busca).
 */
export function decidirAtalho(
  paletaAberta: boolean,
  comb: string | null,
  atalhos: Record<string, string>,
): DecisaoAtalho {
  const acao = acaoDoAtalho(comb, atalhos)
  if (paletaAberta) {
    return acao !== null && acao.tipo === 'paleta' ? { tipo: 'fechar' } : null
  }
  return acao
}
