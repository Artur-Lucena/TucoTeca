import { useEffect, useRef, useState } from 'preact/hooks'
import {
  alternar,
  anterior,
  cicloModo,
  faixaAtual,
  fimDaFaixa,
  parar,
  player,
  proxima,
  pularPara,
  type ModoPlayer,
} from '../estado/player'

/** m:ss a partir de segundos (NaN/∞ → 0:00). */
export function tempoMmSs(segundos: number): string {
  if (!Number.isFinite(segundos) || segundos < 0) return '0:00'
  const total = Math.floor(segundos)
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

const ROTULO_MODO: Record<ModoPlayer, string> = {
  sequencia: 'Sequência',
  repetir: 'Repetir',
  aleatorio: 'Aleatório',
}

/** Rodapé do player: capa, tempo/seek, transporte, modo, volume e fila. */
export function PlayerRodape() {
  const estado = player.value
  const atual = faixaAtual(estado)
  const caminho = String(atual?.musica_path ?? '')
  const url = caminho === '' ? '' : window.tucoteca.mediaUrl(caminho)
  const audio = useRef<HTMLAudioElement | null>(null)
  const [posicao, setPosicao] = useState(0)
  const [duracao, setDuracao] = useState(0)
  const [volume, setVolume] = useState(1)

  useEffect(() => {
    const el = audio.current
    if (el === null) return
    if (url !== '' && el.dataset.faixa !== url) {
      el.dataset.faixa = url
      el.src = url
      setPosicao(0)
      setDuracao(0)
    }
    if (estado.estado === 'tocando' && url !== '') void el.play().catch(() => undefined)
    else el.pause()
  }, [url, estado.estado])

  useEffect(() => {
    if (audio.current !== null) audio.current.volume = volume
  }, [volume])

  const aoFim = () => {
    const antes = player.value
    const novo = fimDaFaixa(antes)
    player.value = novo
    const el = audio.current
    if (
      el !== null &&
      novo.estado === 'tocando' &&
      faixaAtual(novo)?.musica_path === faixaAtual(antes)?.musica_path
    ) {
      el.currentTime = 0
      void el.play().catch(() => undefined)
    }
  }

  const capa = atual?.capa_url === undefined ? '' : window.tucoteca.imagemUrl(String(atual.capa_url))

  return (
    <footer class="player">
      <audio
        ref={audio}
        preload="metadata"
        onTimeUpdate={(evento) =>
          setPosicao((evento.target as HTMLAudioElement).currentTime)
        }
        onLoadedMetadata={(evento) =>
          setDuracao((evento.target as HTMLAudioElement).duration)
        }
        onEnded={aoFim}
      />
      <div class="player-faixa">
        <span class="player-capa">
          {capa !== '' ? (
            <img src={capa} alt="" />
          ) : (
            <span class="capa-vazia">♪</span>
          )}
        </span>
        <span class="player-textos">
          <strong>{String(atual?.titulo ?? '')}</strong>
          <span>{String(atual?.artista ?? '')}</span>
        </span>
      </div>
      <div class="player-controles">
        <div class="player-linha">
          <button type="button" class="player-botao" title="Anterior" aria-label="Faixa anterior" onClick={() => (player.value = anterior(player.value))}>
            ❮
          </button>
          <button
            type="button"
            class="player-botao primario"
            title={estado.estado === 'tocando' ? 'Pausar' : 'Tocar'}
            aria-label={estado.estado === 'tocando' ? 'Pausar' : 'Tocar'}
            onClick={() => (player.value = alternar(player.value))}
          >
            {estado.estado === 'tocando' ? 'Ⅱ' : '▶'}
          </button>
          <button type="button" class="player-botao" title="Próxima" aria-label="Próxima faixa" onClick={() => (player.value = proxima(player.value))}>
            ❯
          </button>
          <button type="button" class="player-botao" title="Parar" aria-label="Parar reprodução" onClick={() => (player.value = parar(player.value))}>
            ■
          </button>
          <span class="player-tempo">
            {tempoMmSs(posicao)} / {tempoMmSs(duracao)}
          </span>
          <input
            class="player-barra"
            type="range"
            min={0}
            max={duracao > 0 ? duracao : 1}
            step={0.1}
            value={Math.min(posicao, duracao > 0 ? duracao : 1)}
            aria-label="Progresso da faixa"
            onInput={(evento) => {
              const el = audio.current
              if (el === null) return
              const valor = Number((evento.target as HTMLInputElement).value)
              el.currentTime = valor
              setPosicao(valor)
            }}
          />
          <button
            type="button"
            class="player-modo"
            title="Modo de reprodução"
            onClick={() => (player.value = cicloModo(player.value))}
          >
            {ROTULO_MODO[estado.modo]}
          </button>
          <input
            class="player-volume"
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={volume}
            aria-label="Volume"
            onInput={(evento) => setVolume(Number((evento.target as HTMLInputElement).value))}
          />
        </div>
      </div>
      <ul class="player-fila">
        {estado.fila.map((faixa, indice) => (
          <li key={String(faixa.id ?? indice)} class={indice === estado.indice ? 'atual' : ''}>
            <button
              type="button"
              onClick={() => (player.value = pularPara(player.value, indice))}
              title={`Tocar ${String(faixa.titulo ?? '')}`}
            >
              {indice === estado.indice ? '▶ ' : ''}
              {String(faixa.titulo ?? '')}
            </button>
          </li>
        ))}
      </ul>
    </footer>
  )
}
