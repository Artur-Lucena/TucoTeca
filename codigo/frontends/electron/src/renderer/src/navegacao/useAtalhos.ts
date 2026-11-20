import { useEffect } from 'preact/hooks'
import { ehMac } from '../plataforma'
import { chaveLegada, avancar, ir, rota, voltar } from '../estado/rota'
import { combinacao, decidirAtalho } from './atalhos'
import { modoTv, moverFoco, type Direcao } from './foco'

const SETAS: Record<string, Direcao> = { Up: 'cima', Down: 'baixo', Left: 'esquerda', Right: 'direita' }

interface Acoes {
  abrirPaleta: () => void
  fecharPaleta: () => void
  focarBusca: () => void
}

/** Teclado (atalhos pessoais, Alt+setas, setas no Big Picture) e botões laterais do mouse. */
export function useAtalhos(paletaAberta: boolean, atalhos: Record<string, string>, acoes: Acoes) {
  useEffect(() => {
    const aoTeclar = (evento: KeyboardEvent) => {
      const comb = combinacao(evento, ehMac())
      const alvo = evento.target as HTMLElement | null
      const emCampo =
        alvo instanceof HTMLInputElement || alvo instanceof HTMLTextAreaElement || alvo instanceof HTMLSelectElement
      // Big Picture: setas do teclado/controle remoto andam pelo foco (fora de campos de texto)
      if (modoTv() && !paletaAberta && SETAS[comb ?? ''] !== undefined) {
        if (!emCampo) {
          if (moverFoco(SETAS[comb ?? ''])) evento.preventDefault()
          return
        }
      }
      if (!paletaAberta && !emCampo && (comb === 'Alt+Left' || comb === 'Alt+Right')) {
        evento.preventDefault()
        if (comb === 'Alt+Left') voltar()
        else avancar()
        return
      }
      const decisao = decidirAtalho(paletaAberta, comb, atalhos, chaveLegada(rota.value))
      if (decisao === null) return
      evento.preventDefault()
      if (decisao.tipo === 'paleta') acoes.abrirPaleta()
      else if (decisao.tipo === 'fechar') acoes.fecharPaleta()
      else if (decisao.tipo === 'focar-busca') acoes.focarBusca()
      else ir(decisao.chave)
    }
    // botões laterais do mouse (voltar/avançar), como num navegador
    const aoMouse = (evento: MouseEvent) => {
      if (evento.button === 3) voltar()
      else if (evento.button === 4) avancar()
    }
    window.addEventListener('keydown', aoTeclar)
    window.addEventListener('mouseup', aoMouse)
    return () => {
      window.removeEventListener('keydown', aoTeclar)
      window.removeEventListener('mouseup', aoMouse)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- as ações só usam setters
  }, [paletaAberta, atalhos])
}
