import type { ModuloDTO } from '../../../shared/protocolo'

interface Props {
  modulos: ModuloDTO[]
  ativa: string
  aoTrocar: (chave: string) => void
}

export function BarraLateral({ modulos, ativa, aoTrocar }: Props) {
  return (
    <aside class="barra-lateral">
      <div class="marca">TucoTeca</div>
      <nav>
        {modulos.map((modulo) => (
          <button
            key={modulo.chave}
            type="button"
            class={`item${modulo.chave === ativa ? ' ativo' : ''}`}
            title={modulo.descricao}
            onClick={() => aoTrocar(modulo.chave)}
          >
            <span class="icone" aria-hidden="true">
              {modulo.nome.trim().charAt(0)}
            </span>
            <span class="rotulo">{modulo.nome}</span>
          </button>
        ))}
      </nav>
    </aside>
  )
}
