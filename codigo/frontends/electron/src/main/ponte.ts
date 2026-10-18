import { spawn } from 'node:child_process'
import type { ChildProcess } from 'node:child_process'
import { existsSync } from 'node:fs'
import { join } from 'node:path'
import type { EventoPonte, PedidoPonte, RespostaPonte } from '../shared/protocolo'

export interface DepsDescoberta {
  existe: (caminho: string) => boolean
  plataforma: NodeJS.Platform
  env: Record<string, string | undefined>
}

/** Ordem: TUCOTECA_PYTHON → runtime embutido do entregável → lançador do sistema. */
export function descobrirPython(
  raiz: string,
  deps?: Partial<DepsDescoberta>,
): { comando: string; prefixo: string[] } {
  const { existe = existsSync, plataforma = process.platform, env = process.env } = deps ?? {}
  const configurado = env.TUCOTECA_PYTHON?.trim()
  if (configurado) return { comando: configurado, prefixo: [] }
  if (plataforma === 'win32') {
    const embutido = join(raiz, 'programa', 'windows-x64', 'python', 'python.exe')
    if (existe(embutido)) return { comando: embutido, prefixo: [] }
    return { comando: 'py', prefixo: ['-3.14'] }
  }
  return { comando: 'python3', prefixo: [] }
}

/** Acumula pedaços de stdout e devolve só linhas completas (NDJSON). */
export class SeparadorLinhas {
  private resto = ''

  empurrar(pedaco: string): string[] {
    const texto = this.resto + pedaco
    const linhas = texto.split('\n')
    this.resto = linhas.pop() ?? ''
    return linhas.map((linha) => (linha.endsWith('\r') ? linha.slice(0, -1) : linha))
  }
}

interface Espera {
  resolver: (resposta: RespostaPonte) => void
  rejeitar: (erro: Error) => void
  timer: ReturnType<typeof setTimeout>
}

/** Esperas por id: respostas podem chegar fora de ordem; id órfão é ignorado. */
export class Pendentes {
  private mapa = new Map<number, Espera>()
  private sequencia = 0

  proximoId(): number {
    this.sequencia += 1
    return this.sequencia
  }

  registrar(
    id: number,
    resolver: (resposta: RespostaPonte) => void,
    rejeitar: (erro: Error) => void,
    ms: number,
  ): void {
    const timer = setTimeout(() => {
      this.mapa.delete(id)
      rejeitar(new Error(`sem resposta em ${ms} ms (id ${id})`))
    }, ms)
    this.mapa.set(id, { resolver, rejeitar, timer })
  }

  responder(resposta: RespostaPonte): boolean {
    const id = typeof resposta.id === 'number' ? resposta.id : null
    if (id === null) return false
    const espera = this.mapa.get(id)
    if (!espera) return false
    clearTimeout(espera.timer)
    this.mapa.delete(id)
    if (resposta.ok) espera.resolver(resposta)
    else espera.rejeitar(new Error(resposta.erro ?? 'erro desconhecido na ponte'))
    return true
  }

  rejeitarTudo(motivo: string): void {
    for (const espera of this.mapa.values()) {
      clearTimeout(espera.timer)
      espera.rejeitar(new Error(motivo))
    }
    this.mapa.clear()
  }

  get tamanho(): number {
    return this.mapa.size
  }
}

export interface OpcoesPonte {
  raiz: string
  db?: string
  ignorarLock?: boolean
  timeoutMs?: number
}

/** Processo filho Python + protocolo NDJSON por stdin/stdout. */
export class ClientePonte {
  private processo: ChildProcess | null = null
  private pendentes = new Pendentes()
  private separador = new SeparadorLinhas()
  private ouvintesEvento = new Set<(evento: string, dados: unknown) => void>()
  private ouvintesEncerrada = new Set<(info: { codigo: number | null; erro?: Error }) => void>()
  private encerrandoPedido = false
  private readonly timeoutMs: number
  private readonly opcoes: OpcoesPonte

  constructor(opcoes: OpcoesPonte) {
    this.opcoes = opcoes
    this.timeoutMs = opcoes.timeoutMs ?? 30000
  }

  get finalizando(): boolean {
    return this.encerrandoPedido
  }

  get encerrado(): boolean {
    return this.processo === null
  }

  iniciar(): void {
    const { comando, prefixo } = descobrirPython(this.opcoes.raiz)
    const args = [...prefixo, '-B', join(this.opcoes.raiz, 'codigo', 'frontends', 'ponte.py')]
    if (this.opcoes.db) args.push('--db', this.opcoes.db)
    if (this.opcoes.ignorarLock) args.push('--ignorar-lock')
    const processo = spawn(comando, args, {
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1', PYTHONIOENCODING: 'utf-8' },
      stdio: ['pipe', 'pipe', 'pipe'],
    })
    this.processo = processo

    processo.stdout?.setEncoding('utf-8')
    processo.stdout?.on('data', (pedaco: string) => {
      for (const linha of this.separador.empurrar(pedaco)) this.recebeLinha(linha)
    })
    processo.stderr?.setEncoding('utf-8')
    processo.stderr?.on('data', (pedaco: string) => process.stderr.write(pedaco))
    processo.on('error', (erro) => this.encerrou(null, erro))
    processo.on('exit', (codigo) => this.encerrou(codigo))
  }

  chamar<T = unknown>(metodo: string, params?: Record<string, unknown>): Promise<T> {
    const processo = this.processo
    if (!processo || !processo.stdin) return Promise.reject(new Error('ponte não iniciada'))
    const id = this.pendentes.proximoId()
    const pedido: PedidoPonte = { id, metodo, ...(params === undefined ? {} : { params }) }
    return new Promise<T>((resolver, rejeitar) => {
      this.pendentes.registrar(
        id,
        (resposta) => resolver(resposta.resultado as T),
        rejeitar,
        this.timeoutMs,
      )
      processo.stdin?.write(`${JSON.stringify(pedido)}\n`)
    })
  }

  aoEvento(ouvinte: (evento: string, dados: unknown) => void): () => void {
    this.ouvintesEvento.add(ouvinte)
    return () => {
      this.ouvintesEvento.delete(ouvinte)
    }
  }

  aoEncerrar(ouvinte: (info: { codigo: number | null; erro?: Error }) => void): () => void {
    this.ouvintesEncerrada.add(ouvinte)
    return () => {
      this.ouvintesEncerrada.delete(ouvinte)
    }
  }

  private recebeLinha(linha: string): void {
    if (!linha.trim()) return
    let mensagem: unknown
    try {
      mensagem = JSON.parse(linha)
    } catch {
      return // lixo no stdout não derruba o cliente
    }
    if (mensagem === null || typeof mensagem !== 'object') return
    const campos = mensagem as Partial<EventoPonte> & Partial<RespostaPonte>
    if (typeof campos.evento === 'string') {
      for (const ouvinte of [...this.ouvintesEvento]) ouvinte(campos.evento, campos.dados)
      return
    }
    if (typeof campos.ok === 'boolean') this.pendentes.responder(campos as RespostaPonte)
  }

  private encerrou(codigo: number | null, erro?: Error): void {
    if (this.processo === null) return
    this.processo = null
    const motivo = erro
      ? `a ponte não iniciou: ${erro.message}`
      : `a ponte encerrou (código ${codigo ?? '?'})`
    this.pendentes.rejeitarTudo(motivo)
    for (const ouvinte of [...this.ouvintesEncerrada]) ouvinte({ codigo, erro })
  }

  async encerrar(): Promise<number | null> {
    const processo = this.processo
    if (!processo) return null
    this.encerrandoPedido = true
    return await new Promise<number | null>((resolver) => {
      const limite = setTimeout(() => {
        matarProcesso(processo)
      }, 3000)
      processo.once('exit', (codigo) => {
        clearTimeout(limite)
        resolver(codigo)
      })
      try {
        processo.stdin?.end()
      } catch {
        // stdin já fechou
      }
    })
  }
}

function matarProcesso(processo: ChildProcess): void {
  if (process.platform === 'win32' && processo.pid) {
    try {
      spawn('taskkill', ['/pid', String(processo.pid), '/t', '/f'])
    } catch {
      // já morreu
    }
    return
  }
  try {
    processo.kill('SIGKILL')
  } catch {
    // já morreu
  }
}
