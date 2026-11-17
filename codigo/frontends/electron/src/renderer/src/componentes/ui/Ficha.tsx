import { useState } from 'preact/hooks'
import type { ComponentChildren } from 'preact'

/** Bloco de texto longo ("Sobre", "Sinopse"): parágrafos e, se `recortar`, "Ler mais". */
export function BlocoDescricao({ titulo, texto, recortar = false }: { titulo: string; texto: string; recortar?: boolean }) {
  const [inteira, setInteira] = useState(false)
  if (texto === '') return null
  const longa = recortar && texto.length > 600
  return (
    <section class="bloco-jogo">
      <h3>{titulo}</h3>
      <div class={`descricao-jogo${longa && !inteira ? ' recortada' : ''}`}>
        {texto.split(/\n{2,}/).map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>
      {longa && (
        <button type="button" class="link-acao" onClick={() => setInteira(!inteira)}>
          {inteira ? 'Mostrar menos' : 'Ler mais'}
        </button>
      )}
    </section>
  )
}

interface PropsFicha {
  capa?: string
  /** [rótulo, valor]; valores vazios não aparecem. */
  itens?: Array<[string, string]>
  generos?: string[]
  site?: string
  origem?: string
  /** Linhas extras da lista (dentro do <dl>). */
  extras?: ComponentChildren
}

/** Coluna lateral das páginas: capa, ficha técnica, gêneros, site e origem dos dados. */
export function FichaLateral({ capa = '', itens = [], generos = [], site = '', origem = '', extras }: PropsFicha) {
  const [semCapa, setSemCapa] = useState(false)
  const visiveis = itens.filter(([, valor]) => valor !== '')
  return (
    <aside class="ficha-jogo">
      {capa !== '' && !semCapa && <img class="ficha-capa" src={capa} alt="" onError={() => setSemCapa(true)} />}
      {(visiveis.length > 0 || extras !== undefined) && (
        <dl>
          {visiveis.map(([rotulo, valor]) => (
            <div key={rotulo}>
              <dt>{rotulo}</dt>
              <dd>{valor}</dd>
            </div>
          ))}
          {extras}
        </dl>
      )}
      {generos.length > 0 && (
        <div class="generos">
          {generos.map((g) => (
            <span key={g} class="chip-estatico">
              {g}
            </span>
          ))}
        </div>
      )}
      {site !== '' && (
        <button type="button" class="link-acao" onClick={() => void window.tucoteca.abrirUrl(site)}>
          Site oficial ↗
        </button>
      )}
      {origem !== '' && <p class="sub origem-dados">Dados: {origem}</p>}
    </aside>
  )
}
