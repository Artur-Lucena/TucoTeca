import type { JogoDaLista } from './jogos'
import { horas as formatarHoras, relativo } from './formato'
import { ABAS_JOGO } from './rota'

interface ConquistaRetro {
  id: number
  titulo: string
  descricao: string
  pontos: number
  ganha_em: string
  hardcore: boolean
}

interface RetroProgresso {
  id: string
  titulo: string
  console: string
  total: number
  ganhas: number
  pontos_total: number
  pontos_ganhos: number
  conquistas: ConquistaRetro[]
}

interface MetaJogo {
  steam_appid: string
  sgdb_id: string
  retro_id: string
  resumo: string
  descricao: string
  generos: string[]
  desenvolvedora: string
  publicadora: string
  lancamento: string
  site: string
  hero_url: string
  logo_url: string
  icone_url: string
  screenshots_urls: string[]
  hltb: { principal: number; extra: number; completo: number } | null
  retro: RetroProgresso | null
  fontes: Record<string, string>
  travado: string[]
}

export interface ProvedorMeta {
  chave: string
  nome: string
  descricao: string
  ligado: boolean
  precisa_credencial: boolean
  configurado: boolean
}

export interface PaginaJogo {
  jogo: JogoDaLista
  meta: MetaJogo
  provedores: ProvedorMeta[]
  enriquecido: boolean
}

const texto = (v: unknown) => (typeof v === 'string' ? v : '')
const numero = (v: unknown) => (Number.isFinite(Number(v)) ? Number(v) : 0)
const textos = (v: unknown) => (Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [])

function normalizarRetro(v: unknown): RetroProgresso | null {
  if (v === null || typeof v !== 'object') return null
  const r = v as Record<string, unknown>
  const conquistas = Array.isArray(r.conquistas)
    ? r.conquistas
        .filter((c): c is Record<string, unknown> => c !== null && typeof c === 'object')
        .map((c) => ({
          id: numero(c.id),
          titulo: texto(c.titulo),
          descricao: texto(c.descricao),
          pontos: numero(c.pontos),
          ganha_em: texto(c.ganha_em),
          hardcore: c.hardcore === true,
        }))
    : []
  return {
    id: texto(r.id),
    titulo: texto(r.titulo),
    console: texto(r.console),
    total: numero(r.total) || conquistas.length,
    ganhas: numero(r.ganhas),
    pontos_total: numero(r.pontos_total),
    pontos_ganhos: numero(r.pontos_ganhos),
    conquistas,
  }
}

/** Resposta de `jogo.pagina` → formato estável (campos ausentes viram vazios). */
export function normalizarPagina(bruto: unknown): PaginaJogo {
  const r = (bruto ?? {}) as Record<string, unknown>
  const m = (r.meta ?? {}) as Record<string, unknown>
  const hltb = m.hltb !== null && typeof m.hltb === 'object' ? (m.hltb as Record<string, unknown>) : null
  return {
    jogo: (r.jogo ?? {}) as JogoDaLista,
    meta: {
      steam_appid: texto(m.steam_appid),
      sgdb_id: texto(m.sgdb_id),
      retro_id: texto(m.retro_id),
      resumo: texto(m.resumo),
      descricao: texto(m.descricao),
      generos: textos(m.generos),
      desenvolvedora: texto(m.desenvolvedora),
      publicadora: texto(m.publicadora),
      lancamento: texto(m.lancamento),
      site: texto(m.site),
      hero_url: texto(m.hero_url),
      logo_url: texto(m.logo_url),
      icone_url: texto(m.icone_url),
      screenshots_urls: textos(m.screenshots_urls),
      hltb: hltb === null ? null : { principal: numero(hltb.principal), extra: numero(hltb.extra), completo: numero(hltb.completo) },
      retro: normalizarRetro(m.retro),
      fontes: m.fontes !== null && typeof m.fontes === 'object' ? (m.fontes as Record<string, string>) : {},
      travado: textos(m.travado),
    },
    provedores: Array.isArray(r.provedores) ? (r.provedores as ProvedorMeta[]) : [],
    enriquecido: r.enriquecido === true,
  }
}

interface Metrica {
  rotulo: string
  valor: string
}

/** Números do topo da página: horas, última vez, conquistas e HLTB (só os que existem). */
export function metricasDoJogo(pagina: PaginaJogo, agora: Date = new Date()): Metrica[] {
  const { jogo, meta } = pagina
  const saida: Metrica[] = [{ rotulo: 'Jogado', valor: formatarHoras(Number(jogo.horas ?? 0)) }]
  const ultima = String(jogo.ultima_execucao ?? '')
  saida.push({ rotulo: 'Última vez', valor: ultima !== '' ? relativo(ultima, agora) || '—' : 'nunca' })
  if (meta.retro !== null && meta.retro.total > 0) {
    saida.push({ rotulo: 'Conquistas', valor: `${meta.retro.ganhas}/${meta.retro.total}` })
  }
  if (meta.hltb !== null && meta.hltb.principal > 0) {
    saida.push({ rotulo: 'Para zerar', valor: formatarHoras(meta.hltb.principal) })
  }
  return saida
}

/** Abas visíveis: Emulação só para jogos de 3DS (onde o painel funciona). */
export function abasDoJogo(jogo: JogoDaLista): string[] {
  const emulado = String(jogo.plataforma ?? '') === '3DS' || String(jogo.launch_options ?? '').trim() !== ''
  return ABAS_JOGO.filter((aba) => aba !== 'emulacao' || emulado)
}

/** Linha "Steam · SteamGridDB, há 3 dias" sobre de onde vieram os dados. */
export function origemDosDados(pagina: PaginaJogo, agora: Date = new Date()): string {
  const nomes = new Map(pagina.provedores.map((p) => [p.chave, p.nome]))
  const entradas = Object.entries(pagina.meta.fontes)
  if (entradas.length === 0) return ''
  const maisNova = entradas.map(([, quando]) => quando).sort().at(-1) ?? ''
  const lista = entradas.map(([chave]) => nomes.get(chave) ?? chave).join(' · ')
  return `${lista}${maisNova !== '' ? `, ${relativo(maisNova, agora)}` : ''}`
}
