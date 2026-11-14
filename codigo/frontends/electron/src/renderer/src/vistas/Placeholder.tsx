import type { ModuloDTO } from '../../../shared/protocolo'

export function Placeholder({ modulo }: { modulo?: ModuloDTO }) {
  return (
    <section class="painel">
      <h1>{modulo?.nome ?? 'Seção'}</h1>
      <p>{modulo?.descricao ?? ''}</p>
      <p class="aviso">
        Esta seção ainda não tem tela no app.
      </p>
    </section>
  )
}
