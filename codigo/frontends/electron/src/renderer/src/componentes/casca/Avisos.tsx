import { useEffect, useRef, useState } from 'preact/hooks'
import type { Aviso } from '../../estado/notificacoes'

interface Props {
  avisos: Aviso[]
  aoDispensar: (id: string) => void
  aoVerTodas?: () => void
  aoLimpar?: () => void
}

/** Sino do cabeçalho: contador e painel com os avisos recentes. */
export function Avisos({ avisos, aoDispensar, aoVerTodas, aoLimpar }: Props) {
  const [aberto, setAberto] = useState(false)
  const raiz = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!aberto) return
    const fora = (evento: MouseEvent) => {
      if (raiz.current !== null && !raiz.current.contains(evento.target as Node)) setAberto(false)
    }
    const esc = (evento: KeyboardEvent) => {
      if (evento.key === 'Escape') setAberto(false)
    }
    document.addEventListener('mousedown', fora)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', fora)
      document.removeEventListener('keydown', esc)
    }
  }, [aberto])

  return (
    <div class="avisos" ref={raiz}>
      <button
        type="button"
        class="avisos-botao"
        aria-expanded={aberto}
        aria-label={`Notificações (${avisos.length})`}
        title="Notificações"
        onClick={() => setAberto(!aberto)}
      >
        <span aria-hidden="true">🔔</span>
        {avisos.length > 0 && <span class="avisos-contador">{avisos.length}</span>}
      </button>
      {aberto && (
        <div class="avisos-painel" aria-live="polite" role="status">
          {avisos.length === 0 ? (
            <p class="avisos-vazio">Nada por aqui.</p>
          ) : (
            <ul>
              {avisos.map((aviso) => (
                <li key={aviso.id} class={aviso.tom}>
                  <span>{aviso.texto}</span>
                  <button
                    type="button"
                    class="avisos-dispensar"
                    aria-label="Dispensar aviso"
                    onClick={() => aoDispensar(aviso.id)}
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
          {aoLimpar !== undefined && avisos.length > 0 && (
            <button type="button" class="avisos-ver-todas" onClick={aoLimpar}>
              Limpar tudo
            </button>
          )}
          {aoVerTodas !== undefined && (
            <button
              type="button"
              class="avisos-ver-todas"
              onClick={() => {
                setAberto(false)
                aoVerTodas()
              }}
            >
              Ver todas
            </button>
          )}
        </div>
      )}
    </div>
  )
}
