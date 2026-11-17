import { useEffect, useState } from 'preact/hooks'
import { GaleriaJogo } from '../../componentes/jogo/GaleriaJogo'
import { EmptyState } from '../../componentes/ui'
import { formatarPreco, type PrecoSteam } from '../../estado/desejos'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { ir } from '../../estado/rota'

interface PaginaSteam {
  appid: string
  nome: string
  resumo: string
  descricao: string
  generos: string[]
  desenvolvedora: string
  publicadora: string
  lancamento: string
  site: string
  hero_url: string
  logo_url: string
  capa_url: string
  screenshots: string[]
  preco: PrecoSteam | null
  url_loja: string
  na_biblioteca: number | null
  nos_desejos: boolean
}

interface Props {
  appid: string
  aoMudou: () => void
  aoAvisar: AoAvisar
}

/** Página de um jogo da loja Steam (`#/loja/:appid`), com o mesmo topo da página do jogo. */
export function PaginaLoja({ appid, aoMudou, aoAvisar }: Props) {
  const [pagina, setPagina] = useState<PaginaSteam | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [semHero, setSemHero] = useState(false)
  const [semLogo, setSemLogo] = useState(false)

  useEffect(() => {
    let vivo = true
    window.tucoteca
      .chamar<PaginaSteam>('loja.pagina', { appid })
      .then((r) => vivo && setPagina(r))
      .catch((falha) => vivo && setErro(textoDeFalha(falha)))
    return () => {
      vivo = false
    }
  }, [appid])

  const desejar = async () => {
    if (pagina === null) return
    try {
      await window.tucoteca.chamar('loja.desejar', { appid, titulo: pagina.nome })
      setPagina({ ...pagina, nos_desejos: true })
      aoAvisar(`${pagina.nome} entrou nos Desejos.`)
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  if (erro !== null) {
    return <EmptyState icone="⚠" titulo="Não abri a página da loja." descricao={erro} acao={{ rotulo: 'Voltar ao catálogo', onClick: () => ir('#/jogos/catalogo') }} />
  }
  if (pagina === null) return <p class="sub">Abrindo a página da loja…</p>

  const preco = formatarPreco(pagina.preco)
  const fundo = semHero ? pagina.capa_url : pagina.hero_url
  const ficha: Array<[string, string]> = [
    ['Desenvolvedora', pagina.desenvolvedora],
    ['Publicadora', pagina.publicadora],
    ['Lançamento', pagina.lancamento],
    ['Preço', preco],
  ]
  return (
    <article class="pagina-jogo pagina-loja">
      <header class={`hero-jogo${semHero ? ' sem-hero' : ''}`}>
        <div class="hero-arte">
          <img class="hero-fundo" src={fundo} alt="" onError={() => setSemHero(true)} />
        </div>
        <div class="hero-conteudo">
          {!semLogo ? (
            <img class="hero-logo" src={pagina.logo_url} alt={pagina.nome} onError={() => setSemLogo(true)} />
          ) : (
            <h1 class="hero-titulo">{pagina.nome}</h1>
          )}
          <p class="hero-linha">Loja Steam{pagina.generos.length > 0 ? ` · ${pagina.generos.slice(0, 3).join(', ')}` : ''}</p>
          <div class="hero-acoes">
            {pagina.na_biblioteca !== null ? (
              <button type="button" class="acao primaria hero-jogar" onClick={() => ir(`#/jogo/${pagina.na_biblioteca}`)}>
                Já na biblioteca · abrir
              </button>
            ) : pagina.nos_desejos ? (
              <button type="button" class="acao" disabled>
                ★ Nos desejos
              </button>
            ) : (
              <button type="button" class="acao primaria hero-jogar" onClick={() => void desejar()}>
                ☆ Adicionar aos Desejos
              </button>
            )}
            <button type="button" class="acao" onClick={() => void window.tucoteca.abrirUrl(pagina.url_loja)}>
              Ver na Steam ↗
            </button>
          </div>
          {preco !== '' && (
            <dl class="hero-metricas">
              <div>
                <dt>Preço</dt>
                <dd>{preco}</dd>
              </div>
            </dl>
          )}
        </div>
      </header>
      <div class="sobre-jogo">
        <div class="sobre-principal">
          {(pagina.descricao || pagina.resumo) !== '' && (
            <section class="bloco-jogo">
              <h3>Sobre</h3>
              <div class="descricao-jogo">
                {(pagina.descricao || pagina.resumo).split(/\n{2,}/).map((p, i) => (
                  <p key={i}>{p}</p>
                ))}
              </div>
            </section>
          )}
          {pagina.screenshots.length > 0 && (
            <section class="bloco-jogo">
              <h3>Imagens</h3>
              <GaleriaJogo urls={pagina.screenshots} titulo={pagina.nome} />
            </section>
          )}
        </div>
        <aside class="ficha-jogo">
          <dl>
            {ficha
              .filter(([, v]) => v !== '')
              .map(([rotulo, valor]) => (
                <div key={rotulo}>
                  <dt>{rotulo}</dt>
                  <dd>{valor}</dd>
                </div>
              ))}
          </dl>
          {pagina.generos.length > 0 && (
            <div class="generos">
              {pagina.generos.map((g) => (
                <span key={g} class="chip-estatico">
                  {g}
                </span>
              ))}
            </div>
          )}
          {pagina.site !== '' && (
            <button type="button" class="link-acao" onClick={() => void window.tucoteca.abrirUrl(pagina.site)}>
              Site oficial ↗
            </button>
          )}
        </aside>
      </div>
    </article>
  )
}
