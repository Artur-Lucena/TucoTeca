import { useEffect, useState } from 'preact/hooks'
import { confirmar } from '../../componentes/ui/Confirmacao'
import { ColecoesDoJogo } from '../../componentes/jogo/ColecoesDoJogo'
import { ConquistasJogo } from '../../componentes/jogo/ConquistasJogo'
import { EditarJogo } from '../../componentes/jogo/EditarJogo'
import { HeroJogo } from '../../componentes/jogo/HeroJogo'
import { SobreJogo } from '../../componentes/jogo/SobreJogo'
import { PainelEmulacao } from '../../componentes/jogo/PainelEmulacao'
import { PainelFerramentasJogo } from '../../componentes/jogo/PainelFerramentasJogo'
import { PainelManutencaoJogo } from '../../componentes/jogo/PainelManutencaoJogo'
import { EmptyState } from '../../componentes/ui'
import { textoDeFalha } from '../../estado/notificacoes'
import { abasDoJogo, normalizarPagina, type PaginaJogo as Pagina } from '../../estado/paginaJogo'
import { ir, NOMES_ABAS } from '../../estado/rota'
import { jogoEmAndamento, listaTrabalhos } from '../../estado/trabalhos'

interface Props {
  id: number
  aba: string
  /** Muda quando a coleção muda (ações em outras telas, fim de tarefas). */
  revisao: number
  aoMudou: () => void
  aoAvisar: (texto: string, tom?: 'info' | 'atencao') => void
}

/** Página do jogo à la Hydra: hero, abas e tudo do jogo num endereço (`#/jogo/12/aba`). */
export function PaginaJogo({ id, aba, revisao, aoMudou, aoAvisar }: Props) {
  const [pagina, setPagina] = useState<Pagina | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [trabalho, setTrabalho] = useState<number | null>(null)
  const [versao, setVersao] = useState(0)

  useEffect(() => {
    let vivo = true
    window.tucoteca
      .chamar('jogo.pagina', { id })
      .then((r) => {
        if (!vivo) return
        setPagina(normalizarPagina(r))
        setErro(null)
      })
      .catch((falha) => {
        if (vivo) setErro(textoDeFalha(falha))
      })
    return () => {
      vivo = false
    }
  }, [id, revisao, versao])

  // fim da busca nos provedores: recarrega a página (o aviso já sai pelo App)
  useEffect(() => {
    if (trabalho === null) return
    return window.tucoteca.assinar('trabalho', (dados) => {
      const evento = dados as { id?: number; motivo?: string } | null
      if (evento?.id === trabalho && evento.motivo === 'fim') {
        setTrabalho(null)
        setVersao((v) => v + 1)
      }
    })
  }, [trabalho])

  const recarregar = () => {
    setVersao((v) => v + 1)
    aoMudou()
  }

  const buscarDados = async (provedores?: string[]) => {
    try {
      const r = await window.tucoteca.chamar<{ trabalho?: { id?: number } }>('jogo.enriquecer', provedores ? { id, provedores } : { id })
      const ident = Number(r?.trabalho?.id)
      if (Number.isInteger(ident)) setTrabalho(ident)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const jogar = async () => {
    try {
      await window.tucoteca.chamar('jogo.jogar', { id })
      aoAvisar(`Iniciando ${String(pagina?.jogo.titulo ?? 'o jogo')}…`)
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const favoritar = async () => {
    try {
      const r = await window.tucoteca.chamar<{ favorito?: boolean }>('jogo.favoritar', { id })
      aoAvisar(r?.favorito === true ? 'Marcado como favorito.' : 'Favorito removido.')
      recarregar()
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  const remover = async () => {
    const titulo = String(pagina?.jogo.titulo ?? 'o jogo')
    if (!(await confirmar({ titulo: 'Remover jogo', texto: `Remover "${titulo}" da biblioteca? Dá para desfazer pela barra de status.`, confirmar: 'Remover', perigo: true }))) return
    try {
      await window.tucoteca.chamar('item.excluir', { categoria: 'jogos', id })
      aoAvisar(`${titulo} foi removido. Use Desfazer na barra de status.`)
      aoMudou()
      ir('#/jogos')
    } catch (falha) {
      aoAvisar(textoDeFalha(falha), 'atencao')
    }
  }

  if (erro !== null) {
    return (
      <EmptyState icone="?" titulo="Não abri este jogo." descricao={erro} acao={{ rotulo: 'Voltar para a biblioteca', onClick: () => ir('#/jogos') }} />
    )
  }
  if (pagina === null) return <p class="sub">Abrindo o jogo…</p>

  const jogando = jogoEmAndamento(listaTrabalhos.value)
  const bloqueado = jogando !== null
  const abas = abasDoJogo(pagina.jogo)
  const atual = abas.includes(aba) ? aba : 'visao'
  const buscando = trabalho !== null
  return (
    <article class="pagina-jogo">
      <HeroJogo
        pagina={pagina}
        jogando={jogando?.rotulo ?? null}
        buscando={buscando}
        aoJogar={() => void jogar()}
        aoFavoritar={() => void favoritar()}
        aoBuscarDados={() => void buscarDados()}
        aoRemover={() => void remover()}
        extras={<ColecoesDoJogo id={id} aoMudou={aoMudou} aoAvisar={aoAvisar} />}
      />
      <nav class="abas" aria-label="Abas do jogo">
        {abas.map((a) => (
          <button
            key={a}
            type="button"
            class={`aba${a === atual ? ' ativa' : ''}`}
            aria-current={a === atual ? 'page' : undefined}
            onClick={() => ir(a === 'visao' ? `#/jogo/${id}` : `#/jogo/${id}/${a}`)}
          >
            {NOMES_ABAS[a] ?? a}
          </button>
        ))}
      </nav>
      {atual === 'visao' && <SobreJogo pagina={pagina} buscando={buscando} aoBuscarDados={() => void buscarDados()} />}
      {atual === 'conquistas' && (
        <ConquistasJogo id={id} pagina={pagina} buscando={buscando} aoAtualizarRetro={() => void buscarDados(['retro'])} aoAvisar={aoAvisar} />
      )}
      {atual === 'emulacao' && <PainelEmulacao id={id} bloqueado={bloqueado} aoAvisar={aoAvisar} />}
      {atual === 'saves' && <PainelFerramentasJogo id={id} bloqueado={bloqueado} aoAvisar={aoAvisar} />}
      {atual === 'manutencao' && <PainelManutencaoJogo id={id} bloqueado={bloqueado} aoMudou={recarregar} aoAvisar={aoAvisar} />}
      {atual === 'editar' && <EditarJogo key={versao} id={id} pagina={pagina} aoMudou={recarregar} aoAvisar={aoAvisar} />}
    </article>
  )
}
