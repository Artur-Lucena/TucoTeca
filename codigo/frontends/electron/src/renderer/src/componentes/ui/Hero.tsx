import { useState } from 'preact/hooks'
import type { ComponentChildren } from 'preact'
import { iniciais } from '../../estado/formato'

export interface MetricaHero {
  rotulo: string
  valor: string
}

interface Props {
  /** Arte larga (hero); vazia ou com erro cai para `reserva` e marca `.sem-hero`. */
  arte: string
  /** Capa/pôster usado quando não há arte larga. */
  reserva?: string
  /** Logo; sem logo (ou se falhar) o título aparece em texto. */
  logo?: string
  titulo: string
  linha?: ComponentChildren
  acoes: ComponentChildren
  /** Abaixo das ações (aviso de sessão, barra de progresso…). */
  rodape?: ComponentChildren
  metricas?: MetricaHero[]
}

/** Topo das páginas de jogo, loja e filme/série: fundo, logo ou título, linha, ações e números. */
export function Hero(props: Props) {
  // trocar de jogo/título remonta: as falhas de imagem do anterior não valem para o novo
  return <HeroInterno key={`${props.arte}|${props.reserva ?? ''}|${props.logo ?? ''}`} {...props} />
}

function HeroInterno({ arte, reserva = '', logo = '', titulo, linha, acoes, rodape, metricas = [] }: Props) {
  const [arteFalhou, setArteFalhou] = useState(false)
  const [reservaFalhou, setReservaFalhou] = useState(false)
  const [logoFalhou, setLogoFalhou] = useState(false)
  const semArte = arte === '' || arteFalhou
  const fundo = !semArte ? arte : !reservaFalhou ? reserva : ''
  const comLogo = logo !== '' && !logoFalhou
  return (
    <header class={`hero-jogo${semArte ? ' sem-hero' : ''}`}>
      <div class="hero-arte">
        {fundo !== '' ? (
          <img
            class="hero-fundo"
            src={fundo}
            alt=""
            onError={() => (semArte ? setReservaFalhou(true) : setArteFalhou(true))}
          />
        ) : (
          <div class="hero-fundo hero-vazio" aria-hidden="true">
            {iniciais(titulo)}
          </div>
        )}
      </div>
      <div class="hero-conteudo">
        {comLogo && <img class="hero-logo" src={logo} alt="" onError={() => setLogoFalhou(true)} />}
        <h1 class={`hero-titulo${comLogo ? ' so-leitor' : ''}`}>{titulo}</h1>
        {linha !== undefined && linha !== '' && <p class="hero-linha">{linha}</p>}
        <div class="hero-acoes">{acoes}</div>
        {rodape}
        {metricas.length > 0 && (
          <dl class="hero-metricas">
            {metricas.map((m) => (
              <div key={m.rotulo}>
                <dt>{m.rotulo}</dt>
                <dd>{m.valor}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </header>
  )
}
