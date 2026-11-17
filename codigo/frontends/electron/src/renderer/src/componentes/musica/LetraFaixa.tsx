import { useEffect, useRef, useState } from 'preact/hooks'
import { indiceLinha, normalizarLetra, pedidoLetra, type Letra } from '../../estado/letras'
import { textoDeFalha } from '../../estado/notificacoes'
import type { Faixa } from '../../estado/player'

interface Props {
  faixa: Faixa | null
  posicao: number
  duracao: number
}

/**
 * Letra da faixa atual (LRCLIB, com cache local). Só consulta quando o painel
 * está aberto — buscar letra é ação de rede do usuário, não automática.
 * Sincronizada: destaca a linha cantada e acompanha a rolagem.
 */
export function LetraFaixa({ faixa, posicao, duracao }: Props) {
  const [letra, setLetra] = useState<Letra | null>(null)
  const [carregando, setCarregando] = useState(false)
  const [falha, setFalha] = useState('')
  const atualRef = useRef<HTMLLIElement | null>(null)
  const pedido = pedidoLetra(faixa, duracao)
  const chave = pedido === null ? '' : `${pedido.artista}\u0000${pedido.titulo}`

  useEffect(() => {
    setLetra(null)
    setFalha('')
    if (pedido === null) return
    let vivo = true
    setCarregando(true)
    void (async () => {
      try {
        const r = normalizarLetra(await window.tucoteca.chamar('musicas.letras', pedido))
        if (vivo) setLetra(r)
      } catch (erro) {
        if (vivo) setFalha(textoDeFalha(erro))
      } finally {
        if (vivo) setCarregando(false)
      }
    })()
    return () => {
      vivo = false
    }
    // a duração chega depois do metadata; buscar de novo por ela não muda a letra
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave])

  const atual = letra?.sincronizadas ? indiceLinha(letra.linhas, posicao) : -1

  useEffect(() => {
    atualRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [atual])

  let corpo
  if (pedido === null) corpo = <p class="sub">Sem artista/título nesta faixa para buscar a letra.</p>
  else if (carregando) corpo = <p class="sub">Buscando letra…</p>
  else if (falha !== '') corpo = <p class="sub">{falha}</p>
  else if (letra === null || !letra.ok) corpo = <p class="sub">{letra?.erro || 'Letra não encontrada.'}</p>
  else if (letra.sincronizadas)
    corpo = (
      <ol class="letra-linhas">
        {letra.linhas.map((l, i) => (
          <li key={`${l.t}-${i}`} ref={i === atual ? atualRef : undefined} class={i === atual ? 'atual' : ''}>
            {l.texto || '♪'}
          </li>
        ))}
      </ol>
    )
  else corpo = <pre class="letra-texto">{letra.texto}</pre>

  return (
    <aside class="letra" aria-label="Letra da faixa" aria-live="off">
      {corpo}
    </aside>
  )
}
