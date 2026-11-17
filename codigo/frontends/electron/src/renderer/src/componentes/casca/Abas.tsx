import { ABAS, formatar, ir, NOMES_ABAS } from '../../estado/rota'

interface Props {
  secao: string
  ativa: string
}

/** Abas da seção (Biblioteca · Desejos, Vídeos · YouTube…), cada uma com seu endereço. */
export function Abas({ secao, ativa }: Props) {
  const abas = ABAS[secao] ?? []
  if (abas.length < 2) return null
  return (
    <nav class="abas" aria-label="Abas da seção">
      {abas.map((aba) => (
        <button
          key={aba}
          type="button"
          class={`aba${aba === ativa ? ' ativa' : ''}`}
          aria-current={aba === ativa ? 'page' : undefined}
          onClick={() => ir(formatar({ secao, aba, jogo: null }))}
        >
          {NOMES_ABAS[aba] ?? aba}
        </button>
      ))}
    </nav>
  )
}
