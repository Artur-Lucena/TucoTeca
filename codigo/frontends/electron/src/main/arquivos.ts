import { net, protocol } from 'electron'
import { pathToFileURL } from 'node:url'
import { caminhoPermitido } from './caminhos'

/** Serve capas locais por `tucoteca-img://`, só de dentro da coleção. */
export function registrarProtocoloMidia(homeDe: () => string): void {
  protocol.handle('tucoteca-img', async (pedido) => {
    const home = homeDe()
    let alvo: string
    try {
      const url = new URL(pedido.url)
      alvo = decodeURIComponent(url.pathname)
      if (process.platform === 'win32' && /^\/[A-Za-z]:/.test(alvo)) alvo = alvo.slice(1)
    } catch {
      return new Response('URL inválida', { status: 400 })
    }
    if (!home || !caminhoPermitido(home, alvo)) {
      return new Response('fora da coleção', { status: 403 })
    }
    return net.fetch(pathToFileURL(alvo).toString())
  })
}
