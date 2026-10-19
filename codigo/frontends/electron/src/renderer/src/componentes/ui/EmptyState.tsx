interface Props {
  icone?: string
  titulo: string
  descricao?: string
  acao?: { rotulo: string; onClick: () => void }
}

/** Estado vazio padronizado (Untitled UI style). */
export function EmptyState({ icone = '∅', titulo, descricao, acao }: Props) {
  return (
    <div class="empty-state">
      <div class="empty-icone">{icone}</div>
      <h3>{titulo}</h3>
      {descricao !== undefined && <p>{descricao}</p>}
      {acao !== undefined && (
        <button type="button" class="acao primaria" onClick={acao.onClick}>
          {acao.rotulo}
        </button>
      )}
    </div>
  )
}
