import { useEffect, useRef } from 'preact/hooks'
import type { RefObject } from 'preact'
import { modoTv } from './foco'

/** Camadas que tomam o teclado (paleta, diálogos, player): a lista de baixo não reage. */
const CAMADAS = '.paleta-fundo, .modal-fundo, .player-tela'

/**
 * Guarda comum das listas navegáveis por seta: no Big Picture as setas são do
 * foco espacial; atalhos com modificador e camadas abertas ficam de fora; num
 * campo de texto só o campo de busca da própria tela deixa passar.
 */
export function teclaDaLista(evento: KeyboardEvent, campo?: HTMLElement | null): boolean {
  if (modoTv() && evento.key.startsWith('Arrow')) return false
  if (evento.ctrlKey || evento.altKey || evento.metaKey) return false
  if (document.querySelector(CAMADAS) !== null) return false
  const alvo = evento.target as HTMLElement | null
  return !(alvo !== null && alvo !== campo && alvo.closest('input, textarea, select') !== null)
}

/**
 * Lista vertical: ↑/↓ movem a seleção (presa às pontas) e Enter, se houver
 * `aoEnter`, age no item — exceto digitando na busca.
 */
export function useSetasLista(
  total: number,
  setSelecionado: (mudar: (atual: number) => number) => void,
  aoEnter?: () => void,
  campo?: RefObject<HTMLElement | null>,
): void {
  const enter = useRef(aoEnter)
  enter.current = aoEnter
  useEffect(() => {
    const aoTeclar = (evento: KeyboardEvent) => {
      if (!teclaDaLista(evento, campo?.current)) return
      if (evento.key === 'Enter') {
        if (enter.current === undefined || total === 0 || evento.target === campo?.current) return
        evento.preventDefault()
        enter.current()
        return
      }
      if (evento.key !== 'ArrowDown' && evento.key !== 'ArrowUp') return
      evento.preventDefault()
      const passo = evento.key === 'ArrowDown' ? 1 : -1
      setSelecionado((atual) => Math.max(0, Math.min(total - 1, Math.min(atual, Math.max(0, total - 1)) + passo)))
    }
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [total, campo, setSelecionado])
}
