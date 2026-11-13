import { useEffect, useState } from 'preact/hooks'

interface EstadoVolume {
  ok?: boolean
  nivel?: number
  mudo?: boolean
  erro?: string
}

/**
 * Volume geral do Windows (Core Audio via núcleo). Fora do Windows ou sem
 * dispositivo a ponte responde ok=false e o controle simplesmente não aparece.
 * O nível só é gravado ao soltar o controle (change), não a cada pixel.
 */
export function VolumePC() {
  const [estado, setEstado] = useState<EstadoVolume | null>(null)
  const [arrasto, setArrasto] = useState<number | null>(null)

  useEffect(() => {
    void (async () => {
      try {
        setEstado(await window.tucoteca.chamar<EstadoVolume>('sistema.volume'))
      } catch {
        setEstado({ ok: false })
      }
    })()
  }, [])

  if (estado === null || estado.ok !== true) return null

  const nivel = arrasto ?? Math.round(Number(estado.nivel ?? 0))

  const definir = async (valor: number) => {
    try {
      setEstado(await window.tucoteca.chamar<EstadoVolume>('sistema.volume_definir', { nivel: valor }))
    } catch {
      // mantém o último estado conhecido; o próximo ajuste tenta de novo
    } finally {
      setArrasto(null)
    }
  }

  const mudo = async () => {
    try {
      setEstado(await window.tucoteca.chamar<EstadoVolume>('sistema.volume_mudo'))
    } catch {
      // idem
    }
  }

  return (
    <span class="volume-pc" title={`Volume do PC: ${nivel}%${estado.mudo ? ' (mudo)' : ''}`}>
      <button
        type="button"
        class="player-botao"
        aria-label={estado.mudo ? 'Ativar som do PC' : 'Silenciar o PC'}
        onClick={() => void mudo()}
      >
        {estado.mudo ? '🔇' : '🖥'}
      </button>
      <input
        class="player-volume"
        type="range"
        min={0}
        max={100}
        step={1}
        value={nivel}
        aria-label="Volume do PC"
        onInput={(e) => setArrasto(Number((e.target as HTMLInputElement).value))}
        onChange={(e) => void definir(Number((e.target as HTMLInputElement).value))}
      />
    </span>
  )
}
