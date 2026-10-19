import { type ComponentChildren } from 'preact'

interface Props {
  children?: ComponentChildren
  class?: string
}

/** Divisor horizontal. */
export function Divider({ children, class: classe = '' }: Props) {
  if (children === undefined) return <hr class={`divider ${classe}`} />
  return (
    <div class={`divider-com-texto ${classe}`}>
      <span>{children}</span>
    </div>
  )
}
