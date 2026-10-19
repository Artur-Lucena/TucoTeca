interface Props {
  marcado?: boolean
  aoMudar?: (marcado: boolean) => void
  label?: string
  disabled?: boolean
}

/** Checkbox padronizado. */
export function Checkbox({ marcado = false, aoMudar, label, disabled = false }: Props) {
  return (
    <label class="checkbox-wrap">
      <input
        type="checkbox"
        checked={marcado}
        disabled={disabled}
        onChange={(e) => aoMudar?.((e.target as HTMLInputElement).checked)}
      />
      {label !== undefined && <span>{label}</span>}
    </label>
  )
}
