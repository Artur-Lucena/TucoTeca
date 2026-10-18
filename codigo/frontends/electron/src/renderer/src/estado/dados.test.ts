import { beforeEach, describe, expect, it, vi } from 'vitest'
import { erroCarga, recarregar, saude, snapshot } from './dados'

const resposta = (metodo: string): unknown => {
  if (metodo === 'nucleo.snapshot') {
    return { jogos: [{ titulo: 'Hollow Knight' }], sistema: { jogos: 1 } }
  }
  if (metodo === 'nucleo.saude') {
    return { total: 1, pendentes: 1, ids_pendentes: [7], problemas: [], ok: 0 }
  }
  throw new Error(`método inesperado: ${metodo}`)
}

describe('dados', () => {
  beforeEach(() => {
    snapshot.value = null
    saude.value = null
    erroCarga.value = null
  })

  it('recarregar junta snapshot e saúde numa tacada', async () => {
    const chamar = vi.fn(async (metodo: string) => resposta(metodo))
    await recarregar(chamar)
    expect(chamar).toHaveBeenCalledWith('nucleo.snapshot')
    expect(chamar).toHaveBeenCalledWith('nucleo.saude')
    expect(snapshot.value?.jogos?.[0]?.titulo).toBe('Hollow Knight')
    expect(saude.value?.pendentes).toBe(1)
    expect(saude.value?.ids_pendentes).toEqual([7])
    expect(erroCarga.value).toBeNull()
  })

  it('falha mantém os dados anteriores e registra o erro', async () => {
    await recarregar(async (metodo: string) => resposta(metodo))
    await recarregar(async () => {
      throw new Error('ponte caiu')
    })
    expect(snapshot.value?.jogos?.[0]?.titulo).toBe('Hollow Knight')
    expect(saude.value?.pendentes).toBe(1)
    expect(erroCarga.value).toContain('ponte caiu')
  })

  it('sucesso depois de falha limpa o erro', async () => {
    await recarregar(async () => {
      throw new Error('ponte caiu')
    })
    await recarregar(async (metodo: string) => resposta(metodo))
    expect(erroCarga.value).toBeNull()
    expect(snapshot.value?.jogos?.[0]?.titulo).toBe('Hollow Knight')
  })
})
