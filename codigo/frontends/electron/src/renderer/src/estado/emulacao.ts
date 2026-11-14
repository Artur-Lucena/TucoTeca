import type { FiltroArquivo } from '../../../shared/api'

/** Estado de emulação de um jogo 3DS (`emulacao.jogo` da ponte). */
export interface EstadoEmulacao {
  id: number
  titulo: string
  tid: string
  erro: string
  mods: Array<{ nome: string; ativo: boolean }>
  mods_off: boolean
  cheats: Array<{ nome: string; ativo: boolean; linhas?: number }>
  textura: { instalado: boolean; ativo: boolean; arquivos: number; mb?: number }
  presets: string[]
}

/** Item de `emulacao.status` / `emulacao.consultar`. */
export interface EmuladorStatus {
  chave: string
  nome: string
  local: string
  tag: string
  atualizado: boolean | null
  tamanho_mb?: number
  info?: Record<string, unknown>
}

export const FILTROS_PACOTE: FiltroArquivo[] = [
  { nome: 'Pacotes (zip, 7z, rar)', extensoes: ['zip', '7z', 'rar'] },
]

/** Normaliza o retorno da ponte (campos ausentes viram vazios seguros). */
export function normalizarEmulacao(bruto: unknown): EstadoEmulacao {
  const r = (bruto ?? {}) as Partial<EstadoEmulacao>
  const textura = (r.textura ?? {}) as Partial<EstadoEmulacao['textura']>
  return {
    id: Number(r.id ?? 0),
    titulo: String(r.titulo ?? ''),
    tid: String(r.tid ?? ''),
    erro: String(r.erro ?? ''),
    mods: Array.isArray(r.mods)
      ? r.mods.map((m) => ({ nome: String(m?.nome ?? ''), ativo: m?.ativo === true }))
      : [],
    mods_off: r.mods_off === true,
    cheats: Array.isArray(r.cheats)
      ? r.cheats.map((c) => ({ nome: String(c?.nome ?? ''), ativo: c?.ativo === true, linhas: Number(c?.linhas ?? 0) }))
      : [],
    textura: {
      instalado: textura.instalado === true,
      ativo: textura.ativo === true,
      arquivos: Number(textura.arquivos ?? 0),
      mb: Number(textura.mb ?? 0),
    },
    presets: Array.isArray(r.presets) ? r.presets.map(String) : [],
  }
}

/** Texto curto do estado das texturas HD. */
export function resumoTextura(t: EstadoEmulacao['textura']): string {
  if (!t.instalado) return 'Nenhum pacote de texturas instalado.'
  const tamanho = t.mb ? `, ${t.mb.toLocaleString('pt-BR')} MB` : ''
  return `${t.ativo ? 'Ativas' : 'Desligadas'} — ${t.arquivos} arquivo(s)${tamanho}.`
}

/**
 * Validação do formulário de cheat antes de ir à ponte (mesmas regras do
 * núcleo: nome de uma linha sem colchetes; código em pares de 8 hex).
 */
export function validarCheat(nome: string, codigo: string): string | null {
  const n = nome.trim()
  if (n === '') return 'Dê um nome ao cheat.'
  if (n.startsWith('[') || n.endsWith(']') || n.includes('\n')) return 'O nome não pode ter colchetes nem quebra de linha.'
  // `*comentário` é aceito pelo núcleo e não conta como linha de código
  const linhas = codigo
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l !== '' && !l.startsWith('*'))
  if (linhas.length === 0) return 'Cole o código do cheat.'
  const invalida = linhas.find((l) => !/^[0-9a-f]{8}\s+[0-9a-f]{8}$/i.test(l))
  if (invalida !== undefined) return `Linha inválida: "${invalida}" (use pares de 8 hex, ex.: 00112233 44556677).`
  return null
}

/** Resumo de versão local × remota para a lista de emuladores. */
export function resumoEmulador(e: EmuladorStatus): string {
  const local = e.local ? `instalado ${e.local}` : 'não instalado'
  if (!e.tag) return local
  if (e.atualizado === true) return `${local} — já é a última (${e.tag})`
  const tamanho = e.tamanho_mb ? ` (${e.tamanho_mb} MB)` : ''
  return `${local} — disponível ${e.tag}${tamanho}`
}
