import type { ColecaoResumo, JogoResumo } from '../derivacoes'

/** Lista do snapshot → coleções válidas (sem nome ou id ruins). */
export function normalizarColecoes(bruto: unknown): ColecaoResumo[] {
  if (!Array.isArray(bruto)) return []
  return bruto
    .filter((c): c is Record<string, unknown> => c !== null && typeof c === 'object')
    .map((c) => ({
      id: Number(c.id),
      nome: String(c.nome ?? '').trim(),
      uuids: Array.isArray(c.uuids) ? c.uuids.filter((u): u is string => typeof u === 'string') : [],
    }))
    .filter((c) => Number.isInteger(c.id) && c.id > 0 && c.nome !== '')
}

/** Jogos da coleção na ordem em que foram adicionados. */
export function jogosDaColecao<T extends JogoResumo>(jogos: T[] | undefined, colecao: ColecaoResumo | undefined): T[] {
  if (colecao === undefined) return []
  const porUuid = new Map((jogos ?? []).map((j) => [String(j.uuid ?? ''), j]))
  return colecao.uuids.map((u) => porUuid.get(u)).filter((j): j is T => j !== undefined)
}

/** Nome digitado → nome limpo, ou o motivo de recusa (espelha `banco/colecoes.py`). */
export function validarNomeColecao(nome: string, existentes: ColecaoResumo[], ignorarId?: number): string | { erro: string } {
  const limpo = String(nome ?? '').split(/\s+/).filter(Boolean).join(' ')
  if (limpo === '') return { erro: 'Dê um nome à coleção.' }
  if (limpo.length > 60) return { erro: 'Nome de coleção com até 60 caracteres.' }
  const repetida = existentes.some((c) => c.id !== ignorarId && c.nome.toLocaleLowerCase('pt-BR') === limpo.toLocaleLowerCase('pt-BR'))
  return repetida ? { erro: `Já existe uma coleção chamada ${limpo}.` } : limpo
}
