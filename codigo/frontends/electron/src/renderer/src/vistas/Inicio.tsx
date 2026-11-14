import { Cartao } from '../componentes/Cartao'
import { EmptyState, Metric } from '../componentes/ui'
import { PainelSessoes } from '../componentes/PainelSessoes'
import { continuarJogando, type Snapshot } from '../derivacoes'

interface Props {
  snapshot: Snapshot
  aoAvisar?: (texto: string, tom?: 'info' | 'atencao') => void
  aoMudou?: () => void
}

export function Inicio({ snapshot, aoAvisar = () => undefined, aoMudou = () => undefined }: Props) {
  const continuar = continuarJogando(snapshot.jogos)
  const sistema = snapshot.sistema ?? {}
  return (
    <div class="inicio">
      <header class="cabecalho">
        <h1>Boas-vindas ao seu hub.</h1>
        <p>Continuar, buscar e cuidar da coleção — sem sair do lugar.</p>
      </header>
      <div class="kpi-row">
        <Metric valor={sistema.jogos ?? snapshot.jogos?.length ?? 0} label="Jogos" icone="🎮" />
        <Metric valor={sistema.musicas ?? snapshot.musicas?.length ?? 0} label="Músicas" icone="♪" />
        <Metric valor={sistema.desejos ?? snapshot.desejos?.length ?? 0} label="Desejos" icone="★" />
      </div>
      <PainelSessoes revisao={Number(sistema.pendentes ?? 0)} aoMudou={aoMudou} aoAvisar={aoAvisar} />
      <section class="secao">
        <h2>Continuar jogando</h2>
        {continuar.length === 0 ? (
          <EmptyState icone="🎮" titulo="Nada por aqui ainda." descricao="Adicione um jogo na tela Jogos e ele aparece aqui." />
        ) : (
          <div class="grade">
            {continuar.map((jogo, indice) => (
              <Cartao key={`${String(jogo.titulo)}-${indice}`} jogo={jogo} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
