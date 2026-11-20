import type { SistemaResumo } from './derivacoes'

/** Callback de toast que as telas recebem do app. */
export type AoAvisar = (texto: string, tom?: 'info' | 'atencao') => void

export interface Aviso {
  id: string
  texto: string
  tom: 'info' | 'atencao'
  /** Quando aconteceu (ISO); os avisos derivados do resumo não têm. */
  em?: string
}

const LIMITE = 200

/** Avisos recalculados a cada abertura (estado atual, não histórico): não vão para o disco. */
export const DERIVADOS = new Set(['sessoes-pendentes', 'backup-ausente', 'backup-velho', 'disco-baixo', 'ponte-ok', 'ponte-erro'])

/** Os avisos que entram no histórico gravado (`avisos.registrar`). */
export function persistiveis(avisos: Aviso[]): Aviso[] {
  return avisos.filter((aviso) => !DERIVADOS.has(aviso.id))
}

/** `2026-11-20T15:04:00-03:00` → `20/11 15:04` (vazio fica vazio). */
export function quandoCurto(iso: string | undefined): string {
  const m = /^\d{4}-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(iso ?? '')
  return m ? `${m[2]}/${m[1]} ${m[3]}:${m[4]}` : ''
}

/** Agora em ISO com o fuso local (igual ao que o núcleo grava). */
export function agoraIso(data = new Date()): string {
  const p = (n: number) => String(n).padStart(2, '0')
  const fuso = -data.getTimezoneOffset()
  const sinal = fuso >= 0 ? '+' : '-'
  return `${data.getFullYear()}-${p(data.getMonth() + 1)}-${p(data.getDate())}T${p(data.getHours())}:${p(data.getMinutes())}:${p(data.getSeconds())}${sinal}${p(Math.floor(Math.abs(fuso) / 60))}:${p(Math.abs(fuso) % 60)}`
}

/** Avisos derivados do resumo do sistema (snapshot): só o que o usuário precisa saber. */
export function avisosDoResumo(sistema: SistemaResumo): Aviso[] {
  const avisos: Aviso[] = []

  const pendentes = Number(sistema.pendentes)
  if (Number.isFinite(pendentes) && pendentes > 0) {
    avisos.push({
      id: 'sessoes-pendentes',
      tom: 'atencao',
      texto:
        pendentes === 1
          ? '1 sessão aberta sem horas registradas — feche em Início.'
          : `${pendentes} sessões abertas sem horas registradas — feche em Início.`,
    })
  }

  if (sistema.backup !== undefined) {
    const backup = String(sistema.backup).trim()
    if (backup === '' || backup === 'sem backup') {
      avisos.push({
        id: 'backup-ausente',
        tom: 'atencao',
        texto: 'Sem backup local da coleção — use “Fazer backup agora” em Configurações.',
      })
    } else {
      const idade = Number(sistema.backup_idade_dias)
      if (Number.isFinite(idade) && idade > 14) {
        avisos.push({ id: 'backup-velho', tom: 'atencao', texto: `Último backup há ${idade} dias.` })
      }
    }
  }

  const disco = Number(sistema.disco_livre_gb)
  if (Number.isFinite(disco) && disco < 5) {
    avisos.push({
      id: 'disco-baixo',
      tom: 'atencao',
      texto: `Pouco espaço em disco: ${disco} GB livres.`,
    })
  }

  return avisos
}

/** Junta avisos novos com os atuais: dedup por id, mais novos primeiro, teto de 200. */
export function juntarAvisos(atual: Aviso[], novos: Aviso[]): Aviso[] {
  const vistos = new Set<string>()
  const resultado: Aviso[] = []
  for (const aviso of [...novos, ...atual]) {
    if (vistos.has(aviso.id)) continue
    vistos.add(aviso.id)
    resultado.push(aviso)
  }
  return resultado.slice(0, LIMITE)
}

export function dispensarAviso(atual: Aviso[], id: string): Aviso[] {
  return atual.filter((aviso) => aviso.id !== id)
}

/** Evento `aviso` vindo da ponte (texto simples ou `{id, texto, tom}`). */
export function avisoDeEvento(dados: unknown): Aviso | null {
  if (typeof dados === 'string') {
    const texto = dados.trim()
    return texto === '' ? null : { id: texto, texto, tom: 'info' }
  }
  if (dados !== null && typeof dados === 'object') {
    const objeto = dados as { id?: unknown; texto?: unknown; tom?: unknown }
    const texto = String(objeto.texto ?? '').trim()
    if (texto === '') return null
    return {
      id: String(objeto.id ?? texto),
      texto,
      tom: objeto.tom === 'atencao' ? 'atencao' : 'info',
    }
  }
  return null
}

/** Texto limpo de falha do IPC: tira o embrulho "Error invoking remote method …". */
export function textoDeFalha(falha: unknown): string {
  const objeto = falha as { message?: unknown } | null
  const bruto = String(objeto?.message ?? falha ?? '').trim()
  return bruto.replace(/^Error invoking remote method '[^']+':\s*(?:Error:\s*)?/, '') || 'Algo deu errado.'
}
