import type { ModuloDTO } from '../../../shared/protocolo'

export function Placeholder({ modulo }: { modulo?: ModuloDTO }) {
  return (
    <section class="painel">
      <h1>{modulo?.nome ?? 'Seção'}</h1>
      <p>{modulo?.descricao ?? ''}</p>
      <p class="aviso">
        Esta tela chega na próxima fatia (F2) — o módulo já está registrado e navegável.
      </p>
    </section>
  )
}
