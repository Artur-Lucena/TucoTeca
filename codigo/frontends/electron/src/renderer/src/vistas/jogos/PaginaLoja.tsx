import { useEffect, useState } from 'preact/hooks'
import { GaleriaJogo } from '../../componentes/jogo/GaleriaJogo'
import { BaixarDasFontes } from '../../componentes/jogo/BaixarDasFontes'
import { OndeBaixar } from '../../componentes/jogo/OndeBaixar'
import { BlocoDescricao, EmptyState, FichaLateral, Hero } from '../../componentes/ui'
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
  const ficha: Array<[string, string]> = [
    ['Desenvolvedora', pagina.desenvolvedora],
    ['Publicadora', pagina.publicadora],
    ['Lançamento', pagina.lancamento],
  ]
  return (
    <article class="pagina-jogo pagina-loja">
      <Hero
        arte={pagina.hero_url}
        reserva={pagina.capa_url}
        logo={pagina.logo_url}
        titulo={pagina.nome}
        linha={`Loja Steam${pagina.generos.length > 0 ? ` · ${pagina.generos.slice(0, 3).join(', ')}` : ''}`}
        metricas={preco !== '' ? [{ rotulo: 'Preço', valor: preco }] : []}
        acoes={
          <>
            {pagina.na_biblioteca !== null ? (
              <button type="button" class="acao primaria hero-jogar" onClick={() => ir(`#/jogo/${pagina.na_biblioteca}`)}>
                Já na biblioteca · abrir
              </button>
            ) : (
              <BaixarDasFontes titulo={pagina.nome} aoAvisar={aoAvisar} primario />
            )}
            {pagina.nos_desejos ? (
              <button type="button" class="acao" disabled>
                ★ Nos desejos
              </button>
            ) : (
              <button type="button" class="acao" onClick={() => void desejar()}>
                ☆ Desejos
              </button>
            )}
            <OndeBaixar titulo={pagina.nome} aoAvisar={aoAvisar} />
            <button type="button" class="acao" onClick={() => void window.tucoteca.abrirUrl(pagina.url_loja)}>
              Ver na Steam ↗
            </button>
          </>
        }
      />
      <div class="sobre-jogo">
        <div class="sobre-principal">
          <BlocoDescricao titulo="Sobre" texto={pagina.descricao || pagina.resumo} />
          {pagina.screenshots.length > 0 && (
            <section class="bloco-jogo">
              <h3>Imagens</h3>
              <GaleriaJogo urls={pagina.screenshots} titulo={pagina.nome} />
            </section>
          )}
        </div>
        <FichaLateral itens={ficha} generos={pagina.generos} site={pagina.site} />
      </div>
    </article>
  )
}
