import { useEffect, useState } from 'preact/hooks'
import type { ModuloDTO } from '../../shared/protocolo'
import { combinacao, decidirAtalho } from './atalhos'
import { BarraLateral } from './componentes/BarraLateral'
import { Paleta } from './componentes/Paleta'
import type { Snapshot } from './derivacoes'
import { avisosDoResumo, dispensarAviso, juntarAvisos, type Aviso } from './estado/notificacoes'
import { paletaInicial, reduzirPaleta, type ItemBusca } from './estado/paleta'
import { Inicio } from './vistas/Inicio'
import { Placeholder } from './vistas/Placeholder'

const DESTINO_DO_ITEM: Record<string, string> = {
  jogo: 'jogos',
  musica: 'musicas',
  desejo: 'desejos',
  download: 'downloads',
}

export function App() {
  const [modulos, setModulos] = useState<ModuloDTO[]>([])
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [secao, setSecao] = useState('inicio')
  const [paleta, setPaleta] = useState(paletaInicial)
  const [atalhos, setAtalhos] = useState<Record<string, string>>({})
  const [avisos, setAvisos] = useState<Aviso[]>([])
  const [perfil, setPerfil] = useState('Tuco')

  useEffect(() => {
    void (async () => {
      try {
        const lista = await window.tucoteca.chamar<ModuloDTO[]>('modulos.listar')
        setModulos(lista)
        const dados = await window.tucoteca.chamar<Snapshot>('nucleo.snapshot')
        setSnapshot(dados)
        setAvisos(avisosDoResumo(dados.sistema ?? {}))
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
        window.tucoteca.pronto({ jogos: dados.jogos?.length ?? 0 })
      } catch (falha) {
        setErro(String(falha))
      }
    })()
  }, [])

  useEffect(() => {
    const aoTeclar = (evento: KeyboardEvent) => {
      const decisao = decidirAtalho(paleta.aberta, combinacao(evento), atalhos)
      if (decisao === null) return
      evento.preventDefault()
      if (decisao.tipo === 'paleta') {
        setPaleta((atual) => reduzirPaleta(atual, { tipo: 'abrir' }))
      } else if (decisao.tipo === 'fechar') {
        setPaleta((atual) => reduzirPaleta(atual, { tipo: 'fechar' }))
      } else {
        setSecao(decisao.chave)
      }
    }
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
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

  if (!snapshot) {
    return (
      <section class="painel">
        <h1>TucoTeca</h1>
        <p>Abrindo a coleção…</p>
      </section>
    )
  }

  const ativo = modulos.find((modulo) => modulo.chave === secao) ?? modulos[0]
  return (
    <>
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
            <Inicio snapshot={snapshot} />
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
