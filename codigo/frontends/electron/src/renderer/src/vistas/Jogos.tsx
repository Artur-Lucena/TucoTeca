import { useEffect, useRef, useState } from 'preact/hooks'
import { PosterCard } from '../componentes/PosterCard'
import { EmptyState } from '../componentes/ui'
import { textoDeFalha } from '../estado/notificacoes'
import { saude, snapshot } from '../estado/dados'
import {
  FILTROS_JOGOS,
  ORDENS_JOGOS,
  filtrarJogos,
  ordenarJogos,
  type FiltroJogo,
  type JogoDaLista,
  type OrdemJogo,
} from '../estado/jogos'

const ROTULO_FILTRO: Record<FiltroJogo, string> = {
  todos: 'Todos',
  favoritos: 'Favoritos',
  jogando: 'Jogando',
  PC: 'PC',
  '3DS': '3DS',
  NDS: 'NDS',
  pendencias: 'Pendências',
}

const ROTULO_ORDEM: Record<OrdemJogo, string> = {
  titulo: 'Título',
  recentes: 'Recentes',
  horas: 'Horas',
}

interface Props {
  /** Incrementa a cada Ctrl+F: foca o campo de busca. */
  focoBusca?: number
  /** Troca de perfil recarrega o filtro salvo do perfil novo. */
  perfil?: string
  /** Abre o detalhe do jogo (botão Abrir, clique direito e Espaço). */
  aoAbrirJogo?: (id: number) => void
  /** Joga o jogo selecionado (botão Jogar, duplo clique e Enter). */
  aoJogarJogo?: (id: number) => void
  /** Toast global. */
  aoAvisar?: (texto: string, tom?: 'info' | 'atencao') => void
  /** Recarrega snapshot após mutação. */
  aoMudou?: () => void
}

export function Jogos({ focoBusca = 0, perfil = '', aoAbrirJogo, aoJogarJogo, aoAvisar, aoMudou }: Props) {
  const [filtro, setFiltro] = useState<FiltroJogo>('todos')
  const [ordem, setOrdem] = useState<OrdemJogo>('titulo')
  const [busca, setBusca] = useState('')
  const [selecionado, setSelecionado] = useState(0)
  const campo = useRef<HTMLInputElement>(null)
  const grade = useRef<HTMLDivElement>(null)

  useEffect(() => {
    void (async () => {
      try {
        const prefs = await window.tucoteca.chamar<{ filtro?: string; ordem?: string }>(
          'preferencias.filtro',
        )
        if (FILTROS_JOGOS.includes(prefs.filtro as FiltroJogo)) setFiltro(prefs.filtro as FiltroJogo)
        if (ORDENS_JOGOS.includes(prefs.ordem as OrdemJogo)) setOrdem(prefs.ordem as OrdemJogo)
      } catch {
        // sem filtro salvo o padrão vale; a tela segue utilizável
      }
    })()
  }, [perfil])

  useEffect(() => {
    if (focoBusca > 0) campo.current?.focus()
  }, [focoBusca])

  const jogos = snapshot.value?.jogos
  const total = jogos?.length ?? 0
  const pendentes = saude.value?.ids_pendentes ?? []
  const lista = ordenarJogos(
    filtrarJogos(jogos as JogoDaLista[] | undefined, { filtro, busca, idsPendentes: pendentes }),
    ordem,
  )
  const indice = Math.min(selecionado, Math.max(0, lista.length - 1))

  const mudarFiltro = (novo: FiltroJogo) => {
    setFiltro(novo)
    setSelecionado(0)
    void window.tucoteca
      .chamar('preferencias.salvar_filtro', { filtro: novo, ordem })
      .catch(() => undefined)
  }

  const mudarOrdem = (nova: OrdemJogo) => {
    setOrdem(nova)
    void window.tucoteca
      .chamar('preferencias.salvar_filtro', { filtro, ordem: nova })
      .catch(() => undefined)
  }

  useEffect(() => {
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.ctrlKey || evento.altKey || evento.metaKey) return
      if (document.querySelector('.paleta-fundo') !== null) return
      if (document.querySelector('.detalhe-fundo') !== null) return
      const alvo = evento.target as HTMLElement | null
      if (alvo !== null && alvo !== campo.current && alvo.closest('input, textarea, select') !== null) {
        return
      }
      const escolhido = lista[indice]
      const id = escolhido?.id === undefined ? null : Number(escolhido.id)
      if (evento.key === 'Enter' || evento.key === ' ') {
        if (alvo === campo.current || id === null) return // digitando na busca
        evento.preventDefault()
        if (evento.key === 'Enter') aoJogarJogo?.(id)
        else aoAbrirJogo?.(id)
        return
      }
      const colunas = colunasDaGrade(grade.current)
      let passo = 0
      if (evento.key === 'ArrowRight') passo = 1
      else if (evento.key === 'ArrowLeft') passo = -1
      else if (evento.key === 'ArrowDown') passo = colunas
      else if (evento.key === 'ArrowUp') passo = -colunas
      else return
      evento.preventDefault()
      setSelecionado((atual) => {
        const base = Math.min(atual, Math.max(0, lista.length - 1))
        return Math.max(0, Math.min(lista.length - 1, base + passo))
      })
    }
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [lista, indice, aoAbrirJogo, aoJogarJogo])

  return (
    <div class="jogos">
      <header class="cabecalho">
        <h1>Jogos</h1>
        <button
          type="button"
          class="acao"
          onClick={async () => {
            try {
              const pasta = await window.tucoteca.escolherPasta()
              if (pasta === null || pasta === '') return
              await window.tucoteca.chamar('jogos.importar', { pasta })
              aoAvisar?.(`Importando jogos de ${pasta}…`)
              aoMudou?.()
            } catch (falha) {
              aoAvisar?.(textoDeFalha(falha), 'atencao')
            }
          }}
        >
          + Importar pasta
        </button>
        <p>{resumoDe(lista.length, total, filtro, ordem, busca)}</p>
      </header>
      <div class="filtros">
        {FILTROS_JOGOS.map((chave) => (
          <button
            key={chave}
            class={`chip ${chave === filtro ? 'ativo' : ''}`}
            onClick={() => mudarFiltro(chave)}
          >
            {chave === 'pendencias'
              ? `Pendências (${saude.value?.pendentes ?? 0})`
              : ROTULO_FILTRO[chave]}
          </button>
        ))}
        <label class="ordem">
          <span>Ordem</span>
          <select value={ordem} onChange={(evento) => mudarOrdem(rotuloOrdem(evento))}>
            {ORDENS_JOGOS.map((chave) => (
              <option key={chave} value={chave}>
                {ROTULO_ORDEM[chave]}
              </option>
            ))}
          </select>
        </label>
        <input
          ref={campo}
          class="busca"
          type="search"
          placeholder="Buscar nos jogos…"
          value={busca}
          onInput={(evento) => {
            setBusca((evento.target as HTMLInputElement).value)
            setSelecionado(0)
          }}
        />
      </div>
      {lista.length === 0 ? (
        <EmptyState icone="🎮" titulo="Nenhum jogo com esse filtro." descricao="Limpe a busca ou troque o filtro." />
      ) : (
        <div class="grade" ref={grade}>
          {lista.map((jogo, posicao) => {
            const id = jogo.id === undefined ? null : Number(jogo.id)
            return (
              <PosterCard
                key={String(jogo.uuid ?? jogo.id ?? posicao)}
                jogo={jogo}
                selecionado={posicao === indice}
                aoSelecionar={() => setSelecionado(posicao)}
                aoAbrir={
                  id === null || aoAbrirJogo === undefined ? undefined : () => aoAbrirJogo(id)
                }
                aoJogar={
                  id === null || aoJogarJogo === undefined ? undefined : () => aoJogarJogo(id)
                }
              />
            )
          })}
        </div>
      )}
    </div>
  )
}

function rotuloOrdem(evento: Event): OrdemJogo {
  const valor = (evento.target as HTMLSelectElement).value
  return (ORDENS_JOGOS as readonly string[]).includes(valor) ? (valor as OrdemJogo) : 'titulo'
}

function colunasDaGrade(elemento: HTMLElement | null): number {
  if (elemento === null) return 1
  const colunas = getComputedStyle(elemento).gridTemplateColumns.split(' ').filter(Boolean).length
  return colunas > 0 ? colunas : 1
}

function resumoDe(
  visiveis: number,
  total: number,
  filtro: FiltroJogo,
  ordem: OrdemJogo,
  busca: string,
): string {
  const partes = [`${visiveis} de ${total} jogos`, ROTULO_FILTRO[filtro], ROTULO_ORDEM[ordem]]
  const termo = busca.trim()
  if (termo !== '') partes.push(`busca "${termo}"`)
  return partes.join(' · ')
}
