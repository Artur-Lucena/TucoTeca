import { useState } from 'preact/hooks'
import type { Aviso } from '../estado/notificacoes'

interface Props {
  avisos: Aviso[]
  aoDispensar: (id: string) => void
}

export function Avisos({ avisos, aoDispensar }: Props) {
  const [aberto, setAberto] = useState(false)
  return (
    <div class="avisos">
      {aberto && (
        <div class="avisos-painel">
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
        </div>
      )}
      <button
        type="button"
        class="avisos-botao"
        aria-expanded={aberto}
        onClick={() => setAberto(!aberto)}
      >
        <span>Notificações</span>
        {avisos.length > 0 && <span class="avisos-contador">{avisos.length}</span>}
      </button>
    </div>
  )
}
