import { useEffect, useMemo, useRef, useState } from 'preact/hooks'
import { snapshot } from '../estado/dados'
import { semAcento } from '../estado/jogos'
import { textoDeFalha } from '../estado/notificacoes'
import { faixaAtual, player, playerInicial, tocarFila } from '../estado/player'
import { listaTrabalhos } from '../estado/trabalhos'
import type { JogoResumo } from '../derivacoes'

interface Props {
  /** Incrementa a cada Ctrl+F: foca o campo de busca. */
  focoBusca?: number
  /** Troca de perfil recarrega o snapshot (a lista não muda com o perfil). */
  perfil?: string
  aoAvisar: (texto: string, tom?: 'info' | 'atencao') => void
  aoMudou: () => void
}

interface FaixaMusica extends JogoResumo {
  id?: number
  artista?: string
  album?: string
  musica_path?: string
}

/** Filtro local: todas as palavras (sem acento) em título/artista/álbum. */
export function filtrarMusicas(musicas: FaixaMusica[], busca: string): FaixaMusica[] {
  const palavras = semAcento(busca).trim().split(/\s+/).filter(Boolean)
  if (palavras.length === 0) return musicas
  return musicas.filter((m) => {
    const alvo = semAcento(`${m.titulo ?? ''} ${m.artista ?? ''} ${m.album ?? ''}`)
    return palavras.every((palavra) => alvo.includes(palavra))
  })
}

/** Tela Músicas: lista com busca, tocar/remover, importar pasta e fila de downloads. */
export function Musicas({ focoBusca = 0, perfil = '', aoAvisar, aoMudou }: Props) {
  const musicas = (snapshot.value?.musicas ?? []) as FaixaMusica[]
  const filaDownloads = (snapshot.value?.fila_musicas ?? []) as FaixaMusica[]
  const [busca, setBusca] = useState('')
  const [selecionado, setSelecionado] = useState(0)
  const campo = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    if (focoBusca > 0) campo.current?.focus()
  }, [focoBusca])

  useEffect(() => {
    setSelecionado(0)
  }, [perfil])

  const lista = useMemo(() => filtrarMusicas(musicas, busca), [musicas, busca])
  const indice = Math.min(selecionado, Math.max(0, lista.length - 1))
  const escolhida = lista[indice]
  const tocando = faixaAtual(player.value)

  const tocar = (indiceAlvo: number) => {
    if (lista.length === 0) return
    player.value = tocarFila(player.value, lista, indiceAlvo)
  }

  useEffect(() => {
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.ctrlKey || evento.altKey || evento.metaKey) return
      if (document.querySelector('.paleta-fundo') !== null) return
      if (document.querySelector('.detalhe-fundo') !== null) return
      const alvo = evento.target as HTMLElement | null
      if (
        alvo !== null &&
        alvo !== campo.current &&
        alvo.closest('input, textarea, select') !== null
      ) {
        return
      }
      if (evento.key === 'Enter') {
        if (alvo === campo.current || lista.length === 0) return
        evento.preventDefault()
        tocar(indice)
        return
      }
      if (evento.key !== 'ArrowDown' && evento.key !== 'ArrowUp') return
      evento.preventDefault()
      const passo = evento.key === 'ArrowDown' ? 1 : -1
      setSelecionado((atual) => {
        const base = Math.min(atual, Math.max(0, lista.length - 1))
        return Math.max(0, Math.min(lista.length - 1, base + passo))
      })
    }
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [lista, indice])

  const remover = async () => {
    if (escolhida?.id === undefined) return
    const titulo = String(escolhida.titulo ?? 'a música')
    const aviso = `Remover "${titulo}"? O arquivo de áudio também será apagado e não dá para desfazer.`
    if (!window.confirm(aviso)) return
    try {
      await window.tucoteca.chamar('item.excluir', { categoria: 'musicas', id: Number(escolhida.id) })
      if (faixaAtual(player.value)?.id === escolhida.id) player.value = playerInicial
      aoAvisar(`${titulo} foi removida (o arquivo foi apagado).`)
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const importar = async () => {
    try {
      const pasta = await window.tucoteca.escolherPasta()
      if (pasta === null || pasta === '') return
      await window.tucoteca.chamar('musicas.importar', { pasta })
      aoAvisar(`Importando músicas de ${pasta}…`)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const baixar = async () => {
    try {
      await window.tucoteca.chamar('musicas.baixar_fila')
      aoAvisar('Baixando a fila de músicas…')
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const pararTrabalho = async (id: number) => {
    try {
      await window.tucoteca.chamar('trabalhos.cancelar', { id })
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const trabalho =
    listaTrabalhos.value.find(
      (item) => item.escopo === 'musicas' && (item.estado === 'rodando' || item.estado === 'cancelando'),
    ) ?? null

  return (
    <section class="vista musicas">
      <header class="vista-topo">
        <h1>Músicas ({lista.length})</h1>
        <div class="vista-acoes">
          <input
            ref={campo}
            class="busca"
            type="search"
            placeholder="Buscar por título, artista ou álbum…"
            value={busca}
            onInput={(evento) => setBusca((evento.target as HTMLInputElement).value)}
          />
          <button
            type="button"
            class="acao"
            onClick={() => tocar(indice)}
            disabled={escolhida === undefined}
          >
            ▶ Tocar
          </button>
          <button
            type="button"
            class="acao perigo"
            onClick={() => void remover()}
            disabled={escolhida === undefined}
          >
            Remover
          </button>
          <button type="button" class="acao" onClick={() => void importar()}>
            + Importar pasta
          </button>
        </div>
      </header>

      {trabalho !== null && (
        <div class="job">
          <span class="job-rotulo">{trabalho.rotulo}</span>
          <progress
            class="job-barra"
            max={100}
            value={trabalho.pct === null ? undefined : trabalho.pct}
          />
          <button
            type="button"
            class="acao"
            onClick={() => void pararTrabalho(trabalho.id)}
            disabled={!trabalho.cancelavel || trabalho.estado === 'cancelando'}
          >
            Parar
          </button>
        </div>
      )}

      {lista.length === 0 ? (
        <p class="aviso">Nada por aqui. Importe uma pasta com arquivos de áudio.</p>
      ) : (
        <ul class="lista-musicas">
          {lista.map((musica, posicao) => {
            const capa =
              musica.capa_url === undefined ? '' : window.tucoteca.imagemUrl(String(musica.capa_url))
            const atual = tocando !== null && tocando.id === musica.id
            return (
              <li
                key={String(musica.id ?? posicao)}
                class={`linha${posicao === indice ? ' selecionado' : ''}${atual ? ' tocando' : ''}`}
                onClick={() => setSelecionado(posicao)}
                onDblClick={() => tocar(posicao)}
              >
                <span class="musica-capa">
                  {capa !== '' ? <img src={capa} alt="" loading="lazy" /> : <span class="capa-vazia">♪</span>}
                </span>
                <span class="musica-textos">
                  <strong>{String(musica.titulo ?? '')}</strong>
                  <span>{[musica.artista, musica.album].filter(Boolean).join(' · ')}</span>
                </span>
                {atual && <span class="selo-tocando">▶ tocando</span>}
              </li>
            )
          })}
        </ul>
      )}

      <section class="fila-musicas">
        <h2>Fila de downloads ({filaDownloads.length})</h2>
        {filaDownloads.length === 0 ? (
          <p class="aviso">Sem downloads na fila.</p>
        ) : (
          <ul>
            {filaDownloads.slice(0, 12).map((item, posicao) => (
              <li key={String(item.id ?? posicao)}>
                <span>{[item.titulo, item.artista].filter(Boolean).join(' — ')}</span>
                <span class="selo">{String(item.estado ?? '')}</span>
              </li>
            ))}
          </ul>
        )}
        <button type="button" class="acao" onClick={() => void baixar()}>
          Baixar pendentes
        </button>
      </section>
    </section>
  )
}
