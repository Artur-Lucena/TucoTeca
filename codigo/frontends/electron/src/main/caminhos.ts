import { isAbsolute, relative, resolve } from 'node:path'

export interface OpcoesCaminho {
  plataforma?: NodeJS.Platform
}

/** Só deixa servir arquivos dentro da pasta da coleção (nem caminho vazio). */
export function caminhoPermitido(home: string, alvo: string, opcoes?: OpcoesCaminho): boolean {
  if (!home || !alvo) return false
  const plataforma = opcoes?.plataforma ?? process.platform
  const normalizar = (caminho: string) => {
    const resolvido = resolve(caminho)
    return plataforma === 'win32' ? resolvido.toLowerCase() : resolvido
  }
  const base = normalizar(home)
  const destino = normalizar(alvo)
  if (base === destino) return true
  const relativo = relative(base, destino)
  return relativo !== '' && !relativo.startsWith('..') && !isAbsolute(relativo)
}
