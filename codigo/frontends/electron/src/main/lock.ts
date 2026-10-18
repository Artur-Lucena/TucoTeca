import { readFileSync } from 'node:fs'
import { hostname } from 'node:os'

export interface DepsLock {
  host: string
  plataforma: string
  vivo: (pid: number) => boolean
}

/**
 * Lock no disco que pertence a um processo já morto neste mesmo host/SO —
 * exatamente o que sobra depois de um crash (taskkill /F), quando o
 * `adquirir_lock` do núcleo ainda recusaria a coleção por 24 h. Host/SO
 * diferentes nunca contam (o lock pode ser de outra máquina, ex.: pasta
 * sincronizada).
 */
export function lockOrfao(caminho: string, deps?: Partial<DepsLock>): boolean {
  const host = deps?.host ?? hostname()
  const plataforma = deps?.plataforma ?? process.platform
  const vivo = deps?.vivo ?? processoVivo
  let dados: { pid?: unknown; host?: unknown; so?: unknown }
  try {
    dados = JSON.parse(readFileSync(caminho, 'utf8')) as { pid?: unknown }
  } catch {
    return false
  }
  if (dados === null || typeof dados !== 'object') return false
  if (dados.host !== host) return false
  const aceitos = plataforma === 'win32' ? ['win32', 'nt'] : [plataforma, 'posix']
  if (typeof dados.so !== 'string' || !aceitos.includes(dados.so)) return false
  const pid = Number(dados.pid)
  if (!Number.isInteger(pid) || pid <= 0) return false
  return !vivo(pid)
}

function processoVivo(pid: number): boolean {
  try {
    process.kill(pid, 0)
    return true
  } catch (erro) {
    // ESRCH = processo não existe; EPERM (sem permissão) = existe.
    return (erro as NodeJS.ErrnoException).code !== 'ESRCH'
  }
}
