import { useRef, useState } from 'preact/hooks'

interface Props {
  urlInicial?: string
}

/** Navegador YouTube embutido (webview), estilo Qt NavegadorEmbed. */
export function NavegadorYouTube({ urlInicial = 'https://www.youtube.com' }: Props) {
  const webviewRef = useRef<HTMLElement | null>(null)
  const [url, setUrl] = useState(urlInicial)
  const [input, setInput] = useState(urlInicial)
  const [carregando, setCarregando] = useState(false)

  const ir = (destino: string) => {
    const alvo = destino.trim()
    if (alvo === '') return
    const final = alvo.startsWith('http') ? alvo : `https://www.youtube.com/results?search_query=${encodeURIComponent(alvo)}`
    setUrl(final)
    setInput(final)
  }

  return (
    <div class="navegador-youtube">
      <div class="navegador-barra">
        <button type="button" class="acao" onClick={() => (webviewRef.current as any)?.goBack?.()}>
          ←
        </button>
        <button type="button" class="acao" onClick={() => (webviewRef.current as any)?.reload?.()}>
          ↻
        </button>
        <input
          class="busca"
          type="text"
          value={input}
          onInput={(evento) => setInput((evento.target as HTMLInputElement).value)}
          onKeyDown={(evento) => {
            if (evento.key === 'Enter') ir(input)
          }}
        />
        <button type="button" class="acao" onClick={() => ir(input)}>
          Ir
        </button>
        {carregando && <span class="aviso">Carregando…</span>}
      </div>
      {/* @ts-expect-error webview is an Electron element */}
      <webview
        ref={webviewRef as any}
        src={url}
        partition="persist:youtube"
        allowpopups="false"
        style={{ width: '100%', height: '480px', border: '0' }}
        onDidStartLoading={() => setCarregando(true)}
        onDidStopLoading={() => setCarregando(false)}
      />
    </div>
  )
}
