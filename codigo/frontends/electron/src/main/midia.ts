import { extname } from 'node:path'
import { caminhoPermitido } from './caminhos'

/** Recorte pedido para o handler de mídia (200 inteiro; 206 faixa; 416 recusa). */
export interface FaixaPedido {
  status: number
  inicio: number
  fim: number
}

const TIPOS: Record<string, string> = {
  '.mp3': 'audio/mpeg',
  '.wav': 'audio/wav',
  '.ogg': 'audio/ogg',
  '.oga': 'audio/ogg',
  '.flac': 'audio/flac',
  '.m4a': 'audio/mp4',
  '.aac': 'audio/aac',
  '.mp4': 'video/mp4',
  '.webm': 'video/webm',
  '.mkv': 'video/x-matroska',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
}

/** Content-Type pelo sufixo do arquivo (fallback binário). */
export function tipoDoArquivo(caminho: string): string {
  return TIPOS[extname(String(caminho)).toLowerCase()] ?? 'application/octet-stream'
}

/**
 * Interpreta o cabeçalho `Range` (só `bytes=a-b`/`bytes=a-`):
 * sem Range → 200 inteiro; recorte válido → 206; malformado/fora → 416.
 */
export function faixaRange(cabecalho: string | null | undefined, tamanho: number): FaixaPedido {
  if (!Number.isFinite(tamanho) || tamanho <= 0) return { status: 416, inicio: 0, fim: -1 }
  const texto = String(cabecalho ?? '').trim()
  if (texto === '') return { status: 200, inicio: 0, fim: tamanho - 1 }
  const casado = /^bytes=(\d+)-(\d*)$/.exec(texto)
  if (casado === null) return { status: 416, inicio: 0, fim: -1 }
  const inicio = Number(casado[1])
  const fim = casado[2] === '' ? tamanho - 1 : Math.min(Number(casado[2]), tamanho - 1)
  if (!Number.isSafeInteger(inicio) || !Number.isSafeInteger(fim)) {
    return { status: 416, inicio: 0, fim: -1 }
  }
  if (inicio >= tamanho || inicio > fim) return { status: 416, inicio: 0, fim: -1 }
  return { status: 206, inicio, fim }
}

/**
 * Resolve `tucoteca-media://arquivo/<caminho escapado>` em caminho local,
 * recusando (null) qualquer alvo fora da coleção.
 */
export function caminhoDaUrlMidia(
  home: string,
  url: string,
  plataforma: NodeJS.Platform = process.platform,
): string | null {
  let alvo: string
  try {
    const parsed = new URL(url)
    if (parsed.protocol !== 'tucoteca-media:' || parsed.host !== 'arquivo') return null
    alvo = decodeURIComponent(parsed.pathname)
  } catch {
    return null
  }
  if (plataforma === 'win32' && /^\/[A-Za-z]:/.test(alvo)) alvo = alvo.slice(1)
  if (!caminhoPermitido(home, alvo, { plataforma })) return null
  return alvo
}
