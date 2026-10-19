import { useState } from 'preact/hooks'
import { type ComponentChildren } from 'preact'

interface Props {
  children: ComponentChildren
  texto: string
  posicao?: 'topo' | 'baixo' | 'esquerda' | 'direita'
}

/** Tooltip simples (hover/focus). */
export function Tooltip({ children, texto, posicao = 'topo' }: Props) {
  const [visivel, setVisivel] = useState(false)
  return (
    <span
      class="tooltip-wrap"
      onMouseEnter={() => setVisivel(true)}
      onMouseLeave={() => setVisivel(false)}
      onFocus={() => setVisivel(true)}
      onBlur={() => setVisivel(false)}
    >
      {children}
      {visivel && <span class={`tooltip tooltip-${posicao}`} role="tooltip">{texto}</span>}
    </span>
  )
}
