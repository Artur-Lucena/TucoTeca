import type { JogoResumo } from '../../estado/derivacoes'

export function Cartao({ jogo }: { jogo: JogoResumo }) {
  const url = window.tucoteca.imagemUrl(String(jogo.capa_url ?? ''))
  return (
    <article class="cartao">
      <div class="capa">
        {url ? (
          <img src={url} alt="" loading="lazy" />
        ) : (
          <div class="capa-vazia">{iniciais(jogo.titulo)}</div>
        )}
      </div>
      <div class="textos">
        <span class="titulo">{jogo.titulo}</span>
        <span class="meta">{metaDe(jogo)}</span>
      </div>
    </article>
  )
}

function iniciais(titulo?: string): string {
  const partes = String(titulo ?? '?').trim().split(/\s+/)
  return `${partes[0]?.charAt(0) ?? '?'}${partes[1]?.charAt(0) ?? ''}`.toUpperCase()
}

function metaDe(jogo: JogoResumo): string {
  const horas = Number(jogo.horas ?? 0)
  if (horas > 0) return `${horas.toLocaleString('pt-BR')} h jogadas`
  return jogo.ultima_execucao
    ? `jogado em ${String(jogo.ultima_execucao).slice(0, 10)}`
    : 'ainda não jogado'
}
