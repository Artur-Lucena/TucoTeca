export type EstadoConexao = 'ok' | 'reabrindo' | 'caiu'

type EventoConexao = { tipo: 'caiu' } | { tipo: 'reabrindo' } | { tipo: 'ok' }

/**
 * Estado da ponte no renderer: queda vem de qualquer estado; "reabrindo" só
 * faz sentido depois de uma queda; "ok" encerra a reabertura.
 */
export function reduzirConexao(estado: EstadoConexao, evento: EventoConexao): EstadoConexao {
  switch (evento.tipo) {
    case 'caiu':
      return 'caiu'
    case 'reabrindo':
      return estado === 'caiu' ? 'reabrindo' : estado
    case 'ok':
      return 'ok'
  }
}
