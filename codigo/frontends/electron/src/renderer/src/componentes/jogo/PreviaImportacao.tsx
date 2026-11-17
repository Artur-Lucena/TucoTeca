import { useEffect, useRef, useState } from 'preact/hooks'
import { detalheItem, type ItemPrevia } from '../../estado/importacao'
import { textoDeFalha } from '../../estado/notificacoes'

interface Props {
  itens: ItemPrevia[]
  avisos: string[]
  aoFechar: () => void
  aoImportou: () => void
  aoAvisar: (texto: string, tom?: 'info' | 'atencao') => void
}

/**
 * Prévia do que foi solto na tela Jogos: nada é gravado antes de "Importar".
 * Tudo vem marcado; a importação faz backup da coleção no núcleo.
 */
export function PreviaImportacao({ itens, avisos, aoFechar, aoImportou, aoAvisar }: Props) {
  const [marcados, setMarcados] = useState<Set<number>>(() => new Set(itens.map((_, i) => i)))
  const [ocupado, setOcupado] = useState(false)
  const caixa = useRef<HTMLDivElement>(null)

  useEffect(() => {
    caixa.current?.querySelector<HTMLElement>('button, input')?.focus()
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        aoFechar()
      }
    }
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [aoFechar])

  const alternar = (i: number) =>
    setMarcados((atual) => {
      const novo = new Set(atual)
      if (novo.has(i)) novo.delete(i)
      else novo.add(i)
      return novo
    })

  const importar = async () => {
    const escolhidos = itens.filter((_, i) => marcados.has(i))
    if (escolhidos.length === 0) return
    setOcupado(true)
    try {
      await window.tucoteca.chamar('jogos.importar_selecionados', { itens: escolhidos })
      aoAvisar(`${escolhidos.length} jogo(s) importado(s).`)
      aoImportou()
      aoFechar()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    } finally {
      setOcupado(false)
    }
  }

  return (
    <div class="detalhe-fundo" onMouseDown={(e) => e.target === e.currentTarget && aoFechar()}>
      <div class="detalhe painel-paridade" role="dialog" aria-modal="true" aria-label="Importar jogos soltos" ref={caixa}>
        <h2>Importar {itens.length} item(ns)</h2>
        {avisos.map((a) => (
          <p key={a} class="sub">
            {a}
          </p>
        ))}
        <ul class="lista-simples">
          {itens.map((item, i) => (
            <li key={i}>
              <label class="marcar">
                <input type="checkbox" checked={marcados.has(i)} onChange={() => alternar(i)} />
                <span>
                  <strong>{String(item.titulo ?? 'Sem título')}</strong>
                  <span class="sub"> {detalheItem(item)}</span>
                </span>
              </label>
            </li>
          ))}
        </ul>
        <div class="detalhe-linha">
          <button type="button" class="acao primaria" disabled={ocupado || marcados.size === 0} onClick={() => void importar()}>
            Importar {marcados.size}
          </button>
          <button type="button" class="acao" onClick={aoFechar}>
            Cancelar
          </button>
        </div>
      </div>
    </div>
  )
}
