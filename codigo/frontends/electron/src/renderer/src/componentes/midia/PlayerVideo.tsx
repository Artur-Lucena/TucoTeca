import { useEffect, useRef, useState } from 'preact/hooks'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'

interface Sessao {
  arquivo: number
  caminho: string
  chave: string
  titulo: string
  posicao: number
  legendas: Array<{ indice: number; idioma: string }>
}

interface Props {
  arquivo: number
  aoFechar: () => void
  aoMudou: () => void
  aoAvisar: AoAvisar
}

const SALVAR_A_CADA = 10_000

/**
 * Player interno de Filmes e Séries: retoma de onde parou, legendas locais
 * (SRT/VTT viram VTT na ponte) e progresso salvo a cada 10 s, ao pausar e ao
 * fechar. Formato que o Chromium não toca → oferece o reprodutor externo.
 */
export function PlayerVideo({ arquivo, aoFechar, aoMudou, aoAvisar }: Props) {
  const [sessao, setSessao] = useState<Sessao | null>(null)
  const [faixas, setFaixas] = useState<Array<{ idioma: string; url: string }>>([])
  const [semSuporte, setSemSuporte] = useState(false)
  const video = useRef<HTMLVideoElement>(null)
  const ultimoSalvo = useRef(0)

  useEffect(() => {
    let vivo = true
    const urls: string[] = []
    void (async () => {
      try {
        const s = await window.tucoteca.chamar<Sessao>('midia.reproduzir', { arquivo })
        if (!vivo) return
        setSessao(s)
        const carregadas: Array<{ idioma: string; url: string }> = []
        for (const leg of s.legendas) {
          try {
            const r = await window.tucoteca.chamar<{ vtt: string }>('midia.legenda', { arquivo, indice: leg.indice })
            const url = URL.createObjectURL(new Blob([r.vtt], { type: 'text/vtt' }))
            urls.push(url)
            carregadas.push({ idioma: leg.idioma, url })
          } catch {
            // legenda ilegível não impede o vídeo
          }
        }
        if (vivo) setFaixas(carregadas)
      } catch (falha) {
        aoAvisar(textoDeFalha(falha), 'atencao')
        aoFechar()
      }
    })()
    return () => {
      vivo = false
      for (const u of urls) URL.revokeObjectURL(u)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- abre uma vez por arquivo
  }, [arquivo])

  const salvar = (forcar = false) => {
    const v = video.current
    if (v === null || sessao === null || !Number.isFinite(v.duration) || v.duration <= 0) return
    const agora = Date.now()
    if (!forcar && agora - ultimoSalvo.current < SALVAR_A_CADA) return
    ultimoSalvo.current = agora
    void window.tucoteca
      .chamar('midia.salvar_posicao', { chave: sessao.chave, posicao: v.currentTime, duracao: v.duration })
      .catch(() => undefined)
  }

  const fechar = () => {
    salvar(true)
    aoMudou()
    aoFechar()
  }

  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        fechar()
      }
    }
    window.addEventListener('keydown', aoTeclar, true)
    return () => window.removeEventListener('keydown', aoTeclar, true)
  })

  const externo = async () => {
    try {
      salvar(true)
      await window.tucoteca.chamar('midia.externo', { arquivo })
      aoAvisar('Abrindo no reprodutor externo.')
      aoFechar()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  return (
    <div class="player-tela" role="dialog" aria-modal="true" aria-label="Player de vídeo">
      <header class="player-topo">
        <strong>{sessao?.titulo ?? 'Abrindo…'}</strong>
        <div class="detalhe-linha">
          <button type="button" class="acao" onClick={() => void externo()}>
            Abrir no reprodutor externo
          </button>
          <button type="button" class="acao" onClick={fechar} aria-label="Fechar player">
            ✕
          </button>
        </div>
      </header>
      {sessao !== null && !semSuporte && (
        <video
          ref={video}
          class="player-video-grande"
          src={window.tucoteca.mediaUrl(sessao.caminho)}
          controls
          autoplay
          onLoadedMetadata={(e) => {
            const v = e.target as HTMLVideoElement
            if (sessao.posicao > 0 && sessao.posicao < v.duration - 5) v.currentTime = sessao.posicao
          }}
          onTimeUpdate={() => salvar()}
          onPause={() => salvar(true)}
          onEnded={() => salvar(true)}
          onError={() => setSemSuporte(true)}
        >
          {faixas.map((f, i) => (
            <track key={f.url} kind="subtitles" src={f.url} label={f.idioma || `Legenda ${i + 1}`} default={i === 0} />
          ))}
        </video>
      )}
      {semSuporte && (
        <div class="player-sem-suporte">
          <p>Este arquivo usa um formato que o player interno não toca (comum em MKV com áudio DTS/AC3 ou vídeo HEVC).</p>
          <button type="button" class="acao primaria" onClick={() => void externo()}>
            Abrir no reprodutor externo (VLC, MPV…)
          </button>
        </div>
      )}
    </div>
  )
}
