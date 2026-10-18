import { signal } from '@preact/signals'
import type { Snapshot } from '../derivacoes'

export interface SaudeColecao {
  total?: number
  pendentes?: number
  ids_pendentes?: number[]
  ok?: number
  problemas?: Array<{ id?: number; titulo?: string; motivo?: string }>
}

export type Chamar = (metodo: string, params?: Record<string, unknown>) => Promise<unknown>

/** Coleção e saúde da ponte, compartilhadas entre as vistas (recarregáveis). */
export const snapshot = signal<Snapshot | null>(null)
export const saude = signal<SaudeColecao | null>(null)
export const erroCarga = signal<string | null>(null)

function chamarDaPonte(metodo: string, params?: Record<string, unknown>): Promise<unknown> {
  return window.tucoteca.chamar(metodo, params)
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
  }
}
