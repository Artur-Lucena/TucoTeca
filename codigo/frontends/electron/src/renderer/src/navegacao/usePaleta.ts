import { useEffect, useState } from 'preact/hooks'
import { paletaInicial, reduzirPaleta, type ItemBusca } from '../estado/paleta'

type AcaoPaleta = Parameters<typeof reduzirPaleta>[1]

/** Estado da paleta de busca (Ctrl+K) e a busca no núcleo com 150 ms de espera. */
export function usePaleta() {
  const [paleta, setPaleta] = useState(paletaInicial)
  const despachar = (acao: AcaoPaleta) => setPaleta((atual) => reduzirPaleta(atual, acao))

  useEffect(() => {
    if (!paleta.aberta) return
    const termo = paleta.termo
    if (!termo.trim()) return
    let vivo = true
    const timer = setTimeout(() => {
      void (async () => {
        let itens: ItemBusca[] = []
        try {
          itens = await window.tucoteca.chamar<ItemBusca[]>('nucleo.buscar', { termo, limite: 12 })
        } catch {
          itens = []
        }
        if (vivo) despachar({ tipo: 'resultados', termo, itens })
      })()
    }, 150)
    return () => {
      vivo = false
      clearTimeout(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- despachar só usa o setter
  }, [paleta.aberta, paleta.termo])

  return [paleta, despachar] as const
}
