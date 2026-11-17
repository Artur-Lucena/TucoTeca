import { useState } from 'preact/hooks'
import { duracao } from '../../estado/formato'
import { filtrarVideos } from '../../estado/midia'
import { snapshot } from '../../estado/dados'
import { EmptyState } from '../../componentes/ui'
import { PlayerVideo } from '../../componentes/midia/PlayerVideo'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { useSetasLista } from '../../navegacao/setas'

interface Props {
  aoAvisar: AoAvisar
  aoMudou: () => void
}

interface VideoItem {
  id?: number
  titulo?: string
  canal?: string
  duracao_s?: number
  video_path?: string
  [campo: string]: unknown
}

export const REPRODUTORES = ['auto', 'vlc', 'mpv', 'mpchc']

/** Tela Vídeos (baixados do YouTube ou importados): lista, player interno e reprodutor externo. */
export function Videos({ aoAvisar, aoMudou }: Props) {
  const videos = (snapshot.value?.videos ?? []) as VideoItem[]
  const [busca, setBusca] = useState('')
  const [selecionado, setSelecionado] = useState(0)
  const [reprodutor, setReprodutor] = useState('auto')
  const [tocando, setTocando] = useState<VideoItem | null>(null)

  const lista = filtrarVideos(videos, busca)
  const indice = Math.min(selecionado, Math.max(0, lista.length - 1))
  const escolhido = lista[indice]

  const abrirInterno = (video: VideoItem | undefined) => {
    if (video?.id === undefined || !video.video_path) return
    setTocando(video)
  }
  useSetasLista(lista.length, setSelecionado, () => abrirInterno(escolhido))

  const abrirExterno = async () => {
    if (escolhido?.id === undefined) return
    try {
      await window.tucoteca.chamar('videos.reproduzir', { id: Number(escolhido.id), reprodutor })
      aoAvisar(`Abrindo em ${reprodutor}.`)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const importar = async () => {
    try {
      const pasta = await window.tucoteca.escolherPasta()
      if (pasta === null || pasta === '') return
      await window.tucoteca.chamar('videos.importar', { pasta })
      aoAvisar(`Importando vídeos de ${pasta}…`)
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  return (
    <section class="vista videos">
      <header class="vista-topo">
        <h1>Vídeos ({lista.length})</h1>
        <div class="vista-acoes">
          <input
            class="busca"
            type="search"
            placeholder="Buscar por título ou canal…"
            value={busca}
            onInput={(evento) => setBusca((evento.target as HTMLInputElement).value)}
          />
          <select
            class="reprodutor"
            value={reprodutor}
            onChange={(evento) => setReprodutor((evento.target as HTMLSelectElement).value)}
          >
            {REPRODUTORES.map((nome) => (
              <option key={nome} value={nome}>
                {nome}
              </option>
            ))}
          </select>
          <button type="button" class="acao" onClick={() => void abrirExterno()} disabled={escolhido === undefined}>
            Assistir externo
          </button>
          <button type="button" class="acao" onClick={() => void importar()}>
            + Importar vídeos
          </button>
        </div>
      </header>

      {lista.length === 0 ? (
        <EmptyState icone="▶" titulo="Nada por aqui." descricao="Baixe vídeos na aba YouTube ou importe uma pasta." />
      ) : (
        <ul class="lista-videos">
          {lista.map((video, posicaoLista) => (
            <li
              key={String(video.id ?? posicaoLista)}
              class={`linha${posicaoLista === indice ? ' selecionado' : ''}`}
              onClick={() => setSelecionado(posicaoLista)}
              onDblClick={() => abrirInterno(video)}
            >
              <span class="video-icone">▶</span>
              <span class="video-textos">
                <strong>{String(video.titulo ?? '')}</strong>
                <span>{[video.canal, duracao(Number(video.duracao_s ?? 0))].filter(Boolean).join(' · ')}</span>
              </span>
            </li>
          ))}
        </ul>
      )}

      {tocando !== null && tocando.id !== undefined && (
        <PlayerVideo
          key={tocando.id}
          fonte={{ tipo: 'videoteca', id: Number(tocando.id), caminho: String(tocando.video_path ?? ''), titulo: String(tocando.titulo ?? '') }}
          aoFechar={() => setTocando(null)}
          aoMudou={aoMudou}
          aoAvisar={aoAvisar}
        />
      )}
    </section>
  )
}
