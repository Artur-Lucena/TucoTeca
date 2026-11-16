import { useEffect, useState } from 'preact/hooks'
import { Modal } from '../ui'

interface Props {
  urls: string[]
  titulo: string
}

/** Miniaturas das screenshots; clicar abre em tamanho grande (← → navegam). */
export function GaleriaJogo({ urls, titulo }: Props) {
  const [aberta, setAberta] = useState<number | null>(null)

  useEffect(() => {
    if (aberta === null) return
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') setAberta((i) => (i === null ? i : (i + 1) % urls.length))
      if (e.key === 'ArrowLeft') setAberta((i) => (i === null ? i : (i - 1 + urls.length) % urls.length))
    }
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [aberta, urls.length])

  return (
    <>
      <div class="galeria-jogo">
        {urls.map((u, i) => (
          <button key={u} type="button" class="galeria-item" onClick={() => setAberta(i)} aria-label={`Abrir imagem ${i + 1}`}>
            <img src={window.tucoteca.imagemUrl(u)} alt="" loading="lazy" />
          </button>
        ))}
      </div>
      <Modal aberto={aberta !== null} aoFechar={() => setAberta(null)} titulo={`${titulo} · ${(aberta ?? 0) + 1}/${urls.length}`} largura="1100px">
        {aberta !== null && <img class="galeria-grande" src={window.tucoteca.imagemUrl(urls[aberta] ?? '')} alt="" />}
      </Modal>
    </>
  )
}
