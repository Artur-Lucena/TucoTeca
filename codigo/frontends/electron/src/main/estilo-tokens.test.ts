import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const RAIZ = join(__dirname, '..', 'renderer', 'src')
const css = readFileSync(join(RAIZ, 'estilo.css'), 'utf8')

function arquivos(pasta: string): string[] {
  return readdirSync(pasta).flatMap((nome: string) => {
    const caminho = join(pasta, nome)
    if (statSync(caminho).isDirectory()) return arquivos(caminho)
    return /\.tsx?$/.test(nome) && !nome.includes('.test.') ? [caminho] : []
  })
}

describe('tokens de CSS', () => {
  it('toda var(--x) usada no CSS e nos componentes está definida', () => {
    const definidos = new Set([...css.matchAll(/^\s*(--[a-z0-9-]+)\s*:/gim)].map((m) => m[1]))
    const fontes = [css, ...arquivos(RAIZ).map((a) => readFileSync(a, 'utf8'))].join('\n')
    const usados = new Set([...fontes.matchAll(/var\((--[a-z0-9-]+)/gi)].map((m) => m[1]))
    const faltando = [...usados].filter((nome) => !definidos.has(nome)).sort()
    expect(faltando).toEqual([])
  })
})
