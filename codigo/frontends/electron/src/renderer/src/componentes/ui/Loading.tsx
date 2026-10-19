import { type ComponentChildren } from 'preact'

interface Props {
  children?: ComponentChildren
  class?: string
}

/** Loading indicator (spinner). */
export function Loading({ children, class: classe = '' }: Props) {
  return (
    <div class={`loading ${classe}`}>
      <span class="loading-spinner" />
      {children !== undefined && <span>{children}</span>}
    </div>
  )
}
