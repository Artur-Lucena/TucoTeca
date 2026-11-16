import { signal } from '@preact/signals'

/**
 * Roteador por hash, sem dependência: `#/jogos/desejos`, `#/jogo/12`.
 *
 * Seções da barra lateral e suas abas (a primeira é a padrão e some da URL).
 * As chaves antigas (`desejos`, `integracoes`, `videos`, `youtube`,
 * `notificacoes`) continuam valendo como apelidos — atalhos pessoais e links
 * internos não quebram.
 */
export const ABAS: Record<string, string[]> = {
  inicio: [],
  jogos: ['biblioteca', 'desejos'],
  midia: ['videos', 'youtube'],
  musicas: [],
  downloads: [],
  configuracoes: ['geral', 'integracoes'],
  notificacoes: [],
}

/** Abas da página do jogo (`#/jogo/12/conquistas`); a primeira é a padrão. */
export const ABAS_JOGO = ['visao', 'conquistas', 'emulacao', 'saves', 'manutencao', 'editar']

export const NOMES_ABAS: Record<string, string> = {
  visao: 'Visão geral',
  conquistas: 'Conquistas',
  emulacao: 'Emulação',
  saves: 'Saves',
  manutencao: 'Manutenção',
  editar: 'Editar',
  biblioteca: 'Biblioteca',
  desejos: 'Desejos',
  videos: 'Vídeos',
  youtube: 'YouTube',
  geral: 'Geral',
  integracoes: 'Integrações',
}

const APELIDOS: Record<string, string> = {
  desejos: '#/jogos/desejos',
  integracoes: '#/configuracoes/integracoes',
  videos: '#/midia/videos',
  youtube: '#/midia/youtube',
}

export interface Rota {
  secao: string
  aba: string
  /** `#/jogo/:id[/aba]` → página do jogo (a seção marcada continua Jogos). */
  jogo: number | null
}

const INICIO: Rota = { secao: 'inicio', aba: '', jogo: null }

/** Hash (ou chave de seção/apelido) → rota válida; o que não se reconhece vira Início. */
export function analisar(entrada: string): Rota {
  let bruto = String(entrada ?? '').trim()
  if (!bruto.startsWith('#')) bruto = APELIDOS[bruto] ?? `#/${bruto}`
  const partes = bruto.replace(/^#\/?/, '').split('/').filter(Boolean)
  const [primeira = 'inicio', segunda = ''] = partes
  if (primeira === 'jogo') {
    const id = Number(segunda)
    const aba = ABAS_JOGO.includes(partes[2] ?? '') ? (partes[2] as string) : ABAS_JOGO[0]
    return Number.isInteger(id) && id > 0 ? { secao: 'jogos', aba, jogo: id } : { ...INICIO }
  }
  if (APELIDOS[primeira] !== undefined && partes.length === 1) return analisar(APELIDOS[primeira])
  const abas = ABAS[primeira]
  if (abas === undefined) return { ...INICIO }
  const aba = abas.includes(segunda) ? segunda : (abas[0] ?? '')
  return { secao: primeira, aba, jogo: null }
}

/** Rota → hash canônico (aba padrão omitida). */
export function formatar(rota: Rota): string {
  if (rota.jogo !== null) {
    return rota.aba === '' || rota.aba === ABAS_JOGO[0] ? `#/jogo/${rota.jogo}` : `#/jogo/${rota.jogo}/${rota.aba}`
  }
  const padrao = ABAS[rota.secao]?.[0] ?? ''
  return rota.aba === '' || rota.aba === padrao ? `#/${rota.secao}` : `#/${rota.secao}/${rota.aba}`
}

/** Chave usada pelas regras antigas (busca da seção, atalhos): `jogos/desejos` → `desejos`. */
export function chaveLegada(rota: Rota): string {
  if (rota.jogo !== null) return 'jogo' // sem busca própria: Ctrl+F abre a paleta
  if (rota.secao === 'jogos' && rota.aba === 'desejos') return 'desejos'
  if (rota.secao === 'midia') return rota.aba
  if (rota.secao === 'configuracoes' && rota.aba === 'integracoes') return 'integracoes'
  return rota.secao
}

// ---------------------------------------------------------------- histórico
export interface Historico {
  pilha: string[]
  posicao: number
}

export type AcaoHistorico =
  | { tipo: 'ir'; hash: string }
  | { tipo: 'voltar' }
  | { tipo: 'avancar' }
  /** O hash mudou por fora (link, digitação): se não é o atual, conta como `ir`. */
  | { tipo: 'externo'; hash: string }

const LIMITE = 50

export function reduzirHistorico(h: Historico, acao: AcaoHistorico): Historico {
  if (acao.tipo === 'voltar') return h.posicao > 0 ? { ...h, posicao: h.posicao - 1 } : h
  if (acao.tipo === 'avancar') return h.posicao < h.pilha.length - 1 ? { ...h, posicao: h.posicao + 1 } : h
  const hash = formatar(analisar(acao.hash))
  if (h.pilha[h.posicao] === hash) return h
  const pilha = [...h.pilha.slice(0, h.posicao + 1), hash].slice(-LIMITE)
  return { pilha, posicao: pilha.length - 1 }
}

export const podeVoltar = (h: Historico) => h.posicao > 0
export const podeAvancar = (h: Historico) => h.posicao < h.pilha.length - 1

// ---------------------------------------------------------------- estado vivo
function hashAtual(): string {
  return typeof location === 'undefined' ? '#/inicio' : location.hash || '#/inicio'
}

const inicial = formatar(analisar(hashAtual()))
export const historico = signal<Historico>({ pilha: [inicial], posicao: 0 })
export const rota = signal<Rota>(analisar(inicial))

function aplicar(novo: Historico) {
  historico.value = novo
  const hash = novo.pilha[novo.posicao] ?? '#/inicio'
  rota.value = analisar(hash)
  if (typeof location !== 'undefined' && location.hash !== hash) location.hash = hash
}

/** Navega para um hash, seção ou apelido (`'jogos'`, `'desejos'`, `'#/jogo/3'`). */
export function ir(destino: string): void {
  aplicar(reduzirHistorico(historico.value, { tipo: 'ir', hash: destino }))
}

export function voltar(): void {
  aplicar(reduzirHistorico(historico.value, { tipo: 'voltar' }))
}

export function avancar(): void {
  aplicar(reduzirHistorico(historico.value, { tipo: 'avancar' }))
}

/** Liga o roteador ao `hashchange` da janela (uma vez, no App). */
export function escutarHash(): () => void {
  const aoMudar = () => {
    const h = historico.value
    if (h.pilha[h.posicao] === location.hash) return
    aplicar(reduzirHistorico(h, { tipo: 'externo', hash: location.hash }))
  }
  window.addEventListener('hashchange', aoMudar)
  if (location.hash !== historico.value.pilha[0]) history.replaceState(null, '', historico.value.pilha[0])
  return () => window.removeEventListener('hashchange', aoMudar)
}
