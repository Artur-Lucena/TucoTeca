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
  | { tipo: 'download'; rotulo: string }
  | { tipo: 'indisponivel'; rotulo: string; motivo: string }

/**
 * Botão principal do card, por tipo/capacidades (mesma ordem do plano):
 * download navega; URL decide entre abrir e buscar; catálogo busca;
 * emulador/músicas online/provedores ficam para a fatia seguinte.
 */
export function acaoDaIntegracao(item: IntegracaoDTO): AcaoIntegracao {
  const caps = item.capacidades ?? []
  if (caps.includes('download') || item.tipo === 'download') {
    return { tipo: 'download', rotulo: 'Ir para Downloads' }
  }
  if (typeof item.url === 'string' && item.url !== '') {
    return item.url.includes('{q}')
      ? { tipo: 'buscar', rotulo: 'Buscar no site' }
      : { tipo: 'abrir', rotulo: 'Abrir site' }
  }
  if (item.tipo === 'catalogo') return { tipo: 'buscar', rotulo: 'Buscar no catálogo' }
  if (caps.includes('emulador')) {
    return {
      tipo: 'indisponivel',
      rotulo: 'Emular',
      motivo: 'Emulação ainda não nesta fatia da interface nova.',
    }
  }
  if (item.tipo === 'musicas_online') {
    return {
      tipo: 'indisponivel',
      rotulo: 'Escolher faixas',
      motivo: 'Músicas online ainda não nesta fatia da interface nova.',
    }
  }
  return {
    tipo: 'indisponivel',
    rotulo: 'Abrir',
    motivo: 'Ainda não nesta fatia da interface nova.',
  }
}
