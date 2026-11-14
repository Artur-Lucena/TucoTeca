import { signal } from '@preact/signals'

export interface OpcoesConfirmacao {
  titulo: string
  texto: string
  /** Rótulo do botão de confirmar (padrão "Confirmar"). */
  confirmar?: string
  /** Ação destrutiva: botão vermelho e foco inicial em Cancelar. */
  perigo?: boolean
}

export interface PedidoConfirmacao extends OpcoesConfirmacao {
  resolver: (ok: boolean) => void
}

/** Pedido em aberto (o `ConfirmacaoHost` no App desenha o modal). */
export const pedidoConfirmacao = signal<PedidoConfirmacao | null>(null)

/**
 * Substitui `window.confirm`: diálogo do app, assíncrono. Um pedido novo
 * cancela o anterior (responde `false`), nunca deixa promessa pendurada.
 */
export function confirmar(opcoes: OpcoesConfirmacao): Promise<boolean> {
  return new Promise((resolver) => {
    pedidoConfirmacao.value?.resolver(false)
    pedidoConfirmacao.value = { ...opcoes, resolver }
  })
}

/** Fecha o pedido atual com a resposta dada (sem pedido, não faz nada). */
export function responderConfirmacao(ok: boolean): void {
  const atual = pedidoConfirmacao.value
  if (atual === null) return
  pedidoConfirmacao.value = null
  atual.resolver(ok)
}
