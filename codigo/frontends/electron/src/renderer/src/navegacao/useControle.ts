import { useEffect } from 'preact/hooks'
import type { ModuloDTO } from '../../../shared/protocolo'
import { historico, ir, podeVoltar, rota, voltar } from '../estado/rota'
import { LeitorControle, type EstadoPad } from './controle'
import { moverFoco, raizAtiva, trocarAba } from './foco'

/** Controle (gamepad) no app inteiro: direcional move o foco, A ativa, B volta, LB/RB trocam aba/seção. */
export function useControle(modulos: ModuloDTO[], abrirBusca: () => void) {
  useEffect(() => {
    const leitor = new LeitorControle()
    const neutro: EstadoPad = { cima: false, baixo: false, a: false, b: false }

    const lerPad = (): EstadoPad | null => {
      for (const pad of navigator.getGamepads()) {
        if (!pad || !pad.connected) continue
        // mapeamento "standard" (Xbox/PlayStation): 12–15 = direcional, 4/5 = LB/RB, 9 = Start
        const [ex = 0, ey = 0] = pad.axes
        const botao = (i: number) => pad.buttons[i]?.pressed === true
        return {
          cima: botao(12) || ey < -0.5,
          baixo: botao(13) || ey > 0.5,
          esquerda: botao(14) || ex < -0.5,
          direita: botao(15) || ex > 0.5,
          a: botao(0),
          b: botao(1),
          lb: botao(4),
          rb: botao(5),
          start: botao(9),
        }
      }
      return null
    }
    const reiniciar = () => leitor.reiniciar(lerPad() ?? neutro)
    reiniciar()
    window.addEventListener('gamepadconnected', reiniciar)
    window.addEventListener('focus', reiniciar)

    const raiz = document.documentElement
    const largarControle = () => raiz.classList.remove('navegando-controle')
    window.addEventListener('mousemove', largarControle)

    const trocarSecao = (delta: 1 | -1) => {
      if (modulos.length === 0) return
      const bruto = modulos.findIndex((modulo) => modulo.chave === rota.value.secao)
      const indice = bruto === -1 ? 0 : bruto
      const proximo = modulos[(indice + delta + modulos.length) % modulos.length]
      if (proximo !== undefined) ir(proximo.chave)
    }

    /** Esc no elemento focado: fecha diálogo, player, paleta ou gaveta abertos. */
    const fecharCamada = () => {
      const alvo = document.activeElement ?? document.body
      alvo.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    }

    const relogio = window.setInterval(() => {
      if (!document.hasFocus()) return
      const estado = lerPad()
      if (estado === null) return
      const acao = leitor.avaliar(estado, performance.now())
      if (acao === null) return
      raiz.classList.add('navegando-controle')
      if (acao === 'cima' || acao === 'baixo' || acao === 'esquerda' || acao === 'direita') {
        moverFoco(acao)
      } else if (acao === 'ativar') {
        const focado = document.activeElement
        if (focado instanceof HTMLElement && focado !== document.body) focado.click()
        else moverFoco('baixo')
      } else if (acao === 'voltar') {
        if (raizAtiva() !== document) fecharCamada()
        else if (podeVoltar(historico.value)) voltar()
        else ir('inicio')
      } else if (acao === 'aba-anterior' || acao === 'aba-seguinte') {
        const delta = acao === 'aba-seguinte' ? 1 : -1
        if (!trocarAba(delta)) trocarSecao(delta)
      } else if (acao === 'busca') {
        abrirBusca()
      }
    }, 100)

    return () => {
      window.clearInterval(relogio)
      window.removeEventListener('gamepadconnected', reiniciar)
      window.removeEventListener('focus', reiniciar)
      window.removeEventListener('mousemove', largarControle)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- abrirBusca só usa setters
  }, [modulos])
}
