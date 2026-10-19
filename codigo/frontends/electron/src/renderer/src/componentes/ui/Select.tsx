interface Opcao {
  valor: string
  rotulo: string
}

interface Props {
  label?: string
  value?: string
  opcoes: Opcao[]
  onChange?: (valor: string) => void
  class?: string
}

/** Select padronizado. */
export function Select({ label, value, opcoes, onChange, class: classe = '' }: Props) {
  return (
    <label class={`select-wrap ${classe}`}>
      {label !== undefined && <span class="input-label">{label}</span>}
      <select
        value={value}
        onChange={(e) => onChange?.((e.target as HTMLSelectElement).value)}
        class="select-campo"
      >
        {opcoes.map((o) => (
          <option key={o.valor} value={o.valor}>
            {o.rotulo}
          </option>
        ))}
      </select>
    </label>
  )
}
