interface Props {
  valor: number
  label: string
  icone?: string
  trend?: string
}

/** Métrica/KPI padronizado. */
export function Metric({ valor, label, icone, trend }: Props) {
  return (
    <div class="metric">
      {icone !== undefined && <div class="metric-icone">{icone}</div>}
      <div class="metric-valor">{valor}</div>
      <div class="metric-label">{label}</div>
      {trend !== undefined && <div class="metric-trend">{trend}</div>}
    </div>
  )
}
