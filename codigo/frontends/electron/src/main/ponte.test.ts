import { afterEach, describe, expect, it, vi } from 'vitest'
import type { RespostaPonte } from '../shared/protocolo'
import { Pendentes, SeparadorLinhas, descobrirPython } from './ponte'

describe('SeparadorLinhas', () => {
  it('junta pedaço partido no meio da linha', () => {
    const separador = new SeparadorLinhas()
    expect(separador.empurrar('{"id":1,')).toEqual([])
    expect(separador.empurrar('"ok":true}\n')).toEqual(['{"id":1,"ok":true}'])
  })

  it('devolve várias linhas de um pedaço e remove o CR', () => {
    const separador = new SeparadorLinhas()
    expect(separador.empurrar('a\r\nb\nc')).toEqual(['a', 'b'])
    expect(separador.empurrar('\n')).toEqual(['c'])
  })

  it('pedaço vazio não gera linha', () => {
    expect(new SeparadorLinhas().empurrar('')).toEqual([])
  })
})

function esperar(pendentes: Pendentes, id: number, ms = 1000): Promise<RespostaPonte> {
  return new Promise((resolver, rejeitar) => pendentes.registrar(id, resolver, rejeitar, ms))
}

describe('Pendentes', () => {
  afterEach(() => vi.useRealTimers())

  it('resolve respostas fora de ordem', async () => {
    const pendentes = new Pendentes()
    const um = esperar(pendentes, 1)
    const dois = esperar(pendentes, 2)
    expect(pendentes.responder({ id: 2, ok: true, resultado: 'b' })).toBe(true)
    expect(pendentes.responder({ id: 1, ok: true, resultado: 'a' })).toBe(true)
    await expect(dois).resolves.toMatchObject({ resultado: 'b' })
    await expect(um).resolves.toMatchObject({ resultado: 'a' })
  })

  it('id desconhecido ou sem id é ignorado', () => {
    const pendentes = new Pendentes()
    expect(pendentes.responder({ id: 99, ok: true })).toBe(false)
    expect(pendentes.responder({ id: null, ok: true })).toBe(false)
  })

  it('erro do serviço rejeita com a mensagem', async () => {
    const pendentes = new Pendentes()
    const promessa = esperar(pendentes, 3)
    pendentes.responder({ id: 3, ok: false, erro: 'falhou de propósito' })
    await expect(promessa).rejects.toThrow('falhou de propósito')
  })

  it('timeout rejeita a espera', async () => {
    vi.useFakeTimers()
    const pendentes = new Pendentes()
    const promessa = esperar(pendentes, 4, 50).catch((erro: Error) => erro)
    vi.advanceTimersByTime(51)
    const erro = await promessa
    expect(erro).toBeInstanceOf(Error)
    expect((erro as Error).message).toContain('sem resposta')
    expect(pendentes.tamanho).toBe(0)
  })

  it('rejeitarTudo derruba todas as esperas', async () => {
    const pendentes = new Pendentes()
    const um = esperar(pendentes, 1).catch((erro: Error) => erro)
    const dois = esperar(pendentes, 2).catch((erro: Error) => erro)
    pendentes.rejeitarTudo('ponte encerrou')
    expect(await um).toMatchObject({ message: 'ponte encerrou' })
    expect(await dois).toMatchObject({ message: 'ponte encerrou' })
    expect(pendentes.tamanho).toBe(0)
  })
})

describe('descobrirPython', () => {
  it('TUCOTECA_PYTHON manda em tudo', () => {
    const r = descobrirPython('C:/raiz', {
      env: { TUCOTECA_PYTHON: 'C:/py/python.exe' },
      existe: () => true,
      plataforma: 'win32',
    })
    expect(r).toEqual({ comando: 'C:/py/python.exe', prefixo: [] })
  })

  it('win32 usa o runtime embutido quando existe', () => {
    const r = descobrirPython('C:/raiz', {
      env: {},
      plataforma: 'win32',
      existe: (caminho) => caminho.includes('windows-x64'),
    })
    expect(r.comando).toContain('windows-x64')
    expect(r.comando.endsWith('python.exe')).toBe(true)
    expect(r.prefixo).toEqual([])
  })

  it('win32 sem runtime cai no lançador py -3.14', () => {
    const r = descobrirPython('C:/raiz', { env: {}, plataforma: 'win32', existe: () => false })
    expect(r).toEqual({ comando: 'py', prefixo: ['-3.14'] })
  })

  it('outras plataformas usam python3', () => {
    const r = descobrirPython('/raiz', { env: {}, plataforma: 'linux', existe: () => true })
    expect(r).toEqual({ comando: 'python3', prefixo: [] })
  })
})
