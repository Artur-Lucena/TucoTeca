import { useEffect, useMemo, useRef, useState } from 'preact/hooks'
import { snapshot } from '../estado/dados'
import { EmptyState } from '../componentes/ui'
import { type AoAvisar, textoDeFalha } from '../estado/notificacoes'
import { faixaAtual, player, playerInicial, tocarFila } from '../estado/player'
import { cancelarTrabalho, listaTrabalhos } from '../estado/trabalhos'
import type { JogoResumo } from '../estado/derivacoes'
import { confirmar } from '../componentes/ui/Confirmacao'
import { semAcento } from '../estado/formato'
import { useSetasLista } from '../navegacao/setas'

/** Rótulos dos presets de `PRESETS_EQ` (equalizadores.py). */
const ROTULO_EQ: Record<string, string> = {
  flat: 'Normalizar volume',
  bass: 'Mais grave',
  treble: 'Mais agudo',
  vocal: 'Voz em destaque',
  rock: 'Rock',
  night: 'Modo noturno',
}

interface Props {
  /** Incrementa a cada Ctrl+F: foca o campo de busca. */
  focoBusca?: number
  /** Troca de perfil recarrega o snapshot (a lista não muda com o perfil). */
  perfil?: string
  aoAvisar: AoAvisar
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

  useSetasLista(lista.length, setSelecionado, () => tocar(indice), campo)

  const remover = async () => {
    if (escolhida?.id === undefined) return
    const titulo = String(escolhida.titulo ?? 'a música')
    const aviso = `Remover "${titulo}"? O arquivo de áudio também será apagado e não dá para desfazer.`
    if (!(await confirmar({ titulo: 'Remover música', texto: aviso, confirmar: 'Remover', perigo: true }))) return
    try {
      await window.tucoteca.chamar('item.excluir', { categoria: 'musicas', id: Number(escolhida.id) })
      if (faixaAtual(player.value)?.id === escolhida.id) player.value = playerInicial
      aoAvisar(`${titulo} foi removida (o arquivo foi apagado).`)
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const [eqPresets, setEqPresets] = useState<string[]>([])
  const [eqPreset, setEqPreset] = useState('bass')
  const [eqFfmpeg, setEqFfmpeg] = useState(false)

  useEffect(() => {
    void (async () => {
      try {
        const r = await window.tucoteca.chamar<{ presets?: string[]; ffmpeg?: boolean }>('musicas.eq_presets')
        const presets = Array.isArray(r?.presets) ? r.presets : []
        setEqPresets(presets)
        setEqFfmpeg(r?.ffmpeg === true)
        if (presets.length > 0 && !presets.includes('bass')) setEqPreset(presets[0])
      } catch {
        // sem presets o controle some; não é erro para o usuário
      }
    })()
  }, [])

  const equalizar = async () => {
    if (escolhida === undefined) return
    const caminho = String(escolhida.musica_path ?? '')
    if (caminho === '') return aoAvisar('Esta faixa não tem arquivo local.', 'atencao')
    try {
      await window.tucoteca.chamar('musicas.eq', { caminho, preset: eqPreset })
      aoAvisar(`Equalizando "${String(escolhida.titulo ?? '')}" (${ROTULO_EQ[eqPreset] ?? eqPreset})… a cópia aparece na lista ao terminar; o original fica intacto.`)
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
      await cancelarTrabalho(id)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const trabalho =
    listaTrabalhos.value.find(
      (item) => item.escopo === 'musicas' && (item.estado === 'rodando' || item.estado === 'cancelando'),
    ) ?? null

  const [onlineTermo, setOnlineTermo] = useState('')
  const [onlineResultados, setOnlineResultados] = useState<Array<Record<string, unknown>>>([])
  const [onlineBuscando, setOnlineBuscando] = useState(false)

  const buscarOnline = async () => {
    if (onlineTermo.trim().length < 2) return
    setOnlineBuscando(true)
    try {
      const r = await window.tucoteca.chamar<Array<Record<string, unknown>> | { itens?: Array<Record<string, unknown>> }>(
        'musicas.buscar_online',
        { termo: onlineTermo.trim(), fonte: 'todas', atualizar: false },
      )
      setOnlineResultados(Array.isArray(r) ? r : (r?.itens ?? []))
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOnlineBuscando(false)
    }
  }

  const enfileirarOnline = async (item: Record<string, unknown>) => {
    try {
      await window.tucoteca.chamar('musicas.enfileirar', { itens: [item] })
      aoAvisar('Faixa enfileirada.')
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }
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
          {eqPresets.length > 0 && (
            <>
              <select
                class="eq-preset"
                value={eqPreset}
                aria-label="Preset de equalização"
                title={eqFfmpeg ? 'Preset de equalização' : 'Instale o FFmpeg para equalizar'}
                onChange={(e) => setEqPreset((e.target as HTMLSelectElement).value)}
              >
                {eqPresets.map((p) => (
                  <option key={p} value={p}>
                    {ROTULO_EQ[p] ?? p}
                  </option>
                ))}
              </select>
              <button
                type="button"
                class="acao"
                onClick={() => void equalizar()}
                disabled={escolhida === undefined || !eqFfmpeg}
                title={eqFfmpeg ? 'Gera uma cópia equalizada da faixa selecionada' : 'Instale o FFmpeg para equalizar'}
              >
                Equalizar
              </button>
            </>
          )}
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
        <EmptyState icone="♪" titulo="Nada por aqui." descricao="Importe uma pasta com arquivos de áudio." />
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

      <section class="musicas-online">
        <h2>Músicas online</h2>
        <div class="vista-acoes">
          <input
            class="busca"
            type="search"
            placeholder="Buscar no Spotify/YouTube..."
            value={onlineTermo}
            onInput={(evento) => setOnlineTermo((evento.target as HTMLInputElement).value)}
          />
          <button type="button" class="acao" onClick={() => void buscarOnline()} disabled={onlineBuscando}>
            {onlineBuscando ? 'Buscando...' : 'Buscar'}
          </button>
        </div>
        {onlineResultados.length > 0 && (
          <ul class="lista-online">
            {onlineResultados.map((item, posicao) => (
              <li key={posicao} class="linha">
                <span class="musica-textos">
                  <strong>{String(item.titulo ?? '')}</strong>
                  <span>{String(item.artista ?? item.canal ?? '')}</span>
                </span>
                <button type="button" class="acao" onClick={() => void enfileirarOnline(item)}>
                  Enfileirar
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

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
