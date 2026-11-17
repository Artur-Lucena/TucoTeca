import { beforeEach, describe, expect, it, vi } from 'vitest'
import { atualizar, erroCarga, partesMudadas, recarregar, revisoes, saude, snapshot } from './dados'

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

describe('atualizar (só o que mudou)', () => {
  beforeEach(() => {
    snapshot.value = null
    saude.value = null
    erroCarga.value = null
    revisoes.value = null
  })

  it('compara contadores por categoria', () => {
    expect(partesMudadas(null, { jogos: 1 })).toBeNull()
    expect(partesMudadas({ jogos: 1, musicas: 2, downloads: 0 }, { jogos: 1, musicas: 3, downloads: 1 })).toEqual([
      'musicas',
      'fila_musicas',
    ])
  })

  it('sem base recarrega tudo; depois pede só as partes mudadas', async () => {
    let rev = { jogos: 1, musicas: 1, desejos: 1, videos: 1, downloads: 1 }
    const chamar = vi.fn(async (metodo: string, params?: Record<string, unknown>) => {
      if (metodo === 'nucleo.revisao') return rev
      if (metodo === 'nucleo.snapshot' && params === undefined) return resposta(metodo)
      if (metodo === 'nucleo.snapshot') return { musicas: [{ titulo: 'Nova' }], sistema: { jogos: 1, musicas: 1 } }
      return resposta(metodo)
    })
    await atualizar(chamar)
    expect(chamar).toHaveBeenCalledWith('nucleo.snapshot')
    expect(revisoes.value).toEqual(rev)
    chamar.mockClear()
    rev = { ...rev, musicas: 2 }
    await atualizar(chamar)
    expect(chamar).toHaveBeenCalledWith('nucleo.snapshot', { partes: ['musicas'] })
    expect(chamar).not.toHaveBeenCalledWith('nucleo.saude')
    expect(snapshot.value?.jogos?.[0]?.titulo).toBe('Hollow Knight')
    expect(snapshot.value?.musicas?.[0]?.titulo).toBe('Nova')
    expect(revisoes.value?.musicas).toBe(2)
  })
})
