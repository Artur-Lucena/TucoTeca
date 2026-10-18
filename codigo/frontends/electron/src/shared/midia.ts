/** Converte o `capa_url` do núcleo em URL carregável pelo renderer. */
export function converterUrlMidia(url: string): string {
  if (!url) return ''
  try {
    const alvo = new URL(url)
    if (alvo.protocol !== 'file:') return url
    // file:///C:/x → tucoteca-img://local/C:/x (o main valida contra a coleção)
    return `tucoteca-img://local${alvo.pathname}`
  } catch {
    return ''
  }
}

/** URL do protocolo de mídia para um caminho local ('' quando vazio). */
export function mediaUrl(caminho: string): string {
  const texto = String(caminho ?? '').trim()
  if (texto === '') return ''
  return `tucoteca-media://arquivo/${encodeURIComponent(texto.replace(/\\/g, '/'))}`
}
