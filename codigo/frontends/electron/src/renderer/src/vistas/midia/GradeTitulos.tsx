import { ir } from '../../estado/rota'

export interface CartaoTitulo {
  imdb_id: string
  tipo: 'movie' | 'series'
  nome: string
  ano?: string
  poster: string
  selo?: string
  fracao?: number
  aoClicar?: () => void
}

/** Grade de pôsteres (filmes e séries); clicar abre `#/titulo/:imdb` (ou a ação do cartão). */
export function GradeTitulos({ itens }: { itens: CartaoTitulo[] }) {
  return (
    <div class="grade-titulos">
      {itens.map((t, i) => (
        <button key={`${t.imdb_id}-${i}`} type="button" class="cartao-titulo" title={t.nome} onClick={t.aoClicar ?? (() => ir(`#/titulo/${t.imdb_id}`))}>
          <span class="cartao-titulo-poster">
            {t.poster !== '' ? (
              <img src={window.tucoteca.imagemUrl(t.poster)} alt="" loading="lazy" onError={(e) => ((e.target as HTMLImageElement).style.display = 'none')} />
            ) : null}
            <span class="cartao-titulo-vazio" aria-hidden="true">
              {t.nome.charAt(0)}
            </span>
            {t.selo !== undefined && t.selo !== '' && <span class="cartao-titulo-selo">{t.selo}</span>}
            {t.fracao !== undefined && t.fracao > 0 && (
              <span class="cartao-titulo-barra" aria-hidden="true">
                <span style={{ width: `${Math.round(t.fracao * 100)}%` }} />
              </span>
            )}
          </span>
          <span class="cartao-titulo-nome">{t.nome}</span>
          {t.ano !== undefined && t.ano !== '' && <span class="sub">{t.ano}</span>}
        </button>
      ))}
    </div>
  )
}
