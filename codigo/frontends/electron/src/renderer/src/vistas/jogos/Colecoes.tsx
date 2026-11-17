import { useState } from 'preact/hooks'
import { confirmar } from '../../componentes/ui/Confirmacao'
import { PosterCard } from '../../componentes/jogo/PosterCard'
import { EmptyState } from '../../componentes/ui'
import { jogosDaColecao, normalizarColecoes, validarNomeColecao } from '../../estado/colecoes'
import { snapshot } from '../../estado/dados'
import type { JogoDaLista } from '../../estado/jogos'
import { textoDeFalha } from '../../estado/notificacoes'
import { ir } from '../../estado/rota'

interface Props {
  aoMudou: () => void
  aoAvisar: (texto: string, tom?: 'info' | 'atencao') => void
}

/** Jogos › Coleções: criar, renomear e apagar listas; ver os jogos de cada uma. */
export function Colecoes({ aoMudou, aoAvisar }: Props) {
  const colecoes = normalizarColecoes(snapshot.value?.colecoes)
  const [ativa, setAtiva] = useState<number | null>(null)
  const [nome, setNome] = useState('')
  const [renomeando, setRenomeando] = useState<string | null>(null)
  const atual = colecoes.find((c) => c.id === ativa) ?? colecoes[0]
  const jogos = jogosDaColecao((snapshot.value?.jogos ?? []) as JogoDaLista[], atual)

  const criar = async (evento: Event) => {
    evento.preventDefault()
    const valido = validarNomeColecao(nome, colecoes)
    if (typeof valido !== 'string') return aoAvisar(valido.erro, 'atencao')
    try {
      const nova = await window.tucoteca.chamar<{ id: number }>('colecoes.criar', { nome: valido })
      setNome('')
      setAtiva(nova.id)
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const renomear = async () => {
    if (atual === undefined || renomeando === null) return
    const valido = validarNomeColecao(renomeando, colecoes, atual.id)
    if (typeof valido !== 'string') return aoAvisar(valido.erro, 'atencao')
    try {
      await window.tucoteca.chamar('colecoes.renomear', { id: atual.id, nome: valido })
      setRenomeando(null)
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const apagar = async () => {
    if (atual === undefined) return
    if (!(await confirmar({ titulo: 'Apagar coleção', texto: `Apagar a coleção "${atual.nome}"? Os jogos continuam na biblioteca.`, confirmar: 'Apagar', perigo: true }))) return
    try {
      await window.tucoteca.chamar('colecoes.apagar', { id: atual.id })
      setAtiva(null)
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  return (
    <section class="colecoes">
      <aside class="colecoes-lista">
        <form class="detalhe-linha" onSubmit={(e) => void criar(e)}>
          <input class="busca" value={nome} placeholder="Nova coleção" maxLength={60} onInput={(e) => setNome((e.target as HTMLInputElement).value)} />
          <button type="submit" class="acao">
            Criar
          </button>
        </form>
        {colecoes.length === 0 ? (
          <p class="sub">Nenhuma coleção ainda. Crie uma aqui ou pela página de um jogo.</p>
        ) : (
          <ul>
            {colecoes.map((c) => (
              <li key={c.id}>
                <button type="button" class={`colecao-item${c.id === atual?.id ? ' ativo' : ''}`} onClick={() => setAtiva(c.id)}>
                  <span>{c.nome}</span>
                  <span class="sub">{c.uuids.length}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>
      <div class="colecoes-conteudo">
        {atual === undefined ? (
          <EmptyState icone="▦" titulo="Organize seus jogos em coleções." descricao="Ex.: “Zerar em 2026”, “Coop com a Isa”, “Clássicos do DS”." />
        ) : (
          <>
            <header class="colecoes-topo">
              {renomeando === null ? (
                <h2>{atual.nome}</h2>
              ) : (
                <input
                  class="busca"
                  value={renomeando}
                  maxLength={60}
                  onInput={(e) => setRenomeando((e.target as HTMLInputElement).value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') void renomear()
                    if (e.key === 'Escape') setRenomeando(null)
                  }}
                />
              )}
              <div class="detalhe-linha">
                {renomeando === null ? (
                  <button type="button" class="acao" onClick={() => setRenomeando(atual.nome)}>
                    Renomear
                  </button>
                ) : (
                  <button type="button" class="acao" onClick={() => void renomear()}>
                    Salvar nome
                  </button>
                )}
                <button type="button" class="acao perigo" onClick={() => void apagar()}>
                  Apagar
                </button>
              </div>
            </header>
            {jogos.length === 0 ? (
              <p class="sub">Coleção vazia. Na página de um jogo, use “Coleções” para colocá-lo aqui.</p>
            ) : (
              <div class="grade">
                {jogos.map((j) => (
                  <PosterCard key={String(j.uuid)} jogo={j} selecionado={false} aoSelecionar={() => ir(`#/jogo/${j.id}`)} aoAbrir={() => ir(`#/jogo/${j.id}`)} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </section>
  )
}
