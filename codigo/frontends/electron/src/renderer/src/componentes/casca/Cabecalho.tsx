import type { Aviso } from '../../estado/notificacoes'
import { avancar, historico, ir, podeAvancar, podeVoltar, voltar } from '../../estado/rota'
import { rotuloAtalho } from '../../navegacao/atalhos'
import { ehMac } from '../../plataforma'
import { Avisos } from './Avisos'

interface Props {
  titulo: string
  avisos: Aviso[]
  aoDispensarAviso: (id: string) => void
  aoLimparAvisos: () => void
  aoBuscar: () => void
  perfil: string
  aoTrocarPerfil: () => void
}

/** Topo do app: voltar/avançar, título da tela, busca (paleta), sino e perfil. */
export function Cabecalho({ titulo, avisos, aoDispensarAviso, aoLimparAvisos, aoBuscar, perfil, aoTrocarPerfil }: Props) {
  const h = historico.value
  const mac = ehMac()
  const busca = rotuloAtalho('Ctrl+K', mac)
  return (
    <header class="topo-app">
      <div class="topo-nav">
        <button type="button" class="topo-botao" title={mac ? 'Voltar (⌥←)' : 'Voltar (Alt+←)'} aria-label="Voltar" disabled={!podeVoltar(h)} onClick={voltar}>
          ◀
        </button>
        <button type="button" class="topo-botao" title={mac ? 'Avançar (⌥→)' : 'Avançar (Alt+→)'} aria-label="Avançar" disabled={!podeAvancar(h)} onClick={avancar}>
          ▶
        </button>
      </div>
      <h2 class="topo-titulo">{titulo}</h2>
      <button type="button" class="topo-busca" onClick={aoBuscar} title={`Buscar em tudo (${busca})`}>
        <span>Buscar jogos, músicas, desejos…</span>
        <kbd>{mac ? busca : busca.replace('+', ' ')}</kbd>
      </button>
      <Avisos avisos={avisos} aoDispensar={aoDispensarAviso} aoLimpar={aoLimparAvisos} aoVerTodas={() => ir('#/notificacoes')} />
      <button type="button" class="perfil" onClick={aoTrocarPerfil} title="Trocar de perfil">
        <span class="icone" aria-hidden="true">
          {perfil.trim().charAt(0)}
        </span>
        <span>{perfil}</span>
      </button>
    </header>
  )
}
