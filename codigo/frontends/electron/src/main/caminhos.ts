import { join, posix, resolve, win32 } from 'node:path'

interface OpcoesCaminho {
  plataforma?: NodeJS.Platform
}

/** Módulo de caminhos da plataforma pedida (nos testes, outra que não a do processo). */
export function caminhosDe(plataforma: NodeJS.Platform = process.platform): typeof posix {
  return plataforma === 'win32' ? win32 : posix
}

/**
 * Forma de comparação: Windows e macOS (APFS/HFS+ padrão) não diferenciam
 * maiúsculas; o macOS também guarda nomes em NFD, então tudo vira NFC.
 */
export function chaveCaminho(caminho: string, plataforma: NodeJS.Platform = process.platform): string {
  const p = caminhosDe(plataforma).resolve(caminho)
  if (plataforma === 'win32') return p.toLowerCase()
  if (plataforma === 'darwin') return p.normalize('NFC').toLowerCase()
  return p
}

/** `pathname` de uma URL local → caminho do SO (`/C:/x` vira `C:/x` no Windows). */
export function caminhoDoPathname(pathname: string, plataforma: NodeJS.Platform = process.platform): string {
  const alvo = decodeURIComponent(pathname)
  if (plataforma === 'win32') return /^\/[A-Za-z]:/.test(alvo) ? alvo.slice(1) : alvo
  // mediaUrl escapa o caminho inteiro: `/%2FUsers/x` decodifica para `//Users/x`
  return alvo.replace(/^\/{2,}/, '/')
}

/** Só deixa servir arquivos dentro da pasta da coleção (nem caminho vazio). */
export function caminhoPermitido(home: string, alvo: string, opcoes?: OpcoesCaminho): boolean {
  if (!home || !alvo) return false
  const plataforma = opcoes?.plataforma ?? process.platform
  const p = caminhosDe(plataforma)
  const base = chaveCaminho(home, plataforma)
  const destino = chaveCaminho(alvo, plataforma)
  if (base === destino) return true
  const relativo = p.relative(base, destino)
  return relativo !== '' && !relativo.startsWith('..') && !p.isAbsolute(relativo)
}

interface EntradaRaizHome {
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
const PASTA_NUCLEO_EMPACOTADO = 'tucoteca'

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
