import type { EstadoConexao } from '../../estado/conexao'

interface Props {
  estado: EstadoConexao
  aoReconectar: () => void
}

export function AvisoPonte({ estado, aoReconectar }: Props) {
  if (estado === 'ok') return null
  const reabrindo = estado === 'reabrindo'
  return (
    <div class="aviso-ponte" role="alert">
      <span>
        {reabrindo
          ? 'Reconectando ao núcleo…'
          : 'O núcleo caiu — a coleção não está acessível.'}
      </span>
      <button type="button" onClick={aoReconectar} disabled={reabrindo}>
        {reabrindo ? 'Reconectando…' : 'Reconectar'}
      </button>
    </div>
  )
}
