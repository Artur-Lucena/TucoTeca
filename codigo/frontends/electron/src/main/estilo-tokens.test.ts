import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const RAIZ = join(__dirname, '..', 'renderer', 'src')
const PASTA_CSS = join(RAIZ, 'estilo')
const arquivosCss = readdirSync(PASTA_CSS)
  .filter((nome) => nome.endsWith('.css'))
  .map((nome) => ({ nome, texto: readFileSync(join(PASTA_CSS, nome), 'utf8') }))
const css = arquivosCss.map((a) => a.texto).join('\n')

function arquivos(pasta: string): string[] {
  return readdirSync(pasta).flatMap((nome: string) => {
    const caminho = join(pasta, nome)
    if (statSync(caminho).isDirectory()) return arquivos(caminho)
    return /\.tsx?$/.test(nome) && !nome.includes('.test.') ? [caminho] : []
  })
}

/** Seletores de topo (o cabeçalho antes de cada `{`), sem comentários nem @-regras. */
function seletores(texto: string): string[] {
  const limpo = texto.replace(/\/\*[\s\S]*?\*\//g, '')
  const saida: string[] = []
  let profundidade = 0
  let inicio = 0
  for (let i = 0; i < limpo.length; i += 1) {
    if (limpo[i] === '{') {
      if (profundidade === 0) {
        const cab = limpo.slice(inicio, i).trim()
        if (cab !== '' && !cab.startsWith('@')) saida.push(cab.replace(/\s+/g, ' '))
      }
      profundidade += 1
    } else if (limpo[i] === '}') {
      profundidade -= 1
      if (profundidade === 0) inicio = i + 1
    }
  }
  return saida
}

describe('tokens de CSS', () => {
  it('toda var(--x) usada no CSS e nos componentes está definida', () => {
    const definidos = new Set([...css.matchAll(/^\s*(--[a-z0-9-]+)\s*:/gim)].map((m) => m[1]))
    const fontes = [css, ...arquivos(RAIZ).map((a) => readFileSync(a, 'utf8'))].join('\n')
    const usados = new Set([...fontes.matchAll(/var\((--[a-z0-9-]+)/gi)].map((m) => m[1]))
    const faltando = [...usados].filter((nome) => !definidos.has(nome)).sort()
    expect(faltando).toEqual([])
  })

  it('nenhum seletor é definido duas vezes (no mesmo arquivo ou entre arquivos)', () => {
    const vistos = new Map<string, string>()
    const repetidos: string[] = []
    for (const { nome, texto } of arquivosCss) {
      for (const sel of seletores(texto)) {
        const antes = vistos.get(sel)
        if (antes !== undefined) repetidos.push(`${sel} (${antes} e ${nome})`)
        else vistos.set(sel, nome)
      }
    }
    expect(repetidos).toEqual([])
  })

  it('o index importa todos os arquivos de estilo', () => {
    const index = readFileSync(join(PASTA_CSS, 'index.ts'), 'utf8')
    for (const { nome } of arquivosCss) expect(index).toContain(`'./${nome}'`)
  })
})
