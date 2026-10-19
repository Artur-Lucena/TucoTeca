import { useEffect } from 'preact/hooks'
import { type ComponentChildren } from 'preact'

interface Props {
  aberto: boolean
  aoFechar: () => void
  titulo?: string
  lado?: 'direita' | 'esquerda'
  largura?: string
  children?: ComponentChildren
}

/** Drawer lateral (slide-in). */
export function Drawer({ aberto, aoFechar, titulo, lado = 'direita', largura = '360px', children }: Props) {
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
    <div class="drawer-fundo" onMouseDown={(e) => { if (e.target === e.currentTarget) aoFechar() }}>
      <div class={`drawer drawer-${lado}`} style={{ width: largura }} role="dialog" aria-modal="true" aria-label={titulo}>
        {titulo !== undefined && (
          <header class="drawer-topo">
            <h2>{titulo}</h2>
            <button type="button" class="acao" onClick={aoFechar} aria-label="Fechar">✕</button>
          </header>
        )}
        <div class="drawer-corpo">{children}</div>
      </div>
    </div>
  )
}
