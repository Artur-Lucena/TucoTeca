import type { ModuloDTO } from '../../../shared/protocolo'
import type { Aviso } from '../estado/notificacoes'
import { Avisos } from './Avisos'

interface Props {
  modulos: ModuloDTO[]
  ativa: string
  aoTrocar: (chave: string) => void
  avisos: Aviso[]
  aoDispensarAviso: (id: string) => void
  perfil: string
  aoTrocarPerfil: () => void
}

export function BarraLateral({
  modulos,
  ativa,
  aoTrocar,
  avisos,
  aoDispensarAviso,
  perfil,
  aoTrocarPerfil,
}: Props) {
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
      <div class="rodape-lateral">
        <Avisos avisos={avisos} aoDispensar={aoDispensarAviso} />
        <button type="button" class="perfil" onClick={aoTrocarPerfil} title="Trocar de perfil">
          <span class="icone" aria-hidden="true">
            {perfil.trim().charAt(0)}
          </span>
          <span>{perfil}</span>
        </button>
      </div>
    </aside>
  )
}
