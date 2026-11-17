import type { Snapshot } from '../../estado/derivacoes'
import type { Aviso } from '../../estado/notificacoes'
import { ir, type Rota } from '../../estado/rota'
import { Inicio } from '../../vistas/Inicio'
import { Abas } from './Abas'
import { Lazy } from './Lazy'
import { EmptyState } from '../ui'
import { type AoAvisar } from '../../estado/notificacoes'

interface ContextoVistas {
  snapshot: Snapshot
  focoBusca: number
  /** Contador de mudanças da coleção (a página do jogo relê quando muda). */
  revisao: number
  perfil: string
  avisos: Aviso[]
  aoAvisar: AoAvisar
  aoMudou: () => void
  aoJogar: (id: number) => void
  aoDispensarAviso: (id: string) => void
  aoLimparAvisos: () => void
}

/** Escolhe a vista da rota. Cada `Lazy` tem `key` própria: trocar de tela remonta. */
export function Roteador({ rota, ctx }: { rota: Rota; ctx: ContextoVistas }) {
  const { focoBusca, perfil, aoAvisar, aoMudou } = ctx
  const comuns = { aoAvisar, aoMudou }
  if (rota.titulo !== undefined) {
    return (
      <Lazy key={`titulo-${rota.titulo}`} fabrica={() => import('../../vistas/midia/PaginaTitulo').then((m) => m.PaginaTitulo)} props={{ imdb: rota.titulo, aoAvisar }} />
    )
  }
  if (rota.loja !== undefined) {
    return (
      <Lazy key={`loja-${rota.loja}`} fabrica={() => import('../../vistas/jogos/PaginaLoja').then((m) => m.PaginaLoja)} props={{ appid: rota.loja, ...comuns }} />
    )
  }
  if (rota.jogo !== null) {
    return (
      <Lazy
        key={`jogo-${rota.jogo}`}
        fabrica={() => import('../../vistas/jogos/PaginaJogo').then((m) => m.PaginaJogo)}
        props={{ id: rota.jogo, aba: rota.aba, revisao: ctx.revisao, ...comuns }}
      />
    )
  }
  switch (rota.secao) {
    case 'inicio':
      return <Inicio snapshot={ctx.snapshot} aoAvisar={aoAvisar} aoMudou={aoMudou} />
    case 'jogos':
      return (
        <>
          <Abas secao="jogos" ativa={rota.aba} />
          {rota.aba === 'catalogo' ? (
            <Lazy key="Catalogo" fabrica={() => import('../../vistas/jogos/Catalogo').then((m) => m.Catalogo)} props={{ aoAvisar }} />
          ) : rota.aba === 'colecoes' ? (
            <Lazy key="Colecoes" fabrica={() => import('../../vistas/jogos/Colecoes').then((m) => m.Colecoes)} props={comuns} />
          ) : rota.aba === 'desejos' ? (
            <Lazy key="Desejos" fabrica={() => import('../../vistas/jogos/Desejos').then((m) => m.Desejos)} props={{ focoBusca, perfil, ...comuns }} />
          ) : (
            <Lazy
              key="Jogos"
              fabrica={() => import('../../vistas/jogos/Jogos').then((m) => m.Jogos)}
              props={{ focoBusca, perfil, aoAbrirJogo: (id: number) => ir(`#/jogo/${id}`), aoJogarJogo: ctx.aoJogar, ...comuns }}
            />
          )}
        </>
      )
    case 'midia':
      return (
        <>
          <Abas secao="midia" ativa={rota.aba} />
          {rota.aba === 'youtube' ? (
            <Lazy key="YouTube" fabrica={() => import('../../vistas/midia/YouTube').then((m) => m.YouTube)} props={comuns} />
          ) : rota.aba === 'videos' ? (
            <Lazy key="Videos" fabrica={() => import('../../vistas/midia/Videos').then((m) => m.Videos)} props={comuns} />
          ) : rota.aba === 'continuar' ? (
            <Lazy key="Continuar" fabrica={() => import('../../vistas/midia/AbasMidia').then((m) => m.Continuar)} props={{ aoAvisar }} />
          ) : rota.aba === 'descobrir' ? (
            <Lazy key="Descobrir" fabrica={() => import('../../vistas/midia/AbasMidia').then((m) => m.Descobrir)} props={{ aoAvisar }} />
          ) : rota.aba === 'lista' ? (
            <Lazy key="MinhaLista" fabrica={() => import('../../vistas/midia/AbasMidia').then((m) => m.MinhaLista)} props={{ aoAvisar }} />
          ) : rota.aba === 'calendario' ? (
            <Lazy key="Calendario" fabrica={() => import('../../vistas/midia/AbasMidia').then((m) => m.Calendario)} props={{ aoAvisar }} />
          ) : (
            <Lazy key="BibliotecaMidia" fabrica={() => import('../../vistas/midia/BibliotecaMidia').then((m) => m.BibliotecaMidia)} props={{ aoAvisar }} />
          )}
        </>
      )
    case 'musicas':
      return <Lazy key="Musicas" fabrica={() => import('../../vistas/Musicas').then((m) => m.Musicas)} props={{ focoBusca, perfil, ...comuns }} />
    case 'downloads':
      return <Lazy key="Downloads" fabrica={() => import('../../vistas/Downloads').then((m) => m.Downloads)} props={comuns} />
    case 'configuracoes':
      return (
        <>
          <Abas secao="configuracoes" ativa={rota.aba} />
          {rota.aba === 'integracoes' ? (
            <Lazy key="Integracoes" fabrica={() => import('../../vistas/configuracoes/Integracoes').then((m) => m.Integracoes)} props={{ aoAvisar, aoNavegar: ir }} />
          ) : (
            <Lazy key="Configuracoes" fabrica={() => import('../../vistas/configuracoes/Configuracoes').then((m) => m.Configuracoes)} props={comuns} />
          )}
        </>
      )
    case 'notificacoes':
      return (
        <Lazy
          key="Notificacoes"
          fabrica={() => import('../../vistas/Notificacoes').then((m) => m.Notificacoes)}
          props={{ avisos: ctx.avisos, aoDispensar: ctx.aoDispensarAviso, aoLimpar: ctx.aoLimparAvisos }}
        />
      )
    default:
      return <EmptyState icone="?" titulo="Tela não encontrada." descricao="Escolha uma seção na barra lateral." />
  }
}
