import { useEffect, useState } from 'preact/hooks'
import { snapshot } from '../../estado/dados'
import { EmptyState } from '../../componentes/ui'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { NavegadorYouTube } from '../../componentes/midia/NavegadorYouTube'
import { listaTrabalhos } from '../../estado/trabalhos'

interface Props {
  aoAvisar: AoAvisar
  aoMudou: () => void
}

interface ResultadoYouTube {
  titulo?: string
  canal?: string
  duracao_s?: number
  video_id?: string
  url?: string
  thumb?: string
}

/** Tela YouTube: busca online + biblioteca local + download/MP3. */
export function YouTube({ aoAvisar, aoMudou }: Props) {
  const videos = (snapshot.value?.videos ?? []) as Array<Record<string, unknown>>
  const [termo, setTermo] = useState('')
  const [resultados, setResultados] = useState<ResultadoYouTube[]>([])
  const [buscando, setBuscando] = useState(false)
  const [videoAtual, setVideoAtual] = useState<string | null>(null)

  useEffect(() => {
    if (termo.trim().length < 2) {
      setResultados([])
      return
    }
    const timer = window.setTimeout(() => {
      setBuscando(true)
      void (async () => {
        try {
          const r = await window.tucoteca.chamar<ResultadoYouTube[] | { itens?: ResultadoYouTube[] }>(
            'videos.buscar_online',
            { termo: termo.trim(), limite: 12 },
          )
          const lista = Array.isArray(r) ? r : (r?.itens ?? [])
          setResultados(lista)
        } catch (falha) {
          setResultados([])
          aoAvisar(textoDeFalha(falha), 'atencao')
        } finally {
          setBuscando(false)
        }
      })()
    }, 350)
    return () => window.clearTimeout(timer)
  }, [termo])

  const baixar = async (item: ResultadoYouTube) => {
    if (!item.video_id) return
    try {
      await window.tucoteca.chamar('videos.baixar', { video_id: item.video_id })
      aoAvisar(`Baixando "${item.titulo ?? item.video_id}"…`)
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const baixarMp3 = async (item: ResultadoYouTube) => {
    try {
      await window.tucoteca.chamar('videos.baixar_mp3', { video: item })
      aoAvisar(`Baixando MP3 de "${item.titulo ?? ''}"…`)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const trabalhoAtivo = listaTrabalhos.value.find(
    (t) => t.escopo === 'videos' && (t.estado === 'rodando' || t.estado === 'cancelando'),
  )

  return (
    <section class="vista youtube">
      <header class="vista-topo">
        <h1>YouTube</h1>
        <div class="vista-acoes">
          <input
            class="busca"
            type="search"
            placeholder="Buscar vídeos no YouTube…"
            value={termo}
            onInput={(evento) => setTermo((evento.target as HTMLInputElement).value)}
          />
        </div>
      </header>

      {videoAtual !== null && (
        <div class="yt-player">
          <iframe
            src={`https://www.youtube.com/embed/${videoAtual}?autoplay=1`}
            title="YouTube player"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen
          />
        </div>
      )}

      <NavegadorYouTube />
      {buscando && <p class="aviso">Buscando…</p>}

      {resultados.length > 0 && (
        <ul class="lista-youtube">
          {resultados.map((item, posicao) => (
            <li class="linha-youtube" key={String(item.video_id ?? posicao)}>
              <div class="yt-textos">
                <strong>{String(item.titulo ?? '')}</strong>
                <span>
                  {[item.canal, item.duracao_s ? `${Math.round(Number(item.duracao_s) / 60)} min` : ''].filter(Boolean).join(' · ')}
                </span>
              </div>
              <div class="yt-acoes">
                <button type="button" class="acao" onClick={() => setVideoAtual(item.video_id ?? null)}>
                  Assistir
                </button>
                <button type="button" class="acao" onClick={() => void baixar(item)}>
                  Baixar
                </button>
                <button type="button" class="acao" onClick={() => void baixarMp3(item)}>
                  MP3
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <h2>Videoteca local ({videos.length})</h2>
      {videos.length === 0 ? (
        <EmptyState icone="▶" titulo="Nada importado ainda." descricao="Busque e baixe vídeos do YouTube." />
      ) : (
        <ul class="lista-videos">
          {videos.map((video, posicao) => (
            <li class="linha" key={String(video.id ?? posicao)}>
              <span class="video-icone">▶</span>
              <span class="video-textos">
                <strong>{String(video.titulo ?? '')}</strong>
                <span>{String(video.canal ?? '')}</span>
              </span>
            </li>
          ))}
        </ul>
      )}

      {trabalhoAtivo !== undefined && trabalhoAtivo !== null && (
        <p class="aviso">Baixando… {trabalhoAtivo.rotulo}</p>
      )}
    </section>
  )
}
