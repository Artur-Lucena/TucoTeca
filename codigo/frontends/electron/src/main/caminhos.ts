import { isAbsolute, join, relative, resolve } from 'node:path'

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

export interface EntradaRaizHome {
  /** `app.isPackaged`. */
  empacotado: boolean
  /** `app.getAppPath()` (no checkout: codigo/frontends/electron). */
  appPath: string
  /** `process.resourcesPath` (no instalado: <app>/resources). */
  resourcesPath: string
  /** `app.getPath('documents')`, onde fica a coleção padrão do instalado. */
  documentos: string
  env: Record<string, string | undefined>
}

/** Pasta (dentro de resources/) onde o instalador copia núcleo, ponte e docs. */
export const PASTA_NUCLEO_EMPACOTADO = 'tucoteca'

/**
 * Raiz dos fontes Python e pasta da coleção.
 *
 * - Checkout: raiz = 3 níveis acima do appPath; coleção = a própria raiz
 *   (mesmo comportamento do TucoTeca.bat).
 * - Instalado: raiz = resources/tucoteca (somente leitura, trocada a cada
 *   atualização); coleção = Documentos/TucoTeca, que sobrevive a
 *   atualizar/desinstalar.
 *
 * `TUCOTECA_RAIZ` e `BIBLIOTECA_HOME` continuam tendo prioridade.
 */
export function resolverRaizHome(e: EntradaRaizHome): { raiz: string; home: string } {
  const raizEnv = e.env.TUCOTECA_RAIZ?.trim()
  const raiz = resolve(
    raizEnv ||
      (e.empacotado
        ? join(e.resourcesPath, PASTA_NUCLEO_EMPACOTADO)
        : join(e.appPath, '..', '..', '..')),
  )
  const homeEnv = e.env.BIBLIOTECA_HOME?.trim()
  const home = resolve(homeEnv || (e.empacotado ? join(e.documentos, 'TucoTeca') : raiz))
  return { raiz, home }
}
