import { afterEach, describe, expect, it, vi } from 'vitest'
import { EventEmitter } from 'node:events'
import { PassThrough } from 'node:stream'
import type { RespostaPonte } from '../shared/protocolo'
import {
  ClientePonte,
  Pendentes,
  SeparadorLinhas,
  ambientePonte,
  descobrirPython,
  type FabricaProcesso,
} from './ponte'

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

  it('Linux x64 usa o runtime embutido do AppImage; sem ele, python3', () => {
    const r = descobrirPython('/raiz', { env: {}, plataforma: 'linux', arquitetura: 'x64', existe: () => true })
    expect(r.comando.replaceAll('\\', '/')).toBe('/raiz/programa/linux-x64/python/bin/python3')
    const semRuntime = descobrirPython('/raiz', { env: {}, plataforma: 'linux', arquitetura: 'x64', existe: () => false })
    expect(semRuntime).toEqual({ comando: 'python3', prefixo: [] })
    const arm = descobrirPython('/raiz', { env: {}, plataforma: 'linux', arquitetura: 'arm64', existe: () => true })
    expect(arm).toEqual({ comando: 'python3', prefixo: [] })
  })

  it('macOS: runtime embutido da arquitetura do processo', () => {
    const vistos: string[] = []
    const existe = (caminho: string) => {
      vistos.push(caminho.replaceAll('\\', '/'))
      return caminho.includes('macos-arm64')
    }
    const r = descobrirPython('/app/tucoteca', { env: {}, plataforma: 'darwin', arquitetura: 'arm64', existe })
    expect(r.comando.replaceAll('\\', '/')).toBe('/app/tucoteca/programa/macos-arm64/python/bin/python3')
    const intel = descobrirPython('/app/tucoteca', { env: {}, plataforma: 'darwin', arquitetura: 'x64', existe })
    expect(intel).toEqual({ comando: 'python3', prefixo: [] })
    expect(vistos.at(-1)).toBe('/app/tucoteca/programa/macos-x64/python/bin/python3')
  })
})

describe('ambientePonte', () => {
  it('macOS: Homebrew entra no PATH (app aberto pelo Finder tem PATH mínimo)', () => {
    const env = ambientePonte({ PATH: '/usr/bin:/bin' }, 'darwin')
    expect(env.PATH).toBe('/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin')
    expect(env.PYTHONIOENCODING).toBe('utf-8')
    expect(ambientePonte({ PATH: '/opt/homebrew/bin:/usr/bin' }, 'darwin').PATH).toBe(
      '/usr/local/bin:/opt/homebrew/bin:/usr/bin',
    )
  })

  it('Windows e Linux: PATH intacto', () => {
    expect(ambientePonte({ PATH: 'C:\\Windows' }, 'win32').PATH).toBe('C:\\Windows')
    expect(ambientePonte({ PATH: '/usr/bin' }, 'linux').PATH).toBe('/usr/bin')
  })
})

class ProcessoFake extends EventEmitter {
  stdout = new PassThrough()
  stderr = new PassThrough()
  stdin = new PassThrough()
  pid = 4242
  respondido: string[] = []
  constructor() {
    super()
    this.stdin.on('data', (pedaco: Buffer) => this.respondido.push(pedaco.toString('utf8')))
  }
  responder(objeto: unknown): void {
    this.stdout.write(`${JSON.stringify(objeto)}\n`)
  }
  sair(codigo: number): void {
    this.emit('exit', codigo)
  }
  kill(): boolean {
    return true
  }
}

function clienteComFake() {
  const processo = new ProcessoFake()
  const cliente = new ClientePonte(
    { raiz: 'C:/raiz' },
    { criarProcesso: (() => processo) as unknown as FabricaProcesso },
  )
  cliente.iniciar()
  return { processo, cliente }
}

describe('ClientePonte — queda e rejeição', () => {
  it('rejeita chamadas pendentes e avisa quando o processo morre', async () => {
    const { processo, cliente } = clienteComFake()
    const encerrou: unknown[] = []
    cliente.aoEncerrar((info) => encerrou.push(info))
    const pendente = cliente.chamar('nucleo.ping')
    expect(processo.respondido[0]).toContain('"nucleo.ping"')
    processo.sair(1)
    await expect(pendente).rejects.toThrow('encerrou')
    expect(encerrou).toEqual([{ codigo: 1, erro: undefined }])
    await expect(cliente.chamar('nucleo.ping')).rejects.toThrow('não iniciada')
  })

  it('resposta fora de ordem resolve por id; id órfão é ignorado', async () => {
    const { processo, cliente } = clienteComFake()
    const primeira = cliente.chamar('a')
    const segunda = cliente.chamar('b')
    processo.responder({ id: 2, ok: true, resultado: 'B' })
    processo.responder({ id: 1, ok: true, resultado: 'A' })
    processo.responder({ id: 99, ok: true, resultado: 'órfã' })
    await expect(primeira).resolves.toBe('A')
    await expect(segunda).resolves.toBe('B')
  })
})
