/**
 * Formatação pt-BR usada pelas telas: horas, tamanho, duração, data e preço.
 * Funções puras (sem DOM); entradas inválidas viram '' ou '—', nunca "NaN".
 */

/** Horas jogadas: 1,5 h · 12 h. */
export function horas(valor: number): string {
  const n = Number(valor)
  return `${(Number.isFinite(n) ? n : 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} h`
}

/** Bytes → 512 B · 1,5 KB · 42 GB ('—' se inválido). */
export function bytes(valor: number): string {
  const n = Number(valor)
  if (!Number.isFinite(n) || n < 0) return '—'
  const unidades = ['B', 'KB', 'MB', 'GB', 'TB']
  let v = n
  let i = 0
  while (v >= 1024 && i < unidades.length - 1) {
    v /= 1024
    i += 1
  }
  const casas = i === 0 ? 0 : v < 10 ? 1 : 0
  return `${v.toLocaleString('pt-BR', { maximumFractionDigits: casas, minimumFractionDigits: casas })} ${unidades[i]}`
}

/** Segundos → 3:07 · 1:02:03. */
export function duracao(segundos: number | undefined): string {
  const total = Math.max(0, Math.round(Number(segundos ?? 0) || 0))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = String(total % 60).padStart(2, '0')
  return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${s}` : `${m}:${s}`
}

function comoData(valor: string | number | Date): Date | null {
  const d = valor instanceof Date ? valor : new Date(valor)
  return Number.isNaN(d.getTime()) ? null : d
}

/** Data curta: 14/11/2026 ('' se inválida). */
export function data(valor: string | number | Date): string {
  const d = comoData(valor)
  return d ? d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' }) : ''
}

/** Dia e hora sem ano: 14/11, 17:15 ('' se inválida). */
export function dataHora(valor: string | number | Date): string {
  const d = comoData(valor)
  return d ? d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''
}

/** Tempo relativo: agora · há 5 min · há 3 h · ontem · há 4 dias · em 2 dias; data cheia além de 30 dias. */
export function relativo(valor: string | number | Date, agora: Date = new Date()): string {
  const d = comoData(valor)
  if (!d) return ''
  const seg = Math.round((agora.getTime() - d.getTime()) / 1000)
  const futuro = seg < 0
  const abs = Math.abs(seg)
  if (abs < 60) return 'agora'
  const quanto = (texto: string) => (futuro ? `em ${texto}` : `há ${texto}`)
  if (abs < 3600) return quanto(`${Math.floor(abs / 60)} min`)
  if (abs < 86400) return quanto(`${Math.floor(abs / 3600)} h`)
  const dias = Math.floor(abs / 86400)
  if (dias === 1) return futuro ? 'amanhã' : 'ontem'
  if (dias <= 30) return quanto(`${dias} dias`)
  return data(d)
}

const SIMBOLOS: Record<string, string> = {
  BRL: 'R$',
  USD: 'US$',
  EUR: '€',
  GBP: '£',
  JPY: '¥',
}

/** Centavos + código ISO → R$ 19,99 (código desconhecido sai como prefixo; '' se inválido). */
export function moeda(centavos: number, codigo = ''): string {
  const n = Number(centavos)
  if (!Number.isFinite(n)) return ''
  const cod = String(codigo ?? '').toUpperCase()
  const prefixo = cod === '' ? '' : `${SIMBOLOS[cod] ?? cod} `
  return `${prefixo}${(n / 100).toFixed(2).replace('.', ',')}`
}
