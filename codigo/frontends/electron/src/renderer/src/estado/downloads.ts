import type { Trabalho } from './trabalhos'

/** Downloads que o próprio app faz (fontes https, atualização), mais novos primeiro. */
export function downloadsNoApp(lista: Trabalho[]): Trabalho[] {
  return lista.filter((t) => t.grupo === 'download').reverse()
}

export function emAndamento(t: Trabalho): boolean {
  return t.estado === 'rodando' || t.estado === 'cancelando'
}

/** Arquivo que o download deixou no disco (vazio enquanto baixa ou se falhou). */
export function arquivoBaixado(t: Trabalho): string {
  if (t.estado !== 'ok') return ''
  const caminho = t.detalhe?.['path'] ?? t.detalhe?.['arquivo']
  return typeof caminho === 'string' ? caminho : ''
}

/** Pasta de um arquivo (Windows ou POSIX), para "Abrir pasta" sem abrir o arquivo em si. */
export function pastaDe(caminho: string): string {
  const i = Math.max(caminho.lastIndexOf('/'), caminho.lastIndexOf('\\'))
  return i > 0 ? caminho.slice(0, i) : caminho
}

/** Atualização do próprio TucoTeca (instala em Configurações), não um jogo para importar. */
export function ehAtualizacao(t: Trabalho): boolean {
  return t.escopo === 'atualizacao'
}

export function estadoDoDownload(t: Trabalho): string {
  switch (t.estado) {
    case 'rodando':
      return t.pct === null ? 'Baixando…' : `Baixando · ${t.pct}%`
    case 'cancelando':
      return 'Cancelando…'
    case 'cancelado':
      return 'Cancelado'
    case 'erro':
      return `Falhou: ${t.erro || 'erro desconhecido'}`
    default:
      return 'Concluído'
  }
}
