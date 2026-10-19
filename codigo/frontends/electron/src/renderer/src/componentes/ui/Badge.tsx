import { type ComponentChildren } from 'preact'

interface Props {
  children?: ComponentChildren
  variant?: 'default' | 'brand' | 'success' | 'warning' | 'error'
  size?: 'sm' | 'md'
  class?: string
}

/** Badge/pill padronizado. */
export function Badge({ children, variant = 'default', size = 'md', class: classe = '' }: Props) {
  return <span class={`badge badge-${variant} badge-${size} ${classe}`}>{children}</span>
}
