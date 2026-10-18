import { useEffect, useState } from 'preact/hooks'
import type { ModuloDTO } from '../../shared/protocolo'
import { combinacao, decidirAtalho } from './atalhos'
import { AvisoPonte } from './componentes/AvisoPonte'
import { BarraLateral } from './componentes/BarraLateral'
import { Paleta } from './componentes/Paleta'
import { LeitorControle, type EstadoPad } from './controle'
import { reduzirConexao, type EstadoConexao } from './estado/conexao'
import { erroCarga, recarregar, snapshot } from './estado/dados'
import { avisosDoResumo, dispensarAviso, juntarAvisos, type Aviso } from './estado/notificacoes'
import { paletaInicial, reduzirPaleta, type ItemBusca } from './estado/paleta'
import { Inicio } from './vistas/Inicio'
import { Jogos } from './vistas/Jogos'
import { Placeholder } from './vistas/Placeholder'

const DESTINO_DO_ITEM: Record<string, string> = {
  jogo: 'jogos',
  musica: 'musicas',
  desejo: 'desejos',
  download: 'downloads',
}

export function App() {
  const [modulos, setModulos] = useState<ModuloDTO[]>([])
  const [erro, setErro] = useState<string | null>(null)
  const [secao, setSecao] = useState('inicio')
  const [focoBusca, setFocoBusca] = useState(0)
  const [paleta, setPaleta] = useState(paletaInicial)
  const [atalhos, setAtalhos] = useState<Record<string, string>>({})
  const [avisos, setAvisos] = useState<Aviso[]>([])
  const [perfil, setPerfil] = useState('Tuco')
  const [conexao, setConexao] = useState<EstadoConexao>('ok')

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
        window.tucoteca.pronto({ jogos: snapshot.value?.jogos?.length ?? 0 })
      } catch (falha) {
        setErro(String(falha))
      }
    })()
  }, [])

  useEffect(() => {
    const aoTeclar = (evento: KeyboardEvent) => {
      const decisao = decidirAtalho(paleta.aberta, combinacao(evento), atalhos, secao)
      if (decisao === null) return
      evento.preventDefault()
      if (decisao.tipo === 'paleta') {
        setPaleta((atual) => reduzirPaleta(atual, { tipo: 'abrir' }))
      } else if (decisao.tipo === 'fechar') {
        setPaleta((atual) => reduzirPaleta(atual, { tipo: 'fechar' }))
      } else if (decisao.tipo === 'focar-busca') {
        setFocoBusca((atual) => atual + 1)
      } else {
        setSecao(decisao.chave)
      }
    }
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [paleta.aberta, atalhos, secao])

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
      setSecao((atual) => {
        if (modulos.length === 0) return atual
        const bruto = modulos.findIndex((modulo) => modulo.chave === atual)
        const indice = bruto === -1 ? 0 : bruto
        const proximo = (indice + delta + modulos.length) % modulos.length
        return modulos[proximo]?.chave ?? atual
      })
    }

    const relogio = window.setInterval(() => {
      if (!document.hasFocus()) return
      const estado = lerPad()
      if (estado === null) return
      const acao = leitor.avaliar(estado, performance.now())
      if (acao === 'cima') navegar(-1)
      else if (acao === 'baixo') navegar(1)
      else if (acao === 'ativar') setPaleta((atual) => reduzirPaleta(atual, { tipo: 'abrir' }))
      else if (acao === 'voltar') setSecao('inicio')
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
  const ativo = modulos.find((modulo) => modulo.chave === secao) ?? modulos[0]
  return (
    <>
      <AvisoPonte estado={conexao} aoReconectar={reconectar} />
      <main class="shell">
        <BarraLateral
          modulos={modulos}
          ativa={ativo?.chave ?? ''}
          aoTrocar={setSecao}
          avisos={avisos}
          aoDispensarAviso={(id) => setAvisos((atual) => dispensarAviso(atual, id))}
          perfil={perfil}
          aoTrocarPerfil={alternarPerfil}
        />
        <section class="conteudo">
          {ativo === undefined || ativo.chave === 'inicio' ? (
            <Inicio snapshot={colecao ?? {}} />
          ) : ativo.chave === 'jogos' ? (
            <Jogos focoBusca={focoBusca} perfil={perfil} />
          ) : (
            <Placeholder modulo={ativo} />
          )}
        </section>
      </main>
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
            const chave = DESTINO_DO_ITEM[item.tipo]
            if (chave !== undefined) setSecao(chave)
            setPaleta((atual) => reduzirPaleta(atual, { tipo: 'fechar' }))
          }}
          aoFechar={() => setPaleta((atual) => reduzirPaleta(atual, { tipo: 'fechar' }))}
        />
      )}
    </>
  )
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
