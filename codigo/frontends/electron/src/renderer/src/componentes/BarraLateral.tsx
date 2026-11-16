import { useEffect, useMemo, useRef, useState } from 'preact/hooks'
import type { ModuloDTO } from '../../../shared/protocolo'
import type { ColecaoResumo, JogoResumo } from '../derivacoes'
import { itensBiblioteca, janelaVisivel, type ModoBiblioteca } from '../estado/biblioteca'
import { ir } from '../estado/rota'

interface Props {
  modulos: ModuloDTO[]
  ativa: string
  jogos: JogoResumo[] | undefined
  colecoes: ColecaoResumo[]
  jogoAberto: number | null
}

const ALTURA_ITEM = 34
const MODOS: Array<{ chave: ModoBiblioteca; nome: string }> = [
  { chave: 'todos', nome: 'Todos' },
  { chave: 'favoritos', nome: 'Favoritos' },
  { chave: 'recentes', nome: 'Recentes' },
]

/** Barra lateral: as seis seções e, abaixo, a biblioteca de jogos (lista virtualizada). */
export function BarraLateral({ modulos, ativa, jogos, colecoes, jogoAberto }: Props) {
  return (
    <aside class="barra-lateral">
      <div class="marca">TucoTeca</div>
      <nav class="nav-secoes">
        {modulos.map((modulo) => (
          <button
            key={modulo.chave}
            type="button"
            class={`item${modulo.chave === ativa ? ' ativo' : ''}`}
            title={modulo.descricao}
            aria-current={modulo.chave === ativa ? 'page' : undefined}
            onClick={() => ir(modulo.chave)}
          >
            <span class="icone" aria-hidden="true">
              {modulo.nome.trim().charAt(0)}
            </span>
            <span class="rotulo">{modulo.nome}</span>
          </button>
        ))}
      </nav>
      <BibliotecaLateral jogos={jogos} colecoes={colecoes} jogoAberto={jogoAberto} />
    </aside>
  )
}

function BibliotecaLateral({ jogos, colecoes, jogoAberto }: { jogos: JogoResumo[] | undefined; colecoes: ColecaoResumo[]; jogoAberto: number | null }) {
  const [termo, setTermo] = useState('')
  const [modo, setModo] = useState<ModoBiblioteca>('todos')
  const [colecaoId, setColecaoId] = useState<number | null>(null)
  const [rolagem, setRolagem] = useState(0)
  const [altura, setAltura] = useState(400)
  const caixa = useRef<HTMLDivElement>(null)
  const colecao = colecoes.find((c) => c.id === colecaoId)
  const filtroColecao = useMemo(() => (colecao === undefined ? undefined : new Set(colecao.uuids)), [colecao])
  const itens = useMemo(() => itensBiblioteca(jogos, termo, modo, filtroColecao), [jogos, termo, modo, filtroColecao])

  useEffect(() => {
    const el = caixa.current
    if (el === null) return
    const medir = () => setAltura(el.clientHeight)
    medir()
    const obs = new ResizeObserver(medir)
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  useEffect(() => {
    if (caixa.current !== null) caixa.current.scrollTop = 0
    setRolagem(0)
  }, [termo, modo, colecaoId])

  const janela = janelaVisivel(itens.length, ALTURA_ITEM, rolagem, altura)
  return (
    <section class="biblioteca-lateral" aria-label="Biblioteca de jogos">
      <div class="biblioteca-topo">
        <span class="biblioteca-titulo">Biblioteca</span>
        <span class="sub">{itens.length}</span>
      </div>
      <input
        class="biblioteca-filtro"
        type="search"
        placeholder="Filtrar biblioteca"
        aria-label="Filtrar biblioteca"
        value={termo}
        onInput={(evento) => setTermo((evento.target as HTMLInputElement).value)}
      />
      <div class="biblioteca-modos" role="tablist">
        {MODOS.map((m) => (
          <button
            key={m.chave}
            type="button"
            role="tab"
            aria-selected={modo === m.chave}
            class={`chip${modo === m.chave ? ' ativo' : ''}`}
            onClick={() => setModo(m.chave)}
          >
            {m.nome}
          </button>
        ))}
      </div>
      {colecoes.length > 0 && (
        <select
          class="biblioteca-colecao"
          aria-label="Filtrar por coleção"
          value={colecao === undefined ? '' : String(colecao.id)}
          onChange={(e) => {
            const v = (e.target as HTMLSelectElement).value
            setColecaoId(v === '' ? null : Number(v))
          }}
        >
          <option value="">Todas as coleções</option>
          {colecoes.map((c) => (
            <option key={c.id} value={String(c.id)}>
              {c.nome} ({c.uuids.length})
            </option>
          ))}
        </select>
      )}
      <div class="biblioteca-lista" ref={caixa} onScroll={(e) => setRolagem((e.target as HTMLDivElement).scrollTop)}>
        {itens.length === 0 ? (
          <p class="biblioteca-vazia">{termo.trim() !== '' || modo !== 'todos' || colecao !== undefined ? 'Nada com esse filtro.' : 'Nenhum jogo ainda.'}</p>
        ) : (
          <ul style={{ paddingTop: `${janela.antes}px`, paddingBottom: `${janela.depois}px` }}>
            {itens.slice(janela.inicio, janela.fim).map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  class={`biblioteca-item${item.id === jogoAberto ? ' ativo' : ''}`}
                  style={{ height: `${ALTURA_ITEM}px` }}
                  title={item.titulo}
                  onClick={() => ir(`#/jogo/${item.id}`)}
                >
                  {item.capa_url !== '' ? (
                    <img src={window.tucoteca.imagemUrl(item.capa_url)} alt="" loading="lazy" />
                  ) : (
                    <span class="biblioteca-sem-capa" aria-hidden="true">
                      {item.titulo.charAt(0)}
                    </span>
                  )}
                  <span class="biblioteca-nome">{item.titulo}</span>
                  {item.favorito && <span class="biblioteca-fav" aria-label="favorito">★</span>}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
