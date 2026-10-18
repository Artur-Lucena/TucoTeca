import { Cartao } from '../componentes/Cartao'
import { continuarJogando, type Snapshot } from '../derivacoes'

export function Inicio({ snapshot }: { snapshot: Snapshot }) {
  const continuar = continuarJogando(snapshot.jogos)
  const sistema = snapshot.sistema ?? {}
  return (
    <div class="inicio">
      <header class="cabecalho">
        <h1>Boas-vindas ao seu hub.</h1>
        <p>Continuar, buscar e cuidar da coleção — sem sair do lugar.</p>
      </header>
      <div class="numeros">
        <Numero rotulo="Jogos" valor={sistema.jogos ?? snapshot.jogos?.length ?? 0} />
        <Numero rotulo="Músicas" valor={sistema.musicas ?? snapshot.musicas?.length ?? 0} />
        <Numero rotulo="Desejos" valor={sistema.desejos ?? snapshot.desejos?.length ?? 0} />
      </div>
      <section class="secao">
        <h2>Continuar jogando</h2>
        {continuar.length === 0 ? (
          <div class="vazio">
            <p>Nada por aqui ainda.</p>
            <p class="dica">Adicione um jogo na tela Jogos e ele aparece aqui.</p>
          </div>
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

function Numero({ rotulo, valor }: { rotulo: string; valor: number }) {
  return (
    <div class="numero">
      <span class="valor">{valor}</span>
      <span class="rotulo">{rotulo}</span>
    </div>
  )
}
