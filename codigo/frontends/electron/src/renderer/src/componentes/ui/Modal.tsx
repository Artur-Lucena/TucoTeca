import { useEffect, useRef } from 'preact/hooks'
import { type ComponentChildren } from 'preact'

interface Props {
  aberto: boolean
  aoFechar: () => void
  titulo?: string
  children?: ComponentChildren
  largura?: string
}

/** Modal padronizado com overlay e fechamento por Esc. */
export function Modal({ aberto, aoFechar, titulo, children, largura = '480px' }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!aberto) return
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === 'Escape') aoFechar()
    }
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [aberto, aoFechar])
  if (!aberto) return null
  return (
    <div class="modal-fundo" onMouseDown={(e) => { if (e.target === e.currentTarget) aoFechar() }}>
      <div class="modal" style={{ maxWidth: largura }} ref={ref} role="dialog" aria-modal="true" aria-label={titulo}>
        {titulo !== undefined && (
          <header class="modal-topo">
            <h2>{titulo}</h2>
            <button type="button" class="acao" onClick={aoFechar} aria-label="Fechar">✕</button>
          </header>
        )}
        <div class="modal-corpo">{children}</div>
      </div>
    </div>
  )
}
