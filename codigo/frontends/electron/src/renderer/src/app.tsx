import { useEffect, useState } from 'preact/hooks'
import type { ModuloDTO } from '../../shared/protocolo'
import { combinacao, decidirAtalho } from './atalhos'
import { AvisoPonte } from './componentes/AvisoPonte'
import { Atividade } from './componentes/Atividade'
import { BarraLateral } from './componentes/BarraLateral'
import { Cabecalho } from './componentes/Cabecalho'
import { ConfirmacaoHost } from './componentes/Confirmacao'
import { Roteador } from './componentes/Roteador'
import { Paleta } from './componentes/Paleta'
import { PlayerRodape } from './componentes/PlayerRodape'
import { LeitorControle, type EstadoPad } from './controle'
import { aplicarAparencia, normalizarAparencia } from './estado/aparencia'
import { reduzirConexao, type EstadoConexao } from './estado/conexao'
import { atualizar, erroCarga, recarregar, snapshot } from './estado/dados'
import { avisosDoResumo, dispensarAviso, juntarAvisos, textoDeFalha, type Aviso } from './estado/notificacoes'
import { paletaInicial, reduzirPaleta, type ItemBusca } from './estado/paleta'
import { player } from './estado/player'
import { avancar, chaveLegada, escutarHash, historico, ir, NOMES_ABAS, podeVoltar, rota, voltar } from './estado/rota'
import {
  aplicarEventoTrabalho,
  jogoEmAndamento,
  listaTrabalhos,
  type EventoTrabalho,
  type Trabalho,
} from './estado/trabalhos'

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
  const [paleta, setPaleta] = useState(paletaInicial)
  const [atalhos, setAtalhos] = useState<Record<string, string>>({})
  const [avisos, setAvisos] = useState<Aviso[]>([])
  const [perfil, setPerfil] = useState('Tuco')
  const [conexao, setConexao] = useState<EstadoConexao>('ok')
  const [revisao, setRevisao] = useState(0)
  const [lixeira, setLixeira] = useState<LixeiraEstado | null>(null)

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
        setAvisos(avisosDoResumo(snapshot.value?.sistema ?? {}))
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
  }, [])

  useEffect(() => {
    const aoTeclar = (evento: KeyboardEvent) => {
      const comb = combinacao(evento)
      if (!paleta.aberta && (comb === 'Alt+Left' || comb === 'Alt+Right')) {
        evento.preventDefault()
        if (comb === 'Alt+Left') voltar()
        else avancar()
        return
      }
      const decisao = decidirAtalho(paleta.aberta, comb, atalhos, chaveLegada(rota.value))
      if (decisao === null) return
      evento.preventDefault()
      if (decisao.tipo === 'paleta') {
        setPaleta((atual) => reduzirPaleta(atual, { tipo: 'abrir' }))
      } else if (decisao.tipo === 'fechar') {
        setPaleta((atual) => reduzirPaleta(atual, { tipo: 'fechar' }))
      } else if (decisao.tipo === 'focar-busca') {
        setFocoBusca((atual) => atual + 1)
      } else {
        ir(decisao.chave)
      }
    }
    // botões laterais do mouse (voltar/avançar), como num navegador
    const aoMouse = (evento: MouseEvent) => {
      if (evento.button === 3) voltar()
      else if (evento.button === 4) avancar()
    }
    window.addEventListener('keydown', aoTeclar)
    window.addEventListener('mouseup', aoMouse)
    return () => {
      window.removeEventListener('keydown', aoTeclar)
      window.removeEventListener('mouseup', aoMouse)
    }
  }, [paleta.aberta, atalhos])

  useEffect(() => {
    if (!paleta.aberta) return
    const termo = paleta.termo
    if (!termo.trim()) return
    let vivo = true
    const timer = setTimeout(() => {
      void (async () => {
        let itens: ItemBusca[] = []
        try {
          itens = await window.tucoteca.chamar<ItemBusca[]>('nucleo.buscar', { termo, limite: 12 })
        } catch {
          itens = []
        }
        if (vivo) setPaleta((atual) => reduzirPaleta(atual, { tipo: 'resultados', termo, itens }))
      })()
    }, 150)
    return () => {
      vivo = false
      clearTimeout(timer)
    }
  }, [paleta.aberta, paleta.termo])

  useEffect(() => {
    return window.tucoteca.assinar('aviso', (dados) => {
      const aviso = avisoDeEvento(dados)
      if (aviso !== null) setAvisos((atual) => juntarAvisos(atual, [aviso]))
    })
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
      if (texto !== '') {
        setAvisos((atual) =>
          juntarAvisos(atual, [
            { id: `trabalho-${evento.id}`, texto, tom: erro !== '' ? 'atencao' : 'info' },
          ]),
        )
      }
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
      setAvisos((atual) =>
        juntarAvisos(atual, [{ id: 'ponte-ok', texto: 'Núcleo reconectado.', tom: 'info' }]),
      )
    } catch (falha) {
      setConexao((atual) => reduzirConexao(atual, { tipo: 'caiu' }))
      setAvisos((atual) =>
        juntarAvisos(atual, [
          { id: 'ponte-erro', texto: `Não reconectei: ${String(falha)}`, tom: 'atencao' },
        ]),
      )
    }
  }

  useEffect(() => {
    const leitor = new LeitorControle()
    const neutro: EstadoPad = { cima: false, baixo: false, a: false, b: false }

    const lerPad = (): EstadoPad | null => {
      for (const pad of navigator.getGamepads()) {
        if (!pad || !pad.connected) continue
        const eixo = pad.axes[1] ?? 0
        return {
          cima: pad.buttons[12]?.pressed === true || eixo < -0.5,
          baixo: pad.buttons[13]?.pressed === true || eixo > 0.5,
          a: pad.buttons[0]?.pressed === true,
          b: pad.buttons[1]?.pressed === true,
        }
      }
      return null
    }
    const reiniciar = () => leitor.reiniciar(lerPad() ?? neutro)
    reiniciar()
    window.addEventListener('gamepadconnected', reiniciar)
    window.addEventListener('focus', reiniciar)

    const navegar = (delta: 1 | -1) => {
      if (modulos.length === 0) return
      const bruto = modulos.findIndex((modulo) => modulo.chave === rota.value.secao)
      const indice = bruto === -1 ? 0 : bruto
      const proximo = modulos[(indice + delta + modulos.length) % modulos.length]
      if (proximo !== undefined) ir(proximo.chave)
    }

    const relogio = window.setInterval(() => {
      if (!document.hasFocus()) return
      const estado = lerPad()
      if (estado === null) return
      const acao = leitor.avaliar(estado, performance.now())
      if (acao === 'cima') navegar(-1)
      else if (acao === 'baixo') navegar(1)
      else if (acao === 'ativar') setPaleta((atual) => reduzirPaleta(atual, { tipo: 'abrir' }))
      else if (acao === 'voltar') {
        if (podeVoltar(historico.value)) voltar()
        else ir('inicio')
      }
    }, 100)

    return () => {
      window.clearInterval(relogio)
      window.removeEventListener('gamepadconnected', reiniciar)
      window.removeEventListener('focus', reiniciar)
    }
  }, [modulos])

  const alternarPerfil = async () => {
    const outro = perfil === 'Tuco' ? 'Isa' : 'Tuco'
    try {
      const dados = await window.tucoteca.chamar<{ ativo?: string }>('preferencias.trocar_perfil', {
        nome: outro,
      })
      const ativo = typeof dados.ativo === 'string' ? dados.ativo : outro
      setPerfil(ativo)
      await recarregar()
      setAvisos((atual) =>
        juntarAvisos(atual, [
          { id: `perfil-${ativo}`, texto: `Perfil trocado para ${ativo}.`, tom: 'info' },
        ]),
      )
    } catch (falha) {
      setAvisos((atual) =>
        juntarAvisos(atual, [
          { id: 'perfil-erro', texto: `Não troquei de perfil: ${String(falha)}`, tom: 'atencao' },
        ]),
      )
    }
  }

  const jogar = async (id: number) => {
    try {
      await window.tucoteca.chamar('jogo.jogar', { id })
    } catch (falha) {
      setAvisos((atual) =>
        juntarAvisos(atual, [{ id: `jogar-${id}`, texto: textoDeFalha(falha), tom: 'atencao' }]),
      )
    }
  }

  /** Toast global das vistas/detalhe (id por texto evita duplicar o mesmo aviso). */
  const avisar = (texto: string, tom: 'info' | 'atencao' = 'info') => {
    setAvisos((atual) => juntarAvisos(atual, [{ id: texto, texto, tom }]))
  }

  const desfazer = async () => {
    try {
      await window.tucoteca.chamar('item.desfazer')
      setAvisos((atual) =>
        juntarAvisos(atual, [{ id: 'desfazer', texto: 'Exclusão desfeita.', tom: 'info' }]),
      )
      await atualizarTudo()
    } catch (falha) {
      setAvisos((atual) =>
        juntarAvisos(atual, [
          { id: 'desfazer-erro', texto: `Não desfiz: ${textoDeFalha(falha)}`, tom: 'atencao' },
        ]),
      )
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
      : atual.jogo !== null
        ? 'Jogos'
        : `${modulo?.nome ?? 'TucoTeca'}${atual.aba !== '' && (NOMES_ABAS[atual.aba] ?? '') !== '' ? ` · ${NOMES_ABAS[atual.aba]}` : ''}`
  const jogando = jogoEmAndamento(listaTrabalhos.value)
  const filaPlayer = player.value.fila
  return (
    <>
      <AvisoPonte estado={conexao} aoReconectar={reconectar} />
      <div class="app">
        <main class="shell">
          <BarraLateral modulos={modulos} ativa={atual.secao} jogos={colecao.jogos} jogoAberto={atual.jogo} />
          <div class="area">
            <Cabecalho
              titulo={titulo}
              avisos={avisos}
              aoDispensarAviso={(id) => setAvisos((lista) => dispensarAviso(lista, id))}
              aoBuscar={() => setPaleta((estado) => reduzirPaleta(estado, { tipo: 'abrir' }))}
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
                  aoDispensarAviso: (id: string) => setAvisos((lista) => dispensarAviso(lista, id)),
                  aoLimparAvisos: () => setAvisos([]),
                }}
              />
            </section>
          </div>
        </main>
        {filaPlayer.length > 0 && <PlayerRodape />}
        <Atividade aoAvisar={avisar} />
        <ConfirmacaoHost />
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
          aoDigitar={(termo) => setPaleta((atual) => reduzirPaleta(atual, { tipo: 'digitou', termo }))}
          aoMover={(delta) =>
            setPaleta((atual) => reduzirPaleta(atual, { tipo: delta === 1 ? 'baixo' : 'cima' }))
          }
          aoDestacar={(indice) =>
            setPaleta((atual) => reduzirPaleta(atual, { tipo: 'selecionar', indice }))
          }
          aoConfirmar={(indice) => {
            const item = paleta.itens[indice ?? paleta.selecionado]
            if (item === undefined) return
            if (item.tipo === 'jogo' && Number.isFinite(Number(item.id))) {
              ir(`#/jogo/${Number(item.id)}`)
            } else {
              const chave = DESTINO_DO_ITEM[item.tipo]
              if (chave !== undefined) ir(chave)
            }
            setPaleta((atual) => reduzirPaleta(atual, { tipo: 'fechar' }))
          }}
          aoFechar={() => setPaleta((atual) => reduzirPaleta(atual, { tipo: 'fechar' }))}
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

/** Evento `aviso` vindo da ponte (texto simples ou `{id, texto, tom}`). */
function avisoDeEvento(dados: unknown): Aviso | null {
  if (typeof dados === 'string') {
    const texto = dados.trim()
    return texto === '' ? null : { id: texto, texto, tom: 'info' }
  }
  if (dados !== null && typeof dados === 'object') {
    const objeto = dados as { id?: unknown; texto?: unknown; tom?: unknown }
    const texto = String(objeto.texto ?? '').trim()
    if (texto === '') return null
    return {
      id: String(objeto.id ?? texto),
      texto,
      tom: objeto.tom === 'atencao' ? 'atencao' : 'info',
    }
  }
  return null
}
