import { type ComponentChildren } from 'preact'

interface TabItem {
  chave: string
  rotulo: string
  conteudo?: ComponentChildren
}

interface Props {
  abas: TabItem[]
  ativa: string
  aoTrocar: (chave: string) => void
  vertical?: boolean
}

/** Tabs horizontal/vertical. */
export function Tabs({ abas, ativa, aoTrocar, vertical = false }: Props) {
  return (
    <div class={`tabs ${vertical ? 'tabs-vertical' : 'tabs-horizontal'}`}>
      <div class="tabs-lista" role="tablist">
        {abas.map((aba) => (
          <button
            key={aba.chave}
            type="button"
            role="tab"
            aria-selected={aba.chave === ativa}
            class={`tab ${aba.chave === ativa ? 'ativo' : ''}`}
            onClick={() => aoTrocar(aba.chave)}
          >
            {aba.rotulo}
          </button>
        ))}
      </div>
      <div class="tabs-conteudo" role="tabpanel">
        {abas.find((a) => a.chave === ativa)?.conteudo}
      </div>
    </div>
  )
}
