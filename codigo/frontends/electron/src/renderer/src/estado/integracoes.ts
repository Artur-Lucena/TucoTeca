/** DTO das integrações (`Integracao.apresentar`), com `buscar` removido. */
export interface IntegracaoDTO {
  chave: string
  nome: string
  descricao?: string
  tipo: string
  inicial?: string
  cor?: string
  url?: string
  personalizada?: boolean
  capacidades?: string[]
}

export type AcaoIntegracao =
  | { tipo: 'abrir'; rotulo: string }
  | { tipo: 'buscar'; rotulo: string }
  | { tipo: 'navegar'; rotulo: string; secao: string }
  | { tipo: 'indisponivel'; rotulo: string; motivo: string }

/**
 * Botão principal do card, por tipo/capacidades: download, emulador, músicas
 * online e provedores levam à tela que faz isso; URL decide entre abrir e
 * buscar; catálogo busca.
 */
export function acaoDaIntegracao(item: IntegracaoDTO): AcaoIntegracao {
  const caps = item.capacidades ?? []
  if (caps.includes('download') || item.tipo === 'download') {
    return { tipo: 'navegar', rotulo: 'Ir para Downloads', secao: 'downloads' }
  }
  if (typeof item.url === 'string' && item.url !== '') {
    return item.url.includes('{q}')
      ? { tipo: 'buscar', rotulo: 'Buscar no site' }
      : { tipo: 'abrir', rotulo: 'Abrir site' }
  }
  if (item.tipo === 'catalogo') return { tipo: 'buscar', rotulo: 'Buscar no catálogo' }
  if (caps.includes('emulador')) {
    return { tipo: 'navegar', rotulo: 'Emuladores e controles', secao: 'configuracoes' }
  }
  if (item.tipo === 'musicas_online') {
    return { tipo: 'navegar', rotulo: 'Buscar músicas', secao: 'musicas' }
  }
  if (item.tipo === 'provedores') {
    return { tipo: 'navegar', rotulo: 'Configurar provedores', secao: 'configuracoes' }
  }
  return { tipo: 'indisponivel', rotulo: 'Abrir', motivo: 'Esta integração não tem endereço nem ação.' }
}

const ROTULO_TIPO: Record<string, string> = {
  catalogo: 'catálogo',
  emulador: 'emulador',
  download: 'download',
  musicas_online: 'músicas online',
  provedores: 'provedores',
  link: 'link',
}

const ROTULO_CAPACIDADE: Record<string, string> = {
  busca: 'busca',
  abrir: 'abrir',
  midia: 'mídia',
  download: 'download',
  emulador: 'emulador',
  config: 'configuração',
  metadados: 'dados de jogo',
}

/** Rótulo legível do tipo (também usado no formulário de nova integração). */
export function rotuloTipo(tipo: string): string {
  return ROTULO_TIPO[tipo] ?? tipo
}

/** Selos do card: tipo + capacidades, legíveis e sem repetir o tipo nas capacidades. */
export function selosDaIntegracao(item: IntegracaoDTO): string[] {
  const selos = [rotuloTipo(item.tipo), ...(item.capacidades ?? []).map((c) => ROTULO_CAPACIDADE[c] ?? c)]
  if (item.personalizada === true) selos.push('personalizada')
  return [...new Set(selos)]
}
