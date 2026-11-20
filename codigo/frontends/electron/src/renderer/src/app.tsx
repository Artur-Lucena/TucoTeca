import { useEffect, useState } from 'preact/hooks'
import type { ModuloDTO } from '../../shared/protocolo'
import { AvisoPonte } from './componentes/casca/AvisoPonte'
import { Atividade } from './componentes/casca/Atividade'
import { BarraLateral } from './componentes/casca/BarraLateral'
import { Cabecalho } from './componentes/casca/Cabecalho'
import { ConfirmacaoHost } from './componentes/ui/Confirmacao'
import { Roteador } from './componentes/casca/Roteador'
import { Paleta } from './componentes/casca/Paleta'
import { PlayerRodape } from './componentes/musica/PlayerRodape'
import { PlayerVideo } from './componentes/midia/PlayerVideo'
import { reproduzindo } from './estado/midia'
import { aplicarAparencia, normalizarAparencia } from './estado/aparencia'
import { reduzirConexao, type EstadoConexao } from './estado/conexao'
import { normalizarColecoes } from './estado/colecoes'
import { atualizar, erroCarga, recarregar, snapshot } from './estado/dados'
import { avisosDoResumo, juntarAvisos, textoDeFalha } from './estado/notificacoes'
import { player } from './estado/player'
import { escutarHash, ir, NOMES_ABAS, rota } from './estado/rota'
import { aplicarEventoTrabalho, jogoEmAndamento, listaTrabalhos, type EventoTrabalho, type Trabalho } from './estado/trabalhos'
import { useAvisos } from './estado/useAvisos'
import { useAtalhos } from './navegacao/useAtalhos'
import { useControle } from './navegacao/useControle'
import { usePaleta } from './navegacao/usePaleta'

const DESTINO_DO_ITEM: Record<string, string> = {
  jogo: 'jogos',
  musica: 'musicas',
  desejo: 'desejos',
  download: 'downloads',
}

export function App() {
  const [modulos, setModulos] = useState<ModuloDTO[]>([])
  const [erro, setErro] = useState<string | null>(null)
  const [focoBusca, setFocoBusca] = useState(0)
  const [paleta, despacharPaleta] = usePaleta()
  const [atalhos, setAtalhos] = useState<Record<string, string>>({})
  const { avisos, setAvisos, juntar, avisar, dispensar, limpar } = useAvisos()
  const [perfil, setPerfil] = useState('Tuco')
  const [conexao, setConexao] = useState<EstadoConexao>('ok')
  const [revisao, setRevisao] = useState(0)
  const [lixeira, setLixeira] = useState<LixeiraEstado | null>(null)

  const abrirPaleta = () => despacharPaleta({ tipo: 'abrir' })
  useAtalhos(paleta.aberta, atalhos, {
    abrirPaleta,
    fecharPaleta: () => despacharPaleta({ tipo: 'fechar' }),
    focarBusca: () => setFocoBusca((atual) => atual + 1),
  })
  useControle(modulos, abrirPaleta)

  /** Recarrega o que mudou no núcleo, o desfazer pendente e avisa as vistas (gaveta). */
  const atualizarTudo = async () => {
    await atualizar()
    setRevisao((atual) => atual + 1)
    try {
      setLixeira(normalizarLixeira(await window.tucoteca.chamar('lixeira.estado')))
    } catch {
      setLixeira(null)
    }
  }

  useEffect(() => escutarHash(), [])

  useEffect(() => {
    void window.tucoteca
      .chamar('aparencia.ler')
      .then((a) => aplicarAparencia(normalizarAparencia(a)))
      .catch(() => undefined) // sem preferências legíveis fica o padrão (escuro/confortável)
  }, [])

  useEffect(() => {
    void (async () => {
      try {
        const lista = await window.tucoteca.chamar<ModuloDTO[]>('modulos.listar')
        setModulos(lista)
        await recarregar()
        if (erroCarga.value !== null) throw new Error(erroCarga.value)
        juntar(avisosDoResumo(snapshot.value?.sistema ?? {}))
        try {
          const prefs = await window.tucoteca.chamar<{
            ativo?: string
            atalhos?: Record<string, string>
          }>('preferencias.ler')
          setAtalhos(prefs.atalhos ?? {})
          if (typeof prefs.ativo === 'string') setPerfil(prefs.ativo)
        } catch {
          // sem atalhos/perfil pessoais o shell segue funcionando; chegam na próxima carga
        }
        try {
          listaTrabalhos.value = await window.tucoteca.chamar<Trabalho[]>('trabalhos.listar')
        } catch {
          // sem trabalhos pendentes o rodapé nem aparece
        }
        try {
          setLixeira(normalizarLixeira(await window.tucoteca.chamar('lixeira.estado')))
        } catch {
          // sem recibo de exclusão pendente
        }
        window.tucoteca.pronto({ jogos: snapshot.value?.jogos?.length ?? 0 })
      } catch (falha) {
        setErro(String(falha))
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- roda uma vez, na abertura
  }, [])

  useEffect(() => {
    return window.tucoteca.assinar('trabalho', (dados) => {
      const evento = dados as EventoTrabalho | null
      if (evento === null || typeof evento.id !== 'number') return
      aplicarEventoTrabalho(evento)
      if (evento.motivo !== 'fim') return
      const aviso = typeof evento.detalhe?.aviso === 'string' ? evento.detalhe.aviso : ''
      const erro = evento.estado === 'erro' ? String(evento.erro ?? 'A tarefa falhou.') : ''
      const texto = aviso !== '' ? aviso : erro
      // id com o início: os ids de trabalho recomeçam a cada abertura e o histórico fica
      const id = `trabalho-${evento.id}-${evento.iniciado_em ?? ''}`
      if (texto !== '') juntar([{ id, texto, tom: erro !== '' ? 'atencao' : 'info' }])
      void atualizarTudo()
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps -- atualizarTudo só usa setters
  }, [])

  useEffect(() => {
    return window.tucoteca.assinar('ponte-estado', (dados) => {
      const estado = (dados as { estado?: unknown } | null)?.estado
      if (estado === 'caiu' || estado === 'reabrindo' || estado === 'ok') {
        setConexao((atual) => reduzirConexao(atual, { tipo: estado }))
      }
    })
  }, [])

  const reconectar = async () => {
    setConexao((atual) => reduzirConexao(atual, { tipo: 'reabrindo' }))
    try {
      await window.tucoteca.reabrir()
      await recarregar()
      if (erroCarga.value !== null) throw new Error(erroCarga.value)
      setAvisos((atual) => juntarAvisos(avisosDoResumo(snapshot.value?.sistema ?? {}), atual))
      juntar([{ id: 'ponte-ok', texto: 'Núcleo reconectado.', tom: 'info' }])
    } catch (falha) {
      setConexao((atual) => reduzirConexao(atual, { tipo: 'caiu' }))
      juntar([{ id: 'ponte-erro', texto: `Não reconectei: ${String(falha)}`, tom: 'atencao' }])
    }
  }

  const alternarPerfil = async () => {
    const outro = perfil === 'Tuco' ? 'Isa' : 'Tuco'
    try {
      const dados = await window.tucoteca.chamar<{ ativo?: string }>('preferencias.trocar_perfil', {
        nome: outro,
      })
      const ativo = typeof dados.ativo === 'string' ? dados.ativo : outro
      setPerfil(ativo)
      await recarregar()
      juntar([{ id: `perfil-${ativo}`, texto: `Perfil trocado para ${ativo}.`, tom: 'info' }])
    } catch (falha) {
      juntar([{ id: 'perfil-erro', texto: `Não troquei de perfil: ${String(falha)}`, tom: 'atencao' }])
    }
  }

  const jogar = async (id: number) => {
    try {
      await window.tucoteca.chamar('jogo.jogar', { id })
    } catch (falha) {
      juntar([{ id: `jogar-${id}`, texto: textoDeFalha(falha), tom: 'atencao' }])
    }
  }

  const desfazer = async () => {
    try {
      await window.tucoteca.chamar('item.desfazer')
      juntar([{ id: 'desfazer', texto: 'Exclusão desfeita.', tom: 'info' }])
      await atualizarTudo()
    } catch (falha) {
      juntar([{ id: 'desfazer-erro', texto: `Não desfiz: ${textoDeFalha(falha)}`, tom: 'atencao' }])
    }
  }
  if (erro) {
    return (
      <section class="painel erro">
        <h1>Não consegui falar com o núcleo</h1>
        <p>{erro}</p>
      </section>
    )
  }

  if (snapshot.value === null) {
    return (
      <section class="painel">
        <h1>TucoTeca</h1>
        <p>Abrindo a coleção…</p>
      </section>
    )
  }

  const colecao = snapshot.value
  const atual = rota.value
  const modulo = modulos.find((m) => m.chave === atual.secao)
  const titulo =
    atual.secao === 'notificacoes'
      ? 'Notificações'
      : atual.jogo !== null || atual.titulo !== undefined
        ? (modulo?.nome ?? 'TucoTeca')
        : `${modulo?.nome ?? 'TucoTeca'}${atual.aba !== '' && (NOMES_ABAS[atual.aba] ?? '') !== '' ? ` · ${NOMES_ABAS[atual.aba]}` : ''}`
  const jogando = jogoEmAndamento(listaTrabalhos.value)
  const filaPlayer = player.value.fila
  return (
    <>
      <AvisoPonte estado={conexao} aoReconectar={reconectar} />
      <div class="app">
        <main class="shell">
          <BarraLateral modulos={modulos} ativa={atual.secao} jogos={colecao.jogos} colecoes={normalizarColecoes(colecao.colecoes)} jogoAberto={atual.jogo} />
          <div class="area">
            <Cabecalho
              titulo={titulo}
              avisos={avisos}
              aoDispensarAviso={dispensar}
              aoLimparAvisos={limpar}
              aoBuscar={abrirPaleta}
              perfil={perfil}
              aoTrocarPerfil={alternarPerfil}
            />
            <section class="conteudo">
              <Roteador
                rota={atual}
                ctx={{
                  snapshot: colecao ?? {},
                  focoBusca,
                  revisao,
                  perfil,
                  avisos,
                  aoAvisar: avisar,
                  aoMudou: () => void atualizarTudo(),
                  aoJogar: (id: number) => void jogar(id),
                  aoDispensarAviso: dispensar,
                  aoLimparAvisos: limpar,
                }}
              />
            </section>
          </div>
        </main>
        {filaPlayer.length > 0 && <PlayerRodape />}
        <Atividade aoAvisar={avisar} />
        <ConfirmacaoHost />
        {reproduzindo.value !== null && (
          <PlayerVideo
            key={reproduzindo.value}
            fonte={{ tipo: 'midia', arquivo: reproduzindo.value }}
            aoFechar={() => (reproduzindo.value = null)}
            aoMudou={() => void atualizarTudo()}
            aoAvisar={avisar}
          />
        )}
        {(jogando !== null || lixeira?.disponivel === true) && (
          <footer class="status">
            {jogando !== null && (
              <span class="status-jogando">● {jogando.rotulo}… aguarde a sessão fechar</span>
            )}
            {lixeira?.disponivel === true && (
              <span class="status-desfazer">
                {lixeira.titulo !== '' ? `${lixeira.titulo} foi removido.` : 'Item removido.'}
                <button type="button" onClick={() => void desfazer()}>
                  Desfazer
                </button>
              </span>
            )}
          </footer>
        )}
      </div>

      {paleta.aberta && (
        <Paleta
          estado={paleta}
          aoDigitar={(termo) => despacharPaleta({ tipo: 'digitou', termo })}
          aoMover={(delta) => despacharPaleta({ tipo: delta === 1 ? 'baixo' : 'cima' })}
          aoDestacar={(indice) => despacharPaleta({ tipo: 'selecionar', indice })}
          aoConfirmar={(indice) => {
            const item = paleta.itens[indice ?? paleta.selecionado]
            if (item === undefined) return
            if (item.tipo === 'jogo' && Number.isFinite(Number(item.id))) {
              ir(`#/jogo/${Number(item.id)}`)
            } else {
              const chave = DESTINO_DO_ITEM[item.tipo]
              if (chave !== undefined) ir(chave)
            }
            despacharPaleta({ tipo: 'fechar' })
          }}
          aoFechar={() => despacharPaleta({ tipo: 'fechar' })}
        />
      )}
    </>
  )
}

interface LixeiraEstado {
  disponivel: boolean
  titulo: string
  tipo: string
}

/** Recibo de exclusão do núcleo; `null` quando não há nada para desfazer. */
function normalizarLixeira(estado: unknown): LixeiraEstado | null {
  if (estado === null || typeof estado !== 'object') return null
  const objeto = estado as { disponivel?: unknown; titulo?: unknown; tipo?: unknown }
  if (objeto.disponivel !== true) return null
  return { disponivel: true, titulo: String(objeto.titulo ?? ''), tipo: String(objeto.tipo ?? '') }
}