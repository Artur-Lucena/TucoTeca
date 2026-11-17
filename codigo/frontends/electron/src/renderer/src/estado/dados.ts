import { signal } from '@preact/signals'
import type { Snapshot } from './derivacoes'

interface SaudeColecao {
  total?: number
  pendentes?: number
  ids_pendentes?: number[]
  ok?: number
  problemas?: Array<{ id?: number; titulo?: string; motivo?: string }>
}

type Chamar = (metodo: string, params?: Record<string, unknown>) => Promise<unknown>

/** Contadores por categoria do núcleo (`nucleo.revisao`). */
type Revisoes = Record<string, number>

/** Coleção e saúde da ponte, compartilhadas entre as vistas (recarregáveis). */
export const snapshot = signal<Snapshot | null>(null)
export const saude = signal<SaudeColecao | null>(null)
export const erroCarga = signal<string | null>(null)
export const revisoes = signal<Revisoes | null>(null)

function chamarDaPonte(metodo: string, params?: Record<string, unknown>): Promise<unknown> {
  return window.tucoteca.chamar(metodo, params)
}

async function lerRevisoes(chamar: Chamar): Promise<Revisoes | null> {
  try {
    const r = await chamar('nucleo.revisao')
    return r !== null && typeof r === 'object' ? (r as Revisoes) : null
  } catch {
    return null // núcleo antigo/sem contador: o próximo `atualizar` recarrega tudo
  }
}

/**
 * Recarrega snapshot + saúde numa tacada. Em falha, mantém o que já tinha e
 * só registra o erro (`erroCarga`) — o shell decide o que mostrar.
 */
export async function recarregar(chamar: Chamar = chamarDaPonte): Promise<void> {
  try {
    const [novoSnapshot, novaSaude] = await Promise.all([
      chamar('nucleo.snapshot'),
      chamar('nucleo.saude'),
    ])
    snapshot.value = novoSnapshot as Snapshot
    saude.value = novaSaude as SaudeColecao
    erroCarga.value = null
  } catch (falha) {
    erroCarga.value = String(falha)
    return
  }
  revisoes.value = await lerRevisoes(chamar)
}

/** Categoria do contador → parte do snapshot. */
const PARTE_DA_CATEGORIA: Record<string, string> = {
  jogos: 'jogos',
  musicas: 'musicas',
  desejos: 'desejos',
  videos: 'videos',
  downloads: 'fila_musicas',
  colecoes: 'colecoes',
}

/** Partes do snapshot cujas categorias mudaram; `null` = sem base, recarregar tudo. */
export function partesMudadas(antes: Revisoes | null, depois: Revisoes | null): string[] | null {
  if (antes === null || depois === null) return null
  const partes: string[] = []
  for (const [categoria, parte] of Object.entries(PARTE_DA_CATEGORIA)) {
    if (antes[categoria] !== depois[categoria]) partes.push(parte)
  }
  return partes
}

/**
 * Depois de uma ação: pergunta ao núcleo o que mudou e recarrega só essas
 * listas (o resumo `sistema` vem sempre; a saúde, só se os jogos mudaram).
 */
export async function atualizar(chamar: Chamar = chamarDaPonte): Promise<void> {
  const nova = await lerRevisoes(chamar)
  const partes = partesMudadas(revisoes.value, nova)
  if (partes === null || snapshot.value === null) {
    await recarregar(chamar)
    return
  }
  try {
    const parcial = (await chamar('nucleo.snapshot', { partes })) as Snapshot
    snapshot.value = { ...snapshot.value, ...parcial }
    if (partes.includes('jogos')) saude.value = (await chamar('nucleo.saude')) as SaudeColecao
    revisoes.value = nova
    erroCarga.value = null
  } catch (falha) {
    erroCarga.value = String(falha)
  }
}
