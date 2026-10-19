import { type ComponentChildren } from 'preact'

interface Props {
  label?: string
  value?: string
  placeholder?: string
  type?: string
  onInput?: (valor: string) => void
  disabled?: boolean
  class?: string
  children?: ComponentChildren
}

/** Input padronizado. */
export function Input({ label, value, placeholder, type = 'text', onInput, disabled = false, class: classe = '' }: Props) {
  return (
    <label class={`input-wrap ${classe}`}>
      {label !== undefined && <span class="input-label">{label}</span>}
      <input
        type={type as any}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        onInput={(e) => onInput?.((e.target as HTMLInputElement).value)}
        class="input-campo"
      />
    </label>
  )
}
