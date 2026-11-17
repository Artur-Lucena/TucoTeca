import { useEffect, useRef } from 'preact/hooks'
import type { EstadoPaleta, ItemBusca } from '../../estado/paleta'

interface Props {
  estado: EstadoPaleta
  aoDigitar: (termo: string) => void
  aoMover: (delta: 1 | -1) => void
  aoDestacar: (indice: number) => void
  aoConfirmar: (indice?: number) => void
  aoFechar: () => void
}

export function Paleta({ estado, aoDigitar, aoMover, aoDestacar, aoConfirmar, aoFechar }: Props) {
  const campo = useRef<HTMLInputElement>(null)

  useEffect(() => {
    campo.current?.focus()
  }, [])

  const aoTeclarCampo = (evento: { key: string; preventDefault(): void }) => {
    if (evento.key === 'Escape') return aoFechar()
    if (evento.key === 'ArrowDown') {
      evento.preventDefault()
      return aoMover(1)
    }
    if (evento.key === 'ArrowUp') {
      evento.preventDefault()
      return aoMover(-1)
    }
    if (evento.key === 'Enter') aoConfirmar()
  }

  const vazio = estado.termo.trim() === ''
  return (
    <div
      class="paleta-fundo"
      onMouseDown={(evento) => {
        if (evento.target === evento.currentTarget) aoFechar()
      }}
    >
      <section class="paleta" role="dialog" aria-label="Busca global">
        <input
          ref={campo}
          class="paleta-campo"
          type="text"
          placeholder="Buscar na coleção…"
          value={estado.termo}
          onInput={(evento) => aoDigitar((evento.target as HTMLInputElement).value)}
          onKeyDown={aoTeclarCampo}
        />
        {vazio ? (
          <p class="paleta-dica">Digite para buscar jogos, músicas e desejos.</p>
        ) : estado.itens.length === 0 ? (
          <p class="paleta-dica">{estado.carregando ? 'Buscando…' : 'Nada encontrado.'}</p>
        ) : (
          <ul class="paleta-lista">
            {estado.itens.map((item, indice) => (
              <li key={`${item.tipo}-${String(item.id)}-${indice}`}>
                <button
                  type="button"
                  class={`paleta-item${indice === estado.selecionado ? ' ativo' : ''}`}
                  onMouseEnter={() => aoDestacar(indice)}
                  onClick={() => aoConfirmar(indice)}
                >
                  <Miniatura item={item} />
                  <span class="paleta-textos">
                    <span class="titulo">{item.titulo}</span>
                    <span class="meta">{item.sub ?? item.tipo}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <footer class="paleta-rodape">Enter abre · Esc fecha · ↑ ↓ navegam</footer>
      </section>
    </div>
  )
}

function Miniatura({ item }: { item: ItemBusca }) {
  const url = window.tucoteca.imagemUrl(String(item.capa_url ?? ''))
  if (url !== '') return <img class="paleta-capa" src={url} alt="" />
  const inicial = item.titulo.trim().charAt(0).toUpperCase()
  return <span class="paleta-inicial">{inicial || '?'}</span>
}
