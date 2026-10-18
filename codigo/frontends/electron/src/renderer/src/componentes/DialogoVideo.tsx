import { REPRODUTORES } from '../vistas/Videos'

interface Props {
  aberto: boolean
  valor: string
  aoEscolher: (reprodutor: string) => void
  aoFechar: () => void
}

/** Modal simples de escolha de reprodutor externo (VLC/MPV/MPC-HC/Auto). */
export function DialogoVideo({ aberto, valor, aoEscolher, aoFechar }: Props) {
  if (!aberto) return null
  return (
    <div class="dialogo-video-fundo" onClick={aoFechar}>
      <div class="dialogo-video" onClick={(evento) => evento.stopPropagation()}>
        <h2>Assistir com</h2>
        <select value={valor} onChange={(evento) => aoEscolher((evento.target as HTMLSelectElement).value)}>
          {REPRODUTORES.map((nome) => (
            <option key={nome} value={nome}>
              {nome}
            </option>
          ))}
        </select>
        <button type="button" class="acao" onClick={aoFechar}>
          Fechar
        </button>
      </div>
    </div>
  )
}
