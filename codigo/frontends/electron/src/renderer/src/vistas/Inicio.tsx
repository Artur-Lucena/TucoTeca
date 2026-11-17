import { useEffect, useState } from 'preact/hooks'
import { PosterCard } from '../componentes/jogo/PosterCard'
import { reproduzindo } from '../estado/midia'
import { ListaContinuar, type ItemContinuar } from './midia/AbasMidia'
import { EmptyState, Metric } from '../componentes/ui'
import { PainelSessoes } from '../componentes/jogo/PainelSessoes'
import { continuarJogando, type Snapshot } from '../estado/derivacoes'
import { ir } from '../estado/rota'
import { type AoAvisar } from '../estado/notificacoes'

interface Props {
  snapshot: Snapshot
  aoAvisar?: AoAvisar
  aoMudou?: () => void
}

export function Inicio({ snapshot, aoAvisar = () => undefined, aoMudou = () => undefined }: Props) {
  const continuar = continuarJogando(snapshot.jogos)
  const [assistindo, setAssistindo] = useState<ItemContinuar[]>([])
  useEffect(() => {
    // só leitura local (progresso e arquivos); sem rede
    window.tucoteca
      .chamar<ItemContinuar[]>('midia.continuar')
      .then((r) => setAssistindo(Array.isArray(r) ? r.slice(0, 6) : []))
      .catch(() => setAssistindo([]))
  }, [reproduzindo.value])
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
      {assistindo.length > 0 && (
        <section class="secao">
          <h2>Continuar assistindo</h2>
          <ListaContinuar itens={assistindo} />
        </section>
      )}
      <section class="secao">
        <h2>Continuar jogando</h2>
        {continuar.length === 0 ? (
          <EmptyState icone="🎮" titulo="Nada por aqui ainda." descricao="Adicione um jogo na tela Jogos e ele aparece aqui." />
        ) : (
          <div class="grade">
            {continuar.map((jogo, indice) => {
              const abrir = () => ir(`#/jogo/${Number(jogo.id)}`)
              return (
                <PosterCard key={`${String(jogo.titulo)}-${indice}`} jogo={jogo} selecionado={false} aoSelecionar={abrir} aoAbrir={abrir} />
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
