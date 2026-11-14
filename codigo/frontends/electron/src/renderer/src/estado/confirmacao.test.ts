import { describe, expect, it } from 'vitest'
import { confirmar, pedidoConfirmacao, responderConfirmacao } from './confirmacao'

describe('confirmar', () => {
  it('abre um pedido e resolve com a resposta', async () => {
    const promessa = confirmar({ titulo: 'Remover', texto: 'Sem desfazer.', perigo: true })
    expect(pedidoConfirmacao.value?.titulo).toBe('Remover')
    responderConfirmacao(true)
    await expect(promessa).resolves.toBe(true)
    expect(pedidoConfirmacao.value).toBeNull()
  })

  it('um pedido novo cancela o anterior', async () => {
    const primeiro = confirmar({ titulo: 'A', texto: '' })
    const segundo = confirmar({ titulo: 'B', texto: '' })
    await expect(primeiro).resolves.toBe(false)
    expect(pedidoConfirmacao.value?.titulo).toBe('B')
    responderConfirmacao(false)
    await expect(segundo).resolves.toBe(false)
  })

  it('responder sem pedido não quebra', () => {
    expect(() => responderConfirmacao(true)).not.toThrow()
  })
})
