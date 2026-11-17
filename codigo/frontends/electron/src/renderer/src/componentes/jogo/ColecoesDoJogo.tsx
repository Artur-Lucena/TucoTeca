import { useEffect, useRef, useState } from 'preact/hooks'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'

interface Item {
  id: number
  nome: string
  tem: boolean
}

interface Props {
  id: number
  aoMudou: () => void
  aoAvisar: AoAvisar
}

/** Botão “Coleções” do topo do jogo: marca/desmarca e cria coleção na hora. */
export function ColecoesDoJogo({ id, aoMudou, aoAvisar }: Props) {
  const [aberto, setAberto] = useState(false)
  const [itens, setItens] = useState<Item[]>([])
  const [nova, setNova] = useState('')
  const raiz = useRef<HTMLDivElement>(null)

  useEffect(() => {
    window.tucoteca
      .chamar<Item[]>('jogo.colecoes', { id })
      .then((r) => setItens(Array.isArray(r) ? r : []))
      .catch((falha) => aoAvisar(textoDeFalha(falha), 'atencao'))
    if (!aberto) return
    const fora = (e: MouseEvent) => {
      if (raiz.current !== null && !raiz.current.contains(e.target as Node)) setAberto(false)
    }
    document.addEventListener('mousedown', fora)
    return () => document.removeEventListener('mousedown', fora)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- recarrega ao abrir
  }, [aberto, id])

  const alternar = async (c: Item) => {
    try {
      setItens(await window.tucoteca.chamar<Item[]>('colecoes.definir', { colecao: c.id, jogo: id, dentro: !c.tem }))
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const criar = async (e: Event) => {
    e.preventDefault()
    if (nova.trim() === '') return
    try {
      const c = await window.tucoteca.chamar<{ id: number }>('colecoes.criar', { nome: nova.trim() })
      setItens(await window.tucoteca.chamar<Item[]>('colecoes.definir', { colecao: c.id, jogo: id, dentro: true }))
      setNova('')
      aoMudou()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const quantas = itens.filter((c) => c.tem).length
  return (
    <div class="colecoes-jogo" ref={raiz}>
      <button type="button" class="acao" aria-expanded={aberto} onClick={() => setAberto(!aberto)}>
        ▦ Coleções{quantas > 0 ? ` (${quantas})` : ''}
      </button>
      {aberto && (
        <div class="colecoes-popover" role="dialog" aria-label="Coleções do jogo">
          {itens.length === 0 && <p class="sub">Nenhuma coleção ainda.</p>}
          {itens.map((c) => (
            <label key={c.id} class="marcar">
              <input type="checkbox" checked={c.tem} onChange={() => void alternar(c)} />
              {c.nome}
            </label>
          ))}
          <form class="detalhe-linha" onSubmit={(e) => void criar(e)}>
            <input value={nova} placeholder="Nova coleção" maxLength={60} onInput={(e) => setNova((e.target as HTMLInputElement).value)} />
            <button type="submit" class="acao">
              Criar
            </button>
          </form>
        </div>
      )}
    </div>
  )
}
