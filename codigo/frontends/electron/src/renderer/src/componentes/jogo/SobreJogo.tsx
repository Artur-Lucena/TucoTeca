import { useState } from 'preact/hooks'
import { horas } from '../../estado/formato'
import { origemDosDados, type PaginaJogo } from '../../estado/paginaJogo'
import { GaleriaJogo } from './GaleriaJogo'

interface Props {
  pagina: PaginaJogo
  buscando: boolean
  aoBuscarDados: () => void
}

/** Visão geral: descrição, galeria e ficha (estúdio, lançamento, gêneros, horas para zerar). */
export function SobreJogo({ pagina, buscando, aoBuscarDados }: Props) {
  const { jogo, meta } = pagina
  const [inteira, setInteira] = useState(false)
  const capa = window.tucoteca.imagemUrl(String(jogo.capa_url ?? ''))
  const descricao = meta.descricao || meta.resumo
  const longa = descricao.length > 600
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
        {descricao !== '' && (
          <section class="bloco-jogo">
            <h3>Sobre</h3>
            <div class={`descricao-jogo${longa && !inteira ? ' recortada' : ''}`}>
              {descricao.split(/\n{2,}/).map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>
            {longa && (
              <button type="button" class="link-acao" onClick={() => setInteira(!inteira)}>
                {inteira ? 'Mostrar menos' : 'Ler mais'}
              </button>
            )}
          </section>
        )}
        {meta.screenshots_urls.length > 0 && (
          <section class="bloco-jogo">
            <h3>Imagens</h3>
            <GaleriaJogo urls={meta.screenshots_urls} titulo={String(jogo.titulo ?? '')} />
          </section>
        )}
      </div>
      <aside class="ficha-jogo">
        {capa !== '' && <img class="ficha-capa" src={capa} alt="" />}
        <dl>
          {ficha
            .filter(([, valor]) => valor !== '')
            .map(([rotulo, valor]) => (
              <div key={rotulo}>
                <dt>{rotulo}</dt>
                <dd>{valor}</dd>
              </div>
            ))}
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
        </dl>
        {meta.generos.length > 0 && (
          <div class="generos">
            {meta.generos.map((g) => (
              <span key={g} class="chip-estatico">
                {g}
              </span>
            ))}
          </div>
        )}
        {meta.site !== '' && (
          <button type="button" class="link-acao" onClick={() => void window.tucoteca.abrirUrl(meta.site)}>
            Site oficial ↗
          </button>
        )}
        {origem !== '' && <p class="sub origem-dados">Dados: {origem}</p>}
      </aside>
    </div>
  )
}
