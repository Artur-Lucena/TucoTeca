/** Letra de `musicas.letras` (LRCLIB): sincronizada ([{t, texto}]) ou texto puro. */
export interface Letra {
  ok: boolean
  sincronizadas: boolean
  linhas: Array<{ t: number; texto: string }>
  texto: string
  erro: string
}

export function normalizarLetra(bruto: unknown): Letra {
  const r = (bruto ?? {}) as Partial<Letra>
  const linhas = Array.isArray(r.linhas)
    ? r.linhas
        .map((l) => ({ t: Number(l?.t), texto: String(l?.texto ?? '') }))
        .filter((l) => Number.isFinite(l.t))
        .sort((a, b) => a.t - b.t)
    : []
  return {
    ok: r.ok === true,
    sincronizadas: r.sincronizadas === true && linhas.length > 0,
    linhas,
    texto: String(r.texto ?? ''),
    erro: String(r.erro ?? ''),
  }
}

/** Índice da linha cantada no tempo `t` (última com início ≤ t); -1 antes da 1ª. */
export function indiceLinha(linhas: Array<{ t: number }>, t: number): number {
  let baixo = 0
  let alto = linhas.length - 1
  let achado = -1
  while (baixo <= alto) {
    const meio = (baixo + alto) >> 1
    if (linhas[meio].t <= t) {
      achado = meio
      baixo = meio + 1
    } else {
      alto = meio - 1
    }
  }
  return achado
}

/** Parâmetros da busca a partir da faixa; null quando falta artista/título. */
export function pedidoLetra(
  faixa: { artista?: unknown; titulo?: unknown; album?: unknown } | null,
  duracao: number,
): { artista: string; titulo: string; album: string; duracao_s: number } | null {
  const artista = String(faixa?.artista ?? '').trim()
  const titulo = String(faixa?.titulo ?? '').trim()
  if (artista === '' || titulo === '') return null
  return {
    artista,
    titulo,
    album: String(faixa?.album ?? '').trim(),
    duracao_s: Number.isFinite(duracao) && duracao > 0 ? Math.round(duracao) : 0,
  }
}
