import { horas } from '../../estado/formato'
import { origemDosDados, type PaginaJogo } from '../../estado/paginaJogo'
import { BlocoDescricao, FichaLateral } from '../ui'
import { GaleriaJogo } from './GaleriaJogo'

interface Props {
  pagina: PaginaJogo
  buscando: boolean
  aoBuscarDados: () => void
}

/** Visão geral: descrição, galeria e ficha (estúdio, lançamento, gêneros, horas para zerar). */
export function SobreJogo({ pagina, buscando, aoBuscarDados }: Props) {
  const { jogo, meta } = pagina
  const capa = window.tucoteca.imagemUrl(String(jogo.capa_url ?? ''))
  const descricao = meta.descricao || meta.resumo
  const ficha: Array<[string, string]> = [
    ['Desenvolvedora', meta.desenvolvedora],
    ['Publicadora', meta.publicadora],
    ['Lançamento', meta.lancamento],
  ]
  const origem = origemDosDados(pagina)
  return (
    <div class="sobre-jogo">
      <div class="sobre-principal">
        {!pagina.enriquecido && (
          <div class="cta-dados">
            <div>
              <strong>Esta página ainda está vazia.</strong>
              <p class="sub">Busque capa, descrição, arte e conquistas nos provedores ligados em Configurações.</p>
            </div>
            <button type="button" class="acao primaria" onClick={aoBuscarDados} disabled={buscando}>
              {buscando ? 'Buscando…' : 'Buscar capa, descrição e arte'}
            </button>
          </div>
        )}
        <BlocoDescricao titulo="Sobre" texto={descricao} recortar />
        {meta.screenshots_urls.length > 0 && (
          <section class="bloco-jogo">
            <h3>Imagens</h3>
            <GaleriaJogo urls={meta.screenshots_urls} titulo={String(jogo.titulo ?? '')} />
          </section>
        )}
      </div>
      <FichaLateral
        capa={capa}
        itens={ficha}
        generos={meta.generos}
        site={meta.site}
        origem={origem}
        extras={
          <>
            {meta.hltb !== null && meta.hltb.principal > 0 && (
              <div>
                <dt>Para zerar</dt>
                <dd>
                  {horas(meta.hltb.principal)} · com extras {horas(meta.hltb.extra)} · 100% {horas(meta.hltb.completo)}
                </dd>
              </div>
            )}
            {String(jogo.etiquetas ?? '').trim() !== '' && (
              <div>
                <dt>Etiquetas</dt>
                <dd>{String(jogo.etiquetas)}</dd>
              </div>
            )}
          </>
        }
      />
    </div>
  )
}
