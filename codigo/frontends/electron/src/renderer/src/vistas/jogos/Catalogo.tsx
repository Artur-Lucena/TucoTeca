import { useEffect, useState } from 'preact/hooks'
import { EmptyState } from '../../componentes/ui'
import { formatarPreco, type PrecoSteam } from '../../estado/desejos'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { ir } from '../../estado/rota'

export interface CartaoLoja {
  appid: string
  nome: string
  imagem: string
  preco: PrecoSteam | null
  na_biblioteca: number | null
  nos_desejos: boolean
}

interface Secao {
  chave: string
  titulo: string
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
      {resultados !== null ? (
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

export function GradeLoja({ itens }: { itens: CartaoLoja[] }) {
  return (
    <div class="grade-loja">
      {itens.map((c) => {
        const preco = formatarPreco(c.preco)
        return (
          <button key={c.appid} type="button" class="cartao-loja" onClick={() => ir(`#/loja/${c.appid}`)} title={c.nome}>
            <img src={c.imagem} alt="" loading="lazy" onError={(e) => ((e.target as HTMLImageElement).style.visibility = 'hidden')} />
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
