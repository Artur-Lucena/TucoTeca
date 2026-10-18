import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { lockOrfao } from './lock'

function arquivo(conteudo: string): string {
  const pasta = mkdtempSync(join(tmpdir(), 'tucoteca-lock-'))
  const caminho = join(pasta, '.biblioteca.lock')
  writeFileSync(caminho, conteudo)
  return caminho
}

const deps = { host: 'pc-do-tuco', plataforma: 'win32', vivo: () => false }
const atual = { pid: 1234, host: 'pc-do-tuco', so: 'win32', inicio: '2026-10-18T10:00:00-03:00' }

describe('lockOrfao', () => {
  it('reconhece lock do mesmo host/SO com pid morto', () => {
    expect(lockOrfao(arquivo(JSON.stringify(atual)), deps)).toBe(true)
    expect(lockOrfao(arquivo(JSON.stringify({ ...atual, so: 'nt' })), deps)).toBe(true)
  })

  it('recusa pid vivo, outro host e outro SO', () => {
    const vivo = { ...deps, vivo: () => true }
    expect(lockOrfao(arquivo(JSON.stringify(atual)), vivo)).toBe(false)
    expect(lockOrfao(arquivo(JSON.stringify({ ...atual, host: 'note' })), deps)).toBe(false)
    expect(lockOrfao(arquivo(JSON.stringify({ ...atual, so: 'darwin' })), deps)).toBe(false)
  })

  it('recusa arquivo ausente, inválido, sem pid ou com pid inválido', () => {
    expect(lockOrfao(join(tmpdir(), 'nao-existe-tucoteca.lock'), deps)).toBe(false)
    expect(lockOrfao(arquivo('nem json'), deps)).toBe(false)
    expect(lockOrfao(arquivo(JSON.stringify({ host: 'pc-do-tuco', so: 'win32' })), deps)).toBe(false)
    expect(lockOrfao(arquivo(JSON.stringify({ ...atual, pid: 'x' })), deps)).toBe(false)
    expect(lockOrfao(arquivo(JSON.stringify({ ...atual, pid: 0 })), deps)).toBe(false)
  })
})
