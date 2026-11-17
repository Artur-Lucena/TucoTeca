import { horas } from './formato'
/** `biblioteca-20261114-171503-123456.db` → `14/11/2026 17:15` ('' se o nome não segue o padrão). */
export function dataDoBackup(nome: string): string {
  const m = /^biblioteca-(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})/.exec(nome)
  if (m === null) return ''
  return `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}`
}

export const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']

/** Resumo do ano (`estatisticas.ler` → `resumo_ano` do núcleo). */
export interface ResumoAno {
  ano: number
  meses: number[]
  total_horas: number
  jogos: Array<{ titulo: string; horas: number }>
}

export function normalizarResumo(bruto: unknown): ResumoAno {
  const r = (bruto ?? {}) as Partial<ResumoAno>
  const meses = Array.from({ length: 12 }, (_, i) => {
    const v = Number(Array.isArray(r.meses) ? r.meses[i] : 0)
    return Number.isFinite(v) && v > 0 ? v : 0
  })
  return {
    ano: Number(r.ano) || new Date().getFullYear(),
    meses,
    total_horas: Number(r.total_horas) || 0,
    jogos: Array.isArray(r.jogos)
      ? r.jogos.map((j) => ({ titulo: String(j?.titulo ?? ''), horas: Number(j?.horas) || 0 }))
      : [],
  }
}

/** Altura relativa (0–100) de cada mês para o gráfico de barras. */
export function alturasMeses(meses: number[]): number[] {
  const maximo = Math.max(0, ...meses)
  return meses.map((h) => (maximo > 0 ? Math.round((h / maximo) * 100) : 0))
}

/** Horas legíveis em pt-BR (1,5 h). */
export function horasTexto(valor: number): string {
  return horas(valor)
}

/** `saves-20261114-171503-123456.zip` → `14/11/2026 17:15` ('' fora do padrão). */
export function dataDoSnapshot(nome: string): string {
  return dataDoBackup(nome.replace(/^saves-/, 'biblioteca-'))
}
