import { iniciais } from '../../estado/formato'
import type { JogoDaLista } from '../../estado/jogos'

interface Props {
  jogo: JogoDaLista
  selecionado: boolean
  aoSelecionar: () => void
  aoAbrir?: () => void
  aoJogar?: () => void
}

export function PosterCard({ jogo, selecionado, aoSelecionar, aoAbrir, aoJogar }: Props) {
  const url = window.tucoteca.imagemUrl(String(jogo.capa_url ?? ''))
  return (
    <article
      class={`cartao poster ${selecionado ? 'selecionado' : ''}`}
      onClick={aoSelecionar}
      onDblClick={aoJogar}
      onContextMenu={(evento) => {
        if (aoAbrir === undefined) return
        evento.preventDefault()
        aoAbrir()
      }}
    >
      <div class="capa">
        {url ? (
          <img
            src={url}
            alt=""
            loading="lazy"
            // arte horizontal (cabeçalho da loja) aparece inteira em vez de cortada na capa em pé
            onLoad={(evento) => {
              const img = evento.currentTarget as HTMLImageElement
              img.classList.toggle('horizontal', img.naturalWidth > img.naturalHeight)
            }}
          />
        ) : (
          <div class="capa-vazia">{iniciais(jogo.titulo)}</div>
        )}
        {jogo.favorito === true && (
          <span class="selo-favorito" title="Favorito">
            ★
          </span>
        )}
      </div>
      <div class="textos">
        <span class="titulo">{jogo.titulo}</span>
        <span class="meta">{[jogo.plataforma, metaDe(jogo)].filter(Boolean).join(' · ')}</span>
      </div>
      {(aoJogar !== undefined || aoAbrir !== undefined) && (
        <div class="acoes">
          {aoJogar !== undefined && (
            <button
              class="acao"
              onClick={(evento) => {
                evento.stopPropagation()
                aoJogar()
              }}
            >
              Jogar
            </button>
          )}
          {aoAbrir !== undefined && (
            <button
              class="acao"
              onClick={(evento) => {
                evento.stopPropagation()
                aoAbrir()
              }}
            >
              Abrir
            </button>
          )}
        </div>
      )}
    </article>
  )
}

function metaDe(jogo: JogoDaLista): string {
  const horas = Number(jogo.horas ?? 0)
  if (horas > 0) return `${horas.toLocaleString('pt-BR')} h`
  return jogo.ultima_execucao ? `jogado ${String(jogo.ultima_execucao).slice(0, 10)}` : 'nunca jogado'
}
