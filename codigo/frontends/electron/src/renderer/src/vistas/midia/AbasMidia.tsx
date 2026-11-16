import { useEffect, useState } from 'preact/hooks'
import { EmptyState } from '../../componentes/ui'
import { agruparPorDia, reproduzindo, rotuloEpisodio, type TituloResumo } from '../../estado/midia'
import { textoDeFalha } from '../../estado/notificacoes'
import { ir } from '../../estado/rota'
import { GradeTitulos } from './GradeTitulos'

type Avisar = (texto: string, tom?: 'info' | 'atencao') => void

export interface ItemContinuar {
  arquivo: number
  chave: string
  imdb_id: string
  titulo: string
  poster: string
  fundo: string
  motivo: string
  fracao: number
}

/** Cartões de "Continuar assistindo" (também usados no Início). */
export function ListaContinuar({ itens }: { itens: ItemContinuar[] }) {
  return (
    <div class="grade-continuar">
      {itens.map((c) => (
        <button key={c.chave} type="button" class="cartao-continuar" onClick={() => (reproduzindo.value = c.arquivo)} title={`Assistir ${c.titulo}`}>
          <span class="cartao-continuar-arte">
            {(c.fundo || c.poster) !== '' && (
              <img src={window.tucoteca.imagemUrl(c.fundo || c.poster)} alt="" loading="lazy" onError={(e) => ((e.target as HTMLImageElement).style.display = 'none')} />
            )}
            <span class="cartao-continuar-play" aria-hidden="true">
              ▶
            </span>
            {c.fracao > 0 && (
              <span class="cartao-titulo-barra">
                <span style={{ width: `${Math.round(c.fracao * 100)}%` }} />
              </span>
            )}
          </span>
          <span class="cartao-titulo-nome">{c.titulo}</span>
          <span class="sub">{c.motivo}</span>
        </button>
      ))}
    </div>
  )
}

export function Continuar({ aoAvisar }: { aoAvisar: Avisar }) {
  const [itens, setItens] = useState<ItemContinuar[] | null>(null)
  useEffect(() => {
    window.tucoteca
      .chamar<ItemContinuar[]>('midia.continuar')
      .then(setItens)
      .catch((falha) => aoAvisar(textoDeFalha(falha), 'atencao'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reproduzindo.value])
  if (itens === null) return <p class="sub">Carregando…</p>
  if (itens.length === 0) return <EmptyState icone="▶" titulo="Nada pela metade." descricao="O que você começar a ver aparece aqui, junto com o próximo episódio das séries." />
  return <ListaContinuar itens={itens} />
}

interface CartaoDescobrir {
  imdb_id: string
  tipo: 'movie' | 'series'
  nome: string
  ano: string
  poster: string
  nota: string
  no_disco: boolean
  na_lista: boolean
}

const GENEROS = ['', 'Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Family', 'Fantasy', 'Horror', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller']
const NOMES_GENERO: Record<string, string> = {
  '': 'Populares', Action: 'Ação', Adventure: 'Aventura', Animation: 'Animação', Comedy: 'Comédia', Crime: 'Crime',
  Documentary: 'Documentário', Drama: 'Drama', Family: 'Família', Fantasy: 'Fantasia', Horror: 'Terror', Mystery: 'Mistério',
  Romance: 'Romance', 'Sci-Fi': 'Ficção científica', Thriller: 'Suspense',
}

/** Descobrir: catálogo Cinemeta por tipo e gênero, com busca (abrir a aba é o pedido de rede). */
export function Descobrir(_props: { aoAvisar: Avisar }) {
  const [tipo, setTipo] = useState<'movie' | 'series'>('movie')
  const [genero, setGenero] = useState('')
  const [termo, setTermo] = useState('')
  const [busca, setBusca] = useState('')
  const [itens, setItens] = useState<CartaoDescobrir[] | null>(null)
  const [pular, setPular] = useState(0)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    let vivo = true
    setErro(null)
    window.tucoteca
      .chamar<CartaoDescobrir[]>('midia.descobrir', { tipo, genero, pular, termo: busca })
      .then((r) => vivo && setItens((atual) => (pular > 0 && atual !== null ? [...atual, ...r] : r)))
      .catch((falha) => vivo && setErro(textoDeFalha(falha)))
    return () => {
      vivo = false
    }
  }, [tipo, genero, pular, busca])

  const trocar = (fn: () => void) => {
    setItens(null)
    setPular(0)
    fn()
  }

  return (
    <section class="descobrir">
      <div class="midia-barra">
        <div class="biblioteca-modos">
          <button type="button" class={`chip${tipo === 'movie' ? ' ativo' : ''}`} onClick={() => trocar(() => setTipo('movie'))}>
            Filmes
          </button>
          <button type="button" class={`chip${tipo === 'series' ? ' ativo' : ''}`} onClick={() => trocar(() => setTipo('series'))}>
            Séries
          </button>
        </div>
        <select value={genero} onChange={(e) => trocar(() => setGenero((e.target as HTMLSelectElement).value))} disabled={busca !== ''}>
          {GENEROS.map((g) => (
            <option key={g} value={g}>
              {NOMES_GENERO[g] ?? g}
            </option>
          ))}
        </select>
        <form
          class="catalogo-busca"
          onSubmit={(e) => {
            e.preventDefault()
            trocar(() => setBusca(termo.trim()))
          }}
        >
          <input
            class="busca"
            type="search"
            placeholder={tipo === 'movie' ? 'Buscar filmes…' : 'Buscar séries…'}
            value={termo}
            onInput={(e) => {
              const v = (e.target as HTMLInputElement).value
              setTermo(v)
              if (v.trim() === '' && busca !== '') trocar(() => setBusca(''))
            }}
          />
          <button type="submit" class="acao">
            Buscar
          </button>
        </form>
      </div>
      {erro !== null ? (
        <EmptyState icone="⚠" titulo="Não deu para abrir o catálogo." descricao={erro} />
      ) : itens === null ? (
        <p class="sub">Carregando o catálogo…</p>
      ) : itens.length === 0 ? (
        <p class="sub">Nada encontrado.</p>
      ) : (
        <>
          <GradeTitulos itens={itens.map((c) => ({ ...c, selo: c.no_disco ? 'No disco' : c.na_lista ? 'Na lista' : c.nota ? `★ ${c.nota}` : '' }))} />
          {busca === '' && itens.length >= pular + 20 && (
            <button type="button" class="acao mais" onClick={() => setPular(itens.length)}>
              Carregar mais
            </button>
          )}
        </>
      )}
      <p class="sub catalogo-nota">Catálogo Cinemeta (o mesmo do Stremio), só informações: nada é baixado nem transmitido.</p>
    </section>
  )
}

export function MinhaLista({ aoAvisar }: { aoAvisar: Avisar }) {
  const [itens, setItens] = useState<Array<TituloResumo & { seguindo: boolean }> | null>(null)
  useEffect(() => {
    window.tucoteca
      .chamar<Array<TituloResumo & { seguindo: boolean }>>('midia.lista')
      .then(setItens)
      .catch((falha) => aoAvisar(textoDeFalha(falha), 'atencao'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  if (itens === null) return <p class="sub">Carregando…</p>
  if (itens.length === 0) {
    return <EmptyState icone="＋" titulo="Sua lista está vazia." descricao="Em Descobrir ou na página de um título, use “+ Minha lista”." acao={{ rotulo: 'Descobrir', onClick: () => ir('#/midia/descobrir') }} />
  }
  return <GradeTitulos itens={itens.map((t) => ({ ...t, selo: t.seguindo ? 'Seguindo' : '' }))} />
}

interface EpisodioCalendario {
  imdb_id: string
  serie: string
  poster: string
  chave: string
  temporada: number
  episodio: number
  nome: string
  data: string
  lancado: boolean
  assistido: boolean
}

/** Calendário das séries seguidas; ao abrir, renova os episódios se a última vez foi há mais de 12 h. */
export function Calendario({ aoAvisar }: { aoAvisar: Avisar }) {
  const [itens, setItens] = useState<EpisodioCalendario[] | null>(null)
  const [renovando, setRenovando] = useState<number | null>(null)

  const carregar = () =>
    window.tucoteca
      .chamar<EpisodioCalendario[]>('midia.calendario')
      .then(setItens)
      .catch((falha) => aoAvisar(textoDeFalha(falha), 'atencao'))

  useEffect(() => {
    void carregar()
    window.tucoteca
      .chamar<{ trabalho?: { id?: number } }>('midia.atualizar_seguidas')
      .then((r) => {
        const ident = Number(r?.trabalho?.id)
        if (Number.isInteger(ident)) setRenovando(ident)
      })
      .catch(() => undefined) // sem rede/sem seguidas: fica o que já está salvo
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (renovando === null) return
    return window.tucoteca.assinar('trabalho', (d) => {
      const e = d as { id?: number; motivo?: string } | null
      if (e?.id === renovando && e.motivo === 'fim') {
        setRenovando(null)
        void carregar()
      }
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [renovando])

  if (itens === null) return <p class="sub">Carregando…</p>
  if (itens.length === 0) {
    return <EmptyState icone="📅" titulo="Nada no calendário." descricao="Siga uma série (botão “Seguir” na página dela) para ver os episódios novos e os próximos aqui." />
  }
  return (
    <section class="calendario">
      {renovando !== null && <p class="sub">Atualizando as séries seguidas…</p>}
      {agruparPorDia(itens).map((g) => (
        <div key={g.rotulo} class="calendario-dia">
          <h3>{g.rotulo}</h3>
          <ul>
            {g.itens.map((e) => (
              <li key={e.chave}>
                <button type="button" class={`calendario-item${e.lancado ? '' : ' futuro'}`} onClick={() => ir(`#/titulo/${e.imdb_id}`)}>
                  {e.poster !== '' && <img src={e.poster} alt="" loading="lazy" onError={(ev) => ((ev.target as HTMLImageElement).style.display = 'none')} />}
                  <span>
                    <strong>{e.serie}</strong>
                    <span class="sub">
                      {rotuloEpisodio(e.temporada, e.episodio)}
                      {e.nome !== '' ? ` · ${e.nome}` : ''}
                    </span>
                  </span>
                  {e.assistido && <span class="selo">✓ visto</span>}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  )
}
