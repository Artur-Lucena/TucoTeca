/** Preferências de aparência (`aparencia.ler`, `bib_nucleo/aparencia_usuario.py`). */
export type Tema = 'escuro' | 'claro'
export type Densidade = 'compacto' | 'conforto' | 'bigpicture'

export interface Aparencia {
  tema: Tema
  densidade: Densidade
  escala_texto: number
  auto_backup: boolean
}

export const TEMAS: Array<{ valor: Tema; rotulo: string }> = [
  { valor: 'escuro', rotulo: 'Escuro' },
  { valor: 'claro', rotulo: 'Claro' },
]

export const DENSIDADES: Array<{ valor: Densidade; rotulo: string; fator: number }> = [
  { valor: 'compacto', rotulo: 'Compacta', fator: 0.9 },
  { valor: 'conforto', rotulo: 'Confortável', fator: 1 },
  { valor: 'bigpicture', rotulo: 'Big Picture (TV/controle)', fator: 1.25 },
]

/** Mesmos limites do núcleo: escala de texto em [0.8, 1.5]. */
export const ESCALA_MIN = 0.8
export const ESCALA_MAX = 1.5

export function normalizarAparencia(bruto: unknown): Aparencia {
  const r = (bruto ?? {}) as Partial<Record<keyof Aparencia, unknown>>
  const tema = TEMAS.some((t) => t.valor === r.tema) ? (r.tema as Tema) : 'escuro'
  const densidade = DENSIDADES.some((d) => d.valor === r.densidade) ? (r.densidade as Densidade) : 'conforto'
  const escala = Number(r.escala_texto)
  return {
    tema,
    densidade,
    escala_texto: Number.isFinite(escala) ? Math.min(ESCALA_MAX, Math.max(ESCALA_MIN, escala)) : 1,
    auto_backup: r.auto_backup !== false,
  }
}

/** Zoom da janela = fator da densidade × escala de texto (arredondado a 0,01). */
export function fatorZoom(a: Pick<Aparencia, 'densidade' | 'escala_texto'>): number {
  const fator = DENSIDADES.find((d) => d.valor === a.densidade)?.fator ?? 1
  return Math.round(fator * a.escala_texto * 100) / 100
}

/** Aplica no documento (tema por atributo) e na janela (zoom pelo preload). */
export function aplicarAparencia(a: Aparencia): void {
  document.documentElement.dataset.tema = a.tema
  document.documentElement.dataset.densidade = a.densidade
  window.tucoteca.definirZoom(fatorZoom(a))
}
