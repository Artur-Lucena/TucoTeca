import type { ComponentChildren } from 'preact'
import { metricasDoJogo, type PaginaJogo } from '../../estado/paginaJogo'
import { iniciais } from './PosterCard'

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
  const hero = window.tucoteca.imagemUrl(meta.hero_url)
  const capa = window.tucoteca.imagemUrl(String(jogo.capa_url ?? ''))
  const logo = window.tucoteca.imagemUrl(meta.logo_url)
  const titulo = String(jogo.titulo ?? '')
  const linha = [jogo.plataforma, jogo.status].filter((x) => String(x ?? '') !== '').join(' · ')
  const fundo = hero !== '' ? hero : capa
  return (
    <header class={`hero-jogo${hero === '' ? ' sem-hero' : ''}`}>
      <div class="hero-arte">
        {fundo !== '' ? (
          <img class="hero-fundo" src={fundo} alt="" />
        ) : (
          <div class="hero-fundo hero-vazio" aria-hidden="true">
            {iniciais(titulo)}
          </div>
        )}
      </div>
      <div class="hero-conteudo">
        {logo !== '' ? <img class="hero-logo" src={logo} alt={titulo} /> : <h1 class="hero-titulo">{titulo}</h1>}
        {linha !== '' && <p class="hero-linha">{linha}</p>}
        <div class="hero-acoes">
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
        </div>
        {jogando !== null && <p class="hero-jogando">● {jogando}… aguarde a sessão fechar</p>}
        <dl class="hero-metricas">
          {metricasDoJogo(pagina).map((m) => (
            <div key={m.rotulo}>
              <dt>{m.rotulo}</dt>
              <dd>{m.valor}</dd>
            </div>
          ))}
        </dl>
      </div>
    </header>
  )
}
