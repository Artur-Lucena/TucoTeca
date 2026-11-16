import type { Aviso } from '../estado/notificacoes'
import { avancar, historico, ir, podeAvancar, podeVoltar, voltar } from '../estado/rota'
import { Avisos } from './Avisos'

interface Props {
  titulo: string
  avisos: Aviso[]
  aoDispensarAviso: (id: string) => void
  aoBuscar: () => void
  perfil: string
  aoTrocarPerfil: () => void
}

/** Topo do app: voltar/avançar, título da tela, busca (paleta), sino e perfil. */
export function Cabecalho({ titulo, avisos, aoDispensarAviso, aoBuscar, perfil, aoTrocarPerfil }: Props) {
  const h = historico.value
  return (
    <header class="topo-app">
      <div class="topo-nav">
        <button type="button" class="topo-botao" title="Voltar (Alt+←)" aria-label="Voltar" disabled={!podeVoltar(h)} onClick={voltar}>
          ◀
        </button>
        <button type="button" class="topo-botao" title="Avançar (Alt+→)" aria-label="Avançar" disabled={!podeAvancar(h)} onClick={avancar}>
          ▶
        </button>
      </div>
      <h2 class="topo-titulo">{titulo}</h2>
      <button type="button" class="topo-busca" onClick={aoBuscar} title="Buscar em tudo (Ctrl+K)">
        <span>Buscar jogos, músicas, desejos…</span>
        <kbd>Ctrl K</kbd>
      </button>
      <Avisos avisos={avisos} aoDispensar={aoDispensarAviso} aoVerTodas={() => ir('#/notificacoes')} />
      <button type="button" class="perfil" onClick={aoTrocarPerfil} title="Trocar de perfil">
        <span class="icone" aria-hidden="true">
          {perfil.trim().charAt(0)}
        </span>
        <span>{perfil}</span>
      </button>
    </header>
  )
}
