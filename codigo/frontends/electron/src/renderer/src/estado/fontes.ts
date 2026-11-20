/** Fontes de download (formato do Hydra) e opções de download de um jogo. */

export interface FonteDownload {
  id: string
  url: string
  nome: string
  total: number
  atualizada_em: string
  erro: string
}

export interface OpcaoDownload {
  titulo: string
  uris: string[]
  tamanho: string
  data: string
  fonte: string
  fonte_id: string
  nota: number
}

export interface LinkDownload {
  uri: string
  tipo: 'torrent' | 'direto'
  rotulo: string
}

/** Links da opção na ordem de preferência: torrent (vai ao qBittorrent) e depois direto. */
export function linksDaOpcao(opcao: OpcaoDownload): LinkDownload[] {
  const links: LinkDownload[] = []
  for (const uri of opcao.uris ?? []) {
    if (uri.startsWith('magnet:?')) links.push({ uri, tipo: 'torrent', rotulo: 'Torrent' })
    else if (uri.startsWith('https://')) {
      let host = ''
      try {
        host = new URL(uri).hostname.replace(/^www\./, '')
      } catch {
        continue
      }
      links.push({ uri, tipo: 'direto', rotulo: `Direto · ${host}` })
    }
  }
  return links.sort((a, b) => (a.tipo === b.tipo ? 0 : a.tipo === 'torrent' ? -1 : 1))
}

/** Data ISO curta → dd/mm/aaaa (vazia fica vazia). */
export function dataCurta(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso ?? '')
  return m ? `${m[3]}/${m[2]}/${m[1]}` : ''
}
