/** Item da prévia de importação (`jogos.prever`): o mesmo dict do núcleo. */
export interface ItemPrevia {
  titulo?: string
  executable_path?: string
  launch_options?: string
  plataforma?: string
  origem?: string
  [campo: string]: unknown
}

/** Junta prévias de vários arquivos soltos, sem repetir o mesmo jogo. */
export function juntarPrevias(listas: ItemPrevia[][]): ItemPrevia[] {
  const vistos = new Set<string>()
  const saida: ItemPrevia[] = []
  for (const lista of listas) {
    for (const item of lista) {
      const chave = [item.executable_path ?? '', item.launch_options ?? '', item.titulo ?? '']
        .map((v) => String(v).trim().toLowerCase())
        .join('\u0000')
      if (vistos.has(chave)) continue
      vistos.add(chave)
      saida.push(item)
    }
  }
  return saida
}

/** Linha de detalhe de um item da prévia (plataforma + arquivo). */
export function detalheItem(item: ItemPrevia): string {
  const arquivo = String(item.launch_options || item.executable_path || '')
  const nome = arquivo.replace(/\\/g, '/').split('/').pop() ?? ''
  return [item.plataforma, nome].filter((v) => v !== undefined && String(v).trim() !== '').join(' · ')
}
