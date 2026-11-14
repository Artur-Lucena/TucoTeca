import { useEffect, useRef } from 'preact/hooks'
import { confirmar, pedidoConfirmacao, responderConfirmacao } from '../estado/confirmacao'
import { Modal } from './ui'

export { confirmar }

/**
 * Desenha o pedido de `confirmar()` (montado uma vez no App). Esc e Enter são
 * tratados na fase de captura e param ali: o Esc do detalhe do jogo (que também
 * escuta no window) não fecha a gaveta junto com a confirmação.
 */
export function ConfirmacaoHost() {
  const pedido = pedidoConfirmacao.value
  const botoes = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (pedido === null) return
    const alvo = botoes.current?.querySelector<HTMLButtonElement>(pedido.perigo ? '.cancelar' : '.confirmar')
    alvo?.focus()
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key !== 'Escape' && e.key !== 'Enter') return
      // Enter num botão focado já dispara o clique; aqui só o Esc e o Enter "solto"
      if (e.key === 'Enter' && document.activeElement instanceof HTMLButtonElement) return
      e.preventDefault()
      e.stopImmediatePropagation()
      responderConfirmacao(e.key === 'Enter' && !pedido.perigo)
    }
    window.addEventListener('keydown', aoTeclar, true)
    return () => window.removeEventListener('keydown', aoTeclar, true)
  }, [pedido])

  return (
    <Modal aberto={pedido !== null} aoFechar={() => responderConfirmacao(false)} titulo={pedido?.titulo} largura="460px">
      <p class="confirmacao-texto">{pedido?.texto}</p>
      <div class="confirmacao-botoes" ref={botoes}>
        <button type="button" class="acao cancelar" onClick={() => responderConfirmacao(false)}>
          Cancelar
        </button>
        <button
          type="button"
          class={`acao confirmar ${pedido?.perigo ? 'perigo' : 'primaria'}`}
          onClick={() => responderConfirmacao(true)}
        >
          {pedido?.confirmar ?? 'Confirmar'}
        </button>
      </div>
    </Modal>
  )
}
