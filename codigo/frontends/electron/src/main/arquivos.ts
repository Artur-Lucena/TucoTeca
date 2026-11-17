import { net, protocol } from 'electron'
import { createReadStream, statSync } from 'node:fs'
import { Readable } from 'node:stream'
import { pathToFileURL } from 'node:url'
import { caminhoDoPathname, caminhoPermitido } from './caminhos'
import { caminhoDaUrlMidia, faixaRange, tipoDoArquivo } from './midia'

/** Serve capas locais por `tucoteca-img://`, só de dentro da coleção. */
export function registrarProtocoloMidia(homeDe: () => string): void {
  protocol.handle('tucoteca-img', async (pedido) => {
    const home = homeDe()
    let alvo: string
    try {
      alvo = caminhoDoPathname(new URL(pedido.url).pathname)
    } catch {
      return new Response('URL inválida', { status: 400 })
    }
    if (!home || !caminhoPermitido(home, alvo)) {
      return new Response('fora da coleção', { status: 403 })
    }
    return net.fetch(pathToFileURL(alvo).toString())
  })
}

/**
 * Serve áudio/vídeo/imagem local por `tucoteca-media://` com suporte a
 * `Range` (o `<audio>` do renderer pede faixas para o seek).
 */
export function registrarProtocoloMedia(homeDe: () => string, raizesDe: () => readonly string[] = () => []): void {
  protocol.handle('tucoteca-media', async (pedido) => {
    const home = homeDe()
    const alvo = home ? caminhoDaUrlMidia(home, pedido.url, process.platform, raizesDe()) : null
    if (alvo === null) return new Response('fora da coleção', { status: 403 })

    let tamanho: number
    try {
      const info = statSync(alvo)
      if (!info.isFile()) return new Response('não é um arquivo', { status: 404 })
      tamanho = info.size
    } catch {
      return new Response('arquivo não encontrado', { status: 404 })
    }

    const faixa = faixaRange(pedido.headers.get('Range'), tamanho)
    if (faixa.status === 416) {
      return new Response(null, {
        status: 416,
        headers: { 'Content-Range': `bytes */${tamanho}` },
      })
    }
    const fluxo = createReadStream(alvo, { start: faixa.inicio, end: faixa.fim })
    const cabecalhos: Record<string, string> = {
      'Content-Type': tipoDoArquivo(alvo),
      'Accept-Ranges': 'bytes',
      'Content-Length': String(faixa.fim - faixa.inicio + 1),
    }
    if (faixa.status === 206) {
      cabecalhos['Content-Range'] = `bytes ${faixa.inicio}-${faixa.fim}/${tamanho}`
    }
    return new Response(Readable.toWeb(fluxo) as ReadableStream, {
      status: faixa.status,
      headers: cabecalhos,
    })
  })
}
