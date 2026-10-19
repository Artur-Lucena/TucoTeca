interface Props {
  marcado?: boolean
  aoMudar?: (marcado: boolean) => void
  label?: string
  disabled?: boolean
}

/** Toggle/switch padronizado. */
export function Toggle({ marcado = false, aoMudar, label, disabled = false }: Props) {
  return (
    <label class="toggle-wrap">
      {label !== undefined && <span class="toggle-label">{label}</span>}
      <button
        type="button"
        role="switch"
        aria-checked={marcado}
        class={`toggle ${marcado ? 'ativo' : ''}`}
        disabled={disabled}
        onClick={() => aoMudar?.(!marcado)}
      >
        <span class="toggle-thumb" />
      </button>
    </label>
  )
}
