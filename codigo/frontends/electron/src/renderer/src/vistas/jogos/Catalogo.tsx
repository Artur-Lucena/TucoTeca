import { useEffect, useState } from 'preact/hooks'
import { EmptyState } from '../../componentes/ui'
import { formatarPreco, type PrecoSteam } from '../../estado/desejos'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { ir } from '../../estado/rota'

interface CartaoLoja {
  appid: string
  nome: string
  imagem: string
  /** Capa em pé (600×900), quando a vitrine é por gênero. */
  capa?: string
  preco: PrecoSteam | null
  na_biblioteca: number | null
  nos_desejos: boolean
}

interface Secao {
  chave: string
  titulo: string
  itens: CartaoLoja[]
}

interface Genero {
  chave: string
  nome: string
}

interface PaginaGenero {
  genero: string
  nome: string
  pagina: number
  total: number
  itens: CartaoLoja[]
}

interface Props {
  aoAvisar: AoAvisar
}

/** Jogos › Catálogo: vitrine e busca da loja Steam (abrir a aba é o pedido de rede). */
export function Catalogo({ aoAvisar }: Props) {
  const [secoes, setSecoes] = useState<Secao[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [termo, setTermo] = useState('')
  const [resultados, setResultados] = useState<CartaoLoja[] | null>(null)
  const [buscando, setBuscando] = useState(false)
  const [generos, setGeneros] = useState<Genero[]>([])
  const [genero, setGenero] = useState<PaginaGenero | null>(null)
  const [carregandoGenero, setCarregandoGenero] = useState(false)

  useEffect(() => {
    window.tucoteca
      .chamar<Genero[]>('loja.generos')
      .then((r) => setGeneros(Array.isArray(r) ? r : []))
      .catch(() => setGeneros([]))
  }, [])

  const abrirGenero = async (chave: string, pagina = 0) => {
    if (pagina === 0 && genero?.genero === chave) {
      setGenero(null)
      return
    }
    setCarregandoGenero(true)
    try {
      const r = await window.tucoteca.chamar<PaginaGenero>('loja.genero', { genero: chave, pagina })
      setGenero((atual) =>
        pagina > 0 && atual !== null && atual.genero === chave ? { ...r, itens: [...atual.itens, ...r.itens] } : r,
      )
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setCarregandoGenero(false)
    }
  }

  const carregar = () => {
    setErro(null)
    window.tucoteca
      .chamar<Secao[]>('loja.destaques')
      .then((r) => setSecoes(Array.isArray(r) ? r : []))
      .catch((falha) => setErro(textoDeFalha(falha)))
  }
  useEffect(carregar, [])

  const buscar = async (evento?: Event) => {
    evento?.preventDefault()
    if (termo.trim().length < 2) {
      setResultados(null)
      return
    }
    setBuscando(true)
    try {
      setResultados(await window.tucoteca.chamar<CartaoLoja[]>('loja.buscar', { termo: termo.trim() }))
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setBuscando(false)
    }
  }

  return (
    <section class="catalogo">
      <form class="catalogo-busca" onSubmit={(e) => void buscar(e)}>
        <input
          class="busca"
          type="search"
          placeholder="Buscar na loja Steam…"
          value={termo}
          onInput={(e) => {
            const v = (e.target as HTMLInputElement).value
            setTermo(v)
            if (v.trim() === '') setResultados(null)
          }}
        />
        <button type="submit" class="acao" disabled={buscando}>
          {buscando ? 'Buscando…' : 'Buscar'}
        </button>
      </form>
      {generos.length > 0 && resultados === null && (
        <div class="filtros generos-loja" role="group" aria-label="Descobrir por gênero">
          {generos.map((g) => (
            <button
              key={g.chave}
              type="button"
              class={`chip${genero?.genero === g.chave ? ' ativo' : ''}`}
              aria-pressed={genero?.genero === g.chave}
              onClick={() => void abrirGenero(g.chave)}
            >
              {g.nome}
            </button>
          ))}
        </div>
      )}
      {resultados === null && genero !== null ? (
        <div class="catalogo-secao">
          <h2>{genero.nome} — mais vendidos</h2>
          {genero.itens.length === 0 ? <p class="sub">Nada neste gênero agora.</p> : <GradeLoja itens={genero.itens} vertical />}
          {genero.itens.length < genero.total && (
            <button
              type="button"
              class="acao catalogo-mais"
              disabled={carregandoGenero}
              onClick={() => void abrirGenero(genero.genero, genero.pagina + 1)}
            >
              {carregandoGenero ? 'Carregando…' : 'Mais jogos'}
            </button>
          )}
        </div>
      ) : carregandoGenero && resultados === null ? (
        <p class="sub">Carregando o gênero…</p>
      ) : resultados !== null ? (
        <div class="catalogo-secao">
          <h2>Resultados para “{termo.trim()}”</h2>
          {resultados.length === 0 ? <p class="sub">Nada encontrado.</p> : <GradeLoja itens={resultados} />}
        </div>
      ) : erro !== null ? (
        <EmptyState icone="⚠" titulo="Não deu para abrir o catálogo." descricao={erro} acao={{ rotulo: 'Tentar de novo', onClick: carregar }} />
      ) : secoes === null ? (
        <p class="sub">Carregando a vitrine da Steam…</p>
      ) : (
        secoes.map((s) => (
          <div key={s.chave} class="catalogo-secao">
            <h2>{s.titulo}</h2>
            <GradeLoja itens={s.itens} />
          </div>
        ))
      )}
      <p class="sub catalogo-nota">Catálogo público da loja Steam (preços do Brasil). A Steam aqui é só referência: nada é comprado nem instalado.</p>
    </section>
  )
}

/** Se a capa em pé não existir, cai na imagem horizontal; se nem ela, some. */
function trocarImagem(c: CartaoLoja) {
  return (e: Event) => {
    const img = e.target as HTMLImageElement
    if (c.capa !== undefined && img.src !== c.imagem) {
      img.src = c.imagem
      img.classList.add('horizontal')
    } else {
      img.style.visibility = 'hidden'
    }
  }
}

function GradeLoja({ itens, vertical = false }: { itens: CartaoLoja[]; vertical?: boolean }) {
  return (
    <div class={`grade-loja${vertical ? ' vertical' : ''}`}>
      {itens.map((c) => {
        const preco = formatarPreco(c.preco)
        return (
          <button key={c.appid} type="button" class="cartao-loja" onClick={() => ir(`#/loja/${c.appid}`)} title={c.nome}>
            <img src={vertical && c.capa ? c.capa : c.imagem} alt="" loading="lazy" onError={trocarImagem(c)} />
            <span class="cartao-loja-nome">{c.nome}</span>
            <span class="cartao-loja-rodape">
              {c.na_biblioteca !== null ? (
                <span class="selo">Na biblioteca</span>
              ) : c.nos_desejos ? (
                <span class="selo">Nos desejos</span>
              ) : (
                <span />
              )}
              {preco !== '' && <span class={`preco${(c.preco?.desconto_pct ?? 0) > 0 ? ' promo' : ''}`}>{preco}</span>}
            </span>
          </button>
        )
      })}
    </div>
  )
}
