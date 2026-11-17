import type { ComponentChildren } from 'preact'
import { metricasDoJogo, type PaginaJogo } from '../../estado/paginaJogo'
import { Hero } from '../ui'

interface Props {
  pagina: PaginaJogo
  /** Rótulo do jogo em andamento (qualquer um): bloqueia Jogar. */
  jogando: string | null
  buscando: boolean
  aoJogar: () => void
  aoFavoritar: () => void
  aoBuscarDados: () => void
  aoRemover: () => void
  /** Ações extras ao lado das principais (ex.: Coleções). */
  extras?: ComponentChildren
}

/** Topo da página do jogo: arte de fundo, logo (ou título), ações e números. */
export function HeroJogo({ pagina, jogando, buscando, aoJogar, aoFavoritar, aoBuscarDados, aoRemover, extras }: Props) {
  const { jogo, meta } = pagina
  const titulo = String(jogo.titulo ?? '')
  return (
    <Hero
      arte={window.tucoteca.imagemUrl(meta.hero_url)}
      reserva={window.tucoteca.imagemUrl(String(jogo.capa_url ?? ''))}
      logo={window.tucoteca.imagemUrl(meta.logo_url)}
      titulo={titulo}
      linha={[jogo.plataforma, jogo.status].filter((x) => String(x ?? '') !== '').join(' · ')}
      metricas={metricasDoJogo(pagina)}
      rodape={jogando !== null && <p class="hero-jogando">● {jogando}… aguarde a sessão fechar</p>}
      acoes={
        <>
          <button type="button" class="acao primaria hero-jogar" onClick={aoJogar} disabled={jogando !== null}>
            ▶ Jogar
          </button>
          <button type="button" class="acao" onClick={aoFavoritar} aria-pressed={jogo.favorito === true}>
            {jogo.favorito === true ? '★ Favorito' : '☆ Favoritar'}
          </button>
          <button type="button" class="acao" onClick={aoBuscarDados} disabled={buscando} title="Steam, SteamGridDB, RetroAchievements…">
            {buscando ? 'Buscando dados…' : pagina.enriquecido ? '↻ Atualizar dados' : 'Buscar dados'}
          </button>
          {extras}
          <button type="button" class="acao perigo" onClick={aoRemover}>
            Remover
          </button>
        </>
      }
    />
  )
}
