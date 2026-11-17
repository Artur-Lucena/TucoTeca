/** Candidato de capa vindo de `capas.buscar` (`bib_nucleo/capas.py::buscar_capas`). */
export interface CandidatoCapa {
  /** Objeto original: é ele que volta para `capas.aplicar`. */
  original: Record<string, unknown>
  url: string
  /** Miniatura: arquivo em cache (file://) ou a própria URL https. */
  preview: string
  fonte: string
  titulo: string
}

/**
 * Lê a resposta de `capas.buscar`. O núcleo devolve `{itens, erros, cache}`;
 * a tela antiga lia `candidatos` e nunca mostrava nada.
 */
export function candidatosDeCapa(resposta: unknown): CandidatoCapa[] {
  const itens = (resposta as { itens?: unknown } | null)?.itens
  if (!Array.isArray(itens)) return []
  return itens
    .filter((i): i is Record<string, unknown> => typeof i === 'object' && i !== null && typeof (i as { url?: unknown }).url === 'string')
    .map((i) => ({
      original: i,
      url: String(i.url),
      preview: String(i.preview_url ?? i.url),
      fonte: String(i.fonte ?? i.provedor ?? ''),
      titulo: String(i.titulo ?? ''),
    }))
}

/** Erros parciais por provedor (ex.: "SteamGridDB: sem chave"), para o aviso. */
export function errosDeCapa(resposta: unknown): string[] {
  const erros = (resposta as { erros?: unknown } | null)?.erros
  return Array.isArray(erros) ? erros.map(String) : []
}
