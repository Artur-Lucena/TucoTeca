import { useEffect, useRef, useState } from 'preact/hooks'
import { detalheItem, type ItemPrevia } from '../../estado/importacao'
import { type AoAvisar, textoDeFalha } from '../../estado/notificacoes'
import { Modal } from '../ui'

interface Props {
  itens: ItemPrevia[]
  avisos: string[]
  aoFechar: () => void
  aoImportou: () => void
  aoAvisar: AoAvisar
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
    caixa.current?.querySelector<HTMLElement>('input, button')?.focus()
  }, [])

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
    <Modal aberto aoFechar={aoFechar} titulo={`Importar ${itens.length} item(ns)`} largura="560px">
      <div class="painel-paridade" ref={caixa}>
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
    </Modal>
  )
}
