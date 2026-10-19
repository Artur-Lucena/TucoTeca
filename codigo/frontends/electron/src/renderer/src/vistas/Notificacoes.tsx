import { useState } from 'preact/hooks'
import { EmptyState } from '../componentes/ui'
import type { Aviso } from '../estado/notificacoes'

interface Props {
  avisos: Aviso[]
  aoDispensar: (id: string) => void
  aoLimpar: () => void
}

/** Tela Notificações: histórico completo dos avisos do sistema. */
export function Notificacoes({ avisos, aoDispensar, aoLimpar }: Props) {
  const [filtro, setFiltro] = useState<'todos' | 'atencao' | 'info'>('todos')
  const [busca, setBusca] = useState('')

  const lista = avisos.filter((a) => {
    if (filtro !== 'todos' && a.tom !== filtro) return false
    if (busca.trim() === '') return true
    return a.texto.toLowerCase().includes(busca.trim().toLowerCase())
  })

  return (
    <section class="vista notificacoes">
      <header class="vista-topo">
        <h1>Notificações ({avisos.length})</h1>
        <div class="vista-acoes">
          <input
            class="busca"
            type="search"
            placeholder="Buscar nos avisos…"
            value={busca}
            onInput={(evento) => setBusca((evento.target as HTMLInputElement).value)}
          />
          <select
            class="filtro-avisos"
            value={filtro}
            onChange={(evento) => setFiltro((evento.target as HTMLSelectElement).value as 'todos' | 'atencao' | 'info')}
          >
            <option value="todos">Todos</option>
            <option value="atencao">Atenção</option>
            <option value="info">Info</option>
          </select>
          <button type="button" class="acao perigo" onClick={aoLimpar} disabled={avisos.length === 0}>
            Limpar tudo
          </button>
        </div>
      </header>

      {lista.length === 0 ? (
        <EmptyState icone="🔔" titulo="Nenhuma notificação." />
      ) : (
        <ul class="lista-notificacoes">
          {lista.map((aviso) => (
            <li key={aviso.id} class={`linha-aviso${aviso.tom === 'atencao' ? ' atencao' : ''}`}>
              <span class="aviso-texto">{aviso.texto}</span>
              <button type="button" class="acao" onClick={() => aoDispensar(aviso.id)}>
                Dispensar
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
