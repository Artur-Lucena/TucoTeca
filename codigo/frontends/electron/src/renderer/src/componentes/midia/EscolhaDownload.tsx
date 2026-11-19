import { useEffect, useState } from 'preact/hooks'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { Modal } from '../ui'

export interface VideoYouTube {
  titulo?: string
  canal?: string
  duracao_s?: number
  video_id?: string
  url?: string
  thumb?: string
}

export interface FaixaSpotify {
  titulo: string
  artista: string
  album: string
  capa_url: string
  url: string
}

interface Versao {
  faixa: FaixaSpotify | null
  aviso: string
}

interface Props {
  video: VideoYouTube | null
  aoFechar: () => void
  aoAvisar: AoAvisar
  aoMudou: () => void
}

/**
 * Baixar um vídeo do YouTube: o clipe (MP4) ou só a música (MP3). Se a mesma
 * música estiver no Spotify, o MP3 pode entrar com título, artista, álbum e
 * capa de lá.
 */
export function EscolhaDownload({ video, aoFechar, aoAvisar, aoMudou }: Props) {
  const [versao, setVersao] = useState<Versao | null>(null)

  useEffect(() => {
    setVersao(null)
    if (video === null) return
    let vivo = true
    window.tucoteca
      .chamar<Versao>('videos.versao_musica', { video })
      .then((r) => vivo && setVersao({ faixa: r?.faixa ?? null, aviso: r?.aviso ?? '' }))
      .catch((falha) => vivo && setVersao({ faixa: null, aviso: textoDeFalha(falha) }))
    return () => {
      vivo = false
    }
  }, [video])

  if (video === null) return null
  const nome = video.titulo ?? video.video_id ?? ''

  const executar = async (metodo: string, params: Record<string, unknown>, aviso: string) => {
    try {
      await window.tucoteca.chamar(metodo, params)
      aoAvisar(aviso)
      aoMudou()
      aoFechar()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }
  const faixa = versao?.faixa ?? null

  return (
    <Modal aberto={true} aoFechar={aoFechar} titulo="Baixar" largura="560px">
      <p class="sub escolha-video">{nome}</p>
      <div class="opcoes-download">
        <button
          type="button"
          class="opcao-download"
          disabled={!video.video_id}
          onClick={() => void executar('videos.baixar', { video_id: video.video_id }, `Baixando o clipe de "${nome}"…`)}
        >
          <strong>🎬 Clipe em vídeo (MP4)</strong>
          <span>Fica em Vídeos.</span>
        </button>
        {faixa !== null && (
          <button
            type="button"
            class="opcao-download destaque"
            onClick={() => void executar('videos.baixar_mp3', { video, musica: faixa }, `Baixando "${faixa.titulo}" (MP3)…`)}
          >
            {faixa.capa_url !== '' && <img src={faixa.capa_url} alt="" />}
            <strong>🎵 Música (MP3) com os dados do Spotify</strong>
            <span>
              {faixa.titulo} — {faixa.artista}
              {faixa.album !== '' ? ` · ${faixa.album}` : ''}
            </span>
          </button>
        )}
        <button
          type="button"
          class="opcao-download"
          onClick={() => void executar('videos.baixar_mp3', { video }, `Baixando o MP3 de "${nome}"…`)}
        >
          <strong>🎵 Só o áudio (MP3)</strong>
          <span>Com o título e o canal do vídeo. Fica em Músicas.</span>
        </button>
      </div>
      <p class="sub">
        {versao === null
          ? 'Procurando a música no Spotify…'
          : faixa !== null
            ? 'Achamos a mesma música no Spotify: o MP3 entra com o nome, o álbum e a capa certos.'
            : versao.aviso}
      </p>
    </Modal>
  )
}
