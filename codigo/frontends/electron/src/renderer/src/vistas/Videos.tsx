import { modoTv } from '../navegacao/foco'
import { duracao } from '../estado/formato'
import { useEffect, useRef, useState } from 'preact/hooks'
import { snapshot } from '../estado/dados'
import { EmptyState } from '../componentes/ui'
import { textoDeFalha } from '../estado/notificacoes'

interface Props {
  aoAvisar: (texto: string, tom?: 'info' | 'atencao') => void
  aoMudou: () => void
}

interface VideoItem {
  id?: number
  titulo?: string
  canal?: string
  duracao_s?: number
  video_path?: string
  video_sha?: string
  [campo: string]: unknown
}

export const REPRODUTORES = ['auto', 'vlc', 'mpv', 'mpchc']

const formatarDuracao = duracao

/** Tela Vídeos: lista, player interno e reprodutor externo. */
export function Videos({ aoAvisar, aoMudou }: Props) {
  const videos = (snapshot.value?.videos ?? []) as VideoItem[]
  const [busca, setBusca] = useState('')
  const [selecionado, setSelecionado] = useState(0)
  const [reprodutor, setReprodutor] = useState('auto')
  const [atual, setAtual] = useState<VideoItem | null>(null)
  const [posicao, setPosicao] = useState(0)
  const [sha, setSha] = useState('')
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const campo = useRef<HTMLInputElement | null>(null)

  const lista = videos.filter((v) =>
    busca.trim() === ''
      ? true
      : String(v.titulo ?? '').toLowerCase().includes(busca.trim().toLowerCase()),
  )
  const indice = Math.min(selecionado, Math.max(0, lista.length - 1))
  const escolhido = lista[indice]

  useEffect(() => {
    const aoTeclar = (evento: KeyboardEvent) => {
      if (modoTv() && evento.key.startsWith('Arrow')) return
      if (evento.ctrlKey || evento.altKey || evento.metaKey) return
      if (document.querySelector('.paleta-fundo') !== null) return
      const alvo = evento.target as HTMLElement | null
      if (alvo !== null && alvo.closest('input, textarea, select') !== null) return
      if (evento.key !== 'ArrowDown' && evento.key !== 'ArrowUp' && evento.key !== 'Enter') return
      evento.preventDefault()
      if (evento.key === 'Enter') {
        if (escolhido !== undefined) void abrirInterno(escolhido)
        return
      }
      const passo = evento.key === 'ArrowDown' ? 1 : -1
      setSelecionado((atual) => Math.max(0, Math.min(lista.length - 1, atual + passo)))
    }
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [lista.length, escolhido])

  const abrirInterno = async (video: VideoItem) => {
    if (video.id === undefined) return
    try {
      const dados = await window.tucoteca.chamar<{ id?: number; titulo?: string; posicao?: number; sha?: string }>(
        'videos.local',
        { id: Number(video.id) },
      )
      setAtual(video)
      setPosicao(Number(dados.posicao ?? 0))
      setSha(String(dados.sha ?? ''))
      if (videoRef.current !== null) {
        videoRef.current.currentTime = Number(dados.posicao ?? 0)
        void videoRef.current.play().catch(() => undefined)
      }
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const abrirExterno = async () => {
    if (escolhido?.id === undefined) return
    try {
      await window.tucoteca.chamar('videos.reproduzir', {
        id: Number(escolhido.id),
        reprodutor,
      })
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

  useEffect(() => {
    const video = videoRef.current
    if (video === null || sha === '') return
    let timer: number | null = null
    const aoTempo = () => {
      if (timer !== null) window.clearTimeout(timer)
      timer = window.setTimeout(() => {
        void window.tucoteca.chamar('videos.salvar_posicao', { sha, posicao: video.currentTime }).catch(() => undefined)
      }, 1000)
    }
    video.addEventListener('timeupdate', aoTempo)
    return () => {
      video.removeEventListener('timeupdate', aoTempo)
      if (timer !== null) window.clearTimeout(timer)
    }
  }, [sha])

  useEffect(() => {
    if (posicao > 0 && videoRef.current !== null) {
      videoRef.current.currentTime = posicao
    }
  }, [posicao])

  return (
    <section class="vista videos">
      <header class="vista-topo">
        <h1>Vídeos ({lista.length})</h1>
        <div class="vista-acoes">
          <input
            ref={campo}
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
          <button
            type="button"
            class="acao"
            onClick={() => void abrirExterno()}
            disabled={escolhido === undefined}
          >
            Assistir externo
          </button>
          <button type="button" class="acao" onClick={() => void importar()}>
            + Importar vídeos
          </button>
        </div>
      </header>

      {atual !== null && atual.video_path !== undefined && (
        <div class="player-video">
          <video
            ref={videoRef}
            src={window.tucoteca.mediaUrl(String(atual.video_path))}
            controls
            autoplay
          />
          <strong>{String(atual.titulo ?? '')}</strong>
        </div>
      )}

      {lista.length === 0 ? (
        <EmptyState icone="▶" titulo="Nada por aqui." descricao="Importe uma pasta com vídeos." />
      ) : (
        <ul class="lista-videos">
          {lista.map((video, posicaoLista) => (
            <li
              key={String(video.id ?? posicaoLista)}
              class={`linha${posicaoLista === indice ? ' selecionado' : ''}`}
              onClick={() => setSelecionado(posicaoLista)}
              onDblClick={() => void abrirInterno(video)}
            >
              <span class="video-icone">▶</span>
              <span class="video-textos">
                <strong>{String(video.titulo ?? '')}</strong>
                <span>
                  {[video.canal, formatarDuracao(Number(video.duracao_s ?? 0))].filter(Boolean).join(' · ')}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
