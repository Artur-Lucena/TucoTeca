import { type ComponentChildren } from 'preact'

interface Props {
  children?: ComponentChildren
  titulo?: string
  class?: string
  hover?: boolean
}

/** Card padronizado com sombra e hover lift. */
export function Card({ children, titulo, class: classe = '', hover = true }: Props) {
  return (
    <div class={`card ${hover ? 'card-hover' : ''} ${classe}`}>
      {titulo !== undefined && <h3 class="card-titulo">{titulo}</h3>}
      {children}
    </div>
  )
}
