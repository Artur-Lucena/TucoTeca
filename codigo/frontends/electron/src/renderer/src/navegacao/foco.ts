/**
 * Navegação espacial (controle/TV): a partir do elemento focado, acha o
 * vizinho mais próximo na direção pedida. A escolha é pura (retângulos) e
 * testável; o resto só lê o DOM e move o foco.
 */
export type Direcao = 'cima' | 'baixo' | 'esquerda' | 'direita'

export interface Retangulo {
  x: number
  y: number
  largura: number
  altura: number
}

export interface Candidato<T> {
  item: T
  ret: Retangulo
}

const centro = (r: Retangulo) => ({ x: r.x + r.largura / 2, y: r.y + r.altura / 2 })

/**
 * Melhor vizinho na direção: só conta quem está à frente (pela borda).
 * Primeiro os que dividem a mesma linha/coluna; entre eles (ou, se não
 * houver, entre todos) vence a menor distância no eixo principal + 2× o
 * desvio no eixo cruzado — a grade anda em linha reta antes de pular.
 */
export function vizinho<T>(atual: Retangulo, candidatos: Candidato<T>[], direcao: Direcao): T | null {
  const c0 = centro(atual)
  let melhor: T | null = null
  let nota = Infinity
  for (const { item, ret } of candidatos) {
    const c = centro(ret)
    let principal: number
    let cruzado: number
    if (direcao === 'direita') {
      if (ret.x < atual.x + atual.largura - 1 || c.x <= c0.x) continue
      principal = ret.x - (atual.x + atual.largura)
      cruzado = Math.abs(c.y - c0.y)
    } else if (direcao === 'esquerda') {
      if (ret.x + ret.largura > atual.x + 1 || c.x >= c0.x) continue
      principal = atual.x - (ret.x + ret.largura)
      cruzado = Math.abs(c.y - c0.y)
    } else if (direcao === 'baixo') {
      if (ret.y < atual.y + atual.altura - 1 || c.y <= c0.y) continue
      principal = ret.y - (atual.y + atual.altura)
      cruzado = Math.abs(c.x - c0.x)
    } else {
      if (ret.y + ret.altura > atual.y + 1 || c.y >= c0.y) continue
      principal = atual.y - (ret.y + ret.altura)
      cruzado = Math.abs(c.x - c0.x)
    }
    // quem cruza a mesma faixa (linha/coluna) vem antes de qualquer diagonal
    const horizontal = direcao === 'direita' || direcao === 'esquerda'
    const sobrepoe = horizontal
      ? ret.y < atual.y + atual.altura && ret.y + ret.altura > atual.y
      : ret.x < atual.x + atual.largura && ret.x + ret.largura > atual.x
    const n = (sobrepoe ? 0 : 100_000) + Math.max(0, principal) + 2 * cruzado
    if (n < nota) {
      nota = n
      melhor = item
    }
  }
  return melhor
}

// ---------------------------------------------------------------- DOM

const FOCAVEIS = 'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/** Camada de cima (diálogo, player, paleta) ou a janela inteira. */
export function raizAtiva(doc: Document = document): ParentNode {
  const camadas = doc.querySelectorAll<HTMLElement>('.player-tela, .modal, .paleta')
  return camadas.length > 0 ? camadas[camadas.length - 1] : doc
}

function visivel(el: HTMLElement): boolean {
  const r = el.getBoundingClientRect()
  if (r.width <= 0 || r.height <= 0) return false
  const estilo = getComputedStyle(el)
  return estilo.visibility !== 'hidden' && estilo.display !== 'none'
}

function ret(el: Element): Retangulo {
  const r = el.getBoundingClientRect()
  return { x: r.left, y: r.top, largura: r.width, altura: r.height }
}

/** Move o foco para o vizinho na direção; sem foco, começa pelo conteúdo. Devolve se moveu. */
export function moverFoco(direcao: Direcao, doc: Document = document): boolean {
  const raiz = raizAtiva(doc)
  const todos = [...raiz.querySelectorAll<HTMLElement>(FOCAVEIS)].filter(visivel)
  if (todos.length === 0) return false
  const atual = doc.activeElement as HTMLElement | null
  if (atual === null || atual === doc.body || !todos.includes(atual)) {
    const conteudo = todos.find((el) => el.closest('.conteudo') !== null) ?? todos[0]
    focar(conteudo)
    return true
  }
  const proximo = vizinho(ret(atual), todos.filter((el) => el !== atual).map((el) => ({ item: el, ret: ret(el) })), direcao)
  if (proximo === null) return false
  focar(proximo)
  return true
}

function focar(el: HTMLElement): void {
  el.focus({ preventScroll: true })
  el.scrollIntoView({ block: 'nearest', inline: 'nearest' })
}

/** Aba anterior/seguinte da tela atual (`.abas .aba`); devolve se trocou. */
export function trocarAba(delta: 1 | -1, doc: Document = document): boolean {
  const barras = [...doc.querySelectorAll<HTMLElement>('.conteudo .abas')]
  const barra = barras[barras.length - 1]
  if (barra === undefined) return false
  const abas = [...barra.querySelectorAll<HTMLButtonElement>('.aba')]
  if (abas.length < 2) return false
  const i = Math.max(0, abas.findIndex((a) => a.classList.contains('ativa')))
  const alvo = abas[(i + delta + abas.length) % abas.length]
  alvo.click()
  alvo.focus({ preventScroll: true })
  return true
}

/** Big Picture (TV/controle): o foco espacial cuida das setas; listas da tela não as tratam. */
export function modoTv(doc: Document = document): boolean {
  return doc.documentElement.dataset.densidade === 'bigpicture'
}
