import { type ComponentChildren } from 'preact'

interface Props {
  children?: ComponentChildren
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  loading?: boolean
  onClick?: () => void
  type?: 'button' | 'submit'
  class?: string
}

/** Botão padronizado (Untitled UI style). */
export function Botao({
  children,
  variant = 'secondary',
  size = 'md',
  disabled = false,
  loading = false,
  onClick,
  type = 'button',
  class: classe = '',
}: Props) {
  return (
    <button
      type={type}
      class={`btn btn-${variant} btn-${size} acao ${classe}`}
      disabled={disabled || loading}
      onClick={onClick}
    >
      {loading && <span class="btn-spinner" />}
      {children}
    </button>
  )
}
